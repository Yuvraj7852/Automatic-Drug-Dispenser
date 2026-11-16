import secrets
from datetime import date, datetime, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user
from ..extensions import db
from ..models import Pharmacy, PharmacyStock, Prescription, Order, OrderItem, OrderStatusHistory
from ..services.qr_service import parse_qr_payload, ensure_qr_image
from ..services.notification_service import notify, log_action, record_status
from .decorators import role_required

pharmacy_bp = Blueprint("pharmacy", __name__, url_prefix="/pharmacy")

@pharmacy_bp.route("/inventory")
@role_required("pharmacy")
def inventory():
    pharmacy = current_user.pharmacy_profile
    if not pharmacy:
        # Auto-create pharmacy profile if missing
        pharmacy = Pharmacy(
            owner_id=current_user.id,
            name=f"{current_user.name} Medical",
            address="Vijay Nagar, Indore, Madhya Pradesh",
            latitude=22.7533,
            longitude=75.8937,
            rating=4.5,
            avg_delivery_minutes=30,
            is_open=True
        )
        db.session.add(pharmacy)
        db.session.commit()

    rows = PharmacyStock.query.filter_by(pharmacy_id=pharmacy.id).all()
    low_stock = [r for r in rows if r.quantity < 10]
    expiring = [r for r in rows if r.expiry_date <= date.today() + timedelta(days=30)]
    return render_template("pharmacy/inventory.html", rows=rows, low_stock=low_stock, expiring=expiring, pharmacy=pharmacy)

@pharmacy_bp.route("/scan", methods=["GET", "POST"])
@role_required("pharmacy")
def scan():
    pharmacy = current_user.pharmacy_profile
    prescription = None
    error = None
    stock_analysis = []
    can_fulfill = True

    if request.method == "POST":
        raw_text = (request.form.get("token") or request.form.get("rx_code") or "").strip()
        parsed_token, parsed_rx = parse_qr_payload(raw_text)

        if parsed_token:
            prescription = Prescription.query.filter_by(qr_token=parsed_token).first()
        if not prescription and parsed_rx:
            prescription = Prescription.query.filter_by(rx_code=parsed_rx.upper()).first()

        if not prescription:
            error = "Prescription not found. Please verify the QR code or prescription code."
        else:
            ensure_qr_image(prescription)
            if prescription.is_used:
                error = "Warning: This prescription QR has already been used / fulfilled."
            elif prescription.qr_expires_at < datetime.utcnow():
                error = "Warning: This prescription QR has expired."

            # Check stock in this pharmacy for each prescription item
            if pharmacy:
                for item in prescription.items:
                    stocks = PharmacyStock.query.filter_by(
                        pharmacy_id=pharmacy.id, medicine_id=item.medicine_id
                    ).filter(PharmacyStock.expiry_date >= date.today()).all()
                    available_qty = sum(s.quantity for s in stocks)
                    has_enough = available_qty >= item.quantity
                    if not has_enough:
                        can_fulfill = False
                    stock_analysis.append({
                        "medicine": item.medicine.name,
                        "required": item.quantity,
                        "available": available_qty,
                        "has_enough": has_enough,
                        "dosage": item.dosage,
                        "frequency": item.frequency
                    })

    return render_template(
        "pharmacy/scan.html",
        prescription=prescription,
        error=error,
        stock_analysis=stock_analysis,
        can_fulfill=can_fulfill,
        pharmacy=pharmacy
    )

@pharmacy_bp.route("/dispense/<int:prescription_id>", methods=["POST"])
@role_required("pharmacy")
def dispense(prescription_id):
    pharmacy = current_user.pharmacy_profile
    if not pharmacy:
        abort(403)
    prescription = Prescription.query.filter_by(id=prescription_id).first_or_404()
    if prescription.is_used or prescription.qr_expires_at < datetime.utcnow():
        flash("This prescription is no longer valid for dispensing.", "danger")
        return redirect(url_for("pharmacy.scan"))

    total = Decimal("0.00")
    pending = []
    try:
        for item in prescription.items:
            stocks = PharmacyStock.query.filter_by(pharmacy_id=pharmacy.id, medicine_id=item.medicine_id).filter(
                PharmacyStock.quantity >= item.quantity, PharmacyStock.expiry_date >= date.today()
            ).with_for_update().all()
            available = sum(s.quantity for s in stocks)
            if available < item.quantity:
                raise ValueError(f"Insufficient stock for {item.medicine.name} (Available: {available}, Required: {item.quantity}).")
            remaining = item.quantity
            for stock in stocks:
                take = min(stock.quantity, remaining)
                if take:
                    pending.append((stock, take))
                    remaining -= take
                if remaining == 0:
                    break
            total += Decimal(str(item.medicine.price)) * item.quantity

        order = Order(
            prescription_id=prescription.id,
            pharmacy_id=pharmacy.id,
            patient_id=prescription.patient_id,
            order_type="COUNTER_DISPENSE",
            status="COMPLETED",
            otp=None,
            total_price=total
        )
        db.session.add(order)
        db.session.flush()

        for item in prescription.items:
            db.session.add(OrderItem(order_id=order.id, medicine_id=item.medicine_id,
                                     quantity=item.quantity, price=item.medicine.price))
        for stock, take in pending:
            stock.quantity -= take

        prescription.is_used = True
        prescription.status = "FULFILLED"
        db.session.add(OrderStatusHistory(order_id=order.id, status="COMPLETED"))
        notify(prescription.patient_id, f"Prescription {prescription.rx_code} dispensed by {pharmacy.name}.")
        log_action(current_user.id, "IN_STORE_DISPENSED", f"Prescription {prescription.rx_code} dispensed at {pharmacy.name}")
        db.session.commit()
        flash(f"Prescription {prescription.rx_code} successfully dispensed and fulfilled! Total: ₹{total}", "success")
        return redirect(url_for("orders.pharmacy_dashboard"))
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
        return redirect(url_for("pharmacy.scan"))
