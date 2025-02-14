import os
import shutil
import yt_dlp
import subprocess
import time  # Импортируем модуль для замера времени

# 📌 Ваша ссылка на видео
video_url = "https://www.youtube.com/watch?v=ds7Rbnh3qw0"

# 📌 Директория для загрузки видео
download_directory = os.path.expanduser("/Users/pzof/PycharmProjects/vk_vid/vids")
os.makedirs(download_directory, exist_ok=True)

# 🔍 Получаем информацию о видео перед скачиванием
print("\n🔍 Доступные форматы видео:")
with yt_dlp.YoutubeDL() as ydl:
    info_dict = ydl.extract_info(video_url, download=False)  # ⬅️ ВАЖНО: download=False
    ydl.list_formats(info_dict)  # ⬅️ Передаём info_dict, а не video_url

# 🛠 Настройки для скачивания видео с ограничением max(1080p)
ydl_opts = {
    "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/bestaudio/best",
    "merge_output_format": "mp4",  # Объединить в MP4
    "outtmpl": os.path.join(download_directory, "%(title)s.%(ext)s"),  # Название файла = название видео
}

# 📥 Скачивание видео с замером времени
print("\n📥 Начинаем скачивание...")
start_download = time.monotonic()  # Засекаем время начала загрузки
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info_dict = ydl.extract_info(video_url, download=True)
    video_filename = ydl.prepare_filename(info_dict)
end_download = time.monotonic()  # Засекаем время окончания загрузки
download_time = end_download - start_download

print(f"\n✅ Скачивание завершено за {download_time:.2f} секунд")

# ✅ Вывод информации о скачанном видео
print("\n✅ Информация о скачанном видео:")
print(f"📺 Разрешение: {info_dict.get('width')}x{info_dict.get('height')}")
print(f"🎵 Аудио битрейт: {info_dict.get('abr')} kbps")
print(f"🎞️ Кодек видео: {info_dict.get('vcodec')}")
print(f"🎶 Кодек аудио: {info_dict.get('acodec')}")
print(f"📁 Файл сохранён: {video_filename}")

# --- Дополнительный шаг: перекодировка для гарантии совместимости с Telegram ---
# Telegram рекомендуется использовать H.264 для видео и AAC для аудио в MP4 контейнере.
# Если исходное видео по каким-либо причинам имеет другие кодеки, можно выполнить перекодировку.

# Задайте имя для перекодированного файла
reencoded_filename = os.path.join(download_directory, "reencoded_" + os.path.basename(video_filename))

print("\n🛠 Перекодировка видео (если требуется) для совместимости с Telegram...")
ffmpeg_cmd = [
    "ffmpeg", "-y", "-i", video_filename,
    "-c:v", "libx264", "-preset", "fast", "-crf", "23",  # Перекодировка видео в H.264
    "-c:a", "aac", "-b:a", "128k",                        # Перекодировка аудио в AAC
    reencoded_filename
]
try:
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"✅ Перекодировка завершена. Перекодированный файл: {reencoded_filename}")
except subprocess.CalledProcessError:
    print("❌ Ошибка при перекодировке видео с помощью FFmpeg.")

# --- Проверка качества с помощью FFmpeg ---
if shutil.which("ffmpeg"):
    print("\n🛠 Анализ видео с помощью FFmpeg:")
    ffprobe_cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,codec_name",
        "-of", "csv=p=0",
        reencoded_filename  # Анализируем перекодированный файл
    ]
    try:
        ffmpeg_output = subprocess.check_output(ffprobe_cmd).decode().strip()
        print(f"🎬 FFmpeg: {ffmpeg_output}")
    except subprocess.CalledProcessError:
        print("❌ Ошибка при запуске FFmpeg.")

# --- Проверка качества с помощью MediaInfo ---
if shutil.which("mediainfo"):
    print("\n🛠 Анализ видео с помощью MediaInfo:")
    mediainfo_cmd = ["mediainfo", reencoded_filename]
    try:
        mediainfo_output = subprocess.check_output(mediainfo_cmd).decode().strip()
        print(mediainfo_output)
    except subprocess.CalledProcessError:
        print("❌ Ошибка при запуске MediaInfo.")

print("\n🎉 Готово!")