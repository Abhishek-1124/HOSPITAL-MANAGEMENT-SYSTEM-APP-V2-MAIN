from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from ..extensions import db
from ..models import Appointment, DoctorAvailability, Treatment, User
from ..security import role_required
from ..serializers import appointment_dict

doctor_bp = Blueprint("doctor", __name__)


def _doctor_profile_or_404():
    user = User.query.get_or_404(get_jwt_identity())
    if not user.doctor_profile:
        return None
    return user.doctor_profile


@doctor_bp.get("/dashboard")
@role_required("doctor")
def dashboard():
    doctor = _doctor_profile_or_404()
    if doctor is None:
        return jsonify({"error": "Doctor profile not found"}), 404

    today = datetime.utcnow()
    week_end = today + timedelta(days=7)

    upcoming = (
        Appointment.query.filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_datetime >= today,
            Appointment.appointment_datetime <= week_end,
            Appointment.status == "Booked",
        )
        .order_by(Appointment.appointment_datetime.asc())
        .all()
    )

    patients = sorted(
        {
            appt.patient.user.full_name: {
                "patient_id": appt.patient.id,
                "patient_name": appt.patient.user.full_name,
                "contact_number": appt.patient.user.contact_number,
            }
            for appt in Appointment.query.filter_by(doctor_id=doctor.id).all()
        }.values(),
        key=lambda x: x["patient_name"],
    )

    return jsonify(
        {
            "upcoming_appointments": [appointment_dict(a) for a in upcoming],
            "patients": patients,
        }
    )


@doctor_bp.post("/availability")
@role_required("doctor")
def upsert_availability():
    doctor = _doctor_profile_or_404()
    if doctor is None:
        return jsonify({"error": "Doctor profile not found"}), 404

    data = request.get_json() or {}
    slots = data.get("slots", [])
    if not isinstance(slots, list) or not slots:
        return jsonify({"error": "slots array is required"}), 400

    today = date.today()
    week_limit = today + timedelta(days=7)

    for slot in slots:
        try:
            slot_date = datetime.strptime(slot["date"], "%Y-%m-%d").date()
            start_time = datetime.strptime(slot["start_time"], "%H:%M").time()
            end_time = datetime.strptime(slot["end_time"], "%H:%M").time()
        except (KeyError, ValueError):
            return jsonify({"error": "Invalid slot format"}), 400

        if slot_date < today or slot_date > week_limit:
            return jsonify({"error": "Availability must be within the next 7 days"}), 400
        if end_time <= start_time:
            return jsonify({"error": "end_time must be after start_time"}), 400

        existing = DoctorAvailability.query.filter_by(
            doctor_id=doctor.id,
            date=slot_date,
            start_time=start_time,
            end_time=end_time,
        ).first()

        if existing:
            existing.is_available = bool(slot.get("is_available", True))
        else:
            db.session.add(
                DoctorAvailability(
                    doctor_id=doctor.id,
                    date=slot_date,
                    start_time=start_time,
                    end_time=end_time,
                    is_available=bool(slot.get("is_available", True)),
                )
            )

    db.session.commit()
    return jsonify({"message": "Availability updated"})


@doctor_bp.get("/appointments")
@role_required("doctor")
def list_doctor_appointments():
    doctor = _doctor_profile_or_404()
    if doctor is None:
        return jsonify({"error": "Doctor profile not found"}), 404

    appointments = (
        Appointment.query.filter_by(doctor_id=doctor.id)
        .order_by(Appointment.appointment_datetime.desc())
        .all()
    )
    return jsonify({"appointments": [appointment_dict(a) for a in appointments]})


@doctor_bp.put("/appointments/<int:appointment_id>/status")
@role_required("doctor")
def set_appointment_status(appointment_id):
    doctor = _doctor_profile_or_404()
    if doctor is None:
        return jsonify({"error": "Doctor profile not found"}), 404
    appointment = Appointment.query.get_or_404(appointment_id)

    if appointment.doctor_id != doctor.id:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    status = data.get("status")
    if status not in {"Completed", "Cancelled"}:
        return jsonify({"error": "Doctor can only set Completed or Cancelled"}), 400

    appointment.status = status
    db.session.commit()
    return jsonify({"appointment": appointment_dict(appointment)})


@doctor_bp.put("/appointments/<int:appointment_id>/treatment")
@role_required("doctor")
def update_treatment(appointment_id):
    doctor = _doctor_profile_or_404()
    if doctor is None:
        return jsonify({"error": "Doctor profile not found"}), 404
    appointment = Appointment.query.get_or_404(appointment_id)

    if appointment.doctor_id != doctor.id:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    diagnosis = data.get("diagnosis")
    if not diagnosis:
        return jsonify({"error": "diagnosis is required"}), 400

    next_visit = data.get("next_visit_date")
    next_visit_date = None
    if next_visit:
        try:
            next_visit_date = datetime.strptime(next_visit, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid next_visit_date"}), 400

    if appointment.treatment:
        treatment = appointment.treatment
        treatment.diagnosis = diagnosis
        treatment.prescription = data.get("prescription")
        treatment.notes = data.get("notes")
        treatment.next_visit_date = next_visit_date
    else:
        treatment = Treatment(
            appointment_id=appointment.id,
            diagnosis=diagnosis,
            prescription=data.get("prescription"),
            notes=data.get("notes"),
            next_visit_date=next_visit_date,
        )
        db.session.add(treatment)

    appointment.status = "Completed"
    db.session.commit()
    return jsonify({"appointment": appointment_dict(appointment)})


@doctor_bp.get("/patients/<int:patient_id>/history")
@role_required("doctor")
def patient_history(patient_id):
    doctor = _doctor_profile_or_404()
    if doctor is None:
        return jsonify({"error": "Doctor profile not found"}), 404
    appointments = (
        Appointment.query.filter_by(doctor_id=doctor.id, patient_id=patient_id)
        .order_by(Appointment.appointment_datetime.desc())
        .all()
    )
    return jsonify({"history": [appointment_dict(a) for a in appointments]})
