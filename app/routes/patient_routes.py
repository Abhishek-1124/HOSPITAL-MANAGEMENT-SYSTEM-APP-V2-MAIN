from datetime import date, datetime, timedelta

from celery.result import AsyncResult
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from ..extensions import db
from ..models import Appointment, Department, DoctorAvailability, DoctorProfile, User
from ..security import role_required
from ..serializers import appointment_dict, doctor_dict
from ..tasks.jobs import export_treatments_csv

patient_bp = Blueprint("patient", __name__)


def _patient_profile_or_404():
    user = User.query.get_or_404(get_jwt_identity())
    if not user.patient_profile:
        return None
    return user.patient_profile


def _parse_datetime(dt_str):
    try:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return None


def _doctor_available(doctor_id, appointment_dt):
    day = appointment_dt.date()
    time_slot = appointment_dt.time()
    return (
        DoctorAvailability.query.filter(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.date == day,
            DoctorAvailability.start_time <= time_slot,
            DoctorAvailability.end_time > time_slot,
            DoctorAvailability.is_available.is_(True),
        ).first()
        is not None
    )


@patient_bp.get("/dashboard")
@role_required("patient")
def dashboard():
    patient = _patient_profile_or_404()
    if patient is None:
        return jsonify({"error": "Patient profile not found"}), 404

    now = datetime.utcnow()
    week_end = now + timedelta(days=7)

    upcoming = (
        Appointment.query.filter(
            Appointment.patient_id == patient.id,
            Appointment.appointment_datetime >= now,
        )
        .order_by(Appointment.appointment_datetime.asc())
        .all()
    )

    history = (
        Appointment.query.filter(
            Appointment.patient_id == patient.id,
            Appointment.appointment_datetime < now,
        )
        .order_by(Appointment.appointment_datetime.desc())
        .all()
    )

    departments = Department.query.order_by(Department.name.asc()).all()

    doctors = (
        DoctorProfile.query.join(User, DoctorProfile.user_id == User.id)
        .filter(User.is_active.is_(True))
        .order_by(DoctorProfile.specialization.asc())
        .all()
    )
    doctors_payload = [doctor_dict(d) for d in doctors]

    availabilities = DoctorAvailability.query.filter(
        DoctorAvailability.date >= date.today(),
        DoctorAvailability.date <= date.today() + timedelta(days=7),
        DoctorAvailability.is_available.is_(True),
    ).all()
    availability_map = {}
    for av in availabilities:
        key = str(av.doctor_id)
        availability_map.setdefault(key, []).append(
            {
                "date": av.date.isoformat(),
                "start_time": av.start_time.strftime("%H:%M"),
                "end_time": av.end_time.strftime("%H:%M"),
            }
        )

    return jsonify(
        {
            "departments": [
                {
                    "id": d.id,
                    "name": d.name,
                    "description": d.description,
                }
                for d in departments
            ],
            "doctors": doctors_payload,
            "doctor_availability": availability_map,
            "upcoming_appointments": [appointment_dict(a) for a in upcoming],
            "past_appointments": [appointment_dict(a) for a in history],
        }
    )


@patient_bp.get("/appointments")
@role_required("patient")
def appointments():
    patient = _patient_profile_or_404()
    if patient is None:
        return jsonify({"error": "Patient profile not found"}), 404
    items = (
        Appointment.query.filter_by(patient_id=patient.id)
        .order_by(Appointment.appointment_datetime.desc())
        .all()
    )
    return jsonify({"appointments": [appointment_dict(a) for a in items]})


@patient_bp.post("/appointments")
@role_required("patient")
def book_appointment():
    patient = _patient_profile_or_404()
    if patient is None:
        return jsonify({"error": "Patient profile not found"}), 404
    data = request.get_json() or {}

    doctor_id = data.get("doctor_id")
    appointment_dt = _parse_datetime(data.get("appointment_datetime"))
    if not doctor_id or not appointment_dt:
        return jsonify({"error": "doctor_id and appointment_datetime are required"}), 400

    doctor = DoctorProfile.query.get(doctor_id)
    if not doctor or not doctor.user.is_active:
        return jsonify({"error": "Doctor not found"}), 404

    if not _doctor_available(doctor_id, appointment_dt):
        return jsonify({"error": "Doctor is not available at this time"}), 400

    existing = Appointment.query.filter_by(
        doctor_id=doctor_id,
        appointment_datetime=appointment_dt,
    ).first()
    if existing and existing.status == "Booked":
        return jsonify({"error": "This slot is already booked"}), 400

    appointment = Appointment(
        doctor_id=doctor_id,
        patient_id=patient.id,
        appointment_datetime=appointment_dt,
        status="Booked",
        reason=data.get("reason"),
    )
    db.session.add(appointment)
    db.session.commit()
    return jsonify({"appointment": appointment_dict(appointment)}), 201


@patient_bp.put("/appointments/<int:appointment_id>/reschedule")
@role_required("patient")
def reschedule_appointment(appointment_id):
    patient = _patient_profile_or_404()
    if patient is None:
        return jsonify({"error": "Patient profile not found"}), 404
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.patient_id != patient.id:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    new_dt = _parse_datetime(data.get("appointment_datetime"))
    if not new_dt:
        return jsonify({"error": "Invalid appointment_datetime"}), 400

    if appointment.status != "Booked":
        return jsonify({"error": "Only booked appointments can be rescheduled"}), 400

    if not _doctor_available(appointment.doctor_id, new_dt):
        return jsonify({"error": "Doctor is not available at this time"}), 400

    conflict = Appointment.query.filter_by(
        doctor_id=appointment.doctor_id,
        appointment_datetime=new_dt,
        status="Booked",
    ).first()
    if conflict and conflict.id != appointment.id:
        return jsonify({"error": "This slot is already booked"}), 400

    appointment.appointment_datetime = new_dt
    db.session.commit()
    return jsonify({"appointment": appointment_dict(appointment)})


@patient_bp.put("/appointments/<int:appointment_id>/cancel")
@role_required("patient")
def cancel_appointment(appointment_id):
    patient = _patient_profile_or_404()
    if patient is None:
        return jsonify({"error": "Patient profile not found"}), 404
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.patient_id != patient.id:
        return jsonify({"error": "Forbidden"}), 403

    appointment.status = "Cancelled"
    db.session.commit()
    return jsonify({"appointment": appointment_dict(appointment)})


@patient_bp.get("/history")
@role_required("patient")
def treatment_history():
    patient = _patient_profile_or_404()
    if patient is None:
        return jsonify({"error": "Patient profile not found"}), 404
    items = (
        Appointment.query.filter_by(patient_id=patient.id)
        .order_by(Appointment.appointment_datetime.desc())
        .all()
    )
    return jsonify({"history": [appointment_dict(a) for a in items]})


@patient_bp.put("/profile")
@role_required("patient")
def update_profile():
    patient = _patient_profile_or_404()
    if patient is None:
        return jsonify({"error": "Patient profile not found"}), 404
    data = request.get_json() or {}

    if "full_name" in data:
        patient.user.full_name = data["full_name"]
    if "contact_number" in data:
        patient.user.contact_number = data["contact_number"]
    if "address" in data:
        patient.address = data["address"]
    if "gender" in data:
        patient.gender = data["gender"]
    if "date_of_birth" in data and data["date_of_birth"]:
        try:
            patient.date_of_birth = datetime.strptime(data["date_of_birth"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date_of_birth"}), 400

    db.session.commit()
    return jsonify({"message": "Profile updated"})


@patient_bp.post("/export/treatments")
@role_required("patient")
def trigger_export():
    patient = _patient_profile_or_404()
    if patient is None:
        return jsonify({"error": "Patient profile not found"}), 404
    task = export_treatments_csv.delay(patient.user_id)
    return jsonify({"task_id": task.id, "message": "Export started"}), 202


@patient_bp.get("/export/status/<task_id>")
@role_required("patient")
def export_status(task_id):
    task = AsyncResult(task_id, app=export_treatments_csv.app)

    if task.state == "PENDING":
        return jsonify({"state": task.state, "message": "Task pending"})
    if task.state == "SUCCESS":
        return jsonify({"state": task.state, "result": task.result})
    if task.state == "FAILURE":
        return jsonify({"state": task.state, "error": str(task.info)}), 500

    return jsonify({"state": task.state, "message": "Task running"})
