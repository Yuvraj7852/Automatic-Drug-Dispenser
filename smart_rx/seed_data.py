from datetime import date, timedelta
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models import User, Medicine, Pharmacy, PharmacyStock, Prescription, PrescriptionItem
from app.services.qr_service import create_qr_token, create_qr_image, expiry_time

app = create_app()

USERS = [
    ("Admin User","admin@smartrx.local","Admin@123","admin",True),
    ("Dr. Asha Sharma","doctor1@smartrx.local","Doctor@123","doctor",True),
    ("Dr. Rahul Jain","doctor2@smartrx.local","Doctor@123","doctor",True),
    ("Dr. Neha Verma","doctor3@smartrx.local","Doctor@123","doctor",True),
    ("Patient One","patient1@smartrx.local","Patient@123","patient",True),
    ("Patient Two","patient2@smartrx.local","Patient@123","patient",True),
    ("Patient Three","patient3@smartrx.local","Patient@123","patient",True),
    ("Patient Four","patient4@smartrx.local","Patient@123","patient",True),
    ("Patient Five","patient5@smartrx.local","Patient@123","patient",True),
    ("Vijay Nagar Medical Owner","pharmacy1@smartrx.local","Pharmacy@123","pharmacy",True),
    ("Palasia Medical Owner","pharmacy2@smartrx.local","Pharmacy@123","pharmacy",True),
    ("Rajwada Medical Owner","pharmacy3@smartrx.local","Pharmacy@123","pharmacy",True),
    ("Bhawarkua Medical Owner","pharmacy4@smartrx.local","Pharmacy@123","pharmacy",True),
    ("Rau Medical Owner","pharmacy5@smartrx.local","Pharmacy@123","pharmacy",True),
]

MEDICINES = [
("Paracetamol 500mg","Paracetamol","Analgesic",12,"OTC"),
("Cetirizine 10mg","Cetirizine","Antihistamine",18,"OTC"),
("ORS Sachet","Oral Rehydration Salts","Electrolyte",22,"OTC"),
("Vitamin C 500mg","Ascorbic Acid","Vitamin",35,"OTC"),
("Vitamin D3","Cholecalciferol","Vitamin",60,"OTC"),
("Calcium 500mg","Calcium Carbonate","Supplement",45,"OTC"),
("Azithromycin 500mg","Azithromycin","Antibiotic",95,"Schedule H"),
("Amoxicillin 500mg","Amoxicillin","Antibiotic",75,"Schedule H"),
("Metformin 500mg","Metformin","Antidiabetic",30,"Schedule H"),
("Amlodipine 5mg","Amlodipine","Antihypertensive",25,"Schedule H"),
("Atorvastatin 10mg","Atorvastatin","Cholesterol",40,"Schedule H"),
("Pantoprazole 40mg","Pantoprazole","Antacid",32,"Schedule H"),
("Omeprazole 20mg","Omeprazole","Antacid",28,"Schedule H"),
("Ibuprofen 200mg","Ibuprofen","Pain relief",20,"OTC"),
("Diclofenac 50mg","Diclofenac","Pain relief",26,"Schedule H"),
("Montelukast 10mg","Montelukast","Allergy",55,"Schedule H"),
("Levocetirizine 5mg","Levocetirizine","Antihistamine",24,"Schedule H"),
("Cough Syrup","Dextromethorphan","Cough",85,"OTC"),
("Salbutamol Inhaler","Salbutamol","Respiratory",120,"Schedule H"),
("Budesonide Inhaler","Budesonide","Respiratory",180,"Schedule H"),
("Iron Folic Acid","Ferrous Fumarate","Supplement",50,"OTC"),
("Folic Acid 5mg","Folic Acid","Vitamin",15,"OTC"),
("Zinc 20mg","Zinc Sulphate","Supplement",20,"OTC"),
("Multivitamin","Multivitamin","Vitamin",75,"OTC"),
("Loratadine 10mg","Loratadine","Antihistamine",22,"OTC"),
("Dolo 650","Paracetamol","Analgesic",18,"OTC"),
("Ecosprin 75mg","Aspirin","Antiplatelet",12,"Schedule H"),
("Warfarin 2mg","Warfarin","Anticoagulant",35,"Schedule H"),
("Insulin 40IU","Insulin","Antidiabetic",180,"Schedule H"),
("Gliclazide 80mg","Gliclazide","Antidiabetic",65,"Schedule H"),
("Losartan 50mg","Losartan","Antihypertensive",38,"Schedule H"),
("Telmisartan 40mg","Telmisartan","Antihypertensive",42,"Schedule H"),
("Clopidogrel 75mg","Clopidogrel","Antiplatelet",48,"Schedule H"),
("Ondansetron 4mg","Ondansetron","Antiemetic",22,"Schedule H"),
("Domperidone 10mg","Domperidone","Antiemetic",18,"Schedule H"),
("Loperamide 2mg","Loperamide","Gastrointestinal",16,"OTC"),
("Mupirocin Ointment","Mupirocin","Topical",90,"Schedule H"),
("Clotrimazole Cream","Clotrimazole","Antifungal",55,"OTC"),
("Betadine Solution","Povidone Iodine","Antiseptic",65,"OTC"),
("Hand Sanitizer","Alcohol-based sanitizer","Hygiene",45,"OTC")
]

PHARMACY_DATA = [
("Demo Medical Vijay Nagar","Vijay Nagar, Indore, Madhya Pradesh",22.7533,75.8937),
("Demo Medical Palasia","Palasia, Indore, Madhya Pradesh",22.7244,75.8839),
("Demo Medical Rajwada","Rajwada, Indore, Madhya Pradesh",22.7196,75.8577),
("Demo Medical Bhawarkua","Bhawarkua, Indore, Madhya Pradesh",22.6906,75.8667),
("Demo Medical Rau","Rau, Indore, Madhya Pradesh",22.6540,75.8040)
]

with app.app_context():
    for name,email,password,role,verified in USERS:
        if not User.query.filter_by(email=email).first():
            u=User(name=name,email=email,role=role,is_verified=verified)
            u.set_password(password)
            db.session.add(u)
    db.session.commit()

    for name,generic,category,price,schedule in MEDICINES:
        if not Medicine.query.filter_by(name=name).first():
            db.session.add(Medicine(name=name,generic_name=generic,category=category,price=Decimal(str(price)),schedule_type=schedule))
    db.session.commit()

    for index,(name,address,lat,lon) in enumerate(PHARMACY_DATA,1):
        owner=User.query.filter_by(email=f"pharmacy{index}@smartrx.local").first()
        pharmacy=Pharmacy.query.filter_by(owner_id=owner.id).first()
        if not pharmacy:
            pharmacy=Pharmacy(owner_id=owner.id,name=name,address=address,latitude=lat,longitude=lon,
                              rating=4.0+index*0.1,avg_delivery_minutes=25+index*5,is_open=True)
            db.session.add(pharmacy)
    db.session.commit()

    medicines=Medicine.query.all()
    for pharmacy in Pharmacy.query.all():
        for med in medicines:
            if not PharmacyStock.query.filter_by(pharmacy_id=pharmacy.id,medicine_id=med.id,batch_no="BATCH-001").first():
                qty=0 if (med.id+pharmacy.id)%11==0 else 20+((med.id*pharmacy.id)%50)
                db.session.add(PharmacyStock(pharmacy_id=pharmacy.id,medicine_id=med.id,quantity=qty,
                    batch_no="BATCH-001",expiry_date=date.today()+timedelta(days=180+(med.id%120))))
    db.session.commit()

    # Three demo prescriptions; sample QR images are generated for each.
    doctors=User.query.filter_by(role="doctor").order_by(User.id).all()
    patients=User.query.filter_by(role="patient").order_by(User.id).all()
    sample_sets=[[(1,"500 mg","Twice daily",3,6),(2,"10 mg","Once daily",5,5)],
                 [(3,"1 sachet","As directed",2,4),(4,"500 mg","Once daily",7,7)],
                 [(12,"40 mg","Once daily",5,5),(1,"500 mg","As needed",3,6)]]
    for idx,items in enumerate(sample_sets):
        rx=f"RXDEMO{idx+1:04d}"
        if not Prescription.query.filter_by(rx_code=rx).first():
            token=create_qr_token()
            p=Prescription(rx_code=rx,patient_id=patients[idx].id,doctor_id=doctors[idx].id,
                notes="Seed sample prescription. Please verify with a licensed pharmacist.",
                qr_token=token,qr_expires_at=expiry_time())
            db.session.add(p)
            db.session.flush()
            for med_id,dosage,freq,duration,qty in items:
                db.session.add(PrescriptionItem(prescription_id=p.id,medicine_id=med_id,dosage=dosage,
                    frequency=freq,duration_days=duration,quantity=qty))
            create_qr_image(token,f"{rx}.png")
    db.session.commit()
    print("Seed completed: users, pharmacies, 40 medicines, stock and 3 sample prescriptions.")
