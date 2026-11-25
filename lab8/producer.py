import json
import random
import time
from datetime import datetime, timezone, timedelta
from kafka import KafkaProducer

print("🚀 Запуск продюсера Redpanda: відправка 100 подій...")

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

TOPIC_NAME = 'payments_stream'
methods = ['card', 'apple_pay', 'google_pay', 'crypto']
statuses = ['success', 'success', 'success', 'failure']

for i in range(1, 101):
    now = datetime.now(timezone.utc)

    # Симуляція запізнення: кожна ~5-та подія створюється із затримкою від 5 до 10 секунд
    is_late = random.random() < 0.20
    if is_late:
        created_dt = now - timedelta(seconds=random.randint(5, 10))
    else:
        created_dt = now

    event = {
        'invoiceId': f"inv_kafka_{1000 + i}",
        'paymentMethod': random.choice(methods),
        'status': random.choice(statuses),
        'amount': random.randint(100, 15000),
        'ccy': 980,
        'createdDate': created_dt.isoformat(),
        'receivedAt': now.isoformat()
    }

    producer.send(TOPIC_NAME, value=event)
    time.sleep(0.02)

producer.flush()
print("✅ Усі 100 подій успішно відправлено в Redpanda!")
