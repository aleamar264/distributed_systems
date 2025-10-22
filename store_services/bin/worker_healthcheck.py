#!/usr/bin/env python3
"""Simple health check that tries to connect to RabbitMQ."""
import os
import sys

import pika

RABBIT_URL = os.environ.get("BROKER_URL", "amqp://guest:guest@rabbitmq:5672//")

params = pika.URLParameters(RABBIT_URL)
try:
    conn = pika.BlockingConnection(params)
    conn.close()
    print("OK")
    sys.exit(0)
except Exception as e:
    print("ERROR", e)
    sys.exit(2)
