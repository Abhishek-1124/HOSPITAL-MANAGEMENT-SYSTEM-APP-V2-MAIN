from datetime import date, datetime, timedelta

import requests
from flask import Blueprint, jsonify, request

from ..extensions import cache
from ..models import Department, DoctorAvailability, DoctorProfile, User
from ..serializers import doctor_dict

public_bp = Blueprint("public", __name__)


@public_bp.get("/health-tip")
def health_tip():
    """Fetch a public health tip from an external API with local fallback."""
    fallback_tip = "Drink enough water daily and follow preventive checkups regularly."
    try:
        response = requests.get("https://api.adviceslip.com/advice", timeout=4)
        response.raise_for_status()
        payload = response.json()
        advice = (payload.get("slip") or {}).get("advice")
        if not advice:
            advice = fallback_tip
        return jsonify({"tip": advice, "source": "external"})
    except requests.RequestException:
        return jsonify({"tip": fallback_tip, "source": "fallback"})


@public_bp.get("/departments")
@cache.cached(timeout=300)
def departments():
    items = Department.query.order_by(Department.name.asc()).all()
    return jsonify(
        {
            "departments": [
                {
                    "id": d.id,
                    "name": d.name,
                    "description": d.description,
                    "doctors_registered": len(d.doctors),
                }
                for d in items
            ]
        }
    )


@public_bp.get("/doctors")
def doctors_search():
    specialization = request.args.get("specialization", "").strip()
    availability_date = request.args.get("date", "").strip()

    query = DoctorProfile.query.join(User, DoctorProfile.user_id == User.id).filter(
        User.is_active.is_(True)
    )
    if specialization:
        query = query.filter(DoctorProfile.specialization.ilike(f"%{specialization}%"))

    doctors = query.order_by(DoctorProfile.specialization.asc()).all()

    availability_lookup = {}
    if availability_date:
        try:
            target_date = datetime.strptime(availability_date, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        availabilities = DoctorAvailability.query.filter_by(date=target_date, is_available=True).all()
        availability_lookup = {av.doctor_id: True for av in availabilities}
    else:
        start = date.today()
        end = start + timedelta(days=7)
        availabilities = DoctorAvailability.query.filter(
            DoctorAvailability.date >= start,
            DoctorAvailability.date <= end,
            DoctorAvailability.is_available.is_(True),
        ).all()
        for av in availabilities:
            availability_lookup[av.doctor_id] = True

    payload = []
    for d in doctors:
        item = doctor_dict(d)
        item["has_availability"] = availability_lookup.get(d.id, False)
        payload.append(item)

    return jsonify({"doctors": payload})
