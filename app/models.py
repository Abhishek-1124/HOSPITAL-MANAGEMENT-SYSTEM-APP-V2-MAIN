from datetime import datetime

from .extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class User(TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    contact_number = db.Column(db.String(20), nullable=True)

    doctor_profile = db.relationship("DoctorProfile", uselist=False, back_populates="user")
    patient_profile = db.relationship("PatientProfile", uselist=False, back_populates="user")


class Department(TimestampMixin, db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)

    doctors = db.relationship("DoctorProfile", back_populates="department")


class DoctorProfile(TimestampMixin, db.Model):
    __tablename__ = "doctor_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    specialization = db.Column(db.String(120), nullable=False, index=True)
    bio = db.Column(db.Text, nullable=True)
    years_experience = db.Column(db.Integer, default=0, nullable=False)

    user = db.relationship("User", back_populates="doctor_profile")
    department = db.relationship("Department", back_populates="doctors")
    availabilities = db.relationship("DoctorAvailability", back_populates="doctor")
    appointments = db.relationship("Appointment", back_populates="doctor")


class PatientProfile(TimestampMixin, db.Model):
    __tablename__ = "patient_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)

    user = db.relationship("User", back_populates="patient_profile")
    appointments = db.relationship("Appointment", back_populates="patient")


class DoctorAvailability(TimestampMixin, db.Model):
    __tablename__ = "doctor_availabilities"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor_profiles.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)

    doctor = db.relationship("DoctorProfile", back_populates="availabilities")


class Appointment(TimestampMixin, db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor_profiles.id"), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient_profiles.id"), nullable=False)
    appointment_datetime = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="Booked", index=True)
    reason = db.Column(db.Text, nullable=True)

    doctor = db.relationship("DoctorProfile", back_populates="appointments")
    patient = db.relationship("PatientProfile", back_populates="appointments")
    treatment = db.relationship("Treatment", uselist=False, back_populates="appointment")

    __table_args__ = (
        db.UniqueConstraint(
            "doctor_id",
            "appointment_datetime",
            name="uq_doctor_datetime",
        ),
    )


class Treatment(TimestampMixin, db.Model):
    __tablename__ = "treatments"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(
        db.Integer, db.ForeignKey("appointments.id"), unique=True, nullable=False
    )
    diagnosis = db.Column(db.Text, nullable=False)
    prescription = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    next_visit_date = db.Column(db.Date, nullable=True)

    appointment = db.relationship("Appointment", back_populates="treatment")
