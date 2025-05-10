# Meeting Service Tests

This directory contains unit tests for the Meeting Service of the Full Stack Meeting App. The tests validate the functionality with a focus on handling both regular user IDs (integers) and guest user IDs (strings).

## Test Structure

- **Unit Tests**: Tests for individual components
  - **API Tests**: Tests for API endpoints
  - **Model Tests**: Tests for database models
  - **Utility Tests**: Tests for helper functions

## Running Tests

To run the tests, make sure you have pytest installed:

```bash
pip install pytest pytest-cov
```

### Running All Tests

From the backend directory, run:

```bash
pytest tests/
```

### Running with Coverage

```bash
pytest --cov=meeting_service tests/
```

### Running Specific Test Files

```bash
pytest tests/unit/meeting_service/api/test_create_meeting.py
```

## Test Environment

The tests use:

- SQLite in-memory database for testing
- Mock objects for external dependencies (Redis)

## Authentication

The tests include fixtures for JWT token generation for both regular and guest users:

- `regular_user_token`: JWT token for a regular user
- `guest_user_token`: JWT token for a guest user

## Test Fixtures

- `app`: Flask application fixture
- `client`: Flask test client
- `db`: Database fixture
- `meeting_data`: Sample meeting data
- `setup_meetings`: Creates test meetings in the database

## Adding New Tests

When adding new tests:

1. Place them in the appropriate directory structure
2. Follow the naming convention `test_*.py`
3. Use the provided fixtures
4. Follow the Arrange-Act-Assert pattern

## CI Integration

These tests are designed to be run in a CI/CD pipeline. They are lightweight and do not require external services. 