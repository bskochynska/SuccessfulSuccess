import json
import random
import time
from datetime import datetime, timezone
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    key_serializer=lambda k: k.encode('utf-8'),
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

methods = ['card', 'apple_pay', 'google_pay', 'crypto']
statuses = ['success', 'success', 'success', 'failure']

print("Початок генерації та відправки 100 подій у топік 'payments'...")

try:
    for i in range(1, 101):
        invoice_id = f"inv_{1000 + i}"
        event_time = datetime.now(timezone.utc).isoformat()
        status = random.choice(statuses) if i % 3 == 0 else 'success'
        event = {
            'invoiceId': invoice_id,
            'paymentMethod': random.choice(methods),
            'status': status,
            'modifiedDate': event_time,
            'receivedAt': event_time
        }

        producer.send('payments', key=invoice_id, value=event)
        print(f"Надіслано подій: {i}/100 | Invoice: {invoice_id} | Status: {status}")

        time.sleep(0.2)

    producer.flush()
    print("Відправку 100 подій повністю завершено!")

except Exception as e:
    print(f"Помилка: {e}")
