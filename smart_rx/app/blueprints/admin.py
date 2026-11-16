from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from ..extensions import db
from ..models import User, Order, OrderItem, Medicine
from ..services.notification_service import log_action
from .decorators import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/")
@role_required("admin")
def dashboard():
    pending = User.query.filter(User.role.in_(["doctor", "pharmacy"]), User.is_verified.is_(False)).all()
    total_users = User.query.count()
    total_orders = Order.query.count()
    popular = db.session.query(Medicine.name, db.func.sum(OrderItem.quantity).label("qty")).join(
        OrderItem, OrderItem.medicine_id == Medicine.id
    ).group_by(Medicine.id, Medicine.name).order_by(db.desc("qty")).limit(10).all()
    return render_template("admin/dashboard.html", pending=pending, total_users=total_users,
                           total_orders=total_orders, popular=popular)

@admin_bp.route("/verify/<int:user_id>", methods=["POST"])
@role_required("admin")
def verify_user(user_id):
    user = db.session.get(User, user_id)
    if not user or user.role not in ("doctor", "pharmacy"):
        abort(404)
    user.is_verified = True
    log_action(user.id, "ACCOUNT_VERIFIED", f"Verified by admin user {user.id}")
    db.session.commit()
    flash(f"{user.name} verified.", "success")
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/users")
@role_required("admin")
def users():
    return render_template("admin/users.html", users=User.query.order_by(User.created_at.desc()).all())
