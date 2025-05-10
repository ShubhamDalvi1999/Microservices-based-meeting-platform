from flask import Flask, jsonify, request, Response
import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import datetime
from flask_jwt_extended import jwt_required, get_jwt_identity, JWTManager
from pydantic import BaseModel, ValidationError, Field
from typing import List, Tuple, Dict, Any, Optional
import redis
import json
from sqlalchemy import event, text
from flask_cors import CORS  # Import CORS

# Type alias for Flask Response
ResponseReturnValue = Tuple[Response, int] | Response

app: Flask = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# --- Configurations ---
# Ensure JWT_SECRET_KEY is consistent with auth_service for validation
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'default-jwt-secret-key-change-me') 
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://appuser:secret@db:5432/appdb')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['REDIS_URL'] = os.environ.get('REDIS_URL', 'redis://redis:6379/0')

# --- Extensions Initialization ---
jwt: JWTManager = JWTManager(app)
db: SQLAlchemy = SQLAlchemy(app)
db.metadata.schema = 'meetings'  # Set schema for all tables in this service

# Add JWT error handlers
@jwt.invalid_token_loader
def invalid_token_callback(error_string):
    app.logger.error(f"Invalid token error: {error_string}")
    return jsonify({"error": "Invalid token", "details": error_string}), 401

@jwt.unauthorized_loader
def unauthorized_callback(error_string):
    app.logger.error(f"Missing token error: {error_string}")
    return jsonify({"error": "Missing or invalid authorization header", "details": error_string}), 401

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    app.logger.error(f"Expired token: {jwt_payload}")
    return jsonify({"error": "Token has expired", "details": "Please login again"}), 401

# Instead of a global event listener, we'll set it up inside a function that runs within the app context
def setup_event_listeners():
    @event.listens_for(db.engine, 'connect')
    def set_search_path(dbapi_connection, connection_record):
        """Set the search path on connection to ensure schema resolution works"""
        cursor = dbapi_connection.cursor()
        cursor.execute('SET search_path TO meetings, public')  # Make meetings the primary schema
        cursor.close()

migrate: Migrate = Migrate(app, db, version_table_schema='meetings')  # Isolate migration version table

# --- Redis client for publishing events ---
redis_client = redis.from_url(app.config['REDIS_URL'])

# Initialize event listeners within app context
with app.app_context():
    setup_event_listeners()

# Helper function to publish meeting events to Redis
def publish_meeting_event(event_type: str, data: Dict[str, Any]) -> None:
    """
    Publish meeting events to Redis channels.
    
    Args:
        event_type: Type of event (e.g., 'meeting_created', 'meeting_updated', 'meeting_deleted', 'participant_added')
        data: Event data to publish
    """
    try:
        # Add timestamp to the event data
        data['timestamp'] = datetime.datetime.utcnow().isoformat() + 'Z'
        data['event_type'] = event_type
        
        # Publish to the general meeting_events channel
        redis_client.publish('meeting_events', json.dumps(data))
        
        # Also publish to a specific channel for this event type
        redis_client.publish(f'meeting_events.{event_type}', json.dumps(data))
        
        # If meeting_id is present, also publish to a meeting-specific channel
        if 'meeting_id' in data:
            redis_client.publish(f'meeting_events.{data["meeting_id"]}', json.dumps(data))
            
        app.logger.info(f"Published {event_type} event to Redis: {data}")
    except Exception as e:
        app.logger.error(f"Failed to publish {event_type} event to Redis: {e}")

# --- Models (SQLAlchemy) ---
# We'll use a simplified approach for the Meeting model
class Meeting(db.Model):
    __tablename__ = 'meetings'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    owner_id = db.Column(db.Integer, nullable=False)
    guest_owner_id = db.Column(db.String(255), nullable=True)  # Store guest user IDs here
    google_event_id = db.Column(db.String(255), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def to_dict(self, include_participants=False):
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time.isoformat() + 'Z',
            "end_time": self.end_time.isoformat() + 'Z',
            "owner_id": self.guest_owner_id if self.guest_owner_id else self.owner_id,
            "google_event_id": self.google_event_id,
            "created_at": self.created_at.isoformat() + 'Z' if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }
        if include_participants:
            participants = db.session.execute(
                text("SELECT * FROM meetings.participants WHERE meeting_id = :meeting_id"),
                {"meeting_id": self.id}
            ).fetchall()
            data['participants'] = [
                {
                    "id": p.id,
                    "meeting_id": p.meeting_id,
                    "user_id": p.user_id,
                    "status": p.status,
                    "created_at": p.created_at.isoformat() + 'Z' if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() + 'Z' if p.updated_at else None,
                }
                for p in participants
            ]
        return data

# Simplified Participant class - we'll use raw SQL for operations
class Participant(db.Model):
    __tablename__ = 'participants'
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "user_id": self.user_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() + 'Z' if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }

# --- Pydantic Schemas for Validation ---
class CreateMeetingSchema(BaseModel):
    title: str = Field(min_length=1)
    description: Optional[str] = None
    start_time: datetime.datetime # Pydantic will parse ISO string
    end_time: datetime.datetime   # Pydantic will parse ISO string

    # Add validator if needed to ensure end_time > start_time

class ParticipantSchema(BaseModel):
    user_id: int = Field(..., gt=0)
    status: Optional[str] = Field(None, pattern='^(pending|accepted|declined)$')

class ParticipantStatusSchema(BaseModel):
    status: str = Field(..., pattern='^(pending|accepted|declined)$')

# --- API Endpoints ---

@app.route('/api/v1/meetings', methods=['GET'])
@jwt_required()
def get_meetings() -> ResponseReturnValue:
    current_user_id = get_jwt_identity()
    try:
        # Check if user is a guest
        is_guest = isinstance(current_user_id, str) and current_user_id.startswith("guest_")
        
        if is_guest:
            # For guest users, query by guest_owner_id
            user_meetings = Meeting.query.filter_by(guest_owner_id=current_user_id).order_by(Meeting.start_time).all()
        else:
            # For regular users, query by owner_id
            user_meetings = Meeting.query.filter_by(owner_id=current_user_id).order_by(Meeting.start_time).all()
        
        # Serialize using the model's to_dict method
        results = [m.to_dict() for m in user_meetings]
        return jsonify(results), 200
    except Exception as e:
        app.logger.error(f"Error fetching meetings for user {current_user_id}: {e}")
        return jsonify({"error": "Failed to fetch meetings"}), 500

@app.route('/api/v1/meetings/<int:meeting_id>', methods=['GET'])
@jwt_required()
def get_meeting_detail(meeting_id: int) -> ResponseReturnValue:
    current_user_id = get_jwt_identity()
    try:
        meeting: Optional[Meeting] = Meeting.query.get(meeting_id)
        if not meeting:
            return jsonify({"error": "Meeting not found"}), 404

        # Check if user is a guest
        is_guest = isinstance(current_user_id, str) and current_user_id.startswith("guest_")
        
        # Authorization Check: Ensure the current user is owner or participant
        is_owner = False
        
        if is_guest:
            # For guest users, check guest_owner_id
            is_owner = (meeting.guest_owner_id == current_user_id)
        else:
            # For regular users, check owner_id
            is_owner = (meeting.owner_id == current_user_id)
            
        # Only check for participant if the user is a regular user (not a guest)
        is_participant = False
        if not is_guest:
            participant_entry: Optional[Participant] = Participant.query.filter_by(
                meeting_id=meeting.id, user_id=current_user_id
            ).first()
            is_participant = participant_entry is not None
        
        if not is_owner and not is_participant:
            return jsonify({"error": "Unauthorized to view this meeting"}), 403
        
        # Serialize using the model's to_dict method, including participants
        return jsonify(meeting.to_dict(include_participants=True)), 200
    
    except Exception as e:
        app.logger.error(f"Error fetching meeting detail {meeting_id} for user {current_user_id}: {e}")
        return jsonify({"error": "Failed to fetch meeting details"}), 500

# TODO: T20 - Implement Shareable Meeting IDs
# - Add a unique shareable_id field to the Meeting model (UUID or short code)
# - Create an endpoint for joining meetings via shareable ID:
#   @app.route('/api/v1/meetings/join/<string:shareable_id>', methods=['GET'])
# - Update the Meeting.to_dict() method to include the shareable_id
# - Implement proper authorization for shareable links
# - Add functionality to generate new shareable_id on demand

# TODO: T27 - Enable Universal Meeting Access for Guest Users
# - Modify authorization logic to allow any guest user to join any meeting
# - Create a public meeting access endpoint that doesn't require explicit invitation
# - Add new field to meetings table to track which guest users have accessed a meeting
# - Implement proper security checks to prevent abuse of guest access
# - Add audit logging for guest access to meetings
# - Update error messages to provide clear guidance for guest users

@app.route('/api/v1/meetings', methods=['POST'])
@jwt_required()
def create_meeting() -> ResponseReturnValue:
    current_user_id = get_jwt_identity()
    app.logger.info(f"Creating meeting with user_id: {current_user_id}")
    
    try:
        # Validate input data
        app.logger.info(f"Validating meeting data...")
        try:
            meeting_data = CreateMeetingSchema(**request.get_json())
            app.logger.info(f"Meeting data validated")
        except ValidationError as e:
            app.logger.error(f"Validation error: {e.errors()}")
            return jsonify({"error": "Invalid input", "details": e.errors()}), 400
        except Exception as e:
            app.logger.error(f"JSON parse error: {str(e)}")
            return jsonify({"error": "Invalid JSON data"}), 400
        
        # Basic validation: end time after start time
        if meeting_data.end_time <= meeting_data.start_time:
            app.logger.error("End time must be after start time")
            return jsonify({"error": "End time must be after start time"}), 400
        
        # Check if user is a guest (guest IDs start with "guest_")
        is_guest = isinstance(current_user_id, str) and current_user_id.startswith("guest_")
        
        # Connect to database directly
        app.logger.info("Connecting to database directly")
        try:
            # Create connection
            from sqlalchemy import create_engine
            engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
            connection = engine.connect()
            
            # Explicitly begin transaction
            trans = connection.begin()
            try:
                # Insert meeting record using raw SQL
                app.logger.info("Inserting meeting record")
                
                if is_guest:
                    # For guest users, use a placeholder user ID (1) and store the guest ID in guest_owner_id
                    sql = """
                        INSERT INTO meetings.meetings 
                        (title, description, start_time, end_time, owner_id, guest_owner_id, created_at, updated_at) 
                        VALUES (:title, :description, :start_time, :end_time, 1, :guest_owner_id, NOW(), NOW())
                        RETURNING id
                    """
                    
                    result = connection.execute(
                        text(sql),
                        {
                            'title': meeting_data.title,
                            'description': meeting_data.description,
                            'start_time': meeting_data.start_time,
                            'end_time': meeting_data.end_time,
                            'guest_owner_id': current_user_id
                        }
                    )
                else:
                    # For regular users, use owner_id as usual
                    sql = """
                        INSERT INTO meetings.meetings 
                        (title, description, start_time, end_time, owner_id, created_at, updated_at) 
                        VALUES (:title, :description, :start_time, :end_time, :owner_id, NOW(), NOW())
                        RETURNING id
                    """
                    
                    result = connection.execute(
                        text(sql),
                        {
                            'title': meeting_data.title,
                            'description': meeting_data.description,
                            'start_time': meeting_data.start_time,
                            'end_time': meeting_data.end_time,
                            'owner_id': current_user_id
                        }
                    )
                
                meeting_id = result.scalar()
                app.logger.info(f"Meeting created with ID: {meeting_id}")
                
                # Insert participant record for owner
                app.logger.info("Creating owner participant record")
                
                if is_guest:
                    # For guest users, we need to handle this differently
                    # Skip the participant record creation as guests don't have entries in auth.users
                    app.logger.info("Skipping participant creation for guest user")
                else:
                    participant_sql = """
                        INSERT INTO meetings.participants
                        (meeting_id, user_id, status, created_at, updated_at)
                        VALUES (:meeting_id, :user_id, 'accepted', NOW(), NOW())
                    """
                    
                    connection.execute(
                        text(participant_sql),
                        {
                            'meeting_id': meeting_id,
                            'user_id': current_user_id
                        }
                    )
                
                # Commit transaction
                trans.commit()
                app.logger.info("Transaction committed")
                
                # Fetch the newly created meeting
                app.logger.info("Fetching meeting details")
                fetch_sql = """
                    SELECT id, title, description, start_time, end_time, owner_id, guest_owner_id,
                           google_event_id, created_at, updated_at
                    FROM meetings.meetings WHERE id = :meeting_id
                """
                result = connection.execute(text(fetch_sql), {'meeting_id': meeting_id})
                meeting_row = result.fetchone()
                
                # Create a dictionary representation of the meeting
                meeting_dict = {
                    "id": meeting_row.id,
                    "title": meeting_row.title,
                    "description": meeting_row.description,
                    "start_time": meeting_row.start_time.isoformat() + 'Z',
                    "end_time": meeting_row.end_time.isoformat() + 'Z',
                    "owner_id": meeting_row.guest_owner_id if meeting_row.guest_owner_id else meeting_row.owner_id,
                    "google_event_id": meeting_row.google_event_id,
                    "created_at": meeting_row.created_at.isoformat() + 'Z',
                    "updated_at": meeting_row.updated_at.isoformat() + 'Z',
                }
                
                # Publish event to Redis
                app.logger.info("Publishing to Redis")
                publish_meeting_event('meeting_created', {
                    'meeting_id': meeting_id,
                    'meeting': meeting_dict,
                    'owner_id': current_user_id,
                    'title': meeting_row.title
                })
                
                return jsonify({
                    "message": "Meeting created successfully", 
                    "meeting": meeting_dict
                }), 201
                
            except Exception as sql_error:
                # Rollback transaction in case of error
                trans.rollback()
                app.logger.error(f"Error executing SQL: {sql_error}")
                raise
            finally:
                # Close connection
                connection.close()
                
        except Exception as db_error:
            app.logger.error(f"Database error: {db_error}")
            app.logger.exception("Full database exception:")
            return jsonify({"error": "Failed to create meeting in database", "details": str(db_error)}), 500
            
    except Exception as e:
        app.logger.error(f"Error creating meeting for user {current_user_id}: {e}")
        app.logger.exception("Full exception:")
        return jsonify({"error": "Failed to create meeting", "details": str(e)}), 500

@app.route('/api/v1/meetings/<int:meeting_id>', methods=['PUT'])
@jwt_required()
def update_meeting(meeting_id: int) -> ResponseReturnValue:
    current_user_id = get_jwt_identity()
    try:
        # Validate input data
        meeting_data = request.get_json()
        if not meeting_data:
            return jsonify({"error": "No data provided"}), 400
        
        # Get the meeting
        meeting: Optional[Meeting] = Meeting.query.get(meeting_id)
        if not meeting:
            return jsonify({"error": "Meeting not found"}), 404
        
        # Check if user is a guest
        is_guest = isinstance(current_user_id, str) and current_user_id.startswith("guest_")
        
        # Authorization: Ensure the current user is the owner
        is_owner = False
        if is_guest:
            is_owner = (meeting.guest_owner_id == current_user_id)
        else:
            is_owner = (meeting.owner_id == current_user_id)
            
        if not is_owner:
            return jsonify({"error": "Unauthorized to modify this meeting"}), 403
        
        # Update meeting fields
        # Store original data for comparison
        original_title = meeting.title
        original_start = meeting.start_time
        original_end = meeting.end_time
        
        if 'title' in meeting_data:
            meeting.title = meeting_data['title']
        if 'description' in meeting_data:
            meeting.description = meeting_data['description']
        if 'start_time' in meeting_data:
            try:
                start_time = datetime.datetime.fromisoformat(meeting_data['start_time'].replace('Z', '+00:00'))
                meeting.start_time = start_time
            except ValueError:
                return jsonify({"error": "Invalid start_time format"}), 400
        if 'end_time' in meeting_data:
            try:
                end_time = datetime.datetime.fromisoformat(meeting_data['end_time'].replace('Z', '+00:00'))
                meeting.end_time = end_time
            except ValueError:
                return jsonify({"error": "Invalid end_time format"}), 400
        
        # Validate: end time after start time
        if meeting.end_time <= meeting.start_time:
            return jsonify({"error": "End time must be after start time"}), 400
        
        db.session.commit()
        
        # Publish meeting_updated event to Redis
        meeting_dict = meeting.to_dict(include_participants=True)
        changes = {
            'title_changed': original_title != meeting.title,
            'time_changed': original_start != meeting.start_time or original_end != meeting.end_time
        }
        
        publish_meeting_event('meeting_updated', {
            'meeting_id': meeting.id,
            'meeting': meeting_dict,
            'owner_id': current_user_id,
            'title': meeting.title,
            'changes': changes
        })
        
        # TODO: Update Google Calendar event if linked (planned)
        
        return jsonify({
            "message": "Meeting updated successfully",
            "meeting": meeting_dict
        }), 200
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating meeting {meeting_id} for user {current_user_id}: {e}")
        return jsonify({"error": "Failed to update meeting"}), 500

@app.route('/api/v1/meetings/<int:meeting_id>', methods=['DELETE'])
@jwt_required()
def delete_meeting(meeting_id: int) -> ResponseReturnValue:
    current_user_id = get_jwt_identity()
    try:
        # Get the meeting
        meeting: Optional[Meeting] = Meeting.query.get(meeting_id)
        if not meeting:
            return jsonify({"error": "Meeting not found"}), 404
        
        # Check if user is a guest
        is_guest = isinstance(current_user_id, str) and current_user_id.startswith("guest_")
        
        # Authorization: Ensure the current user is the owner
        is_owner = False
        if is_guest:
            is_owner = (meeting.guest_owner_id == current_user_id)
        else:
            is_owner = (meeting.owner_id == current_user_id)
            
        if not is_owner:
            return jsonify({"error": "Unauthorized to delete this meeting"}), 403
        
        # Get meeting details for the response before deletion
        meeting_dict = meeting.to_dict(include_participants=True)
        
        # Only fetch participants for regular users (not for guest users)
        participant_ids = []
        if not is_guest:
            participants = Participant.query.filter_by(meeting_id=meeting_id).all()
            participant_ids = [p.user_id for p in participants]
            # Delete participants first (due to foreign key constraint)
            Participant.query.filter_by(meeting_id=meeting_id).delete()
        
        # Then delete the meeting
        db.session.delete(meeting)
        db.session.commit()
        
        # Publish meeting_deleted event to Redis
        publish_meeting_event('meeting_deleted', {
            'meeting_id': meeting_id,
            'meeting': meeting_dict,
            'owner_id': current_user_id,
            'title': meeting_dict['title'],
            'participant_ids': participant_ids
        })
        
        # TODO: Delete Google Calendar event if linked (planned)
        
        return jsonify({
            "message": "Meeting deleted successfully",
            "meeting": meeting_dict
        }), 200
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting meeting {meeting_id} for user {current_user_id}: {e}")
        return jsonify({"error": "Failed to delete meeting"}), 500

# TODO: T21 - Enhance Meeting Deletion Functionality
# - Add CASCADE delete for all meeting data (participants, chat messages, etc.)
# - Implement Redis cleanup for meeting rooms and user-specific chat histories
# - Add notification for all participants when a meeting is deleted
# - Send cancellation notifications to users who have accepted the meeting
# - Consider soft deletion for audit trail purposes

@app.route('/api/v1/meetings/<int:meeting_id>/participants', methods=['POST'])
@jwt_required()
def add_participant(meeting_id: int) -> ResponseReturnValue:
    current_user_id = get_jwt_identity()
    try:
        # Validate input data
        try:
            participant_data = ParticipantSchema(**request.get_json())
        except ValidationError as e:
            return jsonify({"error": "Invalid input", "details": e.errors()}), 400
        except Exception:
            return jsonify({"error": "Invalid JSON data"}), 400
        
        # Get the meeting
        meeting: Optional[Meeting] = Meeting.query.get(meeting_id)
        if not meeting:
            return jsonify({"error": "Meeting not found"}), 404
            
        # Check if user is a guest
        is_guest = isinstance(current_user_id, str) and current_user_id.startswith("guest_")
        
        # Authorization: Ensure the current user is the owner or has permission to invite
        is_owner = False
        if is_guest:
            is_owner = (meeting.guest_owner_id == current_user_id)
        else:
            is_owner = (meeting.owner_id == current_user_id)
            
        if not is_owner:
            return jsonify({"error": "Unauthorized to invite participants to this meeting"}), 403
            
        # Guest users can't add participants since they don't have auth.users entries
        if is_guest:
            return jsonify({"error": "Guest users cannot add participants"}), 403
            
        # Check if participant already exists
        existing_participant = Participant.query.filter_by(
            meeting_id=meeting_id, 
            user_id=participant_data.user_id
        ).first()
        
        if existing_participant:
            return jsonify({
                "error": "User is already a participant of this meeting",
                "participant": existing_participant.to_dict()
            }), 409 # Conflict status code
        
        # Create new participant with pending status by default
        new_participant = Participant(
            meeting_id=meeting_id,
            user_id=participant_data.user_id,
            status=participant_data.status or 'pending'
        )
        
        db.session.add(new_participant)
        db.session.commit()
        
        # Publish participant_added event to Redis
        participant_dict = new_participant.to_dict()
        meeting_dict = meeting.to_dict()
        
        publish_meeting_event('participant_added', {
            'meeting_id': meeting_id,
            'meeting': meeting_dict,
            'participant': participant_dict,
            'added_by_id': current_user_id,
            'title': meeting.title,
            'invited_user_id': participant_data.user_id
        })
        
        return jsonify({
            "message": "Participant added successfully",
            "participant": participant_dict
        }), 201
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding participant to meeting {meeting_id} by user {current_user_id}: {e}")
        return jsonify({"error": "Failed to add participant"}), 500

@app.route('/api/v1/meetings/<int:meeting_id>/participants/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_participant_status(meeting_id: int, user_id: int) -> ResponseReturnValue:
    current_user_id = get_jwt_identity()
    try:
        # Validate input data
        try:
            status_data = ParticipantStatusSchema(**request.get_json())
        except ValidationError as e:
            return jsonify({"error": "Invalid input", "details": e.errors()}), 400
        except Exception:
            return jsonify({"error": "Invalid JSON data"}), 400
        
        # Get the meeting
        meeting: Optional[Meeting] = Meeting.query.get(meeting_id)
        if not meeting:
            return jsonify({"error": "Meeting not found"}), 404
        
        # Check if user is a guest
        is_guest = isinstance(current_user_id, str) and current_user_id.startswith("guest_")
        
        # Guest users can't update participant status
        if is_guest:
            return jsonify({"error": "Guest users cannot update participant status"}), 403
            
        # Get the participant
        participant = Participant.query.filter_by(meeting_id=meeting_id, user_id=user_id).first()
        if not participant:
            return jsonify({"error": "Participant not found"}), 404
            
        # Authorization: 
        # - Meeting owner can update any participant's status
        # - User can update their own status
        is_owner = (meeting.owner_id == current_user_id)
        is_self_update = (user_id == current_user_id)
        
        if not is_owner and not is_self_update:
            return jsonify({"error": "Unauthorized to update this participant's status"}), 403
        
        # Update participant status
        old_status = participant.status
        participant.status = status_data.status
        db.session.commit()
        
        # Publish participant_status_updated event to Redis
        participant_dict = participant.to_dict()
        meeting_dict = meeting.to_dict()
        
        publish_meeting_event('participant_status_updated', {
            'meeting_id': meeting_id,
            'meeting': meeting_dict,
            'participant': participant_dict,
            'user_id': user_id,
            'old_status': old_status,
            'new_status': status_data.status,
            'updated_by_id': current_user_id,
            'title': meeting.title
        })
        
        return jsonify({
            "message": "Participant status updated successfully",
            "participant": participant.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating participant status for meeting {meeting_id}, user {user_id}: {e}")
        return jsonify({"error": "Failed to update participant status"}), 500

# --- Placeholder Endpoints (To be implemented) ---

if __name__ == '__main__':
    with app.app_context():
        setup_event_listeners()
    app.run(host='0.0.0.0', port=5000, debug=True) 
