import json
from collections import defaultdict
from datetime import datetime
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'payments',
    bootstrap_servers=['localhost:9092'],
    group_id='payments-analytics-group',
    auto_offset_reset='earliest',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

seen_invoices = set()
window_stats = defaultdict(lambda: {'total': 0, 'failed': 0})

print("Consumer успішно запущено. Очікування повідомлень з топіку 'payments'...\n")

try:
    for message in consumer:
        event = message.value
        invoice_id = event.get('invoiceId')
        if invoice_id in seen_invoices:
            continue
        seen_invoices.add(invoice_id)
        raw_date = event.get('modifiedDate', '')
        if raw_date:
            event_time = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
            window_key = event_time.strftime('%Y-%m-%d %H:%M')
        else:
            window_key = 'unknown'

        status = event.get('status')
        method = event.get('paymentMethod', 'unknown')
        window_stats[window_key]['total'] += 1
        if status == 'failure':
            window_stats[window_key]['failed'] += 1

        total = window_stats[window_key]['total']
        failed = window_stats[window_key]['failed']
        failure_rate = (failed / total) * 100 if total > 0 else 0
        print(f"[{event_time.strftime('%H:%M:%S')}] Invoice: {invoice_id} | Status: {status} | Method: {method}")

        if total >= 5 and failure_rate > 10.0:
            print(f"[ALERT] Хвилинне вікно {window_key} | Метод: {method} | Failure Rate: {failure_rate:.1f}% ({failed}/{total})\n")

except KeyboardInterrupt:
    print("\nConsumer зупинено користувачем.")
