# Smart QR-Based Digital Prescription, Pharmacy Recommendation & Medicine Ordering System

A Flask + MySQL academic project. It supports doctor-created prescriptions with opaque QR tokens, patient QR scanning/image upload/manual code, pharmacy stock availability and distance ranking, delivery/pickup orders, pharmacy status updates, polling-based tracking, OTP handover, safety warning examples, stock/expiry alerts and a basic admin report.

> **Important:** This is an academic demo, not a clinically validated prescribing or dispensing system. Sample drug-interaction data is incomplete. Allergy/interactions warnings are informational and must not replace professional review. Never use seed data or demo credentials for real patient care.

## Stack
- Python 3.11+, Flask Blueprints, Jinja2, Bootstrap 5
- MySQL + Flask-SQLAlchemy + PyMySQL + Flask-Migrate
- Flask-Login, Werkzeug password hashing, Flask-WTF CSRF, Flask-Limiter
- qrcode + Pillow; html5-qrcode for webcam and QR image file scanning
- Haversine distance; simple Python pharmacy score
- pytest

## MySQL setup

```sql
CREATE DATABASE smart_rx CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Copy `.env.example` to `.env`, then set your local database credentials:

```env
FLASK_APP=run.py
FLASK_DEBUG=1
SECRET_KEY=replace-this-with-a-long-random-secret
DATABASE_URL=mysql+pymysql://root:password@localhost/smart_rx
RATELIMIT_STORAGE_URI=memory://
```

## Windows installation

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Database migration and seed

Run from the project root:

```bash
flask db init
flask db migrate -m "Initial schema"
flask db upgrade
python seed_data.py
flask run
```

If the `migrations` directory already exists, do not run `flask db init` again. Use `flask db migrate -m "description"` and `flask db upgrade`.

Open http://127.0.0.1:5000

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Admin | admin@smartrx.local | Admin@123 |
| Doctor 1 | doctor1@smartrx.local | Doctor@123 |
| Doctor 2 | doctor2@smartrx.local | Doctor@123 |
| Doctor 3 | doctor3@smartrx.local | Doctor@123 |
| Patient 1 | patient1@smartrx.local | Patient@123 |
| Patient 2 | patient2@smartrx.local | Patient@123 |
| Patient 3 | patient3@smartrx.local | Patient@123 |
| Patient 4 | patient4@smartrx.local | Patient@123 |
| Patient 5 | patient5@smartrx.local | Patient@123 |
| Pharmacy 1–5 | pharmacy1@smartrx.local … pharmacy5@smartrx.local | Pharmacy@123 |

All demo doctor and pharmacy users are pre-verified. In normal registration, patients can self-register; doctor and pharmacy onboarding should be handled by admin. Do not expose demo credentials on a public deployment.

## Main workflow

1. Doctor logs in → `/doctor/prescriptions` → selects a patient and adds medicine rows.
2. The server generates an RX code, a random QR token and a QR image. The QR contains only the opaque token and expires in 48 hours.
3. Patient logs in → `/patient/scan` → uses webcam, uploads QR image, or enters RX code. The server checks ownership, expiry and reuse.
4. Patient views the prescription and warning list, then enters coordinates or uses browser geolocation.
5. The pharmacy list shows distance, availability, rating, estimated delivery minutes and a simple ranking score.
6. Patient chooses Home Delivery or Store Pickup. A successful order consumes the QR and reduces non-expired stock in a transaction.
7. Pharmacy updates order status. Patient tracking page refreshes every 10 seconds.
8. Pharmacy verifies the handover OTP and completes the order.

## Demo notes / simplified behaviour
- “Nearby pharmacies” means the pharmacies seeded in this demo database; it is not a live directory of every medical shop in Indore.
- Delivery time is a stored estimate, not live GPS tracking.
- OTP is displayed to the patient in the demo order confirmation flash message. A production system should send it through a verified SMS/email provider and must not expose it to the pharmacy in advance.
- Ranking formula is a simple heuristic. It uses normalized availability, distance, rating and price factors to keep values bounded; it is not a medical recommendation.
- Schedule H/H1 medicines are flagged by their schedule type in the database. A real dispensing workflow needs a pharmacist approval and prescription compliance check. The academic UI still requires pharmacy-side review before processing.
- Interaction JSON contains only a few illustrative pairs and is not comprehensive.
- QR scanning via webcam generally requires localhost or HTTPS browser context. If webcam permission is unavailable, upload the QR image or enter the RX code.
- MySQL is the configured runtime database. Tests use SQLite in-memory for isolated test execution.

## Tests

```bash
pytest -q
```

Tests cover random QR token generation, expiry/reuse flags, stock quantity checks, distance calculation, allergy matching, login, role protection and patient registration.

## Project layout

```text
smart_rx/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── models.py
│   ├── blueprints/
│   ├── services/
│   ├── templates/
│   ├── static/
│   └── data/interactions.json
├── tests/
├── seed_data.py
├── run.py
├── requirements.txt
├── .env.example
└── README.md
```
