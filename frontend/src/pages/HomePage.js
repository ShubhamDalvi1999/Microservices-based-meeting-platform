import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useSocket } from '../context/SocketContext';
import { useNavigate } from 'react-router-dom';
import meetingService from '../services/meetingService';

function HomePage() {
    const { authToken, user, isGuest } = useAuth();
    const { isConnected } = useSocket();
    const navigate = useNavigate();
    const [meetings, setMeetings] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [newMeeting, setNewMeeting] = useState({
        title: '',
        description: '',
        start_time: '',
        end_time: ''
    });

    // Fetch meetings when component mounts
    useEffect(() => {
        const fetchMeetings = async () => {
            try {
                setLoading(true);
                setError(null);
                
                const data = await meetingService.getMeetings();
                
                // Check if data exists and handle null/undefined/empty responses
                if (data) {
                    // The API returns an array directly, not nested under "meetings"
                    setMeetings(Array.isArray(data) ? data : []);
                } else {
                    console.warn('Meeting service returned empty data');
                    setMeetings([]);
                }
            } catch (error) {
                console.error("Error fetching meetings:", error.message || "Unknown error");
                setError(error.message || "Failed to load meetings. Please try again later.");
                // Ensure meetings is initialized to empty array even on error
                setMeetings([]);
            } finally {
                setLoading(false);
            }
        };
        
        // Only fetch if authenticated
        if (authToken) {
            fetchMeetings();
        } else {
            setMeetings([]);
            setLoading(false);
        }
    }, [authToken]);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setNewMeeting({ ...newMeeting, [name]: value });
    };

    const handleCreateMeeting = async (e) => {
        e.preventDefault();
        
        try {
            setLoading(true);
            setError(null);
            
            // Format dates as ISO strings for the API
            const meetingData = {
                ...newMeeting,
                start_time: new Date(newMeeting.start_time).toISOString(),
                end_time: new Date(newMeeting.end_time).toISOString()
            };
            
            console.log('Submitting new meeting data:', meetingData);
            const response = await meetingService.createMeeting(meetingData);
            console.log('Meeting created successfully:', response);
            
            // Add the new meeting to the list
            setMeetings([...meetings, response.meeting]);
            
            // Reset form
            setNewMeeting({
                title: '',
                description: '',
                start_time: '',
                end_time: '',
            });
            
            // Set success state
            setShowCreateForm(false);
            setLoading(false);
            
            // Set flag in session storage and navigate to meeting detail page
            sessionStorage.setItem('newMeetingCreated', 'true');
            navigate(`/meetings/${response.meeting.id}`);
            
        } catch (error) {
            console.error("Error creating meeting:", error.message || "Unknown error");
            setError(error.message || "Failed to create meeting. Please try again later.");
            setLoading(false);
        }
    };

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleString();
    };

    const getUserBadge = () => {
        if (isGuest) {
            return (
                <div className="px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-medium">
                    Guest User
                </div>
            );
        }
        return (
            <div className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                Registered User
            </div>
        );
    };

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center space-x-4">
                    <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
                    {getUserBadge()}
                </div>
                <div className="flex items-center space-x-4">
                    <div className="flex items-center mr-4">
                        <span className={`inline-block w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-gray-400'} mr-2`} />
                        <span className="text-xs text-gray-500">
                            {isConnected ? 'Connected' : 'Connecting...'}
                        </span>
                    </div>
                    <button 
                        type="button" 
                        onClick={() => setShowCreateForm(!showCreateForm)}
                        className={`btn ${showCreateForm ? 'btn-secondary' : 'btn-primary'}`}
                    >
                        {showCreateForm ? 'Cancel' : 'Create New Meeting'}
                    </button>
                </div>
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
                                You are using a guest account. Your meetings will be accessible using this browser session only. 
                                <a href="/register" className="font-medium underline text-amber-700 hover:text-amber-600 ml-1">
                                    Register for a permanent account
                                </a>
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {error && <div className="error mb-4">{error}</div>}

            {showCreateForm && (
                <div className="card mb-8">
                    <h2 className="text-xl font-semibold mb-4">Create a New Meeting</h2>
                    <form onSubmit={handleCreateMeeting} className="space-y-4">
                        <div>
                            <label htmlFor="title" className="label">Title</label>
                            <input
                                type="text"
                                id="title"
                                name="title"
                                value={newMeeting.title}
                                onChange={handleInputChange}
                                required
                                className="input"
                            />
                        </div>
                        
                        <div>
                            <label htmlFor="description" className="label">Description</label>
                            <textarea
                                id="description"
                                name="description"
                                value={newMeeting.description}
                                onChange={handleInputChange}
                                rows="3"
                                className="input"
                            />
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label htmlFor="start_time" className="label">Start Time</label>
                                <input
                                    type="datetime-local"
                                    id="start_time"
                                    name="start_time"
                                    value={newMeeting.start_time}
                                    onChange={handleInputChange}
                                    required
                                    className="input"
                                />
                            </div>
                            
                            <div>
                                <label htmlFor="end_time" className="label">End Time</label>
                                <input
                                    type="datetime-local"
                                    id="end_time"
                                    name="end_time"
                                    value={newMeeting.end_time}
                                    onChange={handleInputChange}
                                    required
                                    className="input"
                                />
                            </div>
                        </div>
                        
                        <div className="flex justify-end">
                            <button 
                                type="submit" 
                                disabled={loading}
                                className="btn-primary"
                            >
                                {loading ? 'Creating...' : 'Create Meeting'}
                            </button>
                        </div>
                    </form>
                </div>
            )}

            <div className="mt-8">
                <h2 className="text-2xl font-semibold mb-4">Your Meetings</h2>
                
                {loading && !showCreateForm ? (
                    <div className="flex justify-center py-8">
                        <div className="animate-pulse text-primary-600">Loading meetings...</div>
                    </div>
                ) : meetings.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {meetings.map(meeting => (
                            <button 
                                key={meeting.id} 
                                className="card hover:shadow-lg transition-shadow cursor-pointer text-left w-full"
                                onClick={() => navigate(`/meetings/${meeting.id}`)}
                                aria-label={`View details of meeting: ${meeting.title}`}
                                type="button"
                            >
                                <div className="flex justify-between items-start">
                                    <h3 className="text-lg font-semibold text-gray-900 mb-2">{meeting.title}</h3>
                                    {meeting.owner_id === (isGuest ? user.id : user.id) && (
                                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">
                                            Owner
                                        </span>
                                    )}
                                </div>
                                {meeting.description && (
                                    <p className="text-gray-600 mb-4 line-clamp-2">{meeting.description}</p>
                                )}
                                <div className="text-sm text-gray-500 mt-auto">
                                    <p className="mb-1">
                                        <span className="font-medium">Start:</span> {formatDate(meeting.start_time)}
                                    </p>
                                    <p>
                                        <span className="font-medium">End:</span> {formatDate(meeting.end_time)}
                                    </p>
                                </div>
                                <div className="mt-4 pt-4 border-t border-gray-100">
                                    <span className="text-primary-600 hover:text-primary-800 text-sm font-medium">
                                        View Details →
                                    </span>
                                </div>
                            </button>
                        ))}
                    </div>
                ) : (
                    <div className="card p-8 text-center">
                        <p className="text-gray-500 mb-4">No meetings found.</p>
                        <button 
                            type="button" 
                            onClick={() => setShowCreateForm(true)}
                            className="btn-primary"
                        >
                            Create Your First Meeting
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

export default HomePage; 