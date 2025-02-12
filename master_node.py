from confluent_kafka import Producer
import os
from aiogram import Bot, Dispatcher, types
from dotenv import load_dotenv
import asyncio
import json

load_dotenv()

# Настроим Telegram Bot с aiogram
BOT_API_TOKEN = os.getenv('BOT_API_TOKEN')  # Токен бота
bot = Bot(token=BOT_API_TOKEN)
dp = Dispatcher()

# Настроим Kafka Producer
KAFKA_BROKER = os.getenv('KAFKA_BROKER')
config = {
    'bootstrap.servers': KAFKA_BROKER,
    'client.id': 'master_node_producer'
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
    username = message.from_user.username
    print(user_message)

    # Формируем сообщение для отправки в Kafka
    kafka_message = serialize_data({"username": username, "message": user_message})

    try:
        # Отправляем сообщение в Kafka в топик "telegram_messages"
        send_message('telegram_messages', kafka_message)

        # Ответим пользователю, что сообщение принято
        await message.reply("Ваше сообщение отправлено в Kafka!")
    except Exception as e:
        # logging.error(f"Error sending message to Kafka: {str(e)}")
        await message.reply("Произошла ошибка при отправке сообщения в Kafka.")

async def main():
    # Запуск polling с передачей bot
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
