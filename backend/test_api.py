import requests
import json
import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Database connection parameters
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'appdb'
DB_USER = 'appuser'
DB_PASS = 'secret'

# Get guest token first
def get_guest_token():
    auth_url = 'http://localhost:5001/api/v1/auth/guest_login'
    print(f"Calling guest login at {auth_url}")
    response = requests.post(auth_url)
    if response.status_code == 200:
        data = response.json()
        token = data.get('access_token')
        user_id = data.get('guest_user_id')
        print(f"Guest login successful. Token: {token[:10]}... User ID: {user_id}")
        return token, user_id
    else:
        print(f"Guest login failed: {response.status_code}")
        print(response.text)
        return None, None

# Create a meeting using direct DB connection
def create_meeting_direct_db(user_id):
    try:
        print(f"Connecting to database directly")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        
        # Calculate time with hour increments
        now = datetime.datetime.now()
        start_time = now + datetime.timedelta(hours=1)
        end_time = now + datetime.timedelta(hours=2)
        
        # Create a cursor
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Start a transaction
            conn.autocommit = False
            
            # Check if user_id is a guest ID (starts with "guest_")
            is_guest = isinstance(user_id, str) and user_id.startswith("guest_")
            
            # Insert meeting record
            print("Inserting meeting record")
            
            if is_guest:
                # For guest users, use a placeholder owner_id and store the guest_id
                cur.execute(
                    """
                    INSERT INTO meetings.meetings 
                    (title, description, start_time, end_time, owner_id, guest_owner_id, created_at, updated_at) 
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                    """,
                    ("Test Meeting Direct", "Test Description Direct", start_time, end_time, 1, user_id)
                )
            else:
                # For regular users, use the regular owner_id
                cur.execute(
                    """
                    INSERT INTO meetings.meetings 
                    (title, description, start_time, end_time, owner_id, created_at, updated_at) 
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                    """,
                    ("Test Meeting Direct", "Test Description Direct", start_time, end_time, user_id)
                )
            
            # Get the meeting ID
            meeting_id = cur.fetchone()['id']
            print(f"Meeting created with ID: {meeting_id}")
            
            # Insert participant record only for regular users
            if not is_guest:
                print("Creating owner participant record")
                cur.execute(
                    """
                    INSERT INTO meetings.participants
                    (meeting_id, user_id, status, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    """,
                    (meeting_id, user_id, 'accepted')
                )
            else:
                print("Skipping participant creation for guest user")
            
            # Commit the transaction
            conn.commit()
            print("Transaction committed")
            
            # Fetch the meeting details
            print("Fetching meeting details")
            cur.execute(
                """
                SELECT * FROM meetings.meetings WHERE id = %s
                """,
                (meeting_id,)
            )
            
            meeting = cur.fetchone()
            print(f"Meeting details: {meeting}")
            
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"Database error: {e}")
            return False
            
        finally:
            cur.close()
            conn.close()
            
    except Exception as e:
        print(f"Connection error: {e}")
        return False

# Create a meeting via API
def create_meeting_api(token):
    url = 'http://localhost:5002/api/v1/meetings'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Calculate time with hour increments
    now = datetime.datetime.now()
    start_time = now + datetime.timedelta(hours=1)
    end_time = now + datetime.timedelta(hours=2)
    
    data = {
        'title': 'Test Meeting',
        'description': 'Test Description',
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z'
    }
    
    print(f"Sending request to {url}")
    print(f"Headers: {headers}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        print("Sending request...")
        response = requests.post(url, json=data, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response: {response.text}")
        return response
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return None

if __name__ == "__main__":
    print("Starting test script")
    token, user_id = get_guest_token()
    if token and user_id:
        print("Testing direct database insertion:")
        create_meeting_direct_db(user_id)
        
        print("\nTesting API endpoint:")
        create_meeting_api(token)
    print("Test script completed") 