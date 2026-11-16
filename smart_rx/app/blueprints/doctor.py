from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from flask_login import current_user
from ..extensions import db
from ..models import User, Medicine, Prescription, PrescriptionItem
from ..forms import PrescriptionForm
from ..services.qr_service import create_qr_token, create_qr_image, ensure_qr_image, expiry_time
from ..services.notification_service import notify, log_action
from .decorators import role_required

doctor_bp = Blueprint("doctor", __name__, url_prefix="/doctor")

@doctor_bp.route("/prescriptions", methods=["GET", "POST"])
@role_required("doctor")
def prescriptions():
    form = PrescriptionForm()
    patients = User.query.filter_by(role="patient").order_by(User.name).all()
    form.patient_id.choices = [(p.id, f"{p.name} ({p.email})") for p in patients]
    medicines = Medicine.query.order_by(Medicine.name).all()
    
    if form.validate_on_submit():
        medicine_ids = request.form.getlist("medicine_id")
        dosages = request.form.getlist("dosage")
        frequencies = request.form.getlist("frequency")
        durations = request.form.getlist("duration_days")
        quantities = request.form.getlist("quantity")

        if not medicine_ids or not (len(medicine_ids) == len(dosages) == len(frequencies) == len(durations) == len(quantities)):
            flash("Please add at least one complete medicine item.", "danger")
            return render_template("doctor/create_prescription.html", form=form, medicines=medicines, patients=patients)

        patient = db.session.get(User, form.patient_id.data)
        if not patient:
            flash("Selected patient does not exist.", "danger")
            return redirect(url_for("doctor.prescriptions"))

        rx_code = "RX" + datetime.utcnow().strftime("%Y%m%d") + f"{int(datetime.utcnow().timestamp() * 1000000) % 10000:04d}"
        while Prescription.query.filter_by(rx_code=rx_code).first():
            rx_code = "RX" + datetime.utcnow().strftime("%Y%m%d") + f"{(int(datetime.utcnow().timestamp() * 1000000) + 1) % 10000:04d}"

        token = create_qr_token()
        prescription = Prescription(
            rx_code=rx_code,
            patient_id=patient.id,
            doctor_id=current_user.id,
            notes=form.notes.data,
            qr_token=token,
            qr_expires_at=expiry_time()
        )
        db.session.add(prescription)
        db.session.flush()

        try:
            for mid, dosage, frequency, duration, quantity in zip(medicine_ids, dosages, frequencies, durations, quantities):
                medicine = db.session.get(Medicine, int(mid))
                duration_i, quantity_i = int(duration), int(quantity)
                if not medicine or not dosage.strip() or not frequency.strip() or not 1 <= duration_i <= 365 or not 1 <= quantity_i <= 1000:
                    raise ValueError(f"Invalid details for medicine {medicine.name if medicine else mid}")
                db.session.add(PrescriptionItem(
                    prescription_id=prescription.id,
                    medicine_id=medicine.id,
                    dosage=dosage.strip(),
                    frequency=frequency.strip(),
                    duration_days=duration_i,
                    quantity=quantity_i
                ))

            image_file = f"{rx_code}.png"
            qr_path = create_qr_image(token, image_file, rx_code=rx_code)
            notify(patient.id, f"Dr. {current_user.name} issued a new prescription: {rx_code}")
            log_action(current_user.id, "PRESCRIPTION_CREATED", rx_code)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not create prescription: {exc}", "danger")
            return redirect(url_for("doctor.prescriptions"))

        return render_template("doctor/prescription_created.html", prescription=prescription, qr_path=qr_path)

    return render_template("doctor/create_prescription.html", form=form, medicines=medicines, patients=patients)

@doctor_bp.route("/history")
@role_required("doctor")
def history():
    rows = Prescription.query.filter_by(doctor_id=current_user.id).order_by(Prescription.created_at.desc()).all()
    # Ensure QR images exist for all prescriptions
    for p in rows:
        ensure_qr_image(p)
    return render_template("doctor/history.html", prescriptions=rows)

@doctor_bp.route("/prescription/<int:prescription_id>")
@role_required("doctor")
def view_prescription(prescription_id):
    prescription = Prescription.query.filter_by(id=prescription_id, doctor_id=current_user.id).first_or_404()
    qr_path = ensure_qr_image(prescription)
    return render_template("doctor/prescription_created.html", prescription=prescription, qr_path=qr_path)
