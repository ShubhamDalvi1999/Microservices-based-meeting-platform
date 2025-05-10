# Meeting Service - Meeting Scheduler App

## 1. Primary Responsibility

Handles the creation, retrieval, updating, and deletion (CRUD) of meetings. It will also manage meeting participants and integrate with Google Calendar to sync meeting events (planned).

## 2. Tech Stack

*   **Framework:** Python, Flask
*   **ORM (Planned):** SQLAlchemy
*   **Database (Interaction Planned):** PostgreSQL
*   **Messaging (Planned):** Publishing events to Redis (e.g., for meeting updates)
*   **Google Calendar API (Planned):** google-api-python-client

## 3. Dependencies

*   **Internal:**
    *   PostgreSQL Database (for storing meeting and participant data - planned)
    *   Redis (for publishing events - planned)
    *   Auth Service (for user authentication/identification - implicit, via JWT planned)
*   **External:**
    *   Google Calendar API (planned)

## 4. Local Setup & Run

This service is part of the `docker-compose.yml` setup in the `backend` directory.

1.  Ensure Docker and Docker Compose are installed.
2.  Navigate to the `backend` directory.
3.  Run `docker-compose up --build meeting-service` (and its dependencies like `db`, `redis`, `auth-service`).
    *   Or run `docker-compose up --build` to start all services.
4.  The service will typically be available on `http://localhost:5002` (as mapped in `docker-compose.yml`).

## 5. Configuration (Environment Variables)

Key environment variables (defined in `docker-compose.yml` or a `.env` file at the `backend` root):

*   `FLASK_ENV`: Set to `development`.
*   `DATABASE_URL`: Connection string for PostgreSQL.
*   `REDIS_URL`: Connection string for Redis (e.g., `redis://redis:6379/0`).
*   `SECRET_KEY` (Planned, if service-specific secrets are needed beyond JWT validation which would use Auth service's key or a shared one).

## 6. API Endpoints (Current)

*   `GET /api/v1/meetings`: Returns a list of all meetings (currently dummy data).
*   `GET /api/v1/meetings/<meeting_id>`: Retrieves details for a specific meeting (currently dummy data).

## 7. Key Code Locations

*   `app.py`: Flask application entry point, route definitions.
*   `Dockerfile`: Instructions to build the Docker image.
*   `requirements.txt`: Python dependencies.
*   (Planned) `/models`: SQLAlchemy models for meetings, participants.
*   (Planned) `/routes` or `/views`: API endpoint definitions.
*   (Planned) `/calendar`: Google Calendar integration logic.

## 8. Assumptions or Constraints

*   Relies on dependent services (DB, Redis, Auth) being available.
*   Current API endpoints provide static, hardcoded data.
*   Authentication and authorization for endpoints are not yet implemented. 