from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from ..extensions import bcrypt, db
from ..models import PatientProfile, User
from ..serializers import user_dict

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register_patient():
    data = request.get_json() or {}
    required = ["username", "email", "password", "full_name"]
    missing = [field for field in required if not data.get(field)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    if User.query.filter(
        (User.username == data["username"]) | (User.email == data["email"])
    ).first():
        return jsonify({"error": "Username or email already exists"}), 400

    user = User(
        username=data["username"],
        email=data["email"],
        password_hash=bcrypt.generate_password_hash(data["password"]).decode("utf-8"),
        role="patient",
        full_name=data["full_name"],
        contact_number=data.get("contact_number"),
    )
    db.session.add(user)
    db.session.flush()

    date_of_birth = None
    if data.get("date_of_birth"):
        try:
            date_of_birth = datetime.strptime(data["date_of_birth"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid date_of_birth. Use YYYY-MM-DD"}), 400

    profile = PatientProfile(
        user_id=user.id,
        date_of_birth=date_of_birth,
        gender=data.get("gender"),
        address=data.get("address"),
    )
    db.session.add(profile)
    db.session.commit()

    return jsonify({"message": "Patient registered successfully"}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    username = data.get("username", "")
    password = data.get("password", "")

    user = User.query.filter_by(username=username).first()
    if not user or not user.is_active:
        return jsonify({"error": "Invalid credentials"}), 401

    if not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=user.id, additional_claims={"role": user.role})
    return jsonify({"token": token, "user": user_dict(user)})


@auth_bp.get("/me")
@jwt_required()
def me():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    if not user or not user.is_active:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"user": user_dict(user)})
