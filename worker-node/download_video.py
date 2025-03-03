import yt_dlp
import os

def download_video(video_url):
    download_directory = os.path.expanduser("/tmp/vids")
    os.makedirs(download_directory, exist_ok=True)
    