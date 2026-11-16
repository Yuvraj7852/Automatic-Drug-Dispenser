from app.models import User, Prescription
from app.extensions import db
from app.services.qr_service import parse_qr_payload, create_qr_token, expiry_time

def add_user(app, email, role):
    with app.app_context():
        user = User(name=role.title(), email=email, role=role, is_verified=True)
        user.set_password("Pass12345")
        db.session.add(user)
        db.session.commit()

def test_login_success(app, client):
    add_user(app, "p@test.local", "patient")
    r = client.post("/auth/login", data={"email": "p@test.local", "password": "Pass12345"}, follow_redirects=True)
    assert r.status_code == 200 and b"Welcome" in r.data

def test_wrong_role_blocked(app, client):
    add_user(app, "p2@test.local", "patient")
    client.post("/auth/login", data={"email": "p2@test.local", "password": "Pass12345"})
    assert client.get("/doctor/prescriptions").status_code == 403

def test_doctor_route_requires_login(client):
    r = client.get("/doctor/prescriptions")
    assert r.status_code == 302

def test_patient_register(client):
    r = client.post(
        "/auth/register",
        data={"name": "New Patient", "email": "new@test.local", "phone": "9999999999", "password": "StrongPass123"},
        follow_redirects=True
    )
    assert r.status_code == 200 and b"Registration successful" in r.data

def test_doctor_register_and_access(app, client):
    r = client.post(
        "/auth/register",
        data={
            "name": "Dr. Test Specialist",
            "email": "drtest@hospital.local",
            "phone": "9876543210",
            "role": "doctor",
            "license_no": "NMC-2024-9988",
            "password": "DoctorPass123"
        },
        follow_redirects=True
    )
    assert r.status_code == 200 and b"Registration successful" in r.data

    # Now login as the doctor
    r_login = client.post(
        "/auth/login",
        data={"email": "drtest@hospital.local", "password": "DoctorPass123"},
        follow_redirects=True
    )
    assert r_login.status_code == 200 and b"Welcome back, Dr. Test Specialist" in r_login.data

    # Doctor should be allowed to access prescription creation
    r_rx = client.get("/doctor/prescriptions")
    assert r_rx.status_code == 200 and b"Create Digital Prescription" in r_rx.data

def test_qr_payload_parser():
    # 1. Plain token
    token = create_qr_token()
    t1, r1 = parse_qr_payload(token)
    assert t1 == token and r1 is None

    # 2. URL with token
    url1 = f"http://localhost:5000/patient/scan?token={token}"
    t2, r2 = parse_qr_payload(url1)
    assert t2 == token

    # 3. Rx code direct
    t3, r3 = parse_qr_payload("RXDEMO0001")
    assert r3 == "RXDEMO0001"

    # 4. JSON payload
    json_data = f'{{"token": "{token}", "rx_code": "RXTEST"}}'
    t4, r4 = parse_qr_payload(json_data)
    assert t4 == token and r4 == "RXTEST"

def test_verify_route(app, client):
    with app.app_context():
        doc = User(name="Dr. Verify", email="doc@v.local", role="doctor", password_hash="x", is_verified=True)
        pat = User(name="Pat Verify", email="pat@v.local", role="patient", password_hash="x", is_verified=True)
        db.session.add_all([doc, pat])
        db.session.flush()

        tok = create_qr_token()
        rx = Prescription(
            rx_code="RXVERIFY01",
            patient_id=pat.id,
            doctor_id=doc.id,
            qr_token=tok,
            qr_expires_at=expiry_time()
        )
        db.session.add(rx)
        db.session.commit()

    # Public verification lookup
    r = client.get(f"/verify/{tok}")
    assert r.status_code == 200 and b"RXVERIFY01" in r.data
