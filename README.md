# Hospital Management System V2

A role-based Hospital Management System built with:

- Flask (API + entry template)
- Vue.js (single-page UI)
- SQLite (database)
- Redis (cache + Celery broker/backend)
- Celery + Celery Beat (scheduled and async jobs)
- Bootstrap (UI styling)

## Roles Implemented

- Admin (pre-created programmatically)
- Doctor
- Patient

## Core Capabilities

- Role-based login using JWT
- Patient registration and profile updates
- Admin dashboard with totals (doctors, patients, appointments)
- Admin doctor management and user blacklisting
- Doctor availability management for next 7 days
- Appointment booking, rescheduling, cancellation
- Conflict prevention: one doctor cannot have multiple appointments at same date-time
- Treatment recording: diagnosis, prescription, notes, next visit
- Patient treatment history and doctor patient history
- Caching for public department list and doctor search
- Celery jobs:
  - Daily reminders task
  - Monthly doctor activity report (HTML)
  - User-triggered async CSV export of patient treatment history

## Project Structure

- `app/` Flask application package
- `app/routes/` role-specific API blueprints
- `app/tasks/` Celery task definitions
- `templates/index.html` Vue + Bootstrap single-page frontend
- `exports/` generated report and CSV files
- `run.py` Flask app entry
- `celery_worker.py` Celery app entry

## Local Setup

### 1. Install and start Redis

On Ubuntu:

```bash
sudo apt update
sudo apt install redis-server -y
sudo systemctl start redis-server
```

### 2. Create Python environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` values if needed.

### 4. Run Flask app

```bash
.venv/bin/python run.py
```

Open: `http://127.0.0.1:5000`

### 5. Run Celery worker (new terminal)

```bash
celery -A app.extensions.celery_app worker --loglevel=info
```

### 6. Run Celery beat scheduler (new terminal)

```bash
celery -A app.extensions.celery_app beat --loglevel=info
```

## Default Admin Account

Created automatically on first run (programmatically):

- Username: `admin`
- Password: `admin123`

You can change this through `.env`:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `ADMIN_EMAIL`

## API Endpoints (Summary)

### Auth

- `POST /api/auth/register` (patient only)
- `POST /api/auth/login`
- `GET /api/auth/me`

### Public

- `GET /api/public/departments`
- `GET /api/public/doctors?specialization=&date=YYYY-MM-DD`

### Admin

- `GET /api/admin/dashboard`
- `POST /api/admin/doctors`
- `PUT /api/admin/doctors/<doctor_id>`
- `GET /api/admin/doctors`
- `GET /api/admin/appointments`
- `PUT /api/admin/appointments/<appointment_id>/status`
- `GET /api/admin/search?q=<query>&type=doctor|patient|all`
- `PUT /api/admin/users/<user_id>/active`

### Doctor

- `GET /api/doctor/dashboard`
- `POST /api/doctor/availability`
- `GET /api/doctor/appointments`
- `PUT /api/doctor/appointments/<appointment_id>/status`
- `PUT /api/doctor/appointments/<appointment_id>/treatment`
- `GET /api/doctor/patients/<patient_id>/history`

### Patient

- `GET /api/patient/dashboard`
- `GET /api/patient/appointments`
- `POST /api/patient/appointments`
- `PUT /api/patient/appointments/<appointment_id>/reschedule`
- `PUT /api/patient/appointments/<appointment_id>/cancel`
- `GET /api/patient/history`
- `PUT /api/patient/profile`
- `POST /api/patient/export/treatments`
- `GET /api/patient/export/status/<task_id>`

## Notes on Reminder/Report Channels

The scheduled tasks currently generate console output/files for local demo.
You can extend them with real integrations (SMTP, webhook, SMS provider) in `app/tasks/jobs.py`.

## Working Local URL

- Main app: `http://127.0.0.1:5000`
- Health check: `http://127.0.0.1:5000/health`

## Step-by-Step Run Commands (Copy/Paste)

```bash
cd /home/abhishek/Hospital_Management_System_V2_23f2004693
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
sudo systemctl start redis-server
```

Terminal 1:

```bash
cd /home/abhishek/Hospital_Management_System_V2_23f2004693
.venv/bin/python run.py
```

Terminal 2:

```bash
cd /home/abhishek/Hospital_Management_System_V2_23f2004693
celery -A app.extensions.celery_app worker --loglevel=info
```

Terminal 3:

```bash
cd /home/abhishek/Hospital_Management_System_V2_23f2004693
celery -A app.extensions.celery_app beat --loglevel=info
```

## MAD-2 Compliance Checklist

- Flask API (Python backend): Implemented using Flask app factory and role-specific blueprints in `app/routes/`.
- Vue.js frontend: Implemented in `templates/index.html` as a dynamic role-based SPA.
- Bootstrap styling: Implemented throughout the UI in `templates/index.html`.
- SQLite database: Configured in `app/config.py` and modeled in `app/models.py`.
- Programmatic DB creation only: Done with `db.create_all()` in `app/__init__.py`.
- Pre-existing admin user: Seeded automatically in `app/__init__.py`.
- Role-based auth: JWT + role guards implemented in `app/routes/auth_routes.py` and `app/security.py`.
- Admin dashboard and management: Implemented in `app/routes/admin_routes.py` + admin UI in `templates/index.html`.
- Doctor workflow and treatment updates: Implemented in `app/routes/doctor_routes.py` + doctor UI in `templates/index.html`.
- Patient registration/booking/history/profile: Implemented in `app/routes/patient_routes.py` + patient UI in `templates/index.html`.
- Appointment conflict prevention: Unique constraint and checks in `app/models.py` and `app/routes/patient_routes.py`.
- Redis caching with expiry: Implemented using Flask-Caching in `app/config.py` and `app/routes/public_routes.py`.
- Celery batch jobs: Daily reminder, monthly report, and CSV export implemented in `app/tasks/jobs.py`.

## Clean Viva Demo Flow (8-10 Minutes)

1. Start all three services (Flask, Celery worker, Celery beat) and open `http://127.0.0.1:5000`.
2. Show login page and explain role-based entry.
3. Login as Admin (`admin/admin123`), show dashboard counters.
4. Create one doctor profile and show doctor listing + blacklist toggle.
5. Use admin search to find doctors/patients.
6. Register a new patient from the registration form.
7. Login as Doctor, add next-7-day availability slot.
8. Login as Patient, search/select doctor and book an appointment.
9. Login as Doctor, mark appointment complete and add treatment details.
10. Login as Patient, show treatment history and trigger CSV export.
11. Show generated files in `exports/` (CSV and monthly HTML report).
12. Explain where caching and Celery jobs are configured (`app/config.py`, `app/tasks/jobs.py`).
