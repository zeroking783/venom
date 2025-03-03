from confluent_kafka import Consumer, KafkaException, KafkaError
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

# Настроим логирование
LOG_FILE = "consumer_logs.log"

logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(LOG_FILE),
                        logging.StreamHandler()
                    ])

# Настроим Kafka Consumer
ADRESS_KAFKA_CLUSTER = os.getenv('ADRESS_KAFKA_CLUSTER')
KAFKA_USERNAME = os.getenv('KAFKA_USERNAME')
KAFKA_PASSWORD = os.getenv('KAFKA_PASSWORD')

config = {
    'bootstrap.servers': ADRESS_KAFKA_CLUSTER,  # Укажи свой адрес брокера Kafka
    'group.id': 'worker',
    'security.protocol': 'SASL_PLAINTEXT',
    'sasl.mechanism': 'SCRAM-SHA-256',  # или другой, если настроено иначе
    'sasl.username': KAFKA_USERNAME,  # Имя пользователя
    'sasl.password': KAFKA_PASSWORD,  # Пароль пользователя
}

consumer = Consumer(config)
consumer.subscribe(['video-download-links'])

def consume_messages():
    try:
        while True:
            msg = consumer.poll(1.0)  # Ожидание 1 сек.
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logging.info(f"End of partition reached {msg.topic()} [{msg.partition()}]")
                else:
                    logging.error(f"Kafka error: {msg.error()}")
                continue

            # Декодируем сообщение
            message_value = msg.value().decode('utf-8')
            try:
                data = json.loads(message_value)
                logging.info(f"Received message: {data}")
                
            except json.JSONDecodeError:
                logging.error(f"Failed to decode JSON: {message_value}")

    except KeyboardInterrupt:
        logging.info("Consumer stopped by user")
    finally:
        consumer.close()
        logging.info("Consumer closed")

if __name__ == '__main__':
    logging.info("Starting Kafka Consumer...")
    consume_messages()
