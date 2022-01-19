# pyinstaller --add-data "./youtube_icon.ico;." --onefile --windowed --icon=youtube_icon.ico --name "Downloader" youtube.pyw
# https://www.youtube.com/watch?v=WY230qkLv_8

from urllib.error import URLError
from pytube import YouTube, Stream
from pytube.exceptions import AgeRestrictedError, LiveStreamError, VideoPrivate, VideoUnavailable, PytubeError, MaxRetriesExceeded
from tkinter import INSIDE, Frame, Label, StringVar, TclError, Tk, Entry, Button, Listbox, Variable
from tkinter.filedialog import askdirectory
from tkinter.messagebox import askokcancel, showwarning
from os.path import normpath, abspath, exists, isdir, join
from threading import Thread
try: from sys import _MEIPASS
except ImportError: pass
from re import match

class Update_Thread(Thread):

    def __init__(self, downloader) -> None:
        super().__init__()
        self.downloader = downloader
    
    def get_url(self, id_or_url: str) -> str:
        found = match("$https?://www\\.", id_or_url)
        if found == None: return "https://www.youtube.com/watch?v={}".format(id_or_url)
        else: return id_or_url
    
    def run(self) -> None:
        try: self.downloader.youtube = YouTube(self.get_url(self.downloader.id_var.get()))
        except PytubeError as error: self.downloader.youtube = error

class Try_Update_Thread(Thread):

    def __init__(self, downloader) -> None:
        super().__init__()
        self.downloader = downloader
    
    def run(self) -> None:
        try: self.downloader.list_var.set(self.downloader.parse_streams(self.downloader.youtube.streams.filter(file_extension = "mp4")))
        except URLError:
            self.downloader.list_var.set([" Internet unavailable"])
            self.downloader.updating = self.downloader.after(200, self.downloader.update_downloads)
        else:
            self.downloader.after_cancel(self.downloader.updating)
            self.downloader.updating = False

class Download_Thread(Thread):

    def __init__(self, downloader, stream: Stream, path: str, file_name: str) -> None:
        super().__init__()
        self.downloader = downloader
        self.stream, self.path, self.file = stream, path, file_name
        self.daemon = True
    
    def run(self) -> None:
        length = len(self.downloader.downloads)
        self.downloader.counter_var.set("current downloads: {}".format(length if length >= 1 else "none"))
        while True:
            try: self.stream.download(self.path, self.file, skip_existing = False)
            except MaxRetriesExceeded: continue
            except URLError:
                self.downloader.downloads.remove(self)
                showwarning("No internet connection", "Please connect to the internet to download anything")
                break
            else:
                self.downloader.downloads.remove(self)
                break
        length = len(self.downloader.downloads)
        self.downloader.counter_var.set("current downloads: {}".format(length if length >= 1 else "none"))
        del self

class Downloader(Tk):

    def __init__(self) -> None:
        super().__init__()
        self.wm_title("Youtube Downloader")
        self.wm_geometry("300x250")
        self.wm_iconbitmap(self.get_resource_path("youtube_icon.ico"))
        self.wm_protocol("WM_DELETE_WINDOW", self.close_handler)
        self.minsize(300, 250)

        self.frame = Frame(self, background = "#fff")
        self.frame.place(x = 0, y = 0, relwidth = 1, relheight = 1)

        self.labels: list[Label] = []
        self.labels.append(Label(self.frame, text = "url / id", background = "#fff"))
        self.labels[-1].place(x = 10, y = 10, width = 50, height = 20, bordermode = INSIDE)

        self.id_var = StringVar(self.frame, "")
        self.id_var.trace("w", self.on_new_id)
        self.id = Entry(self.frame, textvariable = self.id_var, background = "#fcc")
        self.id.place(x = 70, y = 10, relwidth = 1, width = -80, height = 20, bordermode = INSIDE)

        self.labels.append(Label(self.frame, text = "path", background = "#fff"))
        self.labels[-1].place(x = 10, y = 40, width = 50, height = 20, bordermode = INSIDE)

        self.path_var = StringVar(self.frame, "")
        self.path_var.trace("w", self.on_new_path)
        self.path = Entry(self.frame, textvariable = self.path_var, background = "#fcc")
        self.path.place(x = 70, y = 40, relwidth = 1, width = -150, height = 20, bordermode = INSIDE)

        self.chooser = Button(self.frame, borderwidth = 1, text = "choose", background = "#fff", activebackground = "#eee", command = self.choose_path)
        self.chooser.place(relx = 1, x = -60, y = 40, width = 50, height = 20, bordermode = INSIDE)

        self.labels.append(Label(self.frame, text = "available downloads:", background = "#fff"))
        self.labels[-1].place(x = 10, y = 80, width = 120, height = 20, bordermode = INSIDE)

        self.list_var = Variable(self.frame, [])
        self.list = Listbox(self.frame, selectbackground = "#eee", selectforeground = "#000", listvariable = self.list_var)
        self.list.place(x = 10, y = 110, relwidth = 1, width = -20, relheight = 1, height = -150, bordermode = INSIDE)
        self.list.insert(-1, *["test"] * 10)

        self.counter_var = StringVar(self.frame, "current downloads: none")
        self.counter_label = Label(self.frame, textvariable = self.counter_var, background = "#fff")
        self.counter_label.place(x = 10, y = -30, rely = 1, width = -120, relwidth = 1, height = 20)

        self.downloader = Button(self.frame, borderwidth = 1, text = "download", background = "#fff", activebackground = "#eee", command = self.download)
        self.downloader.place(x = -110, relx = 1, y = -30, rely = 1, width = 100, height = 20, bordermode = INSIDE)

        self.youtube = None
        self.youtube_thread = None
        self.downloads = []
        self.updating = False
    
    def get_resource_path(self, resource: str) -> str:
        try: path = _MEIPASS
        except: path = abspath(".")
        return join(path, resource)
    
    def download(self) -> None:
        if self.list_var.get() == (" Loading...", ):
            showwarning("Loading", "Please wait until available downloads have been loaded")
            return
        elif self.list_var.get() == (" Internet unavailable", ):
            showwarning("No internet connection", "Please connect to the internet to download anything")
            return
        elif len(self.list_var.get()) >= 1 and self.list_var.get()[0].find("Invalid video id") != -1:
            if isinstance(self.youtube, AgeRestrictedError): showwarning("Invalid video id", "This video is age restricted")
            elif isinstance(self.youtube, LiveStreamError): showwarning("Invalid video id", "This video is a livestream and cannot be saved")
            elif isinstance(self.youtube, VideoPrivate): showwarning("Invalid video id", "This video is private")
            elif isinstance(self.youtube, VideoUnavailable): showwarning("Invalid video id", "This video is unavailable")
            else: showwarning("Invalid video id", "Please enter a valid video id")
            return
        path = self.path_var.get()
        if not(self.validate_path(path)):
            showwarning("Invalid path", "Please choose another path to save your file")
            return
        path = abspath(normpath(path))
        try: selection: list[str] = self.list.selection_get().split(", ")
        except TclError:
            showwarning("No selection", "Please select a download")
            return
        if selection[0] == " video & audio":
            info = {"mime_type": "video/mp4", "resolution": selection[1], "fps": int(selection[2][:-3]), "abr": selection[3]}
        elif selection[0] == " video":
            info = {"mime_type": "video/mp4", "resolution": selection[1], "fps": int(selection[2][:-3])}
        elif selection[0] == " audio":
            info = {"mime_type": "audio/mp4", "abr": selection[1]}
        try: stream: Stream = self.youtube.streams.filter(**info)[-1]
        except URLError:
            showwarning("No internet connection", "Please connect to the internet to download anything")
            return
        if exists(normpath(path + "/" + stream.default_filename)):
            answer = askokcancel("Override file", "The file to download does already exist in the selected folder.\nDo you want to override it?")
            if not(answer): return
        download = Download_Thread(self, stream, path, stream.default_filename)
        self.downloads.append(download)
        download.start()

    def choose_path(self) -> None:
        dir = askdirectory(mustexist = True)
        if not(dir.strip() == "" or dir == None):
            self.path_var.set(dir)
    
    def on_new_id(self, *_) -> None:
        if self.youtube_thread != None:
            del self.youtube_thread
            self.youtube_thread = None
        self.youtube_thread = Update_Thread(self)
        self.youtube_thread.start()
        self.list_var.set([" Loading..."])
    
    def parse_streams(self, streams: list[Stream]) -> list[str]:
        result: list[str] = []
        for stream in streams:
            if stream.is_progressive:
                info = " video & audio, {}, {}fps, {}, {}byte".format(stream.resolution, stream.fps, stream.abr, stream.filesize_approx)
            elif stream.includes_video_track:
                info = " video, {}, {}fps, {}byte".format(stream.resolution, stream.fps, stream.filesize_approx)
            elif stream.includes_audio_track:
                info = " audio, {}, {}byte".format(stream.abr, stream.filesize_approx)
            result.append(info)
        return result
    
    def on_new_path(self, *_) -> None:
        if not(self.validate_path(self.path_var.get())):
            self.path.configure(background = "#fcc")
        else: self.path.configure(background = "#fff")
        
    def validate_path(self, path: str) -> bool:
        if path.strip() == "": return False
        path = abspath(normpath(path))
        if exists(path) and isdir(path):
            return True
        else: return False
    
    def close_handler(self) -> None:
        if len(self.downloads) >= 1:
            answer = askokcancel("Download running", "{} download{} still running.\nDo you want to quit anyway?".format(len(self.downloads), "s are" if len(self.downloads) >= 2 else " is"))
            if not(answer): return
            for download in self.downloads: del download
        self.quit()
        self.destroy()
    
    def update_downloads(self) -> None:
        if self.updating == False: return
        if type(self.youtube) != YouTube: return
        Try_Update_Thread(self).start()

    def get_youtube(self) -> YouTube | PytubeError:
        return self._youtube
    
    def set_youtube(self, value: YouTube | PytubeError) -> None:
        if type(value) == YouTube:
            try: self.list_var.set(self.parse_streams(value.streams.filter(file_extension = "mp4")))
            except URLError:
                self.list_var.set([" Internet unavailable"])
                self.updating = self.after(200, self.update_downloads)
            self.id.configure(background = "#fff")
        else:
            if isinstance(value, AgeRestrictedError): self.list_var.set([" Invalid video id: Video is age restricted"])
            elif isinstance(value, LiveStreamError): self.list_var.set([" Invalid video id: Video is a livestream"])
            elif isinstance(value, VideoPrivate): self.list_var.set([" Invalid video id: Video is private"])
            elif isinstance(value, VideoUnavailable): self.list_var.set([" Invalid video id: Video is unavailable"])
            else: self.list_var.set([" Invalid video id"])
            self.id.configure(background = "#fcc")
        self._youtube = value

    youtube = property(get_youtube, set_youtube)

def print_streams(streams: list[Stream]) -> None:
    row = "-------|------------|------------|------------|-------------"
    print("{:^7}|{:^12}|{:^12}|{:^12}|{:^13}".format("index", "type", "resolution", "fps/abr", "progressive"))
    for i in range(len(streams)):
        print(row)
        fps = str(streams[i].fps) + "fps" if streams[i].type == "video" else streams[i].abr
        print("{:^7}|{:^12}|{:^12}|{:^12}|{:^13}".format(i, streams[i].mime_type, str(streams[i].resolution), fps, str(streams[i].is_progressive)))

downloader = Downloader()
downloader.mainloop()
