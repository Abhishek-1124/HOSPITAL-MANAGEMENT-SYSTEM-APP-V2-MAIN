from app import create_app
from app.extensions import celery_app

flask_app = create_app()

if __name__ == "__main__":
    celery_app.start()
