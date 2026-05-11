def user_dict(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name,
        "contact_number": user.contact_number,
        "is_active": user.is_active,
    }


def doctor_dict(profile):
    return {
        "doctor_id": profile.id,
        "user_id": profile.user_id,
        "username": profile.user.username,
        "full_name": profile.user.full_name,
        "email": profile.user.email,
        "contact_number": profile.user.contact_number,
        "department": profile.department.name,
        "department_id": profile.department_id,
        "specialization": profile.specialization,
        "bio": profile.bio,
        "years_experience": profile.years_experience,
        "is_active": profile.user.is_active,
    }


def appointment_dict(appt):
    return {
        "appointment_id": appt.id,
        "doctor_id": appt.doctor_id,
        "doctor_name": appt.doctor.user.full_name,
        "patient_id": appt.patient_id,
        "patient_name": appt.patient.user.full_name,
        "appointment_datetime": appt.appointment_datetime.isoformat(),
        "status": appt.status,
        "reason": appt.reason,
        "treatment": treatment_dict(appt.treatment) if appt.treatment else None,
    }


def treatment_dict(treatment):
    return {
        "treatment_id": treatment.id,
        "appointment_id": treatment.appointment_id,
        "diagnosis": treatment.diagnosis,
        "prescription": treatment.prescription,
        "notes": treatment.notes,
        "next_visit_date": (
            treatment.next_visit_date.isoformat() if treatment.next_visit_date else None
        ),
    }
