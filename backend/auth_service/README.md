# Auth Service - Meeting Scheduler App

## 1. Primary Responsibility

Manages user accounts, authentication (including guest login and planned JWT-based full authentication), and will handle OAuth integration with Google for calendar access.

## 2. Tech Stack

*   **Framework:** Python, Flask
*   **Authentication (Planned):** Flask-JWT-Extended
*   **Database (Interaction Planned):** PostgreSQL
*   **Google OAuth (Planned):** google-api-python-client, google-auth-oauthlib

## 3. Dependencies

*   **Internal:**
    *   PostgreSQL Database (for storing user credentials, OAuth tokens - planned)
*   **External:**
    *   Google OAuth Service (planned)

## 4. Local Setup & Run

This service is designed to be run as part of the multi-container Docker setup orchestrated by `docker-compose.yml` located in the `backend` directory.

1.  Ensure Docker and Docker Compose are installed.
2.  Navigate to the `backend` directory.
3.  Run `docker-compose up --build auth-service` (to build and run only this service and its explicit dependencies like `db`).
    *   Or run `docker-compose up --build` to start all services.
4.  The service will typically be available on `http://localhost:5001` (as mapped in `docker-compose.yml`).

## 5. Configuration (Environment Variables)

Key environment variables (defined in `docker-compose.yml` or a `.env` file at the `backend` root):

*   `FLASK_ENV`: Set to `development` for development mode.
*   `DATABASE_URL`: Connection string for PostgreSQL (e.g., `postgresql://appuser:secretpassword@db:5432/appdb`).
*   `SECRET_KEY` (Planned): For Flask app security and JWT signing.
*   `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (Planned): For Google OAuth integration.

## 6. API Endpoints (Current)

*   `GET /api/v1/auth/health`: Health check.
*   `POST /api/v1/auth/guest_login`: Allows a user to log in as a guest (currently returns a dummy token).

## 7. Key Code Locations

*   `app.py`: Flask application entry point, route definitions.
*   `Dockerfile`: Instructions to build the Docker image for this service.
*   `requirements.txt`: Python dependencies.
*   (Planned) `/models`: SQLAlchemy models for users, etc.
*   (Planned) `/routes` or `/views`: Blueprint definitions for API endpoints.

## 8. Assumptions or Constraints

*   Relies on other services (e.g., database) being available as defined in `docker-compose.yml`.
*   Currently provides basic stubbed functionality for guest login. 