# Frontend - Meeting Scheduler App

## 1. Primary Responsibility

Provides the user interface for interacting with the Meeting Scheduler application. This includes viewing and scheduling meetings, real-time chat, and managing user account settings (planned).

## 2. Tech Stack

*   **Framework/Library:** React (initialized with Create React App structure)
*   **HTTP Client:** Axios (for making API calls to backend services)
*   **WebSocket Client:** socket.io-client (for real-time communication with the Chat/Notification Service)
*   **Routing (Planned):** React Router DOM
*   **State Management (Planned):** React Context API or Redux
*   **Styling:** CSS (potentially with a UI component library like Material-UI later)
*   **Build Tool:** Webpack (via react-scripts)
*   **Serving (in Docker):** Nginx

## 3. Dependencies

*   **Backend Services:**
    *   Auth Service (for login, registration, guest access)
    *   Meeting Service (for meeting data)
    *   Chat/Notification Service (for real-time features)

## 4. Local Setup & Run

There are two main ways to run the frontend locally:

**A. Using Docker (Recommended for full-stack testing):**

1.  Ensure Docker and Docker Compose are installed.
2.  Navigate to the `backend` directory (which contains the main `docker-compose.yml`).
3.  Run `docker-compose up --build frontend` (this will also build and start its dependent backend services if not already running).
    *   Or run `docker-compose up --build` to start the entire application stack.
4.  The frontend will be served by Nginx and typically available at `http://localhost:3000`.
    *   API calls starting with `/api/` and WebSocket connections to `/socket.io/` will be proxied by Nginx to the appropriate backend services as configured in `frontend/nginx/default.conf`.

**B. Using Node.js Development Server (for rapid UI development):**

1.  Ensure Node.js and npm (or yarn) are installed.
2.  Navigate to the `frontend` directory.
3.  Install dependencies: `npm install` (or `yarn install`).
4.  Start the development server: `npm start` (or `yarn start`).
5.  The frontend will typically be available at `http://localhost:3000` (or another port if 3000 is busy).
    *   **Proxying API Calls:** For the dev server to communicate with backend services (which might be running via Docker on different ports like 5001, 5002, 5003), you'll need to configure a proxy in `frontend/package.json`.
        Example for `package.json` (if all backend services are behind a single gateway or for one service):
        ```json
        "proxy": "http://localhost:5001" 
        ```
        Or configure individual proxies if using a more complex setup or a library like `http-proxy-middleware`.
        Alternatively, ensure backend services have appropriate CORS headers if calling them directly from different origins.

## 5. Configuration

*   **Environment Variables (via `.env` files for React Dev Server):**
    *   `REACT_APP_API_BASE_URL` (Planned): Base URL for backend APIs if not using proxy.
    *   `REACT_APP_SOCKET_URL` (Planned): URL for the WebSocket server.
*   **Nginx Configuration (for Docker deployment):**
    *   Located in `frontend/nginx/default.conf`. Defines how static files are served and how API/WebSocket requests are proxied.

## 6. Key Code Locations

*   `public/index.html`: Main HTML page.
*   `src/index.js`: Entry point for the React application.
*   `src/App.js`: Main application component (currently very basic).
*   `src/App.css`: Basic styling for `App.js`.
*   `package.json`: Project metadata, dependencies, and scripts.
*   `Dockerfile`: Instructions to build the Docker image for production (multi-stage: builds React app, then serves with Nginx).
*   `nginx/default.conf`: Nginx configuration for serving the app and proxying requests.
*   (Planned) `src/components/`: Reusable UI components.
*   (Planned) `src/pages/`: Top-level page components.
*   (Planned) `src/services/`: Modules for API calls (e.g., `authService.js`, `meetingService.js`).
*   (Planned) `src/hooks/`: Custom React hooks.
*   (Planned) `src/contexts/` or `src/store/`: State management.

## 7. Assumptions or Constraints

*   Assumes backend services are running and accessible (either via Docker networking and Nginx proxy, or direct calls with CORS/dev server proxy).
*   Current UI is extremely basic, primarily a button to test guest login. 