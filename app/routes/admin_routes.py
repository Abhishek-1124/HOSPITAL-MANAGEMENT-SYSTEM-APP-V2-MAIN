from flask import Blueprint, jsonify, request

from ..extensions import bcrypt, db
from ..models import Appointment, Department, DoctorProfile, PatientProfile, User
from ..security import role_required
from ..serializers import appointment_dict, doctor_dict, user_dict

admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/dashboard")
@role_required("admin")
def dashboard():
    total_doctors = User.query.filter_by(role="doctor", is_active=True).count()
    total_patients = User.query.filter_by(role="patient", is_active=True).count()
    total_appointments = Appointment.query.count()

    return jsonify(
        {
            "total_doctors": total_doctors,
            "total_patients": total_patients,
            "total_appointments": total_appointments,
        }
    )


@admin_bp.post("/doctors")
@role_required("admin")
def create_doctor():
    data = request.get_json() or {}
    required = [
        "username",
        "email",
        "password",
        "full_name",
        "specialization",
        "department_id",
    ]
    missing = [field for field in required if not data.get(field)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    if User.query.filter(
        (User.username == data["username"]) | (User.email == data["email"])
    ).first():
        return jsonify({"error": "Username or email already exists"}), 400

    department = Department.query.get(data["department_id"])
    if not department:
        return jsonify({"error": "Department not found"}), 404

    user = User(
        username=data["username"],
        email=data["email"],
        password_hash=bcrypt.generate_password_hash(data["password"]).decode("utf-8"),
        role="doctor",
        full_name=data["full_name"],
        contact_number=data.get("contact_number"),
    )
    db.session.add(user)
    db.session.flush()

    profile = DoctorProfile(
        user_id=user.id,
        department_id=data["department_id"],
        specialization=data["specialization"],
        bio=data.get("bio"),
        years_experience=int(data.get("years_experience", 0)),
    )
    db.session.add(profile)
    db.session.commit()

    return jsonify({"doctor": doctor_dict(profile)}), 201


@admin_bp.put("/doctors/<int:doctor_id>")
@role_required("admin")
def update_doctor(doctor_id):
    profile = DoctorProfile.query.get_or_404(doctor_id)
    data = request.get_json() or {}

    if "full_name" in data:
        profile.user.full_name = data["full_name"]
    if "contact_number" in data:
        profile.user.contact_number = data["contact_number"]
    if "specialization" in data:
        profile.specialization = data["specialization"]
    if "bio" in data:
        profile.bio = data["bio"]
    if "years_experience" in data:
        profile.years_experience = int(data["years_experience"])
    if "department_id" in data:
        department = Department.query.get(data["department_id"])
        if not department:
            return jsonify({"error": "Department not found"}), 404
        profile.department_id = department.id

    db.session.commit()
    return jsonify({"doctor": doctor_dict(profile)})


@admin_bp.get("/doctors")
@role_required("admin")
def list_doctors():
    doctors = DoctorProfile.query.order_by(DoctorProfile.created_at.desc()).all()
    return jsonify({"doctors": [doctor_dict(doc) for doc in doctors]})


@admin_bp.get("/appointments")
@role_required("admin")
def list_appointments():
    status = request.args.get("status")
    query = Appointment.query
    if status:
        query = query.filter_by(status=status)

    appointments = query.order_by(Appointment.appointment_datetime.desc()).all()
    return jsonify({"appointments": [appointment_dict(a) for a in appointments]})


@admin_bp.put("/appointments/<int:appointment_id>/status")
@role_required("admin")
def update_appointment_status(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    data = request.get_json() or {}
    status = data.get("status")
    valid = {"Booked", "Completed", "Cancelled"}
    if status not in valid:
        return jsonify({"error": "Invalid status"}), 400

    appointment.status = status
    db.session.commit()
    return jsonify({"appointment": appointment_dict(appointment)})


@admin_bp.get("/search")
@role_required("admin")
def search_people():
    query_text = request.args.get("q", "").strip()
    search_type = request.args.get("type", "all")

    result = {"doctors": [], "patients": []}
    if not query_text:
        return jsonify(result)

    if search_type in {"doctor", "all"}:
        doctors = (
            DoctorProfile.query.join(User)
            .filter(
                (User.full_name.ilike(f"%{query_text}%"))
                | (DoctorProfile.specialization.ilike(f"%{query_text}%"))
            )
            .all()
        )
        result["doctors"] = [doctor_dict(doc) for doc in doctors]

    if search_type in {"patient", "all"}:
        patients = (
            PatientProfile.query.join(User)
            .filter(
                (User.full_name.ilike(f"%{query_text}%"))
                | (User.username.ilike(f"%{query_text}%"))
                | (User.contact_number.ilike(f"%{query_text}%"))
            )
            .all()
        )
        result["patients"] = [user_dict(p.user) for p in patients]

    return jsonify(result)


@admin_bp.put("/users/<int:user_id>/active")
@role_required("admin")
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    if "is_active" not in data:
        return jsonify({"error": "is_active is required"}), 400

    if user.role == "admin":
        return jsonify({"error": "Cannot deactivate admin"}), 400

    user.is_active = bool(data["is_active"])
    db.session.commit()
    return jsonify({"user": user_dict(user)})
