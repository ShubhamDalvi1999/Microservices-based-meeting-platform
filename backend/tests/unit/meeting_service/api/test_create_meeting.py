"""
Unit tests for meeting creation endpoints.
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from meeting_service.app import Meeting, db

class TestCreateMeeting:
    """Test cases for the create meeting functionality."""
    
    @pytest.fixture
    def meeting_data(self):
        """Return valid meeting data for testing."""
        start_time = datetime.utcnow() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        return {
            "title": "Test Meeting",
            "description": "Test Description",
            "start_time": start_time.isoformat() + "Z",
            "end_time": end_time.isoformat() + "Z"
        }
    
    @patch('meeting_service.app.publish_meeting_event')
    def test_create_meeting_regular_user(self, mock_publish, client, db, regular_user_token, meeting_data):
        """Test creating a meeting as a regular user."""
        # Arrange
        headers = {
            'Authorization': f'Bearer {regular_user_token}',
            'Content-Type': 'application/json'
        }
        
        # Act
        response = client.post(
            '/api/v1/meetings',
            data=json.dumps(meeting_data),
            headers=headers
        )
        data = json.loads(response.data)
        
        # Assert
        assert response.status_code == 201
        assert data['message'] == 'Meeting created successfully'
        assert data['meeting']['title'] == meeting_data['title']
        assert data['meeting']['description'] == meeting_data['description']
        
        # Verify that the meeting was stored in the database
        meeting = Meeting.query.filter_by(title=meeting_data['title']).first()
        assert meeting is not None
        assert meeting.owner_id == 1  # Regular user ID
        assert meeting.guest_owner_id is None
        
        # Verify Redis event was published
        mock_publish.assert_called_once()
    
    @patch('meeting_service.app.publish_meeting_event')
    def test_create_meeting_guest_user(self, mock_publish, client, db, guest_user_token, meeting_data):
        """Test creating a meeting as a guest user."""
        # Arrange
        headers = {
            'Authorization': f'Bearer {guest_user_token}',
            'Content-Type': 'application/json'
        }
        
        # Act
        response = client.post(
            '/api/v1/meetings',
            data=json.dumps(meeting_data),
            headers=headers
        )
        data = json.loads(response.data)
        
        # Assert
        assert response.status_code == 201
        assert data['message'] == 'Meeting created successfully'
        assert data['meeting']['title'] == meeting_data['title']
        assert data['meeting']['description'] == meeting_data['description']
        assert data['meeting']['owner_id'] == 'guest_TestUser123'  # Should return guest ID
        
        # Verify that the meeting was stored in the database correctly
        meeting = Meeting.query.filter_by(title=meeting_data['title']).first()
        assert meeting is not None
        assert meeting.owner_id == 1  # Placeholder ID for guest users
        assert meeting.guest_owner_id == 'guest_TestUser123'
        
        # Verify Redis event was published
        mock_publish.assert_called_once()
    
    def test_create_meeting_invalid_data(self, client, regular_user_token):
        """Test creating a meeting with invalid data."""
        # Arrange
        headers = {
            'Authorization': f'Bearer {regular_user_token}',
            'Content-Type': 'application/json'
        }
        
        invalid_data = {
            "title": "",  # Empty title (invalid)
            "description": "Test Description",
            "start_time": "2023-01-01T10:00:00Z",
            "end_time": "2023-01-01T11:00:00Z"
        }
        
        # Act
        response = client.post(
            '/api/v1/meetings',
            data=json.dumps(invalid_data),
            headers=headers
        )
        
        # Assert
        assert response.status_code == 400  # Bad request
        
    def test_create_meeting_invalid_time(self, client, regular_user_token):
        """Test creating a meeting with end time before start time."""
        # Arrange
        headers = {
            'Authorization': f'Bearer {regular_user_token}',
            'Content-Type': 'application/json'
        }
        
        start_time = datetime.utcnow() + timedelta(hours=2)
        end_time = datetime.utcnow() + timedelta(hours=1)  # End time before start time
        
        invalid_time_data = {
            "title": "Test Meeting",
            "description": "Test Description",
            "start_time": start_time.isoformat() + "Z",
            "end_time": end_time.isoformat() + "Z"
        }
        
        # Act
        response = client.post(
            '/api/v1/meetings',
            data=json.dumps(invalid_time_data),
            headers=headers
        )
        
        # Assert
        assert response.status_code == 400  # Bad request
        data = json.loads(response.data)
        assert "End time must be after start time" in data.get("error", "") 