#!/usr/bin/env python
"""
Script to run RabbitMQ consumer for Notification Service
"""
from app.consumers.order_consumer import start_consumer

if __name__ == "__main__":
    start_consumer()