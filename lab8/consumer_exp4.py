import json
import time
from datetime import datetime
from kafka import KafkaConsumer

LATE_THRESHOLD = 0.0
# Динамічний ID групи гарантує вичитування з самого початку топіка
DYNAMIC_GROUP_ID = f"exp4_group_{int(time.time())}"

print(f"🚀 Запуск споживача Redpanda (Експеримент 4: LATE_THRESHOLD = {LATE_THRESHOLD}s)...")

consumer = KafkaConsumer(
    'payments_stream',
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='earliest',
    group_id=DYNAMIC_GROUP_ID,
    consumer_timeout_ms=3000,
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

total_events = 0
accepted_events = 0
rejected_events = 0

print("-" * 75)

for message in consumer:
    total_events += 1
    event = message.value
    invoice_id = event.get('invoiceId', f'inv_{total_events}')

    created_str = event.get('createdDate') or event.get('modifiedDate')
    received_str = event.get('receivedAt')

    latency = 0.0
    if created_str and received_str:
        try:
            t1 = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
            t2 = datetime.fromisoformat(received_str.replace('Z', '+00:00'))
            latency = max(0.0, (t2 - t1).total_seconds())
        except Exception:
            latency = 0.0

    if latency <= LATE_THRESHOLD:
        accepted_events += 1
        status_tag = "STATUS: PROCESSED"
    else:
        rejected_events += 1
        status_tag = "ALERT: LATE EVENT REJECTED"

    print(f"[{total_events:03d}] Invoice: {invoice_id} | Lag: {latency:.2f}s | [{status_tag}]")

print("-" * 75)
print("\n[STREAMING EXECUTION SUMMARY - EXPERIMENT 4]")
print("-" * 50)
print(f"Total Events Processed : {total_events}")
print(f"Accepted Events        : {accepted_events}  [STATUS: PROCESSED]")
print(f"Rejected Late Events   : {rejected_events}  [ALERT: LATE EVENT REJECTED]")
print(f"Threshold (Allowed)    : {LATE_THRESHOLD}s (Zero-tolerance policy)")
rejection_rate = (rejected_events / total_events * 100) if total_events > 0 else 0.0
print(f"Rejection Rate         : {rejection_rate:.1f}%")
print("-" * 50)
