"""Shared test fixtures and configuration"""

import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass
from datetime import datetime

import pytest

# Загрузка переменных окружения из .env.test
from dotenv import load_dotenv

# Загружаем .env.test перед импортом настроек приложения
env_test_path = Path(__file__).parent.parent / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path, override=True)


# Configure pytest markers for integration tests
def pytest_configure(config):
    """Register custom pytest markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


# Define mock objects without importing from app.models to avoid engine initialization
@dataclass
class MockUser:
    """Mock User for testing"""
    id: str
    username: str
    email: str
    password_hash: str
    email_confirmed: bool = False
    created_at: datetime = None
    updated_at: datetime = None


class MockEmailMessage:
    """Mock EmailMessage for testing"""
    def __init__(self, subject, html_body, text_body, to, from_, template_name):
        self.subject = subject
        self.html_body = html_body
        self.text_body = text_body
        self.to = to
        self.from_ = from_
        self.template_name = template_name
    
    def as_string(self):
        headers = f"From: {self.from_}\r\nTo: {self.to}\r\nSubject: {self.subject}\r\n"
        return f"{headers}\r\n{self.html_body}"


@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    """Create async database session for tests (mock)"""
    # Return a mock database session for unit tests
    # For integration tests, override this fixture
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.execute = AsyncMock()
    return mock_session


@pytest.fixture
def mock_user():
    """Create mock user object"""
    return MockUser(
        id="550e8400-e29b-41d4-a716-446655440000",
        username="testuser",
        email="testuser@example.com",
        password_hash="hashed_password",
        email_confirmed=False,
        created_at=None,
        updated_at=None,
    )


@pytest.fixture
def sample_email_message():
    """Create sample email message for testing"""
    return MockEmailMessage(
        subject="Test Subject",
        html_body="<p>Hello <b>World</b></p>",
        text_body="Hello World",
        to="user@example.com",
        from_="noreply@codelab.local",
        template_name="test",
    )


@pytest.fixture
def template_engine():
    """Create email template engine with test templates (mock)"""
    # Return a mock template engine
    mock_engine = AsyncMock()
    mock_engine.render_template = AsyncMock(
        return_value=MockEmailMessage(
            subject="Test Subject",
            html_body="<p>Test</p>",
            text_body="Test",
            to="test@example.com",
            from_="noreply@codelab.local",
            template_name="test",
        )
    )
    return mock_engine


@pytest.fixture
def mock_smtp_sender():
    """Create mock SMTP sender"""
    mock = AsyncMock()
    mock.send_email = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_retry_service():
    """Create mock retry service"""
    mock = AsyncMock()
    mock.send_with_retry = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_audit_service():
    """Create mock audit service"""
    mock = MagicMock()
    mock.log_email_sent = AsyncMock()
    mock.log_email_failed = AsyncMock()
    mock.log_email_confirmation_token_generated = AsyncMock()
    mock.log_email_confirmation_success = AsyncMock()
    mock.log_email_confirmation_failed = AsyncMock()
    return mock


# Integration test markers configuration
@pytest.fixture(scope="session")
def integration_test_config():
    """Configuration for integration tests"""
    return {
        "mailhog_host": os.environ.get("MAILHOG_HOST", "localhost"),
        "mailhog_smtp_port": int(os.environ.get("MAILHOG_SMTP_PORT", "1025")),
        "mailhog_http_port": int(os.environ.get("MAILHOG_HTTP_PORT", "8025")),
    }
