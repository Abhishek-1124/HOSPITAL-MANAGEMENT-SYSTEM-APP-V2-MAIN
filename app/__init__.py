import os

from flask import Flask, jsonify, render_template

from .config import Config
from .extensions import bcrypt, cache, celery_app, db, jwt
from .models import Department, PatientProfile, User


def _init_celery(app: Flask):
    celery_app.conf.update(app.config["CELERY"])

    class FlaskTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = FlaskTask


def _seed_admin_and_departments():
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@hospital.local")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    existing_admin = User.query.filter_by(role="admin").first()
    if not existing_admin:
        admin = User(
            username=admin_username,
            email=admin_email,
            password_hash=bcrypt.generate_password_hash(admin_password).decode("utf-8"),
            role="admin",
            full_name="System Admin",
        )
        db.session.add(admin)

    default_departments = [
        ("Cardiology", "Heart and blood vessel care"),
        ("Dermatology", "Skin, hair, and nail care"),
        ("Neurology", "Brain and nervous system"),
        ("Orthopedics", "Bone and joint treatments"),
        ("Pediatrics", "Child healthcare"),
        ("General Medicine", "Primary and preventive care"),
    ]

    for dept_name, desc in default_departments:
        exists = Department.query.filter_by(name=dept_name).first()
        if not exists:
            db.session.add(Department(name=dept_name, description=desc))

    db.session.commit()


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates")
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    cache.init_app(app)
    _init_celery(app)
    # Ensure Celery task modules are imported so tasks are registered.
    from .tasks import jobs  # noqa: F401

    from .routes.admin_routes import admin_bp
    from .routes.auth_routes import auth_bp
    from .routes.doctor_routes import doctor_bp
    from .routes.patient_routes import patient_bp
    from .routes.public_routes import public_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(public_bp, url_prefix="/api/public")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(doctor_bp, url_prefix="/api/doctor")
    app.register_blueprint(patient_bp, url_prefix="/api/patient")

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/<path:path>")
    def spa_fallback(path: str):
        if path.startswith("api/") or path == "health" or "." in path:
            return jsonify({"error": "Not found"}), 404
        return render_template("index.html")

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    with app.app_context():
        db.create_all()
        _seed_admin_and_departments()

    return app
