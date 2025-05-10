import io from 'socket.io-client';

let socket = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

// TODO: T24 - Enhance WebSocket Connection Reliability
// - Implement exponential backoff strategy for reconnection attempts
// - Add persistent connection status indicator in UI
// - Improve error handling with specific user feedback
// - Add connection health monitoring with ping/pong
// - Implement better handling of network transitions (wifi to cellular)
// - Add manual reconnection option for users
// - Store unsent messages and retry when connection is restored

const chatService = {
  // Initialize socket connection
  initSocket: (user) => {
    // Use relative path for socket connection, which will be handled by the Nginx proxy
    if (socket) {
      console.log('Disconnecting existing socket before reconnection');
      socket.disconnect();
      socket = null;
    }

    // Get authentication token
    const token = localStorage.getItem('authToken');

    // Only attempt connection if we have a token
    if (!token) {
      console.error('No authentication token available');
      return null;
    }

    // Clear any existing reconnect timer
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }

    try {
      console.log('Initializing socket connection');
      
      // Reset reconnect attempts counter when manually connecting
      reconnectAttempts = 0;
      
      // Create socket instance with proper configuration
      socket = io({
        path: '/socket.io', // This matches the nginx location block
        transports: ['websocket', 'polling'], // Try websocket first, fallback to polling if needed
        reconnection: true,
        reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        timeout: 20000,
        auth: {
          token: token
        },
        query: {
          token: token  // Add token as query parameter as well (alternative auth method)
        }
      });

      // Set up event handlers
      socket.on('connect', () => {
        console.log('Socket connected successfully with ID:', socket.id);
        reconnectAttempts = 0; // Reset counter on successful connection
      });

      socket.on('connect_error', (error) => {
        console.error('Socket connection error:', error);
        reconnectAttempts++;
        
        if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
          console.warn(`Failed to connect after ${MAX_RECONNECT_ATTEMPTS} attempts`);
        }
      });

      socket.on('disconnect', (reason) => {
        console.log('Socket disconnected:', reason);
        
        // If the server closed the connection and we're not manually reconnecting
        if (reason === 'io server disconnect' && !reconnectTimer) {
          // Try to reconnect after a delay
          reconnectTimer = setTimeout(() => {
            console.log('Attempting to reconnect socket...');
            reconnectTimer = null;
            if (socket) {
              socket.connect();
            }
          }, 3000);
        }
      });

      return socket;
    } catch (error) {
      console.error('Error creating socket connection:', error);
      return null;
    }
  },

  // Disconnect socket
  disconnect: () => {
    if (socket) {
      socket.disconnect();
      socket = null;
    }
    
    // Clear any pending reconnect timers
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    
    // Reset reconnect counter
    reconnectAttempts = 0;
  },

  // Try to reconnect if connection is lost
  reconnect: () => {
    if (socket && !socket.connected) {
      return chatService.initSocket();
    }
    return socket;
  },
  
  // Check connection status
  isConnected: () => {
    return socket?.connected || false;
  },

  // Join a meeting chat room
  joinMeetingRoom: (meetingId, user) => {
    if (!socket) {
      console.error('Socket not initialized');
      return false;
    }

    // Ensure we have a valid meeting ID
    if (!meetingId) {
      console.error('Invalid meeting ID');
      return false;
    }

    const userData = {
      meeting_id: meetingId,
      user_id: user.id,
      user_name: user.name || (user.email ? user.email.split('@')[0] : 'Guest')
    };

    console.log(`Joining room for meeting ${meetingId}`);
    socket.emit('join_room', userData);
    return true;
  },

  // Leave a meeting chat room
  leaveMeetingRoom: (meetingId, user) => {
    if (!socket) {
      console.error('Socket not initialized');
      return false;
    }

    if (!meetingId || !user) {
      console.error('Invalid meeting ID or user');
      return false;
    }

    socket.emit('leave_room', {
      meeting_id: meetingId,
      user_id: user.id,
      user_name: user.name || (user.email ? user.email.split('@')[0] : 'Guest')
    });
    return true;
  },

  // Send a chat message
  sendMessage: (meetingId, messageText, user) => {
    if (!socket) {
      console.error('Socket not initialized');
      return false;
    }

    if (!meetingId || !messageText || !user) {
      console.error('Missing required parameters for sending message');
      return false;
    }

    socket.emit('chat_message', {
      meeting_id: meetingId,
      message_text: messageText,
      user_id: user.id,
      user_name: user.name || (user.email ? user.email.split('@')[0] : 'Guest')
    });
    return true;
  },

  // Subscribe to chat messages
  onChatMessage: (callback) => {
    if (!socket) {
      console.error('Socket not initialized');
      return () => {};
    }

    socket.on('chat_message', callback);
    return () => {
      if (socket) {
        socket.off('chat_message', callback);
      }
    };
  },

  // Subscribe to user join notifications
  onUserJoined: (callback) => {
    if (!socket) {
      console.error('Socket not initialized');
      return () => {};
    }

    socket.on('user_joined', callback);
    return () => {
      if (socket) {
        socket.off('user_joined', callback);
      }
    };
  },

  // Subscribe to user leave notifications
  onUserLeft: (callback) => {
    if (!socket) {
      console.error('Socket not initialized');
      return () => {};
    }

    socket.on('user_left', callback);
    return () => {
      if (socket) {
        socket.off('user_left', callback);
      }
    };
  },

  // Subscribe to meeting updates
  onMeetingUpdate: (callback) => {
    if (!socket) {
      console.error('Socket not initialized');
      return () => {};
    }

    socket.on('meeting_update', callback);
    return () => {
      if (socket) {
        socket.off('meeting_update', callback);
      }
    };
  },

  // Subscribe to meeting invitations
  onMeetingInvitation: (callback) => {
    if (!socket) {
      console.error('Socket not initialized');
      return () => {};
    }

    socket.on('meeting_invitation', callback);
    return () => {
      if (socket) {
        socket.off('meeting_invitation', callback);
      }
    };
  },

  // Trigger a meeting update notification
  notifyMeetingUpdate: (meetingId, updateData) => {
    if (!socket) {
      console.error('Socket not initialized');
      return false;
    }

    socket.emit('meeting_update', {
      meeting_id: meetingId,
      ...updateData
    });
    return true;
  },

  // Send an invitation to a meeting
  sendMeetingInvitation: (meetingId, userId, meetingDetails) => {
    if (!socket) {
      console.error('Socket not initialized');
      return false;
    }

    socket.emit('meeting_invitation', {
      meeting_id: meetingId,
      user_id: userId,
      ...meetingDetails
    });
    return true;
  },

  // Subscribe to chat history
  onChatHistory: (callback) => {
    if (!socket) {
      console.error('Socket not initialized');
      return () => {};
    }

    socket.on('chat_history', callback);
    return () => {
      if (socket) {
        socket.off('chat_history', callback);
      }
    };
  },

  // Fetch chat history via REST API
  fetchChatHistory: async (meetingId, perUserLimit = 5) => {
    try {
      const token = localStorage.getItem('authToken');
      if (!token) {
        console.error('No authentication token available');
        return null;
      }

      const response = await fetch(`/api/v1/chat/history/${meetingId}?per_user_limit=${perUserLimit}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch chat history: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching chat history:', error);
      return null;
    }
  },

  // Get current socket instance
  getSocket: () => socket
};

export default chatService; 