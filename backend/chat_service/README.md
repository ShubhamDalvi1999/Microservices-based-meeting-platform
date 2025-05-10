# Chat/Notification Service - Meeting Scheduler App

## 1. Primary Responsibility

Provides real-time communication features (chat for meetings) via WebSockets (Socket.IO) and handles broadcasting real-time notifications (e.g., meeting updates received via Redis Pub/Sub from other services - planned).

## 2. Tech Stack

*   **Framework:** Python, Flask, Flask-SocketIO
*   **Async Mode:** eventlet (or gevent)
*   **Messaging Queue (for Socket.IO scaling):** Redis (configured via `REDIS_URL`)
*   **Pub/Sub (Subscription - Planned):** Redis (for listening to events like `meeting_updates`)

## 3. Dependencies

*   **Internal:**
    *   Redis (for Socket.IO message queue and pub/sub - planned)
    *   Auth Service (for authenticating WebSocket connections via JWT - planned)
*   **External:**
    *   Frontend clients connecting via WebSockets.

## 4. Local Setup & Run

This service is part of the `docker-compose.yml` setup in the `backend` directory.

1.  Ensure Docker and Docker Compose are installed.
2.  Navigate to the `backend` directory.
3.  Run `docker-compose up --build chat-service` (and its dependencies like `redis`, `auth-service`).
    *   Or run `docker-compose up --build` to start all services.
4.  The Socket.IO server will typically be available for WebSocket connections on the host machine via port `5003` (as mapped in `docker-compose.yml`), though HTTP endpoints on this service would also be on `http://localhost:5003`.

## 5. Configuration (Environment Variables)

Key environment variables (defined in `docker-compose.yml` or a `.env` file at the `backend` root):

*   `FLASK_ENV`: Set to `development`.
*   `REDIS_URL`: Connection string for Redis (e.g., `redis://redis:6379/0`), used by Flask-SocketIO.
*   `SECRET_KEY`: Secret key for Flask application and Socket.IO session signing.

## 6. API Endpoints & Socket.IO Events (Current)

*   **REST API:**
    *   `GET /api/v1/chat/health`: Health check.
*   **Socket.IO Events (Basic):**
    *   `connect`: Emitted when a client connects.
    *   `disconnect`: Emitted when a client disconnects.
    *   `message` (client to server): Generic message handler, prints to console and sends a basic reply.
    *   `response` (server to client): Generic reply sent after a `message` event.

## 7. Key Code Locations

*   `app.py`: Flask application entry point, Socket.IO server initialization, event handlers, and route definitions.
*   `Dockerfile`: Instructions to build the Docker image.
*   `requirements.txt`: Python dependencies (Flask, Flask-SocketIO, eventlet, redis).
*   (Planned) `/sockets` or integrated into `app.py`: More specific Socket.IO event handlers (`join_room`, `chat_message`, etc.).

## 8. Assumptions or Constraints

*   Relies on Redis being available for the message queue.
*   Current Socket.IO events are basic; more application-specific events and room logic are planned.
*   WebSocket authentication (e.g., via JWT) is planned but not yet implemented for the `connect` event. 