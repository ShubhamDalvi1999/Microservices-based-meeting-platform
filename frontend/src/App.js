import React from 'react';
import {
    BrowserRouter as Router,
    Routes,
    Route,
    Navigate,
    Outlet,
    Link
} from 'react-router-dom';
import './App.css';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import HomePage from './pages/HomePage';
import MeetingDetailPage from './pages/MeetingDetailPage';
import { AuthProvider, useAuth } from './context/AuthContext';
import { SocketProvider } from './context/SocketContext';
import NotificationPanel from './components/NotificationPanel';

// Navbar component
function Navbar() {
  const { authToken, logout, user } = useAuth();
  
  return (
    <nav className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <Link to="/" className="text-xl font-bold text-primary-600">MeetingApp</Link>
            </div>
          </div>
          <div className="flex items-center">
            {authToken ? (
              <div className="flex items-center space-x-4">
                <NotificationPanel />
                <span className="text-sm text-gray-700">
                  {user?.email ? user.email : 'Guest User'}
                </span>
                <button 
                  onClick={logout}
                  className="btn-secondary text-sm"
                  type="button"
                >
                  Logout
                </button>
              </div>
            ) : (
              <div className="space-x-4">
                <Link to="/login" className="btn-secondary text-sm">Login</Link>
                <Link to="/register" className="btn-primary text-sm">Register</Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

// Layout component that includes the Navbar
function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="page-container">
        <Outlet />
      </main>
      <footer className="bg-white shadow-soft-up mt-12 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500">© 2023 MeetingApp. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

// Component to protect routes
function ProtectedRoute() {
    const { authToken } = useAuth();
    // If no token, redirect to login
    return authToken ? <Outlet /> : <Navigate to="/login" replace />;
}

// Component to handle public routes when logged in
function PublicRoute() {
    const { authToken } = useAuth();
    // If token exists, redirect to home page
    return !authToken ? <Outlet /> : <Navigate to="/" replace />;
}

function App() {
  return (
    <AuthProvider>
      <SocketProvider>
        <Router>
          <Routes>
            {/* Public routes (redirect if logged in) */}
            <Route element={<PublicRoute />}>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
            </Route>
            
            {/* Protected routes with layout */}
            <Route element={<Layout />}>
              <Route element={<ProtectedRoute />}>
                <Route path="/" element={<HomePage />} />
                <Route path="/meetings/:meetingId" element={<MeetingDetailPage />} />
              </Route>
            </Route>

            {/* Fallback for unknown routes */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </SocketProvider>
    </AuthProvider>
  );
}

export default App; 