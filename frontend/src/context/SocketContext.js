import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { useAuth } from './AuthContext';
import chatService from '../services/chatService';

// Create the context
const SocketContext = createContext(null);

export const SocketProvider = ({ children }) => {
  const { authToken, user } = useAuth();
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const reconnectTimerRef = useRef(null);

  // Initialize and manage socket connection
  useEffect(() => {
    let newSocket = null;

    const setupSocket = () => {
      if (authToken && user) {
        // Get existing socket or create a new one
        newSocket = chatService.getSocket() || chatService.initSocket(user);
        
        // Configure socket event listeners
        if (newSocket) {
          newSocket.on('connect', () => {
            console.log('Socket connection established in SocketContext');
            setIsConnected(true);
            
            // Clear any reconnect timer
            if (reconnectTimerRef.current) {
              clearTimeout(reconnectTimerRef.current);
              reconnectTimerRef.current = null;
            }
          });
          
          newSocket.on('disconnect', (reason) => {
            console.log('Socket connection closed in SocketContext:', reason);
            setIsConnected(false);
            
            // If not connected and not already trying to reconnect
            if (reason !== 'io client disconnect' && !reconnectTimerRef.current) {
              reconnectTimerRef.current = setTimeout(() => {
                console.log('Attempting to reconnect socket from SocketContext...');
                reconnectTimerRef.current = null;
                setupSocket();
              }, 5000);
            }
          });
          
          newSocket.on('connect_error', (error) => {
            console.error('Socket connection error in SocketContext:', error);
            setIsConnected(false);
          });
          
          // Listen for meeting notification events
          newSocket.on('meeting_invitation', (data) => {
            const notification = {
              id: Date.now(),
              type: 'invitation',
              ...data,
              read: false,
              timestamp: new Date().toISOString()
            };
            setNotifications(prev => [notification, ...prev]);
          });
          
          newSocket.on('meeting_update', (data) => {
            const notification = {
              id: Date.now(),
              type: 'update',
              ...data,
              read: false,
              timestamp: new Date().toISOString()
            };
            setNotifications(prev => [notification, ...prev]);
          });
          
          setSocket(newSocket);
        }
      }
    };
    
    // Initial setup
    setupSocket();
    
    // Clean up function
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      
      // We do NOT call chatService.disconnect() here to prevent disconnecting 
      // when the user navigates between pages
      // The socket will be cleaned up when the user logs out or the app unmounts
    };
  }, [authToken, user]);

  // Force reconnect socket (for troubleshooting)
  const reconnectSocket = () => {
    chatService.disconnect();
    setSocket(null);
    
    // Slight delay to ensure disconnect completes
    setTimeout(() => {
      const newSocket = chatService.initSocket(user);
      setSocket(newSocket);
      setIsConnected(chatService.isConnected());
    }, 1000);
  };

  // Mark notification as read
  const markNotificationAsRead = (notificationId) => {
    setNotifications(prevNotifications =>
      prevNotifications.map(notification =>
        notification.id === notificationId ? { ...notification, read: true } : notification
      )
    );
  };

  // Clear all notifications
  const clearNotifications = () => {
    setNotifications([]);
  };

  // Properly disconnect when logging out
  useEffect(() => {
    if (!authToken) {
      // User logged out, disconnect socket
      chatService.disconnect();
      setSocket(null);
      setIsConnected(false);
    }
  }, [authToken]);

  return (
    <SocketContext.Provider
      value={{
        socket,
        isConnected,
        notifications,
        markNotificationAsRead,
        clearNotifications,
        reconnectSocket
      }}
    >
      {children}
    </SocketContext.Provider>
  );
};

export const useSocket = () => useContext(SocketContext); 