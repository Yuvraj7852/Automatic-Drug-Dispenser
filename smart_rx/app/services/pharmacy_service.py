from math import radians, sin, cos, asin, sqrt
from datetime import date
from ..models import Pharmacy, PharmacyStock

def haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * radius * asin(sqrt(a))

def active_stock(pharmacy_id, medicine_id):
    rows = PharmacyStock.query.filter_by(
        pharmacy_id=pharmacy_id, medicine_id=medicine_id
    ).filter(PharmacyStock.quantity > 0, PharmacyStock.expiry_date >= date.today()).all()
    return sum(row.quantity for row in rows)

def rank_pharmacies(prescription, user_lat, user_lon):
    results = []
    requested = {item.medicine_id: item.quantity for item in prescription.items}
    for pharmacy in Pharmacy.query.filter_by(is_open=True).all():
        distance = haversine_km(user_lat, user_lon, pharmacy.latitude, pharmacy.longitude)
        available_count = 0
        available_all = True
        total_price = 0.0
        for medicine_id, qty in requested.items():
            stock_qty = active_stock(pharmacy.id, medicine_id)
            if stock_qty >= qty:
                available_count += 1
                medicine = next(i.medicine for i in prescription.items if i.medicine_id == medicine_id)
                total_price += float(medicine.price) * qty
            else:
                available_all = False
        availability_ratio = available_count / max(len(requested), 1)
        # Normalize factors to keep the score useful and bounded.
        distance_factor = 1 / max(distance, 0.1)
        distance_factor = min(distance_factor, 1.0)
        rating_factor = min(max(pharmacy.rating, 0), 5) / 5
        price_factor = 1 / max(total_price, 1) if available_all else 0
        score = 0.4 * availability_ratio + 0.25 * distance_factor + 0.2 * rating_factor + 0.15 * price_factor
        if available_all:
            availability = "All available"
        elif available_count:
            availability = f"{available_count} available"
        else:
            availability = "Not available"
        results.append({
            "pharmacy": pharmacy, "distance": round(distance, 2),
            "availability": availability, "all_available": available_all,
            "available_count": available_count, "total_price": round(total_price, 2),
            "score": score
        })
    return sorted(results, key=lambda row: row["score"], reverse=True)
