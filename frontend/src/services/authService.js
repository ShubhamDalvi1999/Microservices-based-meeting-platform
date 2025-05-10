import apiClient from './api';

const authService = {
  // Register a new user
  register: async (userData) => {
    try {
      const response = await apiClient.post('/auth/register', userData);
      return response.data;
    } catch (error) {
      console.error('Registration error:', error.response?.data || error.message);
      throw error;
    }
  },

  // Login with email and password
  login: async (credentials) => {
    try {
      const response = await apiClient.post('/auth/login', credentials);
      return response.data;
    } catch (error) {
      console.error('Login error:', error.response?.data || error.message);
      throw error;
    }
  },

  // Login as guest
  guestLogin: async () => {
    try {
      const response = await apiClient.post('/auth/guest_login');
      return response.data;
    } catch (error) {
      console.error('Guest login error:', error.response?.data || error.message);
      throw error;
    }
  },

  // Get current user info (protected route test)
  getCurrentUser: async () => {
    try {
      const response = await apiClient.get('/auth/protected');
      return response.data;
    } catch (error) {
      console.error('Get user error:', error.response?.data || error.message);
      throw error;
    }
  }
};

export default authService; 