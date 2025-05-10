# Monkey patch first before any other imports
import eventlet
eventlet.monkey_patch()

from flask import Flask, jsonify, request, Response
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import datetime
from typing import Dict, Any, Optional, Tuple, List
from flask_jwt_extended import JWTManager, decode_token, jwt_required, get_jwt_identity
import jwt
import redis
import json
import threading

# Type alias for Flask Response
ResponseReturnValue = Tuple[Response, int] | Response

app: Flask = Flask(__name__)
# Use SECRET_KEY from environment variable
app.config['SECRET_KEY'] = os.environ.get('CHAT_SERVICE_SECRET_KEY', 'a_dev_secret_key_chat')
# JWT configuration
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'default-jwt-secret-key-change-me')
# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL',
                                                       'postgresql://appuser:secret@db:5432/appdb')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Extensions
db: SQLAlchemy = SQLAlchemy(app)
db.metadata.schema = 'chat'  # Set schema for all tables in this service
migrate: Migrate = Migrate(app, db, version_table_schema='chat')  # Isolate migration version table
jwt_manager: JWTManager = JWTManager(app)

# Configure Socket.IO to use Redis message queue from environment variable
redis_url: Optional[str] = os.environ.get('REDIS_URL')
socketio: SocketIO = SocketIO(app, message_queue=redis_url, cors_allowed_origins="*")

# Dictionary to store user_id -> sid mappings
user_sid_map: Dict[str, List[str]] = {}  # Maps user_id to list of socket IDs (a user can have multiple tabs/devices)
sid_user_map: Dict[str, str] = {}  # Maps socket ID to user_id for quick lookups

# Redis client for subscribing to meeting events
redis_client = redis.from_url(redis_url or 'redis://redis:6379/0')

# Function to handle Redis pubsub messages
def handle_redis_message(message):
    try:
        if message['type'] == 'message':
            channel = message['channel'].decode('utf-8')
            data = json.loads(message['data'].decode('utf-8'))
            app.logger.info(f"Received message from Redis channel {channel}: {data}")
            
            event_type = data.get('event_type')
            meeting_id = data.get('meeting_id')
            
            if not meeting_id:
                app.logger.warning(f"Received event without meeting_id: {data}")
                return
                
            # Convert meeting_id to string for room name consistency in Socket.IO
            room_name = str(meeting_id)
            
            # Process different event types
            if event_type == 'meeting_created':
                # New meeting was created, nothing to broadcast yet since no participants
                pass
                
            elif event_type == 'meeting_updated':
                # Meeting details were updated, notify participants
                socketio.emit('meeting_update', {
                    'meeting_id': meeting_id,
                    'title': data.get('title', 'Meeting Updated'),
                    'message': 'The meeting details have been updated',
                    'timestamp': data.get('timestamp'),
                    'meeting_details': data.get('meeting'),
                    'changes': data.get('changes')
                }, to=room_name)
                
            elif event_type == 'meeting_deleted':
                # Meeting was deleted, notify participants
                socketio.emit('meeting_update', {
                    'meeting_id': meeting_id,
                    'title': data.get('title', 'Meeting Deleted'),
                    'message': 'This meeting has been canceled',
                    'timestamp': data.get('timestamp'),
                    'status': 'deleted'
                }, to=room_name)
                
                # Also try to notify individual participants if they're not in the room
                participant_ids = data.get('participant_ids', [])
                for user_id in participant_ids:
                    if str(user_id) in user_sid_map:
                        for sid in user_sid_map[str(user_id)]:
                            socketio.emit('meeting_update', {
                                'meeting_id': meeting_id,
                                'title': data.get('title', 'Meeting Deleted'),
                                'message': 'A meeting you were invited to has been canceled',
                                'timestamp': data.get('timestamp'),
                                'status': 'deleted'
                            }, to=sid)
                
                # TODO: T21 - Enhance Meeting Deletion in Chat Service
                # - Implement Redis cleanup for deleted meeting chat history
                # - Archive chat messages to database for compliance/audit purposes
                # - Add a grace period before permanent deletion
                # - Handle disconnection of all sockets in the meeting room
                # - Add API endpoint to retrieve archived chat messages for deleted meetings
                
            elif event_type == 'participant_added':
                # New participant added, send them an invitation
                invited_user_id = data.get('invited_user_id')
                if invited_user_id and str(invited_user_id) in user_sid_map:
                    for sid in user_sid_map[str(invited_user_id)]:
                        socketio.emit('meeting_invitation', {
                            'meeting_id': meeting_id,
                            'user_id': invited_user_id,
                            'title': data.get('title', 'Meeting Invitation'),
                            'message': f"You've been invited to a meeting: {data.get('title', 'New Meeting')}",
                            'timestamp': data.get('timestamp'),
                            'meeting_details': data.get('meeting')
                        }, to=sid)
                
            elif event_type == 'participant_status_updated':
                # Participant status changed, notify meeting room
                status = data.get('new_status')
                user_id = data.get('user_id')
                
                if status and user_id:
                    socketio.emit('meeting_update', {
                        'meeting_id': meeting_id,
                        'title': f"Participant Status Updated",
                        'message': f"A participant has {status} the meeting",
                        'timestamp': data.get('timestamp'),
                        'participant_id': user_id,
                        'status': status
                    }, to=room_name)
                    
            else:
                app.logger.warning(f"Unknown event type: {event_type}")
                
    except Exception as e:
        app.logger.error(f"Error processing Redis message: {e}")

# Start Redis pubsub in a background thread
def start_redis_subscriber():
    try:
        pubsub = redis_client.pubsub()
        # Subscribe to all meeting events
        pubsub.subscribe('meeting_events')
        
        app.logger.info("Redis subscriber started, listening for meeting events")
        
        # Process messages
        for message in pubsub.listen():
            handle_redis_message(message)
    except Exception as e:
        app.logger.error(f"Redis subscriber error: {e}")
        # Consider implementing a retry mechanism here

# Start the Redis subscriber in a background thread
redis_thread = threading.Thread(target=start_redis_subscriber)
redis_thread.daemon = True  # Thread will exit when the main thread exits
redis_thread.start()

# Define ChatMessage Model (Based on DATABASE_SCHEMA.md)
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id: int = db.Column(db.Integer, primary_key=True)
    meeting_id: int = db.Column(db.Integer, db.ForeignKey('meetings.meetings.id'), nullable=False)
    user_id: int = db.Column(db.Integer, db.ForeignKey('auth.users.id'), nullable=True)  # Changed to nullable
    guest_user_id: Optional[str] = db.Column(db.String(255), nullable=True)  # Added for guest users
    user_name: Optional[str] = db.Column(db.String(100), nullable=True) # Store sender name for convenience
    content: str = db.Column(db.Text, nullable=False)
    timestamp: datetime.datetime = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        user_identifier = self.guest_user_id if self.guest_user_id else self.user_id
        return f'<ChatMessage user={user_identifier} meeting={self.meeting_id}>'
    
    def to_dict(self) -> Dict[str, Any]: # Helper to convert message to dict for sending
        return {
            'id': self.id,
            'meeting_id': self.meeting_id,
            'user_id': self.guest_user_id if self.guest_user_id else self.user_id,
            'user_name': self.user_name,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() + 'Z' # ISO format UTC
        }

@app.route('/api/v1/chat/health', methods=['GET'])
def health_check() -> ResponseReturnValue:
    return jsonify({"status": "Chat service is running"}), 200

# Helper function to verify JWT token
def verify_jwt(token: str) -> Optional[Dict[str, Any]]:
    try:
        # First try flask_jwt_extended's decode_token
        try:
            decoded_token = decode_token(token)
            user_id = decoded_token.get('sub')  # sub contains user identity
            return {'user_id': user_id}
        except:
            # Fallback to manual decode with PyJWT
            decoded = jwt.decode(
                token, 
                app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            return decoded
    except Exception as e:
        print(f"Error decoding token: {e}")
        return None

# Helper to send message to specific user
def send_to_user(user_id: str, event: str, data: Dict[str, Any]) -> bool:
    """Send a socketio event to a specific user's socket(s)"""
    if user_id in user_sid_map:
        for sid in user_sid_map[user_id]:
            emit(event, data, to=sid)
        return True
    return False

# Add these helper functions for Redis message storage and retrieval
def store_message_in_redis(room: str, message_data: Dict[str, Any]) -> None:
    """
    Store a chat message in Redis for history retrieval
    Messages are stored as sorted sets with timestamp as score for easy retrieval
    """
    try:
        # Convert message data to JSON string
        message_json = json.dumps(message_data)
        
        # Store in a sorted set for the meeting room
        # Use timestamp as score for time-based sorting
        timestamp = datetime.datetime.fromisoformat(message_data['timestamp'].replace('Z', '+00:00')).timestamp()
        
        # Add to room history
        redis_client.zadd(f'chat:history:{room}', {message_json: timestamp})
        
        # Also store in a per-user message list for this room
        user_id = message_data.get('user_id')
        if user_id:
            user_key = f'chat:user:{room}:{user_id}'
            redis_client.zadd(user_key, {message_json: timestamp})
            
            # Set expiration on user-specific history (e.g., 7 days)
            redis_client.expire(user_key, 60 * 60 * 24 * 7)  # 7 days
        
        # Set expiration on room history (e.g., 30 days)
        redis_client.expire(f'chat:history:{room}', 60 * 60 * 24 * 30)  # 30 days
        
        # Trim the lists to reasonable sizes to prevent unbounded growth
        redis_client.zremrangebyrank(f'chat:history:{room}', 0, -501)  # Keep last 500 messages
        if user_id:
            redis_client.zremrangebyrank(user_key, 0, -101)  # Keep last 100 messages per user
            
    except Exception as e:
        app.logger.error(f"Failed to store message in Redis: {e}")

# TODO: T26 - Optimize Redis Usage for Chat Service
# - Implement Redis Cluster for better scalability
# - Add Redis Sentinel for high availability
# - Create Redis data compression for large messages
# - Implement Redis pipelining for batch operations
# - Add Redis connection pooling for improved performance
# - Create more efficient message pruning strategy
# - Implement Redis cache statistics and monitoring
# - Add graceful fallback when Redis is unavailable
# - Create Redis data migration tools for version upgrades

def get_chat_history(room: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieve chat history for a room from Redis
    
    Args:
        room: Meeting ID / room ID
        limit: Maximum number of messages to retrieve (default: 50)
        
    Returns:
        List of message dictionaries, sorted by timestamp (newest last)
    """
    try:
        # Get messages from the sorted set, newest messages last
        messages_json = redis_client.zrange(f'chat:history:{room}', -limit, -1)
        
        # Parse JSON strings back to dictionaries
        return [json.loads(msg.decode('utf-8')) for msg in messages_json]
    except Exception as e:
        app.logger.error(f"Failed to retrieve chat history from Redis: {e}")
        return []

def get_chat_history_with_user_limit(room: str, global_limit: int = 50, per_user_limit: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieve chat history with a limit on messages per user
    
    Args:
        room: Meeting ID / room ID
        global_limit: Maximum total messages to retrieve
        per_user_limit: Maximum messages per user
        
    Returns:
        List of message dictionaries, sorted by timestamp (newest last)
    """
    try:
        # Step 1: Get all recent messages
        all_messages_json = redis_client.zrange(f'chat:history:{room}', -1000, -1)  # Get last 1000 as a reasonable limit
        
        # Step 2: Parse JSON strings back to dictionaries
        all_messages = [json.loads(msg.decode('utf-8')) for msg in all_messages_json]
        
        # Step 3: Group messages by user
        user_messages = {}
        for msg in all_messages:
            user_id = msg.get('user_id', 'system')
            if user_id not in user_messages:
                user_messages[user_id] = []
            user_messages[user_id].append(msg)
        
        # Step 4: Get limited messages per user (most recent)
        limited_messages = []
        for user_id, messages in user_messages.items():
            # Sort by timestamp (newest last)
            sorted_messages = sorted(messages, key=lambda x: x.get('timestamp', ''))
            # Take only the most recent messages, up to per_user_limit
            limited_messages.extend(sorted_messages[-per_user_limit:])
        
        # Step 5: Sort all limited messages by timestamp
        limited_messages.sort(key=lambda x: x.get('timestamp', ''))
        
        # Step 6: Apply global limit if needed
        if len(limited_messages) > global_limit:
            limited_messages = limited_messages[-global_limit:]
            
        return limited_messages
            
    except Exception as e:
        app.logger.error(f"Failed to retrieve limited chat history from Redis: {e}")
        return []

# Add an endpoint to fetch chat history
@app.route('/api/v1/chat/history/<meeting_id>', methods=['GET'])
@jwt_required()
def get_meeting_chat_history(meeting_id: str) -> ResponseReturnValue:
    try:
        # Get current user from JWT
        current_user_id = get_jwt_identity()
        
        # Get limit parameter (optional)
        limit = request.args.get('limit', default=50, type=int)
        per_user_limit = request.args.get('per_user_limit', default=5, type=int)
        
        # Validate meeting ID
        try:
            meeting_id_int = int(meeting_id)
        except ValueError:
            return jsonify({"error": "Invalid meeting ID"}), 400
            
        # Authentication check
        # TODO: Check if user is a participant or owner of the meeting
        
        # Get chat history with user limits
        if per_user_limit > 0:
            messages = get_chat_history_with_user_limit(meeting_id, limit, per_user_limit)
        else:
            messages = get_chat_history(meeting_id, limit)
            
        # If Redis history is empty, fall back to database
        if not messages:
            app.logger.info(f"No Redis history found for meeting {meeting_id}, falling back to database")
            db_messages = ChatMessage.query.filter_by(meeting_id=meeting_id_int) \
                .order_by(ChatMessage.timestamp.asc()) \
                .limit(limit) \
                .all()
                
            messages = [msg.to_dict() for msg in db_messages]
            
            # Also cache these messages in Redis for future requests
            for message in messages:
                store_message_in_redis(meeting_id, message)
        
        return jsonify(messages), 200
        
    except Exception as e:
        app.logger.error(f"Error fetching chat history: {e}")
        return jsonify({"error": "Failed to fetch chat history"}), 500

# --- Socket.IO Event Handlers ---

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    # Get auth token from Socket.IO 'auth' parameter
    auth_data = request.args.get('token') or (
        request.headers.get('Authorization', '').replace('Bearer ', '') if 'Authorization' in request.headers 
        else None
    )
    
    # If we didn't get token from args or headers, check socketio auth data
    if not auth_data and hasattr(request, 'headers') and hasattr(request.headers, 'get'):
        socket_data = request.headers.get('auth', {})
        if isinstance(socket_data, dict):
            auth_data = socket_data.get('token')
    
    if not auth_data:
        print("No authentication token provided")
        # Don't disconnect yet, allow anonymous connections with limited access
        return
    
    # Verify the token
    decoded = verify_jwt(auth_data)
    if not decoded:
        print("Invalid authentication token")
        # Don't disconnect yet, allow with limited access
        return
    
    # Extract user information
    user_id = str(decoded.get('sub', decoded.get('user_id', '')))
    
    if user_id:
        print(f"Authenticated user {user_id} connected with socket {request.sid}")
        # Store user_id -> sid mapping
        if user_id not in user_sid_map:
            user_sid_map[user_id] = []
        user_sid_map[user_id].append(request.sid)
        
        # Store sid -> user_id mapping
        sid_user_map[request.sid] = user_id

# TODO: T27 - Support Multiple Guest Login Sessions in Chat
# - Enhance WebSocket authentication to handle multiple guest users correctly
# - Update user_sid_map to support isolated guest sessions across browser tabs
# - Add metadata to WebSocket connections to track guest session details
# - Improve visual differentiation of guest users in chat messages
# - Handle different naming conventions for guest users to avoid confusion
# - Add proper cleanup for disconnected guest sessions
# - Prevent session confusion when multiple guest users are in the same meeting

@socketio.on('disconnect')
def handle_disconnect() -> None:
    print(f'Client disconnected: {request.sid}')
    # Clean up user_id -> sid mapping
    if request.sid in sid_user_map:
        user_id = sid_user_map[request.sid]
        if user_id in user_sid_map:
            user_sid_map[user_id].remove(request.sid)
            if not user_sid_map[user_id]:  # If this was the last connection for this user
                del user_sid_map[user_id]
        del sid_user_map[request.sid]

@socketio.on('join_room')
def handle_join_room(data: Dict[str, Any]) -> None:
    # Get authentication info
    user_id = None
    if request.sid in sid_user_map:
        user_id = sid_user_map[request.sid]
        
    room: Optional[str] = data.get('meeting_id')
    # Get user info from data or from authenticated session
    data_user_id: str = data.get('user_id', '')
    
    # Use authenticated user_id if available, otherwise use the one from data
    if user_id:
        # Authenticated user
        active_user_id = user_id
    else:
        # Non-authenticated user (guest or fallback)
        active_user_id = data_user_id or f'temp_user_{request.sid}'
    
    user_name: str = data.get('user_name', 'Guest')
    
    if room:
        join_room(room)
        print(f'User {active_user_id} joined room: {room}')
        
        # Optionally notify others in the room
        emit_data: Dict[str, str] = {
            'user_id': active_user_id,
            'user_name': user_name,
            'room': room,
            'meeting_id': room,  # Add meeting_id for consistency
            'authenticated': user_id is not None
        }
        emit('user_joined', emit_data, to=room, include_self=False)
        
        # Send message history to the user who just joined
        try:
            # Get recent messages with per-user limit
            messages = get_chat_history_with_user_limit(room, global_limit=50, per_user_limit=5)
            
            # Send message history to the user
            if messages:
                emit('chat_history', {
                    'meeting_id': room,
                    'messages': messages
                }, to=request.sid)
        except Exception as e:
            print(f"Error sending chat history: {e}")
    else:
        print('Join room request missing meeting_id')

@socketio.on('leave_room')
def handle_leave_room(data: Dict[str, Any]) -> None:
    # Get authentication info
    user_id = None
    if request.sid in sid_user_map:
        user_id = sid_user_map[request.sid]
        
    room: Optional[str] = data.get('meeting_id')
    # Get user info from data or from authenticated session
    data_user_id: str = data.get('user_id', '')
    
    # Use authenticated user_id if available, otherwise use the one from data
    if user_id:
        # Authenticated user
        active_user_id = user_id
    else:
        # Non-authenticated user (guest or fallback)
        active_user_id = data_user_id or f'temp_user_{request.sid}'
    
    user_name: str = data.get('user_name', 'Guest')
    
    if room:
        leave_room(room)
        print(f'User {active_user_id} left room: {room}')
        
        # Optionally notify others in the room
        emit_data: Dict[str, str] = {
            'user_id': active_user_id,
            'user_name': user_name,
            'room': room,
            'authenticated': user_id is not None
        }
        emit('user_left', emit_data, to=room, include_self=False)
    else:
        print('Leave room request missing meeting_id')

@socketio.on('chat_message')
def handle_chat_message(data: Dict[str, Any]) -> None:
    # Get authentication info
    user_id = None
    if request.sid in sid_user_map:
        user_id = sid_user_map[request.sid]
        
    room: Optional[str] = data.get('meeting_id')
    message_content: Optional[str] = data.get('message_text')
    
    # Get user info from data or from authenticated session
    data_user_id: str = data.get('user_id', '')
    
    # Use authenticated user_id if available, otherwise use the one from data
    if user_id:
        # Authenticated user
        active_user_id = user_id
    else:
        # Non-authenticated user (guest or fallback)
        active_user_id = data_user_id or f'temp_user_{request.sid}'
    
    user_name: str = data.get('user_name', 'Guest')

    if room and message_content:
        print(f'Received message for room {room}: {message_content} from {active_user_id}')
        
        # Save message to database
        try:
            # Check if this is a guest user (starts with "guest_")
            is_guest = isinstance(active_user_id, str) and active_user_id.startswith("guest_")
            
            if is_guest:
                # For guest users, use guest_user_id and set user_id to 1 (placeholder)
                new_message = ChatMessage(
                    meeting_id=int(room), 
                    user_id=1,  # Placeholder value for the foreign key
                    guest_user_id=active_user_id,
                    user_name=user_name,
                    content=message_content
                )
            else:
                # For regular users, use user_id as usual
                new_message = ChatMessage(
                    meeting_id=int(room), 
                    user_id=int(active_user_id),
                    guest_user_id=None,
                    user_name=user_name,
                    content=message_content
                )
                
            db.session.add(new_message)
            db.session.commit()
            print(f"Message saved with id {new_message.id}")
            
            # Prepare message data for broadcasting and Redis
            message_data = new_message.to_dict()
            message_data['authenticated'] = user_id is not None
            
            # Store message in Redis for history
            store_message_in_redis(room, message_data)
            
            # Broadcast message to the room
            emit('chat_message', message_data, to=room)
        except Exception as e:
            db.session.rollback()
            print(f"Error saving message: {e}")
            # Emit an error back to the sender
            emit('message_error', {'error': 'Failed to save message'}, to=request.sid)
    else:
        print('Chat message missing room or content')
        emit('message_error', {'error': 'Missing room or message content'}, to=request.sid)

@socketio.on('meeting_update')
def handle_meeting_update(data: Dict[str, Any]) -> None:
    # Get authentication info
    user_id = None
    if request.sid in sid_user_map:
        user_id = sid_user_map[request.sid]
    
    # Require authentication for sending meeting updates
    if not user_id:
        print(f"Unauthorized attempt to send meeting update: {request.sid}")
        emit('update_error', {'error': 'Authentication required'}, to=request.sid)
        return
        
    # This event is triggered when a meeting is updated and we need to notify participants
    meeting_id: Optional[str] = data.get('meeting_id')
    if not meeting_id:
        print('Meeting update missing meeting_id')
        emit('update_error', {'error': 'Missing meeting_id'}, to=request.sid)
        return
        
    # Check if we need to send to a specific user or broadcast to the whole room
    target_user_id: Optional[str] = data.get('user_id')
    
    # Prepare the notification data
    notification_data = {
        'meeting_id': meeting_id,
        'title': data.get('title', 'Meeting Updated'),
        'message': data.get('message', 'A meeting has been updated'),
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
        'sender_id': user_id
    }
    
    # Add any additional details provided
    if 'meeting_details' in data:
        notification_data['meeting_details'] = data['meeting_details']
    if 'status' in data:
        notification_data['status'] = data['status']
    if 'participant_id' in data:
        notification_data['participant_id'] = data['participant_id']
    
    print(f'Broadcasting meeting update for meeting {meeting_id}')
    
    if target_user_id:
        # Try to send to specific user
        if send_to_user(target_user_id, 'meeting_update', notification_data):
            print(f'Sent meeting update to user {target_user_id}')
        else:
            # If user not connected, broadcast to the meeting room as fallback
            print(f'User {target_user_id} not connected, broadcasting to room instead')
            emit('meeting_update', notification_data, to=meeting_id)
    else:
        # Broadcast to everyone in the meeting room
        emit('meeting_update', notification_data, to=meeting_id)

@socketio.on('meeting_invitation')
def handle_meeting_invitation(data: Dict[str, Any]) -> None:
    # Get authentication info
    user_id = None
    if request.sid in sid_user_map:
        user_id = sid_user_map[request.sid]
    
    # Require authentication for sending meeting invitations
    if not user_id:
        print(f"Unauthorized attempt to send meeting invitation: {request.sid}")
        emit('invitation_error', {'error': 'Authentication required'}, to=request.sid)
        return
        
    # This event is triggered when a user is invited to a meeting
    meeting_id: Optional[str] = data.get('meeting_id')
    target_user_id: Optional[str] = data.get('user_id')
    
    if not meeting_id or not target_user_id:
        print('Meeting invitation missing required data (meeting_id or user_id)')
        emit('invitation_error', {'error': 'Missing required data'}, to=request.sid)
        return
    
    # Prepare the invitation data
    invitation_data = {
        'meeting_id': meeting_id,
        'user_id': target_user_id,
        'title': data.get('title', 'Meeting Invitation'),
        'message': data.get('message', 'You have been invited to a meeting'),
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
        'sender_id': user_id
    }
    
    # Add any additional details provided
    if 'meeting_details' in data:
        invitation_data['meeting_details'] = data['meeting_details']
    
    print(f'Sending meeting invitation for meeting {meeting_id} to user {target_user_id}')
    
    # Try to send directly to the target user
    if send_to_user(target_user_id, 'meeting_invitation', invitation_data):
        print(f'Sent invitation directly to user {target_user_id}')
    else:
        # If user not connected, broadcast to all clients as fallback
        # In production, you might want to store this in a database for delivery when user connects
        print(f'User {target_user_id} not connected, broadcasting to all')
        emit('meeting_invitation', invitation_data, broadcast=True)

if __name__ == '__main__':
    # Apply migrations automatically on startup (optional, can be risky in prod)
    # Consider a separate startup script or manual application for production.
    with app.app_context():
        try:
            # Check if tables exist before trying to create (less robust than migrations)
            # db.create_all() # Avoid if using migrations
            pass # Migrations should be handled externally or in a startup script
        except Exception as e:
            print(f"Error during initial DB setup: {e}")
            
    socketio.run(app, host='0.0.0.0', port=5000, debug=True) # Enable debug 