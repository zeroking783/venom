from confluent_kafka import Producer
import os
from aiogram import Bot, Dispatcher, types
from dotenv import load_dotenv
import asyncio
import logging
import sys
import json

load_dotenv()

# Настроим логирование
LOG_FILE = "app_logs.log"

# Настроим logging для записи логов в файл
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(LOG_FILE),
                        logging.StreamHandler(sys.stdout)  # Также вывод в консоль
                    ])

# Перехватываем print для записи в файл
sys.stdout = open(LOG_FILE, "a")
sys.stderr = sys.stdout

# Настроим Telegram Bot с aiogram
BOT_API_TOKEN = os.getenv('BOT_API_TOKEN')  # Токен бота
bot = Bot(token=BOT_API_TOKEN)
dp = Dispatcher()

# Настроим Kafka Producer
ADRESS_KAFKA_CLUSTER = os.getenv('ADRESS_KAFKA_CLUSTER')
KAFKA_USERNAME = os.getenv('KAFKA_USERNAME')
KAFKA_PASSWORD = os.getenv('KAFKA_PASSWORD')

config = {
    'bootstrap.servers': ADRESS_KAFKA_CLUSTER,  # Укажи свой адрес брокера Kafka
    'security.protocol': 'SASL_PLAINTEXT',
    'sasl.mechanism': 'SCRAM-SHA-256',  # или другой, если настроено иначе
    'sasl.username': KAFKA_USERNAME,  # Имя пользователя
    'sasl.password': KAFKA_PASSWORD,  # Пароль пользователя
}

producer = Producer(config)

def send_message(topic, message):
    producer.produce(topic, value=message.encode('utf-8'))
    producer.flush()

def serialize_data(data):
    return json.dumps(data)

# send_message('test_topic', 'Hello Kafka World!')

@dp.message()
async def send_to_kafka(message: types.Message):
    user_message = message.text
    user_id = message.from_user.user_id
    username = message.from_user.username
    logging.info(f"Received message: {user_message} from {user_id} with username {username}")  # Логируем входящие сообщения


    # Формируем сообщение для отправки в Kafka
    kafka_message = serialize_data({"user_id": user_id, "message": user_message, "username": username})

    try:
        # Отправляем сообщение в Kafka в топик "video-download-links"
        send_message('video-download-links', kafka_message)

        # Ответим пользователю, что сообщение принято
        await message.reply("Ваше сообщение отправлено в Kafka!")
    except Exception as e:
        # logging.error(f"Error sending message to Kafka: {str(e)}")
        logging.error(f"Error sending message to Kafka: {str(e)}")
        await message.reply("Произошла ошибка при отправке сообщения в Kafka.")

async def main():
    # Запуск polling с передачей bot
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.info("Starting the bot...")
    asyncio.run(main())
