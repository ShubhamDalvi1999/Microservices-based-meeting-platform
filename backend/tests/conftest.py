"""
Global pytest fixtures and configuration.
"""
import os
import pytest
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import create_access_token
import datetime
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    from meeting_service.app import app as flask_app
    
    # Set testing configurations
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['JWT_SECRET_KEY'] = 'test-secret-key'
    
    # Create the application context
    with flask_app.app_context():
        yield flask_app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def db(app):
    """Database fixture for testing."""
    from meeting_service.app import db as _db
    
    # Create tables in the test database
    _db.create_all()
    
    yield _db
    
    # Clean up after test
    _db.session.close()
    _db.drop_all()

@pytest.fixture
def regular_user_token(app):
    """Generate a JWT token for a regular user."""
    with app.app_context():
        user_id = 1  # Sample user ID
        token = create_access_token(identity=user_id)
        return token

@pytest.fixture
def guest_user_token(app):
    """Generate a JWT token for a guest user."""
    with app.app_context():
        guest_id = "guest_TestUser123"  # Sample guest ID
        token = create_access_token(identity=guest_id, additional_claims={"is_guest": True})
        return token 