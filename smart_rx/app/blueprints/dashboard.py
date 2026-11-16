from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models import Prescription, User, Pharmacy, Order
from ..services.qr_service import parse_qr_payload, ensure_qr_image

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
def home():
    stats = {
        "doctors": User.query.filter_by(role="doctor").count(),
        "pharmacies": Pharmacy.query.count(),
        "prescriptions": Prescription.query.count(),
        "orders": Order.query.count(),
    }
    return render_template("home.html", stats=stats)

@dashboard_bp.route("/dashboard")
@login_required
def index():
    # Gather role-specific metrics for attractive dashboard display
    metrics = {}
    if current_user.role == "doctor":
        metrics["prescriptions_count"] = Prescription.query.filter_by(doctor_id=current_user.id).count()
        metrics["active_count"] = Prescription.query.filter_by(doctor_id=current_user.id, is_used=False).count()
    elif current_user.role == "patient":
        metrics["prescriptions_count"] = Prescription.query.filter_by(patient_id=current_user.id).count()
        metrics["orders_count"] = Order.query.filter_by(patient_id=current_user.id).count()
    elif current_user.role == "pharmacy":
        pharm = current_user.pharmacy_profile
        if pharm:
            metrics["orders_count"] = Order.query.filter_by(pharmacy_id=pharm.id).count()
            metrics["pending_orders"] = Order.query.filter_by(pharmacy_id=pharm.id).filter(Order.status != "COMPLETED").count()
    return render_template("dashboard/index.html", metrics=metrics)

@dashboard_bp.route("/verify", methods=["GET", "POST"])
@dashboard_bp.route("/verify/<token_or_code>")
def verify(token_or_code=None):
    prescription = None
    error = None
    raw = token_or_code or request.args.get("token") or request.args.get("code") or (request.form.get("query") if request.method == "POST" else None)

    if raw:
        token, rx = parse_qr_payload(raw)
        if token:
            prescription = Prescription.query.filter_by(qr_token=token).first()
        if not prescription and rx:
            prescription = Prescription.query.filter_by(rx_code=rx.upper()).first()

        if not prescription:
            error = "Prescription not found or cryptographic signature invalid."
        else:
            ensure_qr_image(prescription)

    return render_template("verify.html", prescription=prescription, error=error, raw_query=raw)
