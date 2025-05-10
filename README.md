# Meeting Scheduler Application

A full-stack meeting scheduling application using Python Flask microservices for the backend and React for the frontend.

## Features

- User authentication (register, login, guest access)
- Create and manage meetings
- View meeting details
- Real-time chat for meeting participants
- Responsive UI

## Prerequisites

- Docker and Docker Compose
- Node.js and npm (for frontend development)
- Python 3.10+ (for backend development)

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/your-organization/meeting-scheduler-app.git
cd meeting-scheduler-app
```

### 2. Starting the Application

Start the application using Docker Compose:

```bash
cd backend
docker-compose up --build -d
```

This will start all services:
- PostgreSQL database
- Redis for message queueing
- Auth Service (port 5001)
- Meeting Service (port 5002)
- Chat Service (port 5003)
- Frontend (port 3000)

### 3. Initialize the Database

After all services are running, initialize the database migrations:

**Linux/macOS:**
```bash
cd backend
chmod +x initialize_db.sh
./initialize_db.sh
```

**Windows:**
```powershell
cd backend
.\initialize_db.ps1
```

### 4. Create a Test User

Create a test user to log in:

**Linux/macOS:**
```bash
cd backend
chmod +x create_test_user.sh
./create_test_user.sh
```

**Windows:**
```powershell
cd backend
.\create_test_user.ps1
```

### 5. Access the Application

Open your browser and navigate to:
- http://localhost:3000

Log in with the test user:
- Email: test@example.com
- Password: password123

## Testing Features

1. **Authentication**
   - Log in with the test user credentials
   - Try registering a new user
   - Try the guest login option

2. **Creating Meetings**
   - Click "Create New Meeting" on the dashboard
   - Fill in the meeting details (title, description, start/end times)
   - Submit the form

3. **Viewing Meetings**
   - View your created meetings on the dashboard
   - Click "View Details" to see meeting information

4. **Chat Functionality**
   - Open a meeting detail page
   - Send chat messages
   - Open the same meeting in another browser/incognito window
   - Test real-time communication between different users

## Development

### Frontend Development

To run the frontend in development mode:

```bash
cd frontend
npm install
npm start
```

### Backend Development

Each service can be developed independently. To run a specific service:

```bash
cd backend/auth_service  # or meeting_service or chat_service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
flask run --port=5001  # adjust port as needed
```

## Documentation

For more detailed information, see the documentation in the `docs` folder and the runbooks in the `runbooks` folder.

## Troubleshooting

If you encounter issues, check the logs:
```bash
docker-compose logs auth-service
docker-compose logs meeting-service
docker-compose logs chat-service
```

See the troubleshooting guide in `runbooks/05-troubleshooting-common-local-issues.md` for more help. 