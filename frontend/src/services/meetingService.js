import apiClient from './api';
import chatService from './chatService';

const meetingService = {
  // Get all meetings for the current user
  getMeetings: async () => {
    try {
      const response = await apiClient.get('/meetings');
      return response.data;
    } catch (error) {
      console.error('Get meetings error:', error.response?.data || error.message);
      // Add user-friendly error message
      const errorMessage = error.userMessage || 
                          (error.response?.data?.message) || 
                          'Unable to retrieve meetings. Please try again later.';
      
      // Return a structured error object that the UI can handle gracefully
      throw {
        message: errorMessage,
        originalError: error
      };
    }
  },

  // Get a specific meeting by ID
  getMeeting: async (meetingId) => {
    try {
      const response = await apiClient.get(`/meetings/${meetingId}`);
      return response.data;
    } catch (error) {
      console.error('Get meeting error:', error.response?.data || error.message);
      throw error;
    }
  },

  // Create a new meeting
  createMeeting: async (meetingData) => {
    try {
      console.log("Creating meeting with data:", meetingData);
      console.log("Using auth token:", localStorage.getItem('authToken'));
      
      const response = await apiClient.post('/meetings', meetingData);
      
      console.log("Meeting creation successful. Response:", response.data);
      
      // If the meeting was created successfully and participants are included,
      // send socket notifications to participants
      const meeting = response.data?.meeting;
      if (meeting?.participants) {
        const title = meeting.title;
        
        // Notify participants via socket
        for (const participant of meeting.participants) {
          chatService.sendMeetingInvitation(meeting.id, participant.user_id, {
            title: `New Meeting Invitation: ${title}`,
            message: `You have been invited to a meeting: ${title}`,
            meeting_details: {
              title,
              start_time: meeting.start_time,
              end_time: meeting.end_time
            }
          });
        }
      }
      
      return response.data;
    } catch (error) {
      console.error('Create meeting error details:', {
        message: error.message,
        status: error.response?.status,
        data: error.response?.data,
        headers: error.response?.headers
      });
      
      // Add user-friendly error message
      const errorMessage = error.userMessage || 
                          (error.response?.data?.message) || 
                          'Unable to create meeting. Please try again later.';
      
      // Return a structured error object that the UI can handle gracefully
      throw {
        message: errorMessage,
        originalError: error
      };
    }
  },

  // Update an existing meeting
  updateMeeting: async (meetingId, meetingData) => {
    try {
      const response = await apiClient.put(`/meetings/${meetingId}`, meetingData);
      
      // If the meeting was updated successfully, send socket notifications
      const meeting = response.data?.meeting;
      if (meeting) {
        // Notify via socket for real-time updates
        chatService.notifyMeetingUpdate(meetingId, {
          title: `Meeting Updated: ${meeting.title}`,
          message: 'The meeting details have been updated.',
          meeting_details: {
            title: meeting.title,
            start_time: meeting.start_time,
            end_time: meeting.end_time,
            description: meeting.description
          }
        });
      }
      
      return response.data;
    } catch (error) {
      console.error('Update meeting error:', error.response?.data || error.message);
      throw error;
    }
  },

  // Delete a meeting
  deleteMeeting: async (meetingId) => {
    try {
      const response = await apiClient.delete(`/meetings/${meetingId}`);
      
      // Notify participants about deletion if we have meeting data
      // Note: The API might not return meeting details on deletion
      const meeting = response.data?.meeting;
      if (meeting) {
        chatService.notifyMeetingUpdate(meetingId, {
          title: `Meeting Cancelled: ${meeting.title}`,
          message: 'The meeting has been cancelled.'
        });
      }
      
      return response.data;
    } catch (error) {
      console.error('Delete meeting error:', error.response?.data || error.message);
      throw error;
    }
  },

  // Invite a participant to a meeting
  inviteParticipant: async (meetingId, participantData) => {
    try {
      const response = await apiClient.post(`/meetings/${meetingId}/participants`, participantData);
      
      // Get meeting data to construct notification
      const meetingResponse = await apiClient.get(`/meetings/${meetingId}`);
      const meeting = meetingResponse.data;
      
      if (meeting && participantData.user_id) {
        chatService.sendMeetingInvitation(meetingId, participantData.user_id, {
          title: `New Meeting Invitation: ${meeting.title}`,
          message: `You have been invited to a meeting: ${meeting.title}`,
          meeting_details: {
            title: meeting.title,
            start_time: meeting.start_time,
            end_time: meeting.end_time
          }
        });
      }
      
      return response.data;
    } catch (error) {
      console.error('Invite participant error:', error.response?.data || error.message);
      throw error;
    }
  },

  // Update participant status (accept/decline)
  updateParticipantStatus: async (meetingId, userId, status) => {
    try {
      const response = await apiClient.put(`/meetings/${meetingId}/participants/${userId}`, { status });
      
      // Notify meeting owner of status change
      const meetingResponse = await apiClient.get(`/meetings/${meetingId}`);
      const meeting = meetingResponse.data;
      
      if (meeting?.owner_id) {
        const statusText = status.charAt(0).toUpperCase() + status.slice(1);
        
        chatService.notifyMeetingUpdate(meetingId, {
          title: `Participant Response: ${statusText}`,
          message: `A participant has ${status} the meeting invitation.`,
          user_id: meeting.owner_id,
          participant_id: userId,
          status: status
        });
      }
      
      return response.data;
    } catch (error) {
      console.error('Update participant error:', error.response?.data || error.message);
      throw error;
    }
  }
};

export default meetingService; 