import json
import time
from datetime import datetime, timezone
from kafka import KafkaProducer

TOPIC_NAME = 'payments_stream'
DATASET_FILE = 'dataset.json'  # Вкажіть шлях до вашого файлу датасету
EVENTS_PER_SEC = 20
DELAY = 1.0 / EVENTS_PER_SEC   # 0.05 секунди між подіями

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

try:
    with open(DATASET_FILE, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    print(f"📂 Завантажено {len(dataset)} записів з датасету '{DATASET_FILE}'.")
except FileNotFoundError:
    print(f"⚠️ Файл '{DATASET_FILE}' не знайдено! Використовуємо зріз згенерованих даних датасету.")
    dataset = [
        {
            "invoiceId": f"inv_ds_{i}",
            "paymentMethod": "card" if i % 2 == 0 else "apple_pay",
            "status": "success" if i % 5 != 0 else "failure",
            "amount": 1000 + (i * 15),
            "ccy": 980,
            "createdDate": datetime.now(timezone.utc).isoformat()
        }
        for i in range(1, 501)  # Симуляція 500 записів датасету
    ]

print(f"🚀 Запуск відтворення датасету: {EVENTS_PER_SEC} подій/сек...")
start_time = time.time()

for i, record in enumerate(dataset, 1):
    # Оновлюємо точний час отримання події стримером
    record['receivedAt'] = datetime.now(timezone.utc).isoformat()

    producer.send(TOPIC_NAME, value=record)

    if i % EVENTS_PER_SEC == 0:
        elapsed = time.time() - start_time
        print(f"⏱️ Надіслано {i} подій | Пройшло: {elapsed:.2f}s | Швидкість: ~{i/elapsed:.1f} evt/s")

    time.sleep(DELAY)

producer.flush()
print("✅ Відтворення датасету успішно завершено!")
