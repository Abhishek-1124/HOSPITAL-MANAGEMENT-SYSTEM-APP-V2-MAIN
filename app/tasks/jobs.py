import csv
import os
from datetime import date, datetime, timedelta

from ..extensions import celery_app
from ..models import Appointment, DoctorProfile, User


def _exports_dir():
    root = os.getcwd()
    out = os.path.join(root, "exports")
    os.makedirs(out, exist_ok=True)
    return out


@celery_app.task(name="app.tasks.jobs.send_daily_reminders")
def send_daily_reminders():
    today = date.today()
    tomorrow = today + timedelta(days=1)

    upcoming = Appointment.query.filter(
        Appointment.appointment_datetime >= datetime.combine(today, datetime.min.time()),
        Appointment.appointment_datetime < datetime.combine(tomorrow, datetime.min.time()),
        Appointment.status == "Booked",
    ).all()

    # Replace this print with your email/SMS/Google Chat webhook integration.
    for appt in upcoming:
        print(
            f"Reminder: {appt.patient.user.full_name} has an appointment with "
            f"Dr. {appt.doctor.user.full_name} at {appt.appointment_datetime}."
        )

    return {"reminders_sent": len(upcoming), "date": today.isoformat()}


@celery_app.task(name="app.tasks.jobs.send_monthly_doctor_reports")
def send_monthly_doctor_reports():
    now = datetime.utcnow()
    first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    doctors = DoctorProfile.query.all()
    generated = 0

    for doctor in doctors:
        appointments = Appointment.query.filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_datetime >= first_day,
            Appointment.status == "Completed",
        ).all()

        report_path = os.path.join(
            _exports_dir(),
            f"doctor_report_{doctor.id}_{now.strftime('%Y_%m')}.html",
        )

        rows = "".join(
            [
                "<tr>"
                f"<td>{a.id}</td>"
                f"<td>{a.patient.user.full_name}</td>"
                f"<td>{a.appointment_datetime}</td>"
                f"<td>{a.treatment.diagnosis if a.treatment else '-'}</td>"
                f"<td>{a.treatment.prescription if a.treatment else '-'}</td>"
                "</tr>"
                for a in appointments
            ]
        )

        html = f"""
        <html>
        <head><title>Monthly Activity Report</title></head>
        <body>
            <h2>Monthly Activity Report - Dr. {doctor.user.full_name}</h2>
            <p>Generated at: {now.isoformat()}</p>
            <table border=\"1\" cellpadding=\"6\" cellspacing=\"0\">
                <thead>
                    <tr>
                        <th>Appointment ID</th>
                        <th>Patient</th>
                        <th>Date/Time</th>
                        <th>Diagnosis</th>
                        <th>Prescription</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </body>
        </html>
        """

        with open(report_path, "w", encoding="utf-8") as file:
            file.write(html)
        generated += 1

    return {"reports_generated": generated, "month": now.strftime("%Y-%m")}


@celery_app.task(name="app.tasks.jobs.export_treatments_csv")
def export_treatments_csv(user_id):
    user = User.query.get(user_id)
    if not user or user.role != "patient" or not user.patient_profile:
        raise ValueError("Invalid patient")

    patient = user.patient_profile
    appointments = (
        Appointment.query.filter_by(patient_id=patient.id)
        .order_by(Appointment.appointment_datetime.desc())
        .all()
    )

    filename = f"treatment_export_user_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.csv"
    file_path = os.path.join(_exports_dir(), filename)

    with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [
                "user_id",
                "username",
                "doctor_name",
                "appointment_date",
                "status",
                "diagnosis",
                "prescription",
                "notes",
                "next_visit_suggested",
            ]
        )

        for appt in appointments:
            treatment = appt.treatment
            writer.writerow(
                [
                    user.id,
                    user.username,
                    appt.doctor.user.full_name,
                    appt.appointment_datetime.isoformat(),
                    appt.status,
                    treatment.diagnosis if treatment else "",
                    treatment.prescription if treatment else "",
                    treatment.notes if treatment else "",
                    (
                        treatment.next_visit_date.isoformat()
                        if treatment and treatment.next_visit_date
                        else ""
                    ),
                ]
            )

    # Replace this return payload with a notification dispatch (mail/chat/SMS) if needed.
    return {"message": "Export complete", "file_path": file_path}
