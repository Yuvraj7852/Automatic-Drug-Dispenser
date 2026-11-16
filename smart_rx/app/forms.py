from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, IntegerField, FloatField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError, Regexp
from .models import User

EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
EMAIL_VALIDATOR = Regexp(EMAIL_REGEX, message="Please enter a valid email address.")

class RegisterForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired(), EMAIL_VALIDATOR, Length(max=255)])
    phone = StringField("Phone", validators=[Optional(), Length(max=25)])
    role = SelectField("Account Type", choices=[("patient", "Patient"), ("doctor", "Doctor"), ("pharmacy", "Pharmacy")], default="patient")
    license_no = StringField("Medical License / Reg. No.", validators=[Optional(), Length(max=100)])
    age = IntegerField("Age", validators=[Optional(), NumberRange(min=1, max=120)])
    allergies = StringField("Known Allergies (comma-separated)", validators=[Optional(), Length(max=500)])
    pharmacy_name = StringField("Pharmacy Name", validators=[Optional(), Length(max=150)])
    address = TextAreaField("Clinic / Pharmacy Address", validators=[Optional(), Length(max=500)])
    password = PasswordField("Password (minimum 8 characters)", validators=[DataRequired(), Length(min=8, max=128)])
    submit = SubmitField("Create Account")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("Email already registered.")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), EMAIL_VALIDATOR])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class PrescriptionForm(FlaskForm):
    patient_id = SelectField("Patient", coerce=int, validators=[DataRequired()])
    notes = TextAreaField("Notes / Instructions", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Create Digital Prescription")

class LocationForm(FlaskForm):
    latitude = FloatField("Latitude", validators=[DataRequired(), NumberRange(min=-90, max=90)])
    longitude = FloatField("Longitude", validators=[DataRequired(), NumberRange(min=-180, max=180)])
    submit = SubmitField("Find nearby pharmacies")
