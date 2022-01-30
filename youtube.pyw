# pyinstaller --add-data "./youtube_icon.ico;." --onefile --windowed --icon=youtube_icon.ico --name "Downloader" youtube.pyw
# example video link: https://www.youtube.com/watch?v=WY230qkLv_8

from typing import Literal
from urllib.error import URLError
from pytube import YouTube, Stream
from pytube.exceptions import AgeRestrictedError, LiveStreamError, VideoPrivate, VideoUnavailable, PytubeError, MaxRetriesExceeded
from tkinter import INSIDE, Frame, Label, StringVar, TclError, Tk, Entry, Button, Listbox, Variable
from tkinter.filedialog import asksaveasfilename
from tkinter.messagebox import askokcancel, showwarning
from os.path import normpath, abspath, exists, join, isfile, split
from time import sleep
from threading import Thread
try: from sys import _MEIPASS
except ImportError: pass
from re import match

class Update_Thread(Thread):
    # update the youtube object, when new url/id was entered
    # important for non-blocking funcionality

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
    # try updating available downloads every 0.2s, if no connection was provided
    # URLError is not throws on creation of YouTube object

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
    # downloading the requested stream

    def __init__(self, downloader) -> None:
        super().__init__()
        self.downloader = downloader
        # set as daemon to quit on window deletion
        self.daemon = True
    
    def run(self) -> None:
        while True:
            if len(self.downloader.downloads) >= 1:
                download = self.downloader.downloads[0]
                length = len(self.downloader.downloads)
                self.downloader.counter_var.set("downloads: {}".format(length if length >= 1 else "none"))
                stream, path, file = download
                try: stream.download(path, file, skip_existing = False, )
                except URLError:
                    self.downloader.downloads.remove(download)
                    showwarning("No internet connection", "Please connect to the internet to download anything")
                else: self.downloader.downloads.remove(download)
                length = len(self.downloader.downloads)
                self.downloader.counter_var.set("downloads: {}".format(length if length >= 1 else "none"))
            sleep(0.2)

class Downloader(Tk):
    # ui for downloading

    def __init__(self) -> None:
        super().__init__()
        # set initials etc.
        self.wm_title("Youtube Downloader")
        self.wm_geometry("300x250")
        self.wm_iconbitmap(self.get_resource_path("youtube_icon.ico"))
        self.wm_protocol("WM_DELETE_WINDOW", self.close_handler)
        self.minsize(300, 250)

        # main frame for setting background color
        self.frame = Frame(self, background = "#fff")
        self.frame.place(x = 0, y = 0, relwidth = 1, relheight = 1)

        # anonymous label; will never bee used again
        Label(self.frame, text = "url / id", background = "#fff").place(x = 10, y = 10, width = 50, height = 20, bordermode = INSIDE)

        # input for url / id
        self.id_var = StringVar(self.frame, "")
        self.id_var.trace("w", self.on_new_id)
        self.id = Entry(self.frame, textvariable = self.id_var, background = "#fcc")
        self.id.place(x = 70, y = 10, relwidth = 1, width = -80, height = 20, bordermode = INSIDE)

        Label(self.frame, text = "available downloads:", background = "#fff").place(x = 10, y = 45, width = 120, height = 20, bordermode = INSIDE)

        # list of available downloads
        self.list_var = Variable(self.frame, [])
        self.list = Listbox(self.frame, selectbackground = "#eee", selectforeground = "#000", listvariable = self.list_var)
        self.list.place(x = 10, y = 70, relwidth = 1, width = -20, relheight = 1, height = -110, bordermode = INSIDE)
        self.list.insert(-1, *["test"] * 10)

        # counter label for currently running downloads
        self.counter_var = StringVar(self.frame, "downloads: none")
        self.counter_label = Label(self.frame, textvariable = self.counter_var, background = "#fff")
        self.counter_label.place(x = 10, y = -30, rely = 1, width = -120, relwidth = 1, height = 20)

        # download button
        self.downloader = Button(self.frame, borderwidth = 1, text = "download", background = "#fff", activebackground = "#eee", command = self.download)
        self.downloader.place(x = -110, relx = 1, y = -30, rely = 1, width = 100, height = 20, bordermode = INSIDE)

        # variables for handling downloads etc.
        self.youtube = None
        self.youtube_thread = None
        self.downloads = []
        self.downloader = Download_Thread(self)
        self.updating = False
    
    def mainloop(self, *args, **kwargs) -> None:
        self.downloader.start()
        return super().mainloop(*args, **kwargs)
    
    def get_resource_path(self, resource: str) -> str:
        # get resource path of youtube_icon.ico -> stored in temporyra directory _MEIPASS at runtime
        try: path = _MEIPASS # exists just when running as exe
        except: path = abspath(".")
        return join(path, resource)
    
    def download(self) -> None:
        # download stuff when pressing download button

        # errors visible in available downloads:
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

        # error: no selection
        try: selection: list[str] = self.list.selection_get().split(", ")
        except TclError:
            showwarning("No selection", "Please select a download")
            return
        
        # select the correct stream form all available streams
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
        
        # get valid file
        path = self.choose_path(stream.default_filename)
        if path == None: return
        elif path == False:
            showwarning("Invalid path", "Please choose another path to save your file")
            return
        
        # download
        self.downloads.append((stream, *split(path)))

    def choose_path(self, default_filename: str) -> str | Literal[False] | None:
        file = asksaveasfilename(defaultextension = "mp4", initialfile = default_filename)
        if not(file): return None
        if not(self.validate_path(file)):
            return False
        path = abspath(normpath(file))
        return path
    
    def on_new_id(self, *_) -> None:
        # start updating available downloads on new url / id
        if self.youtube_thread != None:
            del self.youtube_thread
            self.youtube_thread = None
        self.youtube_thread = Update_Thread(self)
        self.youtube_thread.start()
        self.list_var.set([" Loading..."])
    
    def parse_streams(self, streams: list[Stream]) -> list[str]:
        # make list of strings containing all important information from streams to display in available downloads
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
        
    def validate_path(self, path: str) -> bool:
        # validate the given path
        if path.strip() == "": return False
        path = abspath(normpath(path))
        if (not(exists(path)) or isfile(path)) and path.rsplit(".", maxsplit = 1)[-1] == "mp4":
            return True
        else: return False
    
    def close_handler(self) -> None:
        # on close: check if downloads are running
        if len(self.downloads) >= 1:
            answer = askokcancel("Download running", "{} download{} still running.\nDo you want to quit anyway?".format(len(self.downloads), "s are" if len(self.downloads) >= 2 else " is"))
            # if ok: cancel all downloads
            if not(answer): return
            self.downloads.clear()
        self.quit()
        self.destroy()
    
    def update_downloads(self) -> None:
        # update available downloads on missing internet connection
        if self.updating == False: return
        if type(self.youtube) != YouTube: return
        Try_Update_Thread(self).start()

    def get_youtube(self) -> YouTube | PytubeError:
        return self._youtube
    
    def set_youtube(self, value: YouTube | PytubeError) -> None:
        # set new youtube object
        if type(value) == YouTube:
            # update available streams in available downloads
            try: self.list_var.set(self.parse_streams(value.streams.filter(file_extension = "mp4")))
            except URLError:
                # if no connection: try later
                self.list_var.set([" Internet unavailable"])
                self.updating = self.after(200, self.update_downloads)
            self.id.configure(background = "#fff")
        else:
            # handle errors
            if isinstance(value, AgeRestrictedError): self.list_var.set([" Invalid video id: Video is age restricted"])
            elif isinstance(value, LiveStreamError): self.list_var.set([" Invalid video id: Video is a livestream"])
            elif isinstance(value, VideoPrivate): self.list_var.set([" Invalid video id: Video is private"])
            elif isinstance(value, VideoUnavailable): self.list_var.set([" Invalid video id: Video is unavailable"])
            else: self.list_var.set([" Invalid video id"])
            self.id.configure(background = "#fcc")
        self._youtube = value

    youtube = property(get_youtube, set_youtube)

downloader = Downloader()
downloader.mainloop()
