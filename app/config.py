import os
from datetime import timedelta

from celery.schedules import crontab


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///hms.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_DEFAULT_TIMEOUT = 300

    CELERY = {
        "broker_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        "result_backend": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        "task_ignore_result": False,
        "beat_schedule": {
            "daily-patient-reminders": {
                "task": "app.tasks.jobs.send_daily_reminders",
                "schedule": crontab(hour=8, minute=0),
            },
            "monthly-doctor-reports": {
                "task": "app.tasks.jobs.send_monthly_doctor_reports",
                "schedule": crontab(day_of_month="1", hour=9, minute=0),
            },
        },
        "timezone": "UTC",
    }

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
