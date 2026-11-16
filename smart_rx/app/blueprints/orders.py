import secrets
from datetime import datetime, date
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import current_user
from ..extensions import db
from ..models import Prescription, Pharmacy, PharmacyStock, Order, OrderItem, OrderStatusHistory
from ..services.pharmacy_service import active_stock
from ..services.notification_service import notify, log_action, record_status
from .decorators import role_required

orders_bp = Blueprint("orders", __name__, url_prefix="/orders")

@orders_bp.route("/create/<int:prescription_id>/<int:pharmacy_id>", methods=["POST"])
@role_required("patient")
def create_order(prescription_id, pharmacy_id):
    prescription = Prescription.query.filter_by(id=prescription_id, patient_id=current_user.id).first_or_404()
    pharmacy = db.session.get(Pharmacy, pharmacy_id)
    order_type = request.form.get("order_type", "PICKUP").upper()
    if order_type not in ("DELIVERY", "PICKUP") or not pharmacy or not pharmacy.is_open:
        flash("Invalid pharmacy or order option.", "danger")
        return redirect(url_for("patient.pharmacies", prescription_id=prescription.id))
    if prescription.is_used or prescription.qr_expires_at < datetime.utcnow():
        flash("Prescription QR is expired or already used.", "danger")
        return redirect(url_for("patient.prescriptions"))
    # Lock stock rows to prevent two simultaneous orders taking the same stock.
    total = Decimal("0.00")
    pending = []
    try:
        for item in prescription.items:
            stocks = PharmacyStock.query.filter_by(pharmacy_id=pharmacy.id, medicine_id=item.medicine_id).filter(
                PharmacyStock.quantity >= item.quantity, PharmacyStock.expiry_date >= date.today()
            ).with_for_update().all()
            available = sum(s.quantity for s in stocks)
            if available < item.quantity:
                raise ValueError(f"Insufficient stock for {item.medicine.name}.")
            remaining = item.quantity
            for stock in stocks:
                take = min(stock.quantity, remaining)
                if take:
                    pending.append((stock, take))
                    remaining -= take
                if remaining == 0:
                    break
            total += Decimal(str(item.medicine.price)) * item.quantity
        order = Order(prescription_id=prescription.id, pharmacy_id=pharmacy.id, patient_id=current_user.id,
                      order_type=order_type, status="PLACED", otp=f"{secrets.randbelow(1000000):06d}", total_price=total)
        db.session.add(order)
        db.session.flush()
        for item in prescription.items:
            db.session.add(OrderItem(order_id=order.id, medicine_id=item.medicine_id,
                                     quantity=item.quantity, price=item.medicine.price))
        for stock, take in pending:
            stock.quantity -= take
        prescription.is_used = True
        prescription.status = "ORDERED"
        db.session.add(OrderStatusHistory(order_id=order.id, status="PLACED"))
        notify(pharmacy.owner_id, f"New order #{order.id} received.")
        notify(current_user.id, f"Order #{order.id} placed successfully.")
        log_action(current_user.id, "ORDER_CREATED", f"Order {order.id}, pharmacy {pharmacy.id}")
        db.session.commit()
        flash(f"Order placed. Handover OTP: {order.otp} (demo only).", "success")
        return redirect(url_for("orders.track", order_id=order.id))
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
        return redirect(url_for("patient.pharmacies", prescription_id=prescription.id))

@orders_bp.route("/mine")
@role_required("patient")
def mine():
    rows = Order.query.filter_by(patient_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("orders/mine.html", orders=rows)

@orders_bp.route("/track/<int:order_id>")
@role_required("patient")
def track(order_id):
    order = Order.query.filter_by(id=order_id, patient_id=current_user.id).first_or_404()
    return render_template("orders/track.html", order=order)

@orders_bp.route("/status/<int:order_id>")
@role_required("patient")
def status(order_id):
    order = Order.query.filter_by(id=order_id, patient_id=current_user.id).first_or_404()
    return jsonify({"status": order.status, "history": [
        {"status": h.status, "timestamp": h.timestamp.strftime("%d %b %Y, %I:%M %p")}
        for h in sorted(order.status_history, key=lambda x: x.timestamp)
    ]})

@orders_bp.route("/pharmacy")
@role_required("pharmacy")
def pharmacy_dashboard():
    pharmacy = current_user.pharmacy_profile
    if not pharmacy:
        abort(403)
    rows = Order.query.filter_by(pharmacy_id=pharmacy.id).order_by(Order.created_at.desc()).all()
    return render_template("orders/pharmacy.html", orders=rows, pharmacy=pharmacy)

@orders_bp.route("/<int:order_id>/update", methods=["POST"])
@role_required("pharmacy")
def update_status(order_id):
    pharmacy = current_user.pharmacy_profile
    order = Order.query.filter_by(id=order_id, pharmacy_id=pharmacy.id).first_or_404()
    new_status = request.form.get("status", "").upper()
    allowed = {"VERIFIED", "PACKING", "OUT_FOR_DELIVERY", "READY_FOR_PICKUP"}
    if new_status not in allowed:
        abort(400)
    if new_status in {"OUT_FOR_DELIVERY"} and order.order_type != "DELIVERY":
        abort(400)
    if new_status == "READY_FOR_PICKUP" and order.order_type != "PICKUP":
        abort(400)
    record_status(order, new_status, current_user.id)
    db.session.commit()
    flash("Order status updated.", "success")
    return redirect(url_for("orders.pharmacy_dashboard"))

@orders_bp.route("/<int:order_id>/complete", methods=["POST"])
@role_required("pharmacy")
def complete_order(order_id):
    pharmacy = current_user.pharmacy_profile
    order = Order.query.filter_by(id=order_id, pharmacy_id=pharmacy.id).first_or_404()
    if order.status not in {"READY_FOR_PICKUP", "OUT_FOR_DELIVERY"}:
        flash("Order is not ready for handover.", "warning")
        return redirect(url_for("orders.pharmacy_dashboard"))
    otp = request.form.get("otp", "").strip()
    if not secrets.compare_digest(otp, order.otp or ""):
        flash("Incorrect OTP.", "danger")
        return redirect(url_for("orders.pharmacy_dashboard"))
    record_status(order, "COMPLETED", current_user.id)
    order.otp = None
    db.session.commit()
    flash("Order completed after OTP verification.", "success")
    return redirect(url_for("orders.pharmacy_dashboard"))
