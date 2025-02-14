import os
import shutil
import time
import asyncio
import tempfile
import matplotlib.pyplot as plt

import yt_dlp
from telethon import TelegramClient

# =====================================================================
# ПАРАМЕТРЫ ДЛЯ НАСТРОЙКИ
# =====================================================================

VIDEO_URLS = [
    "https://www.youtube.com/watch?v=kk6Rir_-sJ4",
    "https://www.youtube.com/watch?v=K9nu7Uq9DFI",
    "https://www.youtube.com/watch?v=2AMBaGFIUwk",
    "https://www.youtube.com/watch?v=6kzdYO9H6Xo",
    "https://www.youtube.com/watch?v=gBm5CDF3pPc"
]

BASE_DOWNLOAD_DIRECTORY = os.path.expanduser("~/PycharmProjects/vk_vid/vids/benchmark")
GRAPHICS_DIRECTORY = os.path.expanduser("~/PycharmProjects/vk_vid/graphics/")
os.makedirs(BASE_DOWNLOAD_DIRECTORY, exist_ok=True)
os.makedirs(GRAPHICS_DIRECTORY, exist_ok=True)

API_ID =
API_HASH = ''
SESSION_NAME = 'benchmark_session'
CHAT = 566646763  # ID или @username

CONCURRENCY_LEVELS = [1, 2,3,4, 5,6]
ITERATIONS = 3  # Количество повторов для каждого уровня параллелизма
# CONCURRENCY_LEVELS = [1, 2,3,4, 5]
# ITERATIONS = 3  # Количество повторов для каждого ур

# =====================================================================
# 1. Извлечение МЕТАДАННЫХ (без скачивания)
# =====================================================================

def get_video_info(video_url: str):
    """
    Получаем информацию о видео (в том числе filesize_approx) без скачивания.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=False)
    return info_dict


# =====================================================================
# 2. Скачивание видео (MP4) с yt-dlp
# =====================================================================

def download_video(video_url: str, task_dir: str):
    """
    Скачивает видео (лучший mp4 до 1080p) в task_dir.
    Возвращает (video_filename, info_dict).
    """
    print(f"[download_video] Начинается скачивание видео: {video_url}")
    ydl_opts = {
        "format": "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/mp4",
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(task_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        video_filename = ydl.prepare_filename(info_dict)
    print(f"[download_video] Скачивание завершено. Файл: {video_filename}")
    return video_filename, info_dict


# =====================================================================
# 3. Основная функция обработки одного видео:
#    - получить метаданные
#    - скачать
#    - измерить размер, вычислить скорость
#    - загрузить в Telegram
#    - измерить время удаления
# =====================================================================

async def process_video(task_id: str, video_url: str, base_dir: str,
                        client: TelegramClient, chat) -> dict:
    """
    Возвращает словарь с метриками:
      - metadata_time
      - download_time, upload_time, total_time
      - remove_time (время удаления локальных файлов)
      - approx_size_mb, actual_size_mb
      - download_throughput_mb_s, upload_throughput_mb_s
      - ошибка (None если нет)
    """
    print(f"[Task {task_id}] Создаём временную папку для задачи.")
    task_dir = tempfile.mkdtemp(prefix=f"task_{task_id}_", dir=base_dir)
    result = {"task_id": task_id}
    start_total = time.monotonic()

    # -----------------------------------------------
    # 3.1 Извлечение метаданных
    # -----------------------------------------------
    print(f"[Task {task_id}] Извлекаем метаданные для видео: {video_url}")
    start_md = time.monotonic()
    try:
        info_dict_meta = await asyncio.to_thread(get_video_info, video_url)
    except Exception as e:
        print(f"[Task {task_id}] Ошибка при получении метаданных: {e}")
        shutil.rmtree(task_dir)
        result["error"] = str(e)
        return None
    end_md = time.monotonic()
    result["metadata_time"] = end_md - start_md
    print(f"[Task {task_id}] Метаданные получены за {result['metadata_time']:.2f} сек.")

    # Предполагаемый размер (может быть более точным при наличии 'filesize' или 'filesize_approx')
    approximate_size_bytes = info_dict_meta.get("filesize_approx") or info_dict_meta.get("filesize") or 0
    result["approx_size_mb"] = approximate_size_bytes / (1024 * 1024)

    # -----------------------------------------------
    # 3.2 Скачивание видео
    # -----------------------------------------------
    print(f"[Task {task_id}] Начало скачивания видео: {video_url}")
    start_dl = time.monotonic()
    try:
        video_filename, info_dict = await asyncio.to_thread(download_video, video_url, task_dir)
    except Exception as e:
        print(f"[Task {task_id}] Ошибка при скачивании: {e}")
        shutil.rmtree(task_dir)
        result["error"] = str(e)
        return None
    end_dl = time.monotonic()
    result["download_time"] = end_dl - start_dl
    print(f"[Task {task_id}] Скачивание заняло {result['download_time']:.2f} сек.")

    # Определяем фактический размер скачанного файла
    if os.path.exists(video_filename):
        file_size_bytes = os.path.getsize(video_filename)
        result["actual_size_mb"] = file_size_bytes / (1024 * 1024)
        print(f"[Task {task_id}] Фактический размер файла: {result['actual_size_mb']:.2f} MB")
    else:
        result["actual_size_mb"] = 0

    # Вычисляем пропускную способность для скачивания (MB/s), если время > 0
    if result["download_time"] > 0 and result["actual_size_mb"] > 0:
        result["download_throughput_mb_s"] = result["actual_size_mb"] / result["download_time"]
        print(f"[Task {task_id}] Скорость скачивания: {result['download_throughput_mb_s']:.2f} MB/s")
    else:
        result["download_throughput_mb_s"] = None

    # -----------------------------------------------
    # 3.3 Загрузка в Telegram
    # -----------------------------------------------
    print(f"[Task {task_id}] Начало загрузки в Telegram.")
    start_up = time.monotonic()
    try:
        await client.send_file(
            chat,
            video_filename,
            caption=f"Задача: {task_id}\nВидео: {video_url}",
            progress_callback=None
        )
    except Exception as e:
        print(f"[Task {task_id}] Ошибка при загрузке в Telegram: {e}")
        shutil.rmtree(task_dir)
        result["error"] = str(e)
        return None
    end_up = time.monotonic()
    result["upload_time"] = end_up - start_up
    print(f"[Task {task_id}] Загрузка заняла {result['upload_time']:.2f} сек.")

    # Вычисляем пропускную способность для загрузки (MB/s)
    if result["upload_time"] > 0 and result["actual_size_mb"] > 0:
        result["upload_throughput_mb_s"] = result["actual_size_mb"] / result["upload_time"]
        print(f"[Task {task_id}] Скорость загрузки: {result['upload_throughput_mb_s']:.2f} MB/s")
    else:
        result["upload_throughput_mb_s"] = None

    # -----------------------------------------------
    # 3.4 Удаление временных файлов
    # -----------------------------------------------
    start_remove = time.monotonic()
    shutil.rmtree(task_dir)
    end_remove = time.monotonic()
    remove_time = end_remove - start_remove
    result["remove_time"] = remove_time
    print(f"[Task {task_id}] Удаление заняло {remove_time:.2f} сек.")

    # -----------------------------------------------
    # 3.5 Завершаем задачу
    # -----------------------------------------------
    end_total = time.monotonic()
    result["total_time"] = end_total - start_total
    print(f"[Task {task_id}] Завершено. Общее время: {result['total_time']:.2f} сек.")

    return result


# =====================================================================
# 4. Обёртка с семафором (параллелизм)
# =====================================================================
async def process_video_with_semaphore(
        semaphore: asyncio.Semaphore,
        task_id: str,
        video_url: str,
        base_dir: str,
        client: TelegramClient,
        chat
) -> dict:
    print(f"[Task {task_id}] Ожидание разрешения (semaphore)...")
    async with semaphore:
        print(f"[Task {task_id}] Получено разрешение (semaphore).")
        return await process_video(task_id, video_url, base_dir, client, chat)


# =====================================================================
# 5. Запуск серии задач для набора видео при заданном concurrency
# =====================================================================
async def run_benchmark_for_videos(
        concurrency: int,
        video_urls: list,
        base_dir: str,
        client: TelegramClient,
        chat,
        iterations: int = 1
) -> dict:
    """
    Для concurrency и набора видео выполняем <iterations> итераций.
    Собираем время, размеры, пропускную способность, ошибки.
    """
    all_results = []
    error_count = 0

    for i in range(iterations):
        print(f"[Benchmark] Итерация {i + 1}/{iterations} при concurrency={concurrency}.")
        semaphore = asyncio.Semaphore(concurrency)
        tasks = []
        for idx, video_url in enumerate(video_urls):
            task_id = f"{concurrency}_{i}_{idx}"
            print(f"[Benchmark] Создаётся задача {task_id} для {video_url}")
            tasks.append(
                process_video_with_semaphore(semaphore, task_id, video_url, base_dir, client, chat)
            )
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                print(f"[Benchmark] Получено исключение: {res}")
                error_count += 1
        # Фильтруем None и исключения, оставляя валидные словари
        valid_results = [r for r in results if isinstance(r, dict) and r.get("error") is None]
        all_results.extend(valid_results)

    # Если у нас есть результаты, усредняем
    n = len(all_results)
    if n > 0:
        avg_metadata_time = sum(r["metadata_time"] for r in all_results) / n
        avg_download_time = sum(r["download_time"] for r in all_results) / n
        avg_upload_time = sum(r["upload_time"] for r in all_results) / n
        avg_remove_time = sum(r["remove_time"] for r in all_results) / n
        avg_total_time = sum(r["total_time"] for r in all_results) / n
        # Файловый размер
        sizes = [r["actual_size_mb"] for r in all_results if r["actual_size_mb"] is not None]
        avg_size_mb = sum(sizes) / len(sizes) if sizes else 0
        # Пропускная способность
        dl_speeds = [r["download_throughput_mb_s"] for r in all_results if r["download_throughput_mb_s"]]
        up_speeds = [r["upload_throughput_mb_s"] for r in all_results if r["upload_throughput_mb_s"]]
        avg_download_speed = sum(dl_speeds) / len(dl_speeds) if dl_speeds else 0
        avg_upload_speed = sum(up_speeds) / len(up_speeds) if up_speeds else 0
    else:
        avg_metadata_time = avg_download_time = avg_upload_time = avg_remove_time = avg_total_time = None
        avg_size_mb = 0
        avg_download_speed = 0
        avg_upload_speed = 0

    return {
        "concurrency": concurrency,
        "avg_metadata_time": avg_metadata_time,
        "avg_download_time": avg_download_time,
        "avg_upload_time": avg_upload_time,
        "avg_remove_time": avg_remove_time,
        "avg_total_time": avg_total_time,
        "avg_size_mb": avg_size_mb,
        "avg_download_speed": avg_download_speed,
        "avg_upload_speed": avg_upload_speed,
        "num_tasks": n,
        "error_count": error_count
    }


# =====================================================================
# 6. Сводное усреднение по всем экспериментам (всем concurrency)
# =====================================================================
def compute_global_averages(benchmark_results: list) -> dict:
    """
    По всей совокупности результатов (разные concurrency) считаем
    взвешенные средние метрики.
    """
    if not benchmark_results:
        return {}

    # Суммарное количество задач
    total_tasks = sum(r["num_tasks"] for r in benchmark_results)
    if total_tasks == 0:
        return {}

    # Накопительные суммы для взвешенного среднего
    sum_metadata_time = 0.0
    sum_download_time = 0.0
    sum_upload_time = 0.0
    sum_remove_time = 0.0
    sum_total_time = 0.0

    sum_size = 0.0
    sum_download_speed = 0.0
    sum_upload_speed = 0.0
    sum_errors = 0

    for r in benchmark_results:
        n = r["num_tasks"]
        # Для времени берём среднюю * n, чтобы потом делить на суммарное количество задач
        if r["avg_metadata_time"] is not None:
            sum_metadata_time += r["avg_metadata_time"] * n
        if r["avg_download_time"] is not None:
            sum_download_time += r["avg_download_time"] * n
        if r["avg_upload_time"] is not None:
            sum_upload_time += r["avg_upload_time"] * n
        if r["avg_remove_time"] is not None:
            sum_remove_time += r["avg_remove_time"] * n
        if r["avg_total_time"] is not None:
            sum_total_time += r["avg_total_time"] * n

        sum_size += r["avg_size_mb"] * n
        sum_download_speed += r["avg_download_speed"] * n
        sum_upload_speed += r["avg_upload_speed"] * n
        sum_errors += r["error_count"]

    return {
        "global_avg_metadata_time": sum_metadata_time / total_tasks,
        "global_avg_download_time": sum_download_time / total_tasks,
        "global_avg_upload_time": sum_upload_time / total_tasks,
        "global_avg_remove_time": sum_remove_time / total_tasks,
        "global_avg_total_time": sum_total_time / total_tasks,
        "global_avg_size_mb": sum_size / total_tasks,
        "global_avg_download_speed": sum_download_speed / total_tasks,
        "global_avg_upload_speed": sum_upload_speed / total_tasks,
        "global_error_count": sum_errors,
        "global_num_tasks": total_tasks
    }


# =====================================================================
# Основная функция: поднимаем Telethon-клиент, проводим замеры, строим графики
# =====================================================================
async def main():
    print("[Main] Запуск Telethon-клиента...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    print("[Main] Telethon: клиент запущен и авторизован.")

    benchmark_results = []
    for concurrency in CONCURRENCY_LEVELS:
        print(f"\n[Main] Запуск теста для concurrency={concurrency} (итераций={ITERATIONS})...")
        result = await run_benchmark_for_videos(
            concurrency, VIDEO_URLS, BASE_DOWNLOAD_DIRECTORY,
            client, CHAT, ITERATIONS
        )
        if result["num_tasks"] > 0:
            benchmark_results.append(result)
            print(f"[Main] Результаты (concurrency={concurrency}):")
            print(f"  Среднее время (метаданные): {result['avg_metadata_time']:.2f} с")
            print(f"  Среднее время (скачивание): {result['avg_download_time']:.2f} с")
            print(f"  Среднее время (загрузка): {result['avg_upload_time']:.2f} с")
            print(f"  Среднее время (удаление): {result['avg_remove_time']:.2f} с")
            print(f"  Среднее время (всё вместе): {result['avg_total_time']:.2f} с (на {result['num_tasks']} задач)")
            print(f"  Средний размер файла: {result['avg_size_mb']:.2f} MB")
            print(f"  Средняя скорость скачивания: {result['avg_download_speed']:.2f} MB/s")
            print(f"  Средняя скорость загрузки: {result['avg_upload_speed']:.2f} MB/s")
            print(f"  Ошибок: {result['error_count']}")
        else:
            print(f"[Main] Нет валидных результатов для concurrency={concurrency}. Ошибок: {result['error_count']}")

    await client.disconnect()
    print("[Main] Telethon: клиент отключён.")

    # -----------------------------------------------------------------
    # Если нечего отображать – выходим
    if not benchmark_results:
        print("[Main] Нет данных для построения графиков.")
        return

    # -----------------------------------------------------------------
    # Усреднённые метрики по ВСЕМ экспериментам
    # -----------------------------------------------------------------
    global_avg = compute_global_averages(benchmark_results)
    if global_avg and "global_num_tasks" in global_avg and global_avg["global_num_tasks"] > 0:
        print("\n===== Сводная статистика по всем экспериментам =====")
        print(f"Всего задач: {global_avg['global_num_tasks']}")
        print(f"Ошибок: {global_avg['global_error_count']}")
        print(f"Среднее время (метаданные): {global_avg['global_avg_metadata_time']:.2f} с")
        print(f"Среднее время (скачивание): {global_avg['global_avg_download_time']:.2f} с")
        print(f"Среднее время (загрузка): {global_avg['global_avg_upload_time']:.2f} с")
        print(f"Среднее время (удаление): {global_avg['global_avg_remove_time']:.2f} с")
        print(f"Среднее время (общее): {global_avg['global_avg_total_time']:.2f} с")
        print(f"Средний размер файла: {global_avg['global_avg_size_mb']:.2f} MB")
        print(f"Средняя скорость скачивания: {global_avg['global_avg_download_speed']:.2f} MB/s")
        print(f"Средняя скорость загрузки: {global_avg['global_avg_upload_speed']:.2f} MB/s")

    # -----------------------------------------------------------------
    # Подготовка массивов для графиков
    # -----------------------------------------------------------------
    concs = [r["concurrency"] for r in benchmark_results]
    meta_times = [r["avg_metadata_time"] or 0 for r in benchmark_results]
    dl_times = [r["avg_download_time"] or 0 for r in benchmark_results]
    up_times = [r["avg_upload_time"] or 0 for r in benchmark_results]
    remove_times = [r["avg_remove_time"] or 0 for r in benchmark_results]
    tot_times = [r["avg_total_time"] or 0 for r in benchmark_results]
    sizes_mb = [r["avg_size_mb"] or 0 for r in benchmark_results]
    dl_speeds = [r["avg_download_speed"] or 0 for r in benchmark_results]
    up_speeds = [r["avg_upload_speed"] or 0 for r in benchmark_results]
    errors = [r["error_count"] for r in benchmark_results]

    # -----------------------------------------------------------------
    # 7.1 График: времена по этапам
    # -----------------------------------------------------------------
    plt.figure(figsize=(10, 6))
    plt.plot(concs, meta_times, marker='o', label='Метаданные')
    plt.plot(concs, dl_times, marker='o', label='Скачивание')
    plt.plot(concs, up_times, marker='o', label='Загрузка')
    plt.plot(concs, remove_times, marker='o', label='Удаление')
    plt.plot(concs, tot_times, marker='o', label='Общее')
    plt.xlabel('Уровень параллелизма')
    plt.ylabel('Время (среднее, секунды)')
    plt.title('Время выполнения этапов vs параллелизм')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPHICS_DIRECTORY, "benchmark_stage_times.png"))
    plt.show()

    # -----------------------------------------------------------------
    # 7.2 График: средний размер скачанного файла
    # -----------------------------------------------------------------
    plt.figure(figsize=(6, 4))
    plt.plot(concs, sizes_mb, marker='o', color='green')
    plt.xlabel('Уровень параллелизма')
    plt.ylabel('Средний размер файла (MB)')
    plt.title('Средний размер итоговых видео')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPHICS_DIRECTORY, "benchmark_file_sizes.png"))
    plt.show()

    # -----------------------------------------------------------------
    # 7.3 График: пропускная способность (MB/s)
    # -----------------------------------------------------------------
    plt.figure(figsize=(8, 5))
    plt.plot(concs, dl_speeds, marker='o', label='Скачивание (MB/s)', color='blue')
    plt.plot(concs, up_speeds, marker='o', label='Загрузка (MB/s)', color='red')
    plt.xlabel('Уровень параллелизма')
    plt.ylabel('Скорость (MB/s)')
    plt.title('Пропускная способность (throughput) vs параллелизм')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPHICS_DIRECTORY, "benchmark_throughput.png"))
    plt.show()

    # -----------------------------------------------------------------
    # 7.4 График: число ошибок
    # -----------------------------------------------------------------
    plt.figure(figsize=(6, 4))
    plt.bar(concs, errors, color='orange', width=0.5)
    plt.xlabel('Уровень параллелизма')
    plt.ylabel('Число ошибок')
    plt.title('Число ошибок (ConnectionResetError и пр.)')
    plt.grid(True, axis='y')
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPHICS_DIRECTORY, "benchmark_errors.png"))
    plt.show()


if __name__ == '__main__':
    asyncio.run(main())