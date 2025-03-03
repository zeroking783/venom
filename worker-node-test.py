import os
import shutil
import yt_dlp
import subprocess
import time  # Импортируем модуль для замера времени

# 📌 Ваша ссылка на видео
video_url = "https://www.youtube.com/watch?v=ds7Rbnh3qw0"

# 📌 Директория для загрузки видео
download_directory = os.path.expanduser("/tmp/vids")
os.makedirs(download_directory, exist_ok=True)

# 🔍 Получаем информацию о видео перед скачиванием
print("\n🔍 Доступные форматы видео:")
with yt_dlp.YoutubeDL() as ydl:
    info_dict = ydl.extract_info(video_url, download=False)  # ⬅️ ВАЖНО: download=False
    ydl.list_formats(info_dict)  # ⬅️ Передаём info_dict, а не video_url

