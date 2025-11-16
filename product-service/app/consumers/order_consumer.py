"""
RabbitMQ Consumer for OrderCreated events
"""
import pika
import json
import sys
from typing import Callable

from app.config import settings
from app.database import SessionLocal
from app.services.product_service import ProductService


def callback(ch, method, properties, body):
    """
    Callback function to process OrderCreated events
    
    Args:
        ch: Channel
        method: Method
        properties: Properties
        body: Message body (JSON string)
    """
    db = SessionLocal()
    
    try:
        # Parse event
        event = json.loads(body)
        event_id = event.get("event_id")
        event_type = event.get("event_type")
        
        print(f"Received event: {event_type} (ID: {event_id})")
        
        # Process event
        service = ProductService(db)
        success = service.process_order_created_event(event)
        
        if success:
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print(f"✓ Event {event_id} processed successfully")
        else:
            # Reject and don't requeue (send to DLQ if configured)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            print(f"✗ Event {event_id} processing failed")
            
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        print(f"✗ Error processing event: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    finally:
        db.close()


def start_consumer():
    """
    Start RabbitMQ consumer
    
    Connects to RabbitMQ and starts consuming OrderCreated events
    """
    try:
        # Connect to RabbitMQ
        print(f"Connecting to RabbitMQ: {settings.RABBITMQ_URL}")
        connection = pika.BlockingConnection(
            pika.URLParameters(settings.RABBITMQ_URL)
        )
        channel = connection.channel()
        
        # Declare exchange
        channel.exchange_declare(
            exchange=settings.RABBITMQ_EXCHANGE,
            exchange_type='topic',
            durable=True
        )
        print(f"✓ Exchange declared: {settings.RABBITMQ_EXCHANGE}")
        
        # Declare queue
        channel.queue_declare(
            queue=settings.RABBITMQ_QUEUE,
            durable=True
        )
        print(f"✓ Queue declared: {settings.RABBITMQ_QUEUE}")
        
        # Bind queue to exchange
        channel.queue_bind(
            exchange=settings.RABBITMQ_EXCHANGE,
            queue=settings.RABBITMQ_QUEUE,
            routing_key=settings.RABBITMQ_ROUTING_KEY
        )
        print(f"✓ Queue bound to exchange with routing key: {settings.RABBITMQ_ROUTING_KEY}")
        
        # Set prefetch count (QoS)
        channel.basic_qos(prefetch_count=10)
        
        # Start consuming
        channel.basic_consume(
            queue=settings.RABBITMQ_QUEUE,
            on_message_callback=callback,
            auto_ack=False  # Manual acknowledgement
        )
        
        print(f"✓ {settings.SERVICE_NAME} Consumer started")
        print(f"✓ Waiting for OrderCreated events on queue: {settings.RABBITMQ_QUEUE}")
        print("Press CTRL+C to exit")
        
        channel.start_consuming()
        
    except KeyboardInterrupt:
        print("\nConsumer stopped by user")
        try:
            connection.close()
        except:
            pass
        sys.exit(0)
    except Exception as e:
        print(f"✗ Error starting consumer: {e}")
        sys.exit(1)


if __name__ == "__main__":
    start_consumer()