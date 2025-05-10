import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import apiClient from '../services/api';
import { useAuth } from '../context/AuthContext';

// TODO: T22 - Frontend Login Enhancements
// - Add "Remember Me" checkbox functionality
// - Implement password reset request UI
// - Add form validation with better error messages
// - Implement login attempt throttling/lockout UI
// - Add support for MFA when implemented in backend
// - Store tokens securely (HttpOnly cookies via backend)
// - Add session timeout warnings and auto-refresh logic

function LoginPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState(null);
    const { login, guestLogin } = useAuth();
    const navigate = useNavigate();

    const handleLogin = async (e) => {
        e.preventDefault();
        setError(null);
        try {
            const response = await apiClient.post('/auth/login', { email, password });
            login(response.data.access_token, response.data.user);
            navigate('/');
        } catch (err) {
            const errorMsg = err.response?.data?.error || 'Login failed. Please try again.';
            setError(errorMsg);
            console.error('Login error:', err.response || err);
        }
    };

    const handleGuestLogin = async () => {
        setError(null);
        try {
            const response = await apiClient.post('/auth/guest_login');
            guestLogin(response.data.access_token, response.data.guest_user_id);
            navigate('/');
        } catch (err) {
            const errorMsg = err.response?.data?.error || 'Guest login failed. Please try again.';
            setError(errorMsg);
            console.error('Guest login error:', err.response || err);
        }
    };

    return (
        <div className="flex min-h-screen bg-gray-50 flex-col justify-center py-12 sm:px-6 lg:px-8">
            <div className="sm:mx-auto sm:w-full sm:max-w-md">
                <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
                    Sign in to your account
                </h2>
            </div>

            <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
                <div className="card py-8 px-4 shadow sm:rounded-lg sm:px-10">
                    <form className="space-y-6" onSubmit={handleLogin}>
                        <div>
                            <label htmlFor="login-email" className="label">
                                Email address
                            </label>
                            <div className="mt-1">
                                <input
                                    id="login-email"
                                    name="email"
                                    type="email"
                                    autoComplete="email"
                                    required
                                    className="input"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                />
                            </div>
                        </div>

                        <div>
                            <label htmlFor="login-password" className="label">
                                Password
                            </label>
                            <div className="mt-1">
                                <input
                                    id="login-password"
                                    name="password"
                                    type="password"
                                    autoComplete="current-password"
                                    required
                                    className="input"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                            </div>
                        </div>

                        {error && <p className="error">{error}</p>}

                        <div>
                            <button
                                type="submit"
                                className="btn-primary w-full"
                            >
                                Sign in
                            </button>
                        </div>
                    </form>

                    <div className="mt-6">
                        <div className="relative">
                            <div className="absolute inset-0 flex items-center">
                                <div className="w-full border-t border-gray-300" />
                            </div>
                            <div className="relative flex justify-center text-sm">
                                <span className="px-2 bg-white text-gray-500">
                                    Or continue with
                                </span>
                            </div>
                        </div>

                        <div className="mt-6">
                            <button
                                type="button"
                                onClick={handleGuestLogin}
                                className="btn-secondary w-full"
                            >
                                Continue as Guest
                            </button>
                        </div>
                    </div>
                    
                    <p className="mt-6 text-center text-sm text-gray-600">
                        Don't have an account?{' '}
                        <Link to="/register" className="font-medium text-primary-600 hover:text-primary-500">
                            Sign up now
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}

export default LoginPage; 