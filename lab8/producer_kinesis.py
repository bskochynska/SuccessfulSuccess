import json
import random
import time
from datetime import datetime, timezone
import boto3

# Ініціалізація Kinesis клієнта AWS
kinesis_client = boto3.client('kinesis', region_name='us-east-1')

STREAM_NAME = 'payments-kinesis-stream'
methods = ['card', 'apple_pay', 'google_pay', 'crypto']
statuses = ['success', 'success', 'success', 'failure']

print(f"🚀 Початок відправки 100 подій у AWS Kinesis Data Stream '{STREAM_NAME}'...")

try:
    for i in range(1, 101):
        invoice_id = f"inv_aws_{2000 + i}"
        now_iso = datetime.now(timezone.utc).isoformat()
        status = random.choice(statuses)

        event = {
            'invoiceId': invoice_id,
            'paymentMethod': random.choice(methods),
            'status': status,
            'amount': random.randint(100, 15000),
            'ccy': 980,
            'modifiedDate': now_iso,
            'receivedAt': now_iso
        }

        # Відправка в Kinesis з PartitionKey=invoiceId
        response = kinesis_client.put_record(
            StreamName=STREAM_NAME,
            Data=json.dumps(event),
            PartitionKey=invoice_id
        )

        print(f"[{i}/100] Invoice: {invoice_id} | SequenceNo: {response['SequenceNumber'][:15]}... | Status: {status}")
        time.sleep(0.1)

    print("✅ Усі 100 подій успішно надіслано в AWS Kinesis!")

except Exception as e:
    print(f"❌ Помилка відправки в AWS: {e}")
