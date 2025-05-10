"""
Unit tests for getting meetings endpoints.
"""
import json
import pytest
from datetime import datetime, timedelta
from meeting_service.app import Meeting, db

class TestGetMeetings:
    """Test cases for the get meetings functionality."""
    
    @pytest.fixture
    def setup_meetings(self, db):
        """Create test meetings in the database."""
        # Create meetings for regular user
        regular_user_meetings = [
            Meeting(
                title=f"Regular User Meeting {i}",
                description=f"Description {i}",
                start_time=datetime.utcnow() + timedelta(hours=i),
                end_time=datetime.utcnow() + timedelta(hours=i+1),
                owner_id=1
            ) for i in range(3)
        ]
        
        # Create meetings for guest user
        guest_user_meetings = [
            Meeting(
                title=f"Guest User Meeting {i}",
                description=f"Description {i}",
                start_time=datetime.utcnow() + timedelta(hours=i),
                end_time=datetime.utcnow() + timedelta(hours=i+1),
                owner_id=1,  # Placeholder
                guest_owner_id="guest_TestUser123"
            ) for i in range(2)
        ]
        
        # Add all meetings to the database
        for meeting in regular_user_meetings + guest_user_meetings:
            db.session.add(meeting)
        
        db.session.commit()
        
        return {
            "regular_user_meetings": regular_user_meetings,
            "guest_user_meetings": guest_user_meetings
        }
    
    def test_get_meetings_regular_user(self, client, setup_meetings, regular_user_token):
        """Test getting meetings for a regular user."""
        # Arrange
        headers = {
            'Authorization': f'Bearer {regular_user_token}',
            'Content-Type': 'application/json'
        }
        
        # Act
        response = client.get('/api/v1/meetings', headers=headers)
        data = json.loads(response.data)
        
        # Assert
        assert response.status_code == 200
        assert len(data) == 3  # Should have 3 meetings for the regular user
        
        # Verify meeting titles
        titles = [meeting["title"] for meeting in data]
        for i in range(3):
            assert f"Regular User Meeting {i}" in titles
    
    def test_get_meetings_guest_user(self, client, setup_meetings, guest_user_token):
        """Test getting meetings for a guest user."""
        # Arrange
        headers = {
            'Authorization': f'Bearer {guest_user_token}',
            'Content-Type': 'application/json'
        }
        
        # Act
        response = client.get('/api/v1/meetings', headers=headers)
        data = json.loads(response.data)
        
        # Assert
        assert response.status_code == 200
        assert len(data) == 2  # Should have 2 meetings for the guest user
        
        # Verify meeting titles
        titles = [meeting["title"] for meeting in data]
        for i in range(2):
            assert f"Guest User Meeting {i}" in titles
        
        # Verify owner_id is the guest ID
        for meeting in data:
            assert meeting["owner_id"] == "guest_TestUser123"
    
    def test_get_meeting_detail_regular_user(self, client, setup_meetings, regular_user_token):
        """Test getting a specific meeting for a regular user."""
        # Arrange
        regular_meetings = setup_meetings["regular_user_meetings"]
        meeting_id = regular_meetings[0].id
        
        headers = {
            'Authorization': f'Bearer {regular_user_token}',
            'Content-Type': 'application/json'
        }
        
        # Act
        response = client.get(f'/api/v1/meetings/{meeting_id}', headers=headers)
        data = json.loads(response.data)
        
        # Assert
        assert response.status_code == 200
        assert data["title"] == "Regular User Meeting 0"
        assert data["owner_id"] == 1
    
    def test_get_meeting_detail_guest_user(self, client, setup_meetings, guest_user_token):
        """Test getting a specific meeting for a guest user."""
        # Arrange
        guest_meetings = setup_meetings["guest_user_meetings"]
        meeting_id = guest_meetings[0].id
        
        headers = {
            'Authorization': f'Bearer {guest_user_token}',
            'Content-Type': 'application/json'
        }
        
        # Act
        response = client.get(f'/api/v1/meetings/{meeting_id}', headers=headers)
        data = json.loads(response.data)
        
        # Assert
        assert response.status_code == 200
        assert data["title"] == "Guest User Meeting 0"
        assert data["owner_id"] == "guest_TestUser123"
    
    def test_get_meeting_unauthorized(self, client, setup_meetings, regular_user_token, guest_user_token):
        """Test that users cannot access meetings they don't own."""
        # Arrange
        guest_meetings = setup_meetings["guest_user_meetings"]
        meeting_id = guest_meetings[0].id
        
        headers = {
            'Authorization': f'Bearer {regular_user_token}',  # Regular user trying to access guest meeting
            'Content-Type': 'application/json'
        }
        
        # Act
        response = client.get(f'/api/v1/meetings/{meeting_id}', headers=headers)
        
        # Assert
        assert response.status_code == 403  # Forbidden 