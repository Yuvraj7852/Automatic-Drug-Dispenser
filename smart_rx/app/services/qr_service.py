import secrets
import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import qrcode
from flask import current_app

def create_qr_token():
    """Generate cryptographically secure 32-byte opaque token for prescription QR."""
    return secrets.token_urlsafe(32)

def create_qr_image(token, filename, rx_code=None):
    """
    Generate QR code image file in app/static/qr_codes.
    The QR payload stores the opaque token (or structured token) for privacy & security.
    """
    target = Path(current_app.root_path) / "static" / "qr_codes"
    target.mkdir(parents=True, exist_ok=True)
    image_path = target / filename

    # Payload: we save the token
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(image_path)

    return f"qr_codes/{filename}"

def ensure_qr_image(prescription):
    """Ensures that the QR code image exists on disk; creates it if missing."""
    target = Path(current_app.root_path) / "static" / "qr_codes"
    target.mkdir(parents=True, exist_ok=True)
    filename = f"{prescription.rx_code}.png"
    image_path = target / filename
    if not image_path.exists():
        create_qr_image(prescription.qr_token, filename, prescription.rx_code)
    return f"qr_codes/{filename}"

def parse_qr_payload(raw_input):
    """
    Intelligently extracts token and/or rx_code from any scanned text format:
    - Raw token: 'aB3_...'
    - Full URL: 'http://.../patient/scan?token=abc' or 'http://.../verify/abc'
    - Rx Code: 'RXDEMO0001' or 'RX202611160001'
    - JSON payload: '{"token": "...", "rx_code": "..."}'
    """
    if not raw_input:
        return None, None
    raw = str(raw_input).strip()

    # 1. JSON
    if raw.startswith("{") and raw.endswith("}"):
        try:
            data = json.loads(raw)
            return data.get("token"), data.get("rx_code")
        except Exception:
            pass

    # 2. URL parsing
    if "://" in raw or "token=" in raw or "rx_code=" in raw or "/verify/" in raw:
        try:
            parsed = urlparse(raw)
            qs = parse_qs(parsed.query)
            token = qs.get("token", [None])[0]
            rx_code = qs.get("rx_code", [None])[0] or qs.get("code", [None])[0]
            if not token and "/verify/" in parsed.path:
                token = parsed.path.split("/verify/")[-1].strip("/")
            if not token and "/scan/" in parsed.path:
                token = parsed.path.split("/scan/")[-1].strip("/")
            if token or rx_code:
                return token, rx_code
        except Exception:
            pass

    # 3. Rx Code direct match (starts with RX)
    if raw.upper().startswith("RX") and len(raw) <= 30:
        return None, raw.upper()

    # 4. Default: token string
    return raw, None

def expiry_time():
    """Prescription QR valid for 48 hours."""
    return datetime.utcnow() + timedelta(hours=48)
