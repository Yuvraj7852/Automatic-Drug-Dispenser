from ..extensions import db
from ..models import Notification, AuditLog, OrderStatusHistory

def notify(user_id, message):
    db.session.add(Notification(user_id=user_id, message=message))

def log_action(user_id, action, details=""):
    db.session.add(AuditLog(user_id=user_id, action=action, details=details))

def record_status(order, status, user_id=None):
    order.status = status
    db.session.add(OrderStatusHistory(order_id=order.id, status=status))
    notify(order.patient_id, f"Order #{order.id} status updated: {status.replace('_', ' ').title()}")
    log_action(user_id, "ORDER_STATUS_CHANGED", f"Order {order.id}: {status}")
