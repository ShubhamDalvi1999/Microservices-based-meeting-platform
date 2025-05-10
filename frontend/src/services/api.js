import axios from 'axios';

// Helper function to retry failed requests
const retryRequest = async (config, retries = 3, delay = 1000) => {
    try {
        return await axios(config);
    } catch (error) {
        // Only retry network errors
        if (!error.response && retries > 0) {
            console.log(`Retrying request to ${config.url}, ${retries} attempts left`);
            await new Promise(resolve => setTimeout(resolve, delay));
            return retryRequest(config, retries - 1, delay * 1.5);
        }
        throw error;
    }
};

// Create an Axios instance
const apiClient = axios.create({
    // Base URL for API calls. Use relative path that will be handled by Nginx proxy
    baseURL: '/api/v1', 
    headers: {
        'Content-Type': 'application/json',
    },
    // Add longer timeout for network issues
    timeout: 10000,
});

// Add request interceptor to handle CORS and network issues
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('authToken');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        
        // Add debugging info
        console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`, { 
            headers: config.headers,
            baseURL: config.baseURL
        });
        
        return config;
    },
    (error) => {
        console.error('API request interceptor error:', error);
        return Promise.reject(error);
    }
);

// Add response interceptor to handle CORS and network issues
apiClient.interceptors.response.use(
    (response) => {
        console.log(`API Response: ${response.status} ${response.config.url}`, { 
            headers: response.headers,
            data: response.data
        });
        return response;
    },
    async (error) => {
        if (error.response) {
            // The request was made and the server responded with a status code
            // that falls out of the range of 2xx
            console.error('API Error Response:', {
                status: error.response.status,
                data: error.response.data,
                headers: error.response.headers,
                url: error.config?.url
            });
            
            if (error.response.status === 401) {
                // Handle unauthorized - token might be expired or invalid
                console.log('API call Unauthorized (401). Logging out.');
                localStorage.removeItem('authToken');
                localStorage.removeItem('user');
                localStorage.removeItem('isGuest');
                window.location.href = '/login';
            }
        } else if (error.request) {
            // The request was made but no response was received
            console.error('API Error Request (No response):', {
                url: error.config?.url,
                baseURL: error.config?.baseURL,
                method: error.config?.method,
                request: error.request
            });
            
            // Try to retry the request if it's a network error
            try {
                if (error.config) {
                    console.log(`Attempting to retry request to ${error.config.url}`);
                    return await retryRequest(error.config);
                }
            } catch (retryError) {
                console.error('Retry also failed:', retryError);
                // Show a user-friendly error message
                error.userMessage = 'Network error - unable to connect to the server after multiple attempts';
            }
        } else {
            // Something happened in setting up the request that triggered an Error
            console.error('API Error Setup:', error.message);
            error.userMessage = 'Error preparing request - please try again';
        }
        
        return Promise.reject(error);
    }
);

// Export the apiClient with retry mechanism
export default apiClient; 