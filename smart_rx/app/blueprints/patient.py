from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from ..extensions import db
from ..models import Prescription, Order, Notification
from ..forms import LocationForm
from ..services.pharmacy_service import rank_pharmacies
from ..services.safety_service import check_allergies, check_interactions
from ..services.notification_service import log_action
from ..services.qr_service import ensure_qr_image, parse_qr_payload
from .decorators import role_required

patient_bp = Blueprint("patient", __name__, url_prefix="/patient")

def get_valid_prescription(token=None, rx_code=None):
    query = Prescription.query.filter_by(patient_id=current_user.id)
    prescription = None
    if token:
        prescription = query.filter_by(qr_token=token).first()
    if not prescription and rx_code:
        prescription = query.filter_by(rx_code=rx_code.upper()).first()

    if not prescription:
        # Check if the prescription exists at all (maybe under different patient)
        other = Prescription.query.filter((Prescription.qr_token == token) | (Prescription.rx_code == rx_code)).first()
        if other:
            return None, "This prescription belongs to a different patient account."
        return None, "Prescription not found. Please check the code or try scanning again."

    if prescription.is_used:
        return prescription, "Notice: This prescription QR has already been fulfilled/used."
    if prescription.qr_expires_at < datetime.utcnow():
        return prescription, "Notice: This prescription QR has expired (48h validity exceeded)."
    return prescription, None

@patient_bp.route("/prescriptions")
@role_required("patient")
def prescriptions():
    rows = Prescription.query.filter_by(patient_id=current_user.id).order_by(Prescription.created_at.desc()).all()
    for p in rows:
        ensure_qr_image(p)
    return render_template("patient/history.html", prescriptions=rows)

@patient_bp.route("/prescription/<int:prescription_id>")
@role_required("patient")
def prescription_detail(prescription_id):
    prescription = Prescription.query.filter_by(id=prescription_id, patient_id=current_user.id).first_or_404()
    ensure_qr_image(prescription)
    alerts = check_allergies(current_user, prescription.items) + check_interactions(prescription.items)
    return render_template("patient/prescription_detail.html", prescription=prescription, alerts=alerts)

@patient_bp.route("/scan", methods=["GET", "POST"])
@role_required("patient")
def scan():
    prescription, error = None, None
    if request.method == "POST":
        raw_text = (request.form.get("token") or request.form.get("rx_code") or "").strip()
        parsed_token, parsed_rx = parse_qr_payload(raw_text)
        
        prescription, error = get_valid_prescription(token=parsed_token, rx_code=parsed_rx)
        if prescription:
            ensure_qr_image(prescription)
            alerts = check_allergies(current_user, prescription.items) + check_interactions(prescription.items)
            log_action(current_user.id, "PRESCRIPTION_VIEWED", prescription.rx_code)
            db.session.commit()
            return render_template("patient/prescription_detail.html", prescription=prescription, alerts=alerts, notice=error)
    return render_template("patient/scan.html", error=error)

@patient_bp.route("/pharmacies/<int:prescription_id>", methods=["GET", "POST"])
@role_required("patient")
def pharmacies(prescription_id):
    prescription = Prescription.query.filter_by(id=prescription_id, patient_id=current_user.id).first_or_404()
    if prescription.is_used or prescription.qr_expires_at < datetime.utcnow():
        flash("This prescription is no longer valid for a new order.", "danger")
        return redirect(url_for("patient.prescriptions"))
    form = LocationForm()
    results = None
    # Default coordinates for demo if not supplied
    if not form.latitude.data and not form.longitude.data:
        form.latitude.data = 22.7196
        form.longitude.data = 75.8577
    if form.validate_on_submit():
        results = rank_pharmacies(prescription, form.latitude.data, form.longitude.data)
    else:
        results = rank_pharmacies(prescription, 22.7196, 75.8577)
    return render_template("patient/pharmacies.html", prescription=prescription, form=form, results=results)

@patient_bp.route("/notifications")
@role_required("patient")
def notifications():
    rows = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    for row in rows:
        row.is_read = True
    db.session.commit()
    return render_template("patient/notifications.html", notifications=rows)
