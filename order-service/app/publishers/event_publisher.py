"""
RabbitMQ Event Publisher
"""
import pika
import json
import uuid
from datetime import datetime
from typing import Dict

from app.config import settings


class EventPublisher:
    """Publisher for sending events to RabbitMQ"""
    
    def __init__(self):
        self.rabbitmq_url = settings.RABBITMQ_URL
        self.exchange = settings.RABBITMQ_EXCHANGE
        self.routing_key = settings.RABBITMQ_ROUTING_KEY
    
    def publish_order_created(self, order_data: Dict) -> bool:
        """
        Publish OrderCreated event to RabbitMQ
        
        Args:
            order_data: Order data to publish
        
        Returns:
            True if published successfully, False otherwise
        """
        try:
            # Connect to RabbitMQ
            connection = pika.BlockingConnection(
                pika.URLParameters(self.rabbitmq_url)
            )
            channel = connection.channel()
            
            # Declare exchange
            channel.exchange_declare(
                exchange=self.exchange,
                exchange_type='topic',
                durable=True
            )
            
            # Create event payload
            event = {
                "event_type": "OrderCreated",
                "event_id": str(uuid.uuid4()),
                "event_version": "1.0",
                "timestamp": datetime.utcnow().isoformat(),
                "source": settings.SERVICE_NAME,
                "data": order_data
            }
            
            # Enable publisher confirms
            channel.confirm_delivery()
            
            # Publish message
            channel.basic_publish(
                exchange=self.exchange,
                routing_key=self.routing_key,
                body=json.dumps(event),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent message
                    content_type='application/json',
                    correlation_id=event["event_id"]
                ),
                mandatory=True
            )
            
            connection.close()
            
            print(f"✓ Event published: OrderCreated (ID: {event['event_id']})")
            return True
            
        except pika.exceptions.UnroutableError:
            print(f"✗ Event could not be routed to any queue")
            return False
        except Exception as e:
            print(f"✗ Error publishing event: {e}")
            return False
    
    def publish_order_status_changed(self, order_data: Dict) -> bool:
        """
        Publish OrderStatusChanged event to RabbitMQ
        
        Args:
            order_data: Order data including new status
        
        Returns:
            True if published successfully, False otherwise
        """
        try:
            connection = pika.BlockingConnection(
                pika.URLParameters(self.rabbitmq_url)
            )
            channel = connection.channel()
            
            channel.exchange_declare(
                exchange=self.exchange,
                exchange_type='topic',
                durable=True
            )
            
            event = {
                "event_type": "OrderStatusChanged",
                "event_id": str(uuid.uuid4()),
                "event_version": "1.0",
                "timestamp": datetime.utcnow().isoformat(),
                "source": settings.SERVICE_NAME,
                "data": order_data
            }
            
            channel.confirm_delivery()
            
            channel.basic_publish(
                exchange=self.exchange,
                routing_key="order.status.changed",
                body=json.dumps(event),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json',
                    correlation_id=event["event_id"]
                ),
                mandatory=False
            )
            
            connection.close()
            
            print(f"✓ Event published: OrderStatusChanged (ID: {event['event_id']})")
            return True
            
        except Exception as e:
            print(f"✗ Error publishing status change event: {e}")
            return False