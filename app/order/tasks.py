from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_order_confirmation_email(order_id, user_email, user_first_name, items_data, total_price, discount):
    """Send an order confirmation email with pre-fetched data as an HTML message"""
    try:
        subject = f"Order Confirmation - Order #{order_id}"
        recipient_list = [user_email]
        
        # Prepare email context
        context = {
            "user_first_name": user_first_name or user_email,
            "order_id": order_id,
            "total_price": total_price,
            "discount": discount,
            "items": items_data
        }

        # Render email as HTML
        html_message = render_to_string("email/order_confirmation.html", context)
        
        logger.info(f"Sending confirmation email for order {order_id} to {recipient_list}")
        
        send_mail(
            subject=subject,
            message=None,  
            from_email=settings.DEFAULT_FROM_EMAIL or 'no-reply@orderapp.com',
            recipient_list=recipient_list,
            fail_silently=False,
            html_message=html_message
        )

        logger.info(f"Confirmation email sent for order {order_id}")
    
    except Exception as e:
        logger.error(f"Failed to send email for order {order_id}: {str(e)}")
