"""
RabbitMQ Consumer for OrderCreated and OrderStatusChanged events
"""
import pika
import json
import sys

from app.config import settings
from app.services.notification_service import NotificationService


def callback(ch, method, properties, body):
    """
    Callback function to process order events
    
    Args:
        ch: Channel
        method: Method
        properties: Properties
        body: Message body (JSON string)
    """
    try:
        # Parse event
        event = json.loads(body)
        event_id = event.get("event_id")
        event_type = event.get("event_type")
        event_data = event.get("data", {})
        
        print(f"Received event: {event_type} (ID: {event_id})")
        
        # Process event
        notification_service = NotificationService()
        
        if event_type == "OrderCreated":
            success = notification_service.send_order_created_notification(event_data)
        elif event_type == "OrderStatusChanged":
            success = notification_service.send_order_status_changed_notification(event_data)
        else:
            print(f"Unknown event type: {event_type}")
            success = False
        
        if success:
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print(f"✓ Event {event_id} processed successfully")
        else:
            # Reject and don't requeue
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            print(f"✗ Event {event_id} processing failed")
            
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        print(f"✗ Error processing event: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def start_consumer():
    """
    Start RabbitMQ consumer
    
    Connects to RabbitMQ and starts consuming order events
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
        
        # Bind queue to exchange for OrderCreated
        channel.queue_bind(
            exchange=settings.RABBITMQ_EXCHANGE,
            queue=settings.RABBITMQ_QUEUE,
            routing_key=settings.RABBITMQ_ROUTING_KEY
        )
        print(f"✓ Queue bound to exchange with routing key: {settings.RABBITMQ_ROUTING_KEY}")
        
        # Also bind to OrderStatusChanged (optional)
        channel.queue_bind(
            exchange=settings.RABBITMQ_EXCHANGE,
            queue=settings.RABBITMQ_QUEUE,
            routing_key="order.status.changed"
        )
        print(f"✓ Queue also bound to: order.status.changed")
        
        # Set prefetch count (QoS)
        channel.basic_qos(prefetch_count=5)
        
        # Start consuming
        channel.basic_consume(
            queue=settings.RABBITMQ_QUEUE,
            on_message_callback=callback,
            auto_ack=False  # Manual acknowledgement
        )
        
        print(f"✓ {settings.SERVICE_NAME} Consumer started")
        print(f"✓ Waiting for order events on queue: {settings.RABBITMQ_QUEUE}")
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