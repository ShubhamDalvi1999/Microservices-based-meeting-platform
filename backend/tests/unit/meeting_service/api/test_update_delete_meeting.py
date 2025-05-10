"""
Unit tests for updating and deleting meetings.
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from meeting_service.app import Meeting, db

class TestUpdateDeleteMeeting:
    """Test cases for updating and deleting meetings."""
    
    @pytest.fixture
    def setup_meetings(self, db):
        """Create test meetings in the database."""
        # Create a meeting for regular user
        regular_meeting = Meeting(
            title="Regular User Meeting",
            description="Regular Description",
            start_time=datetime.utcnow() + timedelta(hours=1),
            end_time=datetime.utcnow() + timedelta(hours=2),
            owner_id=1
        )
        
        # Create a meeting for guest user
        guest_meeting = Meeting(
            title="Guest User Meeting",
            description="Guest Description",
            start_time=datetime.utcnow() + timedelta(hours=1),
            end_time=datetime.utcnow() + timedelta(hours=2),
            owner_id=1,  # Placeholder
            guest_owner_id="guest_TestUser123"
        )
        
        db.session.add(regular_meeting)
        db.session.add(guest_meeting)
        db.session.commit()
        
        return {
            "regular_meeting": regular_meeting,
            "guest_meeting": guest_meeting
        }
    
    @patch('meeting_service.app.publish_meeting_event')
    def test_update_meeting_regular_user(self, mock_publish, client, setup_meetings, regular_user_token):
        """Test updating a meeting as a regular user."""
        # Arrange
        regular_meeting = setup_meetings["regular_meeting"]
        meeting_id = regular_meeting.id
        
        headers = {
            'Authorization': f'Bearer {regular_user_token}',
            'Content-Type': 'application/json'
        }
        
        update_data = {
            "title": "Updated Regular Meeting",
            "description": "Updated Description"
        }
        
        # Act
        response = client.put(
            f'/api/v1/meetings/{meeting_id}',
            data=json.dumps(update_data),
            headers=headers
        )
        data = json.loads(response.data)
        
        # Assert
        assert response.status_code == 200
        assert data['message'] == 'Meeting updated successfully'
        assert data['meeting']['title'] == update_data['title']
        assert data['meeting']['description'] == update_data['description']
        
        # Verify that the meeting was updated in the database
        updated_meeting = Meeting.query.get(meeting_id)
        assert updated_meeting.title == update_data['title']
        assert updated_meeting.description == update_data['description']
        
        # Verify Redis event was published
        mock_publish.assert_called_once()
    
    @patch('meeting_service.app.publish_meeting_event')
    def test_update_meeting_guest_user(self, mock_publish, client, setup_meetings, guest_user_token):
        """Test updating a meeting as a guest user."""
        # Arrange
        guest_meeting = setup_meetings["guest_meeting"]
        meeting_id = guest_meeting.id
        
        headers = {
            'Authorization': f'Bearer {guest_user_token}',
            'Content-Type': 'application/json'
        }
        
        update_data = {
            "title": "Updated Guest Meeting",
            "description": "Updated Guest Description"
        }
        
        # Act
        response = client.put(
            f'/api/v1/meetings/{meeting_id}',
            data=json.dumps(update_data),
            headers=headers
        )
        data = json.loads(response.data)
        
        # Assert
        assert response.status_code == 200
        assert data['message'] == 'Meeting updated successfully'
        assert data['meeting']['title'] == update_data['title']
        assert data['meeting']['description'] == update_data['description']
        assert data['meeting']['owner_id'] == "guest_TestUser123"  # Should return guest ID
        
        # Verify that the meeting was updated in the database
        updated_meeting = Meeting.query.get(meeting_id)
        assert updated_meeting.title == update_data['title']
        assert updated_meeting.description == update_data['description']
        assert updated_meeting.guest_owner_id == "guest_TestUser123"
        
        # Verify Redis event was published
        mock_publish.assert_called_once()
    
    def test_update_meeting_unauthorized(self, client, setup_meetings, regular_user_token):
        """Test that users cannot update meetings they don't own."""
        # Arrange
        guest_meeting = setup_meetings["guest_meeting"]
        meeting_id = guest_meeting.id
        
        headers = {
            'Authorization': f'Bearer {regular_user_token}',  # Regular user trying to update guest meeting
            'Content-Type': 'application/json'
        }
        
        update_data = {
            "title": "Unauthorized Update",
            "description": "Should Not Work"
        }
        
        # Act
        response = client.put(
            f'/api/v1/meetings/{meeting_id}',
            data=json.dumps(update_data),
            headers=headers
        )
        
        # Assert
        assert response.status_code == 403  # Forbidden
    
    @patch('meeting_service.app.publish_meeting_event')
    def test_delete_meeting_regular_user(self, mock_publish, client, setup_meetings, regular_user_token):
        """Test deleting a meeting as a regular user."""
        # Arrange
        regular_meeting = setup_meetings["regular_meeting"]
        meeting_id = regular_meeting.id
        
        headers = {
            'Authorization': f'Bearer {regular_user_token}',
            'Content-Type': 'application/json'
        }
        
        # Act
        response = client.delete(
            f'/api/v1/meetings/{meeting_id}',
            headers=headers
        )
        data = json.loads(response.data)
        
        # Assert
        assert response.status_code == 200
        assert data['message'] == 'Meeting deleted successfully'
        
        # Verify the meeting was deleted from the database
        deleted_meeting = Meeting.query.get(meeting_id)
        assert deleted_meeting is None
        
        # Verify Redis event was published
        mock_publish.assert_called_once()
    
    @patch('meeting_service.app.publish_meeting_event')
    def test_delete_meeting_guest_user(self, mock_publish, client, setup_meetings, guest_user_token):
        """Test deleting a meeting as a guest user."""
        # Arrange
        guest_meeting = setup_meetings["guest_meeting"]
        meeting_id = guest_meeting.id
        
        headers = {
            'Authorization': f'Bearer {guest_user_token}',
            'Content-Type': 'application/json'
        }
        
        # Act
        response = client.delete(
            f'/api/v1/meetings/{meeting_id}',
            headers=headers
        )
        data = json.loads(response.data)
        
        # Assert
        assert response.status_code == 200
        assert data['message'] == 'Meeting deleted successfully'
        
        # Verify the meeting was deleted from the database
        deleted_meeting = Meeting.query.get(meeting_id)
        assert deleted_meeting is None
        
        # Verify Redis event was published
        mock_publish.assert_called_once()
    
    def test_delete_meeting_unauthorized(self, client, setup_meetings, regular_user_token):
        """Test that users cannot delete meetings they don't own."""
        # Arrange
        guest_meeting = setup_meetings["guest_meeting"]
        meeting_id = guest_meeting.id
        
        headers = {
            'Authorization': f'Bearer {regular_user_token}',  # Regular user trying to delete guest meeting
            'Content-Type': 'application/json'
        }
        
        # Act
        response = client.delete(
            f'/api/v1/meetings/{meeting_id}',
            headers=headers
        )
        
        # Assert
        assert response.status_code == 403  # Forbidden 