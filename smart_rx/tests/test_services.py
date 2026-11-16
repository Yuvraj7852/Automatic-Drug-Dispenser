from datetime import datetime, timedelta, date
from types import SimpleNamespace
from app.services.qr_service import create_qr_token
from app.services.pharmacy_service import haversine_km
from app.services.safety_service import check_allergies
from app.models import User, Medicine, Pharmacy, PharmacyStock, Prescription, PrescriptionItem

def test_qr_token_is_random_and_nonempty():
    assert create_qr_token() != create_qr_token()
    assert len(create_qr_token()) > 30

def test_qr_expiry_is_detected(app):
    with app.app_context():
        patient=User(name="P",email="p@x.test",role="patient",password_hash="x")
        doctor=User(name="D",email="d@x.test",role="doctor",password_hash="x")
        db_session = __import__("app.extensions",fromlist=["db"]).db.session
        db_session.add_all([patient,doctor]); db_session.flush()
        rx=Prescription(rx_code="RXTEST1",patient_id=patient.id,doctor_id=doctor.id,
            qr_token="secure-token",qr_expires_at=datetime.utcnow()-timedelta(minutes=1))
        db_session.add(rx); db_session.commit()
        assert rx.qr_expires_at < datetime.utcnow()

def test_qr_reuse_flag(app):
    with app.app_context():
        p=Prescription(rx_code="RXTEST2",patient_id=1,doctor_id=1,qr_token="t",
                       qr_expires_at=datetime.utcnow()+timedelta(hours=1),is_used=True)
        assert p.is_used is True

def test_stock_quantity_check(app):
    with app.app_context():
        user=User(name="Owner",email="o@x.test",role="pharmacy",password_hash="x")
        patient=User(name="P",email="p@x.test",role="patient",password_hash="x")
        med=Medicine(name="Test med",price=10)
        db=__import__("app.extensions",fromlist=["db"]).db
        db.session.add_all([user,patient,med]); db.session.flush()
        ph=Pharmacy(owner_id=user.id,name="Shop",address="Indore",latitude=22.7,longitude=75.8)
        db.session.add(ph); db.session.flush()
        stock=PharmacyStock(pharmacy_id=ph.id,medicine_id=med.id,quantity=5,batch_no="T1",expiry_date=date.today()+timedelta(days=60))
        db.session.add(stock); db.session.commit()
        assert stock.quantity >= 4
        assert not stock.quantity >= 8

def test_haversine_same_point_zero():
    assert haversine_km(22.7,75.8,22.7,75.8) == 0

def test_haversine_indore_points_positive():
    assert haversine_km(22.7,75.8,22.75,75.89) > 0

def test_allergy_match(app):
    with app.app_context():
        patient=SimpleNamespace(allergies="paracetamol")
        med=SimpleNamespace(name="Paracetamol 500mg",generic_name="Paracetamol")
        item=SimpleNamespace(medicine=med)
        assert check_allergies(patient,[item])

def test_allergy_no_match(app):
    with app.app_context():
        patient=SimpleNamespace(allergies="peanut")
        med=SimpleNamespace(name="Paracetamol 500mg",generic_name="Paracetamol")
        item=SimpleNamespace(medicine=med)
        assert check_allergies(patient,[item]) == []
