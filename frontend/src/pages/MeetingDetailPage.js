import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useSocket } from '../context/SocketContext';
import meetingService from '../services/meetingService';
import chatService from '../services/chatService';

// TODO: T20 - Implement Shareable Meeting Links UI
// - Add a button to generate and display shareable meeting link
// - Implement copy-to-clipboard functionality for meeting links
// - Add visual indicator for shareable vs. private meetings
// - Create a modal for managing link permissions (public/private/password)
// - Add functionality to revoke or regenerate meeting links
// - Implement UI for accessing meetings via shareable links
// - Track and display number of views/joins from shared links

// Custom hook to store previous value
function usePrevious(value) {
  const ref = useRef();
  
  useEffect(() => {
    ref.current = value;
  }, [value]);
  
  return ref.current;
}

function MeetingDetailPage() {
    const { meetingId } = useParams();
    const navigate = useNavigate();
    const { user, authToken, isGuest } = useAuth();
    const { isConnected } = useSocket();
    const [meeting, setMeeting] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [messages, setMessages] = useState([]);
    const [newMessage, setNewMessage] = useState('');
    const [chatConnected, setChatConnected] = useState(false);
    const messagesEndRef = useRef(null);
    const chatContainerRef = useRef(null);
    const [showSuccessNotification, setShowSuccessNotification] = useState(false);
    const [userMessageCounts, setUserMessageCounts] = useState({});
    const MAX_MESSAGES_PER_USER = 5;
    
    // Track if this is a new meeting that was just created
    const isNewlyCreated = useRef(false);
    
    // Track message count changes to scroll only when needed
    const prevMessageCount = usePrevious(messages.length);
    
    // Scroll to bottom when new messages arrive
    const scrollToBottom = useCallback(() => {
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    }, []);
    
    // Effect to handle scrolling when messages change
    useEffect(() => {
      if (prevMessageCount !== undefined && messages.length > prevMessageCount) {
        scrollToBottom();
      }
    }, [messages.length, prevMessageCount, scrollToBottom]);

    // Check if we arrived from creating a meeting
    useEffect(() => {
        // Check if this page was loaded directly after creating a meeting
        const fromCreate = sessionStorage.getItem('fromMeetingCreate') === 'true';
        
        if (fromCreate && meetingId) {
            isNewlyCreated.current = true;
            setShowSuccessNotification(true);
            // Clear the flag
            sessionStorage.removeItem('fromMeetingCreate');
            
            // Auto-hide the notification after 5 seconds
            const timer = setTimeout(() => {
                setShowSuccessNotification(false);
            }, 5000);
            
            return () => clearTimeout(timer);
        }
    }, [meetingId]);

    // Fetch chat history
    const fetchChatHistory = useCallback(async () => {
        if (!authToken || !meetingId) return;
        
        try {
            // Use the chatService to fetch history
            const historyData = await chatService.fetchChatHistory(meetingId, 5);
            if (!historyData) return;
            
            setMessages(historyData);
            
            // Calculate how many messages each user has
            const counts = {};
            for (const msg of historyData) {
                const userId = msg.user_id;
                counts[userId] = (counts[userId] || 0) + 1;
            }
            setUserMessageCounts(counts);
            
        } catch (error) {
            console.error('Error fetching chat history:', error);
        }
    }, [authToken, meetingId]);

    // Fetch meeting details and chat history
    useEffect(() => {
        const fetchMeeting = async () => {
            try {
                setLoading(true);
                const data = await meetingService.getMeeting(meetingId);
                setMeeting(data);
                setError(null);
                
                // If this is a newly created meeting, add a welcome message
                if (isNewlyCreated.current) {
                    setMessages([{
                        id: `system-welcome-${Date.now()}`,
                        user_id: 'system',
                        user_name: 'System',
                        content: 'Welcome to your newly created meeting chat!',
                        timestamp: new Date().toISOString()
                    }]);
                    isNewlyCreated.current = false;
                } else {
                    // Fetch chat history for existing meetings
                    await fetchChatHistory();
                }
            } catch (err) {
                setError('Failed to fetch meeting details. Please try again later.');
                console.error('Error fetching meeting:', err);
            } finally {
                setLoading(false);
            }
        };

        if (authToken && meetingId) {
            fetchMeeting();
        }
    }, [meetingId, authToken, fetchChatHistory]);

    // Setup chat functionality
    useEffect(() => {
        if (!meeting || !user) return;

        // Initialize chat connection if not already connected
        const socket = chatService.getSocket() || chatService.initSocket(user);
        setChatConnected(chatService.isConnected());

        // Join the meeting room
        if (socket) {
            chatService.joinMeetingRoom(meetingId, user);
            
            // Check connection status after a brief delay
            const connectionCheckTimer = setTimeout(() => {
                setChatConnected(chatService.isConnected());
            }, 1000);
            
            // Set up event listeners
            const messageHandler = (msg) => {
                if (msg?.meeting_id?.toString() === meetingId.toString()) {
                    setMessages((prevMessages) => {
                        // Check if we already have this message (avoid duplicates)
                        const messageExists = prevMessages.some(existingMsg => 
                            existingMsg.id === msg.id || 
                            (existingMsg.timestamp === msg.timestamp && 
                             existingMsg.user_id === msg.user_id && 
                             existingMsg.content === msg.content)
                        );
                        
                        if (messageExists) return prevMessages;
                        
                        // Update user message count
                        setUserMessageCounts(prev => {
                            const userId = msg.user_id;
                            return { ...prev, [userId]: (prev[userId] || 0) + 1 };
                        });
                        
                        // Add the new message
                        const newMessages = [...prevMessages, msg];
                        
                        // Apply per-user message limit if needed
                        return limitMessagesPerUser(newMessages);
                    });
                }
            };

            // Handle chat history received when joining a room
            const chatHistoryHandler = (data) => {
                if (data?.meeting_id?.toString() === meetingId.toString()) {
                    // Only set messages if we don't already have messages
                    // This prevents overwriting newer messages with history
                    setMessages(prevMessages => {
                        if (prevMessages.length === 0 && data.messages && data.messages.length > 0) {
                            // Calculate user message counts
                            const counts = {};
                            for (const msg of data.messages) {
                                const userId = msg.user_id;
                                counts[userId] = (counts[userId] || 0) + 1;
                            }
                            setUserMessageCounts(counts);
                            
                            return data.messages;
                        }
                        return prevMessages;
                    });
                }
            };

            const userJoinedHandler = (data) => {
                // Only process if it's for this meeting
                if (data?.meeting_id?.toString() === meetingId.toString()) {
                    // Add system message when someone joins
                    setMessages((prevMessages) => [
                        ...prevMessages,
                        {
                            id: `system-join-${Date.now()}`,
                            user_id: 'system',
                            user_name: 'System',
                            content: `${data.user_name} joined the chat`,
                            timestamp: new Date().toISOString()
                        }
                    ]);
                }
            };

            const userLeftHandler = (data) => {
                // Only process if it's for this meeting
                if (data?.meeting_id?.toString() === meetingId.toString()) {
                    // Add system message when someone leaves
                    setMessages((prevMessages) => [
                        ...prevMessages,
                        {
                            id: `system-leave-${Date.now()}`,
                            user_id: 'system',
                            user_name: 'System',
                            content: `${data.user_name} left the chat`,
                            timestamp: new Date().toISOString()
                        }
                    ]);
                }
            };

            const connectionStatusHandler = () => {
                setChatConnected(chatService.isConnected());
            };

            // Subscribe to chat events
            const unsubscribeMessage = chatService.onChatMessage(messageHandler);
            
            // Add handler for chat history
            socket.on('chat_history', chatHistoryHandler);
            const unsubscribeUserJoined = chatService.onUserJoined(userJoinedHandler);
            const unsubscribeUserLeft = chatService.onUserLeft(userLeftHandler);
            
            // Also listen for socket connection changes
            socket.on('connect', connectionStatusHandler);
            socket.on('disconnect', connectionStatusHandler);

            // Clean up function
            return () => {
                chatService.leaveMeetingRoom(meetingId, user);
                clearTimeout(connectionCheckTimer);
                
                // Remove all event listeners
                if (unsubscribeMessage) unsubscribeMessage();
                socket.off('chat_history', chatHistoryHandler);
                if (unsubscribeUserJoined) unsubscribeUserJoined();
                if (unsubscribeUserLeft) unsubscribeUserLeft();
                
                socket.off('connect', connectionStatusHandler);
                socket.off('disconnect', connectionStatusHandler);
                
                // Don't disconnect here to prevent socket being destroyed when navigating between pages
                // We'll let the SocketContext handle socket lifecycle
            };
        }
    }, [meeting, user, meetingId]);

    // Add effect to attempt reconnection if needed
    useEffect(() => {
        if (!chatConnected && meeting && user) {
            const reconnectTimer = setTimeout(() => {
                console.log('Attempting to reconnect chat...');
                const socket = chatService.reconnect();
                if (socket) {
                    setChatConnected(chatService.isConnected());
                    if (chatService.isConnected()) {
                        chatService.joinMeetingRoom(meetingId, user);
                    }
                }
            }, 3000);
            
            return () => clearTimeout(reconnectTimer);
        }
    }, [chatConnected, meeting, user, meetingId]);

    // Function to limit messages per user
    const limitMessagesPerUser = useCallback((messageList) => {
        const userMessages = {};
        
        // Group messages by user
        for (const msg of messageList) {
            const userId = msg.user_id;
            if (!userMessages[userId]) {
                userMessages[userId] = [];
            }
            userMessages[userId].push(msg);
        }
        
        // Keep only the last 5 messages per user
        let limitedMessages = [];
        for (const userId of Object.keys(userMessages)) {
            const messages = userMessages[userId];
            // Sort by timestamp
            messages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
            // Take only the most recent messages
            limitedMessages = limitedMessages.concat(
                messages.slice(Math.max(0, messages.length - 5))
            );
        }
        
        // Sort all messages by timestamp
        limitedMessages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        return limitedMessages;
    }, []);

    // Handle sending a message with per-user limit
    const handleSendMessage = (e) => {
        e.preventDefault();
        if (!newMessage.trim() || !chatConnected) return;

        // Add optimistic message to UI first
        const optimisticMessage = {
            id: `local-${Date.now()}`,
            user_id: user.id,
            user_name: user.name || (user.email ? user.email.split('@')[0] : 'Guest'),
            content: newMessage.trim(),
            timestamp: new Date().toISOString(),
            pending: true
        };
        
        setMessages(prev => {
            // Update user message count
            setUserMessageCounts(prevCounts => {
                return { ...prevCounts, [user.id]: (prevCounts[user.id] || 0) + 1 };
            });
            
            // Add the new message and apply limits
            const updatedMessages = [...prev, optimisticMessage];
            return limitMessagesPerUser(updatedMessages);
        });
        
        // Try to send message
        const success = chatService.sendMessage(meetingId, newMessage, user);
        
        // Clear input regardless of success
        setNewMessage('');
        
        // If sending failed, mark message as failed
        if (!success) {
            setTimeout(() => {
                setMessages(prev => prev.map(msg => 
                    msg.id === optimisticMessage.id 
                        ? { ...msg, pending: false, failed: true, content: `${msg.content} (Failed to send)` } 
                        : msg
                ));
            }, 500);
        }
    };

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleString();
    };

    // Check if current user is the meeting owner
    const isOwner = meeting && user && meeting.owner_id === user.id;

    // Get user type badge for display
    const getUserTypeBadge = () => {
        if (isGuest) {
            return (
                <div className="text-xs px-2 py-1 bg-amber-100 text-amber-800 rounded-md font-medium">
                    Guest Access
                </div>
            );
        }
        return null;
    };

    // Add a visual indicator to the UI to show message limiting
    const renderChatHistory = () => {
        if (messages.length === 0) {
            return (
                <div className="flex items-center justify-center h-full">
                    <p className="text-gray-500 text-center">
                        No messages yet. Be the first to say hello!
                    </p>
                </div>
            );
        }
        
        const limitedMessageCount = {};
        for (const userId of Object.keys(userMessageCounts)) {
            if (userMessageCounts[userId] > 5) {
                limitedMessageCount[userId] = userMessageCounts[userId] - 5;
            }
        }
        
        return (
            <div className="space-y-4">
                {Object.keys(limitedMessageCount).length > 0 && (
                    <div className="text-xs text-center text-gray-500 p-2 bg-gray-100 rounded">
                        Some older messages are hidden. Only showing the last 5 messages per user.
                    </div>
                )}
                
                {messages.map((msg) => (
                    <div 
                        key={msg.id || `${msg.user_id}-${msg.timestamp}`}
                        className={`flex ${msg.user_id === user?.id ? 'justify-end' : 'justify-start'}`}
                    >
                        <div
                            className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                                msg.user_id === 'system' 
                                    ? 'bg-gray-200 text-gray-600 italic text-center mx-auto' 
                                    : msg.failed
                                    ? 'bg-red-100 text-red-700 border border-red-200'
                                    : msg.pending
                                    ? 'bg-gray-100 text-gray-600 border border-gray-200'
                                    : msg.user_id === user?.id 
                                    ? 'bg-primary-500 text-white' 
                                    : 'bg-white border border-gray-200'
                            }`}
                        >
                            {msg.user_id !== 'system' && msg.user_id !== user?.id && (
                                <div className="font-semibold text-xs text-gray-700 mb-1">
                                    {msg.user_name || `User ${msg.user_id}`}
                                </div>
                            )}
                            <div className="text-sm">
                                {msg.content}
                                {msg.pending && <span className="inline-block ml-2 text-xs opacity-70">(Sending...)</span>}
                            </div>
                            <div className={`text-xs mt-1 ${
                                msg.user_id === user?.id 
                                    ? 'text-primary-100' 
                                    : msg.user_id === 'system'
                                    ? 'text-gray-500'
                                    : 'text-gray-500'
                            }`}>
                                {formatDate(msg.timestamp)}
                            </div>
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>
        );
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center">
                <p className="text-red-600 mb-4">{error}</p>
                <button 
                    type="button" 
                    onClick={() => navigate('/')}
                    className="btn-secondary"
                >
                    Back to Dashboard
                </button>
            </div>
        );
    }

    if (!meeting) {
        return (
            <div className="text-center">
                <p className="text-gray-600 mb-4">Meeting not found.</p>
                <button 
                    type="button" 
                    onClick={() => navigate('/')}
                    className="btn-secondary"
                >
                    Back to Dashboard
                </button>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto">
            {showSuccessNotification && (
                <div className="bg-green-50 border-l-4 border-green-400 p-4 mb-6">
                    <div className="flex">
                        <div className="flex-shrink-0">
                            <svg className="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                        </div>
                        <div className="ml-3">
                            <p className="text-sm text-green-700">
                                Meeting was created successfully! You can now start chatting and inviting participants.
                            </p>
                        </div>
                    </div>
                </div>
            )}
            
            <div className="mb-6 flex justify-between items-center">
                <button 
                    type="button"
                    onClick={() => navigate('/')} 
                    className="btn-secondary"
                >
                    &larr; Back to Dashboard
                </button>
                
                <div className="flex items-center space-x-4">
                    {getUserTypeBadge()}
                    <div className="flex items-center">
                        <span className={`inline-block w-2 h-2 rounded-full ${chatConnected ? 'bg-green-500' : 'bg-gray-400'} mr-2`} />
                        <span className="text-sm text-gray-500">
                            {chatConnected ? 'Connected' : 'Connecting...'}
                        </span>
                    </div>
                </div>
            </div>

            <div className="card mb-8">
                <div className="flex justify-between items-start mb-4">
                    <h1 className="text-2xl font-bold text-gray-900">{meeting.title}</h1>
                    {isOwner && (
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                            You are the owner
                        </span>
                    )}
                </div>
                
                {isGuest && (
                    <div className="bg-amber-50 border-l-4 border-amber-400 p-4 mb-6">
                        <div className="flex">
                            <div className="flex-shrink-0">
                                <svg className="h-5 w-5 text-amber-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                </svg>
                            </div>
                            <div className="ml-3">
                                <p className="text-sm text-amber-700">
                                    You are viewing this meeting as a guest user.
                                    <a href="/register" className="font-medium underline text-amber-700 hover:text-amber-600 ml-1">
                                        Register for a permanent account
                                    </a>
                                </p>
                            </div>
                        </div>
                    </div>
                )}
                
                {meeting.description && (
                    <p className="text-gray-600 mb-6">{meeting.description}</p>
                )}
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                    <div className="p-4 bg-gray-50 rounded-md">
                        <h3 className="text-sm font-medium text-gray-500 mb-1">Start Time</h3>
                        <p className="text-base font-medium">{formatDate(meeting.start_time)}</p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-md">
                        <h3 className="text-sm font-medium text-gray-500 mb-1">End Time</h3>
                        <p className="text-base font-medium">{formatDate(meeting.end_time)}</p>
                    </div>
                </div>
                
                {!isGuest && meeting.participants && meeting.participants.length > 0 && (
                    <div className="mt-6">
                        <h3 className="text-lg font-semibold mb-4">Participants</h3>
                        <ul className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                            {meeting.participants.map(participant => (
                                <li key={participant.id} className="flex items-center p-2 bg-gray-50 rounded-md">
                                    <div className="w-8 h-8 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center mr-3">
                                        {participant.user_name ? participant.user_name.charAt(0).toUpperCase() : 'U'}
                                    </div>
                                    <div>
                                        <p className="font-medium text-sm">
                                            {participant.user_name || `User ${participant.user_id}`}
                                            {meeting.owner_id === participant.user_id && (
                                                <span className="ml-1 text-xs text-blue-600">(Owner)</span>
                                            )}
                                        </p>
                                        <span className={`text-xs ${
                                            participant.status === 'accepted' ? 'text-green-500' :
                                            participant.status === 'declined' ? 'text-red-500' :
                                            'text-yellow-500'
                                        }`}>
                                            {participant.status.charAt(0).toUpperCase() + participant.status.slice(1)}
                                        </span>
                                    </div>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
                
                {isGuest && (
                    <div className="mt-6 p-4 bg-gray-50 rounded-md">
                        <h3 className="text-lg font-semibold mb-2">Participants</h3>
                        <p className="text-sm text-gray-600">As a guest user, you cannot view the participant list. Register for a full account to access all features.</p>
                    </div>
                )}
            </div>

            <div className="card">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold text-gray-900">Meeting Chat</h2>
                    
                    {/* Add reconnect button when disconnected */}
                    {!chatConnected && (
                        <button 
                            type="button"
                            onClick={() => {
                                const socket = chatService.reconnect();
                                if (socket && user && meetingId) {
                                    chatService.joinMeetingRoom(meetingId, user);
                                    setTimeout(() => setChatConnected(chatService.isConnected()), 1000);
                                }
                            }}
                            className="text-sm px-3 py-1 bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 transition-colors"
                        >
                            Try to reconnect
                        </button>
                    )}
                </div>
                
                {!chatConnected && (
                    <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
                        <div className="flex">
                            <div className="flex-shrink-0">
                                <svg className="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                </svg>
                            </div>
                            <div className="ml-3">
                                <p className="text-sm text-yellow-700">
                                    Connecting to chat... If this persists, please try the reconnect button or refresh the page.
                                </p>
                            </div>
                        </div>
                    </div>
                )}
                
                <div 
                    ref={chatContainerRef}
                    className="h-96 overflow-y-auto bg-gray-50 rounded-md p-4 mb-4"
                >
                    {renderChatHistory()}
                </div>
                
                <form onSubmit={handleSendMessage} className="flex space-x-2">
                    <input
                        type="text"
                        value={newMessage}
                        onChange={(e) => setNewMessage(e.target.value)}
                        placeholder={chatConnected ? "Type your message..." : "Chat disconnected..."}
                        className="input flex-grow"
                        disabled={!chatConnected}
                    />
                    <button 
                        type="submit"
                        disabled={!chatConnected || !newMessage.trim()}
                        className={`btn px-4 ${
                            !chatConnected || !newMessage.trim() 
                                ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
                                : 'btn-primary'
                        }`}
                    >
                        Send
                    </button>
                </form>
            </div>
        </div>
    );
}

export default MeetingDetailPage; 