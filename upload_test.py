import asyncio
import time
from telethon import TelegramClient

# Замените на корректные данные, полученные на my.telegram.org
api_id = 10580667  # Ваш api_id
api_hash = 'b16d970f853de6894bf3eea844245d78'  # Ваш api_hash

# Имя сессии – файл, в котором хранится информация авторизации
session_name = 'user_session'

# Идентификатор или username чата, куда нужно отправить видео
chat = 566646763  # Можно указать id (как число) или username (например, '@username')

# Путь к видеофайлу
video_path = '/Users/pzof/PycharmProjects/vk_vid/vids/papa.mp4'


def progress_callback(current, total):
    percent = current / total * 100
    print(f'Загружено: {current} из {total} байт ({percent:.2f}%)')


async def send_video(client):
    # Засекаем время начала загрузки
    start_time = time.monotonic()

    # Отправляем видео с указанием функции обратного вызова для логирования прогресса
    result = await client.send_file(
        chat,
        video_path,
        caption='Видео отправлено юзер-ботом',
        progress_callback=progress_callback
    )

    # Засекаем время после успешной загрузки
    elapsed_time = time.monotonic() - start_time
    print(f"Видео загружено успешно. Время загрузки: {elapsed_time:.2f} секунд")
    return result


async def main():
    client = TelegramClient(session_name, api_id, api_hash)

    # Запускаем клиента и проводим авторизацию (при первом запуске может потребоваться ввод кода)
    await client.start()
    await send_video(client)

    # Завершаем сессию, если больше не планируете использовать клиента
    await client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())