import React, { createContext, useState, useContext } from 'react';

const AuthContext = createContext(null);

// TODO: T27 - Support Multiple Guest Login Sessions
// - Update localStorage handling to isolate guest sessions in different tabs
// - Add session-specific metadata to guest logins
// - Implement session fingerprinting to prevent session conflicts
// - Add visual indicators for guest mode in the UI
// - Ensure proper cleanup of guest session data on logout/expiry
// - Add clear documentation for guest users on limitations and security considerations

export const AuthProvider = ({ children }) => {
    const [authToken, setAuthToken] = useState(localStorage.getItem('authToken'));
    const [user, setUser] = useState(JSON.parse(localStorage.getItem('user'))); // Basic user info
    const [isGuest, setIsGuest] = useState(localStorage.getItem('isGuest') === 'true');

    const login = (token, userData) => {
        localStorage.setItem('authToken', token);
        localStorage.setItem('user', JSON.stringify(userData));
        localStorage.setItem('isGuest', 'false');
        setAuthToken(token);
        setUser(userData);
        setIsGuest(false);
    };

    const guestLogin = (token, guestId) => {
        localStorage.setItem('authToken', token);
        localStorage.setItem('user', JSON.stringify({ id: guestId, name: 'Guest' }));
        localStorage.setItem('isGuest', 'true');
        setAuthToken(token);
        setUser({ id: guestId, name: 'Guest' });
        setIsGuest(true);
    };

    const logout = () => {
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
        localStorage.removeItem('isGuest');
        setAuthToken(null);
        setUser(null);
        setIsGuest(false);
    };

    return (
        <AuthContext.Provider value={{ authToken, user, isGuest, login, guestLogin, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext); 