from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db, limiter
from ..forms import RegisterForm, LoginForm
from ..models import User, Pharmacy
from ..services.notification_service import log_action

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        role = (form.role.data or "patient").lower().strip()
        if role not in ("patient", "doctor", "pharmacy"):
            role = "patient"

        user = User(
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip() if form.phone.data else None,
            role=role,
            is_verified=True,  # Auto-verify on registration so doctor/patient/pharmacy can immediately login
            license_no=form.license_no.data.strip() if form.license_no.data else None,
            age=form.age.data if form.age.data else None,
            allergies=form.allergies.data.strip() if form.allergies.data else None,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        # If pharmacy, also setup default pharmacy store profile
        if role == "pharmacy":
            p_name = form.pharmacy_name.data.strip() if (form.pharmacy_name and form.pharmacy_name.data) else f"{user.name} Medical Store"
            p_addr = form.address.data.strip() if (form.address and form.address.data) else "Main Road, Indore, Madhya Pradesh"
            pharm = Pharmacy(
                owner_id=user.id,
                name=p_name,
                address=p_addr,
                latitude=22.7196,
                longitude=75.8577,
                rating=4.5,
                avg_delivery_minutes=30,
                is_open=True
            )
            db.session.add(pharm)

        log_action(user.id, f"{role.upper()}_REGISTERED", f"Self registration as {role}")
        db.session.commit()
        flash(f"Registration successful as {role.title()}. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("60 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            if user.role in ("doctor", "pharmacy") and not user.is_verified:
                flash("Account pending admin verification.", "warning")
                return render_template("auth/login.html", form=form)
            login_user(user)
            log_action(user.id, "LOGIN", f"Successful login as {user.role}")
            db.session.commit()
            return redirect(request.args.get("next") or url_for("dashboard.index"))
        flash("Invalid email or password.", "danger")
    return render_template("auth/login.html", form=form)

@auth_bp.route("/demo-login/<role>")
def demo_login(role):
    """1-Click quick login for demo and testing purposes."""
    role = role.lower().strip()
    credentials = {
        "doctor": "doctor1@smartrx.local",
        "patient": "patient1@smartrx.local",
        "pharmacy": "pharmacy1@smartrx.local",
        "admin": "admin@smartrx.local",
    }
    target_email = credentials.get(role)
    if not target_email:
        flash("Unknown demo role.", "warning")
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(email=target_email).first()
    if not user:
        # Fallback to any user with this role
        user = User.query.filter_by(role=role).first()

    if user:
        user.is_verified = True
        db.session.commit()
        login_user(user)
        log_action(user.id, "DEMO_LOGIN", f"1-Click Demo Login as {user.role}")
        flash(f"Welcome back, {user.name}! Logged in as {user.role.title()}.", "success")
        return redirect(url_for("dashboard.index"))
    
    flash(f"No demo account found for {role}. Please register one.", "warning")
    return redirect(url_for("auth.login"))

@auth_bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    log_action(current_user.id, "LOGOUT", "User logged out")
    db.session.commit()
    logout_user()
    flash("You have been logged out safely.", "info")
    return redirect(url_for("auth.login"))
