"""
Notification Service - Business Logic
"""
from typing import Dict
from datetime import datetime

from app.config import settings


class NotificationService:
    """Service for sending notifications"""
    
    def __init__(self):
        self.email_service = settings.EMAIL_SERVICE
    
    def send_order_created_notification(self, order_data: Dict) -> bool:
        """
        Send notification for OrderCreated event
        
        Args:
            order_data: Order data from event
        
        Returns:
            True if notification sent successfully
        """
        order_id = order_data.get("order_id")
        product_name = order_data.get("product_name")
        quantity = order_data.get("quantity")
        total_price = order_data.get("total_price")
        customer_email = order_data.get("customer_email", "no-email@example.com")
        
        # Format notification message
        subject = f"Order #{order_id} Created Successfully"
        body = f"""
Hi!

Your order has been created successfully:

Order ID: {order_id}
Product: {product_name}
Quantity: {quantity}
Total Price: {total_price:.2f} UAH

Thank you for your purchase!

---
Order Management System
        """
        
        # Send notification based on configured service
        if self.email_service == "console":
            return self._send_console_notification(customer_email, subject, body, order_id)
        elif self.email_service == "sendgrid":
            return self._send_sendgrid_notification(customer_email, subject, body)
        elif self.email_service == "smtp":
            return self._send_smtp_notification(customer_email, subject, body)
        else:
            print(f"Unknown email service: {self.email_service}")
            return False
    
    def send_order_status_changed_notification(self, order_data: Dict) -> bool:
        """
        Send notification for OrderStatusChanged event
        
        Args:
            order_data: Order status change data
        
        Returns:
            True if notification sent successfully
        """
        order_id = order_data.get("order_id")
        new_status = order_data.get("new_status")
        
        subject = f"Order #{order_id} Status Updated"
        body = f"""
Hi!

Your order status has been updated:

Order ID: {order_id}
New Status: {new_status}

---
Order Management System
        """
        
        if self.email_service == "console":
            return self._send_console_notification("customer@example.com", subject, body, order_id)
        
        return True
    
    def _send_console_notification(self, to: str, subject: str, body: str, order_id: int) -> bool:
        """
        Simulate email sending by printing to console
        
        This is for development/testing purposes
        """
        print("\n" + "="*60)
        print("📧 EMAIL NOTIFICATION (Console Mode)")
        print("="*60)
        print(f"To: {to}")
        print(f"Subject: {subject}")
        print("-"*60)
        print(body)
        print("="*60)
        print(f"✓ Notification sent for Order #{order_id} at {datetime.utcnow().isoformat()}")
        print("="*60 + "\n")
        return True
    
    def _send_sendgrid_notification(self, to: str, subject: str, body: str) -> bool:
        """
        Send email via SendGrid
        
        Production implementation would use SendGrid API
        """
        # TODO: Implement SendGrid integration
        # from sendgrid import SendGridAPIClient
        # from sendgrid.helpers.mail import Mail
        # ...
        print(f"TODO: Send email via SendGrid to {to}")
        return True
    
    def _send_smtp_notification(self, to: str, subject: str, body: str) -> bool:
        """
        Send email via SMTP
        
        Production implementation would use SMTP
        """
        # TODO: Implement SMTP integration
        # import smtplib
        # from email.mime.text import MIMEText
        # ...
        print(f"TODO: Send email via SMTP to {to}")
        return True