from flask import Flask, jsonify, request, Response
import random
import string
import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import datetime
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, JWTManager, get_jwt_identity
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr, ValidationError, Field
from typing import Tuple, Dict, Any, Optional, Union
from flask_cors import CORS  # Import CORS

# Type alias for Flask Response
ResponseReturnValue = Tuple[Response, int] | Response

load_dotenv()

app: Flask = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# --- Configurations ---
app.config['SECRET_KEY'] = os.environ.get('AUTH_SERVICE_SECRET_KEY', 'default-auth-secret-key-change-me')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'default-jwt-secret-key-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://appuser:secret@db:5432/appdb')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Extensions Initialization ---
db: SQLAlchemy = SQLAlchemy(app)
db.metadata.schema = 'auth'  # Set schema for all tables in this service
migrate: Migrate = Migrate(app, db, version_table_schema='auth')  # Isolate migration version table
bcrypt: Bcrypt = Bcrypt(app)
jwt: JWTManager = JWTManager(app)

# --- Models (SQLAlchemy) ---
class User(db.Model):
    __tablename__ = 'users'
    id: int = db.Column(db.Integer, primary_key=True)
    name: Optional[str] = db.Column(db.String(100), nullable=True)
    email: str = db.Column(db.String(255), unique=True, nullable=False)
    password_hash: str = db.Column(db.String(255), nullable=False)
    google_access_token: Optional[str] = db.Column(db.Text, nullable=True)
    google_refresh_token: Optional[str] = db.Column(db.Text, nullable=True)
    google_token_expiry: Optional[datetime.datetime] = db.Column(db.DateTime, nullable=True)
    created_at: datetime.datetime = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at: datetime.datetime = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def __repr__(self) -> str:
        return f'<User {self.email}>'

# TODO: T23 - Implement Secure User Data Storage
# - Add table encryption for sensitive user data
# - Implement additional user profile fields (preferences, profile picture, etc.)
# - Add account verification via email
# - Create separate UserSession model to track and manage active sessions
# - Add user preferences for notifications and privacy settings
# - Improve password hashing with adaptive work factors
# - Consider GDPR compliance features (data export, deletion, etc.)

# --- Pydantic Schemas for Validation ---
class RegisterSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: Optional[str] = None

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

# --- API Endpoints ---

@app.route('/api/v1/auth/health', methods=['GET'])
def health_check() -> ResponseReturnValue:
    return jsonify({"status": "Auth service is running"}), 200

@app.route('/api/v1/auth/register', methods=['POST'])
def register() -> ResponseReturnValue:
    try:
        data = RegisterSchema(**request.get_json())
    except ValidationError as e:
        return jsonify({"error": "Invalid input", "details": e.errors()}), 400
    except Exception:
         return jsonify({"error": "Invalid JSON data"}), 400

    existing_user: Optional[User] = User.query.filter_by(email=data.email).first()
    if existing_user:
        return jsonify({"error": "Email already exists"}), 409

    hashed_password: str = bcrypt.generate_password_hash(data.password).decode('utf-8')

    new_user = User(
        email=data.email,
        password_hash=hashed_password,
        name=data.name
    )
    try:
        db.session.add(new_user)
        db.session.commit()
        # Return user info (excluding password)
        user_info: Dict[str, Any] = {
            "id": new_user.id, 
            "email": new_user.email, 
            "name": new_user.name
        }
        return jsonify({
            "message": "User registered successfully", 
            "user": user_info
        }), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Registration DB error: {e}") # Use app logger
        return jsonify({"error": "Registration failed due to server error"}), 500


@app.route('/api/v1/auth/login', methods=['POST'])
def login() -> ResponseReturnValue:
    try:
        data = LoginSchema(**request.get_json())
    except ValidationError as e:
        return jsonify({"error": "Invalid input", "details": e.errors()}), 400
    except Exception:
        return jsonify({"error": "Invalid JSON data"}), 400

    user: Optional[User] = User.query.filter_by(email=data.email).first()

    if user and bcrypt.check_password_hash(user.password_hash, data.password):
        access_token: str = create_access_token(identity=user.id)
        user_info: Dict[str, Any] = {
            "id": user.id, 
            "email": user.email, 
            "name": user.name
        }
        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "user": user_info
        }), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

# TODO: T22 - Enhance Login System 
# - Add refresh tokens for longer sessions
# - Implement token blacklisting in Redis for proper logout
# - Add rate limiting for failed login attempts
# - Implement remember-me functionality
# - Add password reset capability
# - Track login history for security purposes
# - Consider adding MFA support

@app.route('/api/v1/auth/guest_login', methods=['POST'])
def guest_login() -> ResponseReturnValue:
    guest_id: str = "guest_" + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(12))
    guest_claims: Dict[str, bool] = {"is_guest": True}
    access_token: str = create_access_token(identity=guest_id, additional_claims=guest_claims)

    return jsonify({
        "message": "Guest login successful",
        "access_token": access_token,
        "guest_user_id": guest_id
    }), 200

# TODO: T27 - Enable Multiple Guest Login Support
# - Enhance guest ID generation to ensure uniqueness across concurrent sessions
# - Add metadata to guest tokens (session ID, creation timestamp, fingerprint)
# - Implement improved security measures for guest tokens
# - Update token generation to support localStorage-based session isolation
# - Add rate limiting for guest account creation to prevent abuse
# - Consider adding temporary persistence for guest sessions (Redis)
    
@app.route('/api/v1/auth/protected', methods=['GET'])
@jwt_required()
def protected() -> ResponseReturnValue:
    current_user_id: Union[int, str] = get_jwt_identity() # Can be int (user) or str (guest)
    return jsonify(logged_in_as=current_user_id), 200


if __name__ == '__main__':
    # Migrations should handle table creation
    # with app.app_context():
    #      db.create_all()
         
    app.run(host='0.0.0.0', port=5000, debug=True) 