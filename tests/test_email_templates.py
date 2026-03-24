"""Tests for email template engine functionality"""

from pathlib import Path

import pytest
from jinja2 import TemplateNotFound

from app.services.email_templates import EmailMessage, EmailTemplateEngine


class TestEmailMessage:
    """Test EmailMessage dataclass"""

    def test_email_message_creation(self):
        """Test creating an EmailMessage instance"""
        msg = EmailMessage(
            subject="Test Subject",
            html_body="<p>Hello</p>",
            text_body="Hello",
            to="user@example.com",
            from_="noreply@codelab.local",
            template_name="test",
        )
        assert msg.subject == "Test Subject"
        assert msg.html_body == "<p>Hello</p>"
        assert msg.text_body == "Hello"
        assert msg.to == "user@example.com"
        assert msg.from_ == "noreply@codelab.local"
        assert msg.template_name == "test"

    def test_email_message_as_string(self):
        """Test converting EmailMessage to string format for SMTP"""
        msg = EmailMessage(
            subject="Test Subject",
            html_body="<p>Hello</p>",
            text_body="Hello",
            to="user@example.com",
            from_="noreply@codelab.local",
            template_name="test",
        )
        result = msg.as_string()
        assert "From: noreply@codelab.local" in result
        assert "To: user@example.com" in result
        assert "Subject: Test Subject" in result
        assert "<p>Hello</p>" in result


class TestEmailTemplateEngine:
    """Test EmailTemplateEngine functionality"""

    @pytest.fixture
    def template_engine(self):
        """Create email template engine with app templates directory"""
        template_dir = Path(__file__).parent.parent / "app" / "templates" / "emails"
        return EmailTemplateEngine(template_dir)

    @pytest.mark.asyncio
    async def test_render_welcome_template(self, template_engine):
        """Test rendering welcome email template"""
        context = {
            "username": "john",
            "email": "john@example.com",
            "activation_link": "https://example.com/confirm?token=abc123",
            "registration_date": "2026-03-24",
            "to_email": "john@example.com",
            "from_email": "noreply@codelab.local",
        }
        message = await template_engine.render_template("welcome", context)

        assert message.subject is not None
        assert message.to == "john@example.com"
        assert message.from_ == "noreply@codelab.local"
        assert message.template_name == "welcome"
        assert "john" in message.html_body.lower() or "john" in message.text_body.lower()

    @pytest.mark.asyncio
    async def test_render_confirmation_template(self, template_engine):
        """Test rendering confirmation email template"""
        context = {
            "username": "jane",
            "confirmation_link": "https://example.com/confirm?token=def456",
            "expires_at": "2026-03-25 21:03:00",
            "to_email": "jane@example.com",
            "from_email": "noreply@codelab.local",
        }
        message = await template_engine.render_template("confirmation", context)

        assert message.subject is not None
        assert message.to == "jane@example.com"
        assert message.template_name == "confirmation"
        assert len(message.html_body) > 0
        assert len(message.text_body) > 0

    @pytest.mark.asyncio
    async def test_render_password_reset_template(self, template_engine):
        """Test rendering password reset email template"""
        context = {
            "username": "bob",
            "reset_link": "https://example.com/reset?token=ghi789",
            "expires_at": "2026-03-25 21:03:00",
            "to_email": "bob@example.com",
            "from_email": "noreply@codelab.local",
        }
        message = await template_engine.render_template("password_reset", context)

        assert message.subject is not None
        assert message.to == "bob@example.com"
        assert message.template_name == "password_reset"

    @pytest.mark.asyncio
    async def test_template_missing_required_context(self, template_engine):
        """Test template rendering fails when required context is missing"""
        context = {
            "username": "john",
            # Missing to_email
            "from_email": "noreply@codelab.local",
        }
        with pytest.raises(ValueError, match="to_email must be provided"):
            await template_engine.render_template("welcome", context)

    @pytest.mark.asyncio
    async def test_template_not_found(self, template_engine):
        """Test handling of missing template files"""
        context = {
            "username": "john",
            "to_email": "john@example.com",
            "from_email": "noreply@codelab.local",
        }
        with pytest.raises(TemplateNotFound):
            await template_engine.render_template("nonexistent_template", context)

    @pytest.mark.asyncio
    async def test_invalid_template_name(self, template_engine):
        """Test validation of template name (prevent path traversal)"""
        context = {
            "username": "john",
            "to_email": "john@example.com",
            "from_email": "noreply@codelab.local",
        }
        # Test with path traversal attempt
        with pytest.raises(ValueError, match="Invalid template name"):
            await template_engine.render_template("../etc/passwd", context)

        # Test with backslash
        with pytest.raises(ValueError, match="Invalid template name"):
            await template_engine.render_template("test\\template", context)

    def test_extract_text_from_html_simple(self):
        """Test extracting plain text from HTML content"""
        html = "<p>Hello <b>World</b></p>"
        text = EmailTemplateEngine._extract_text_from_html(html)
        assert text == "Hello World"

    def test_extract_text_from_html_with_tags(self):
        """Test HTML text extraction with various tags"""
        html = "<html><body><p>Hello</p><div>World</div></body></html>"
        text = EmailTemplateEngine._extract_text_from_html(html)
        assert "Hello" in text
        assert "World" in text

    def test_extract_text_from_html_with_entities(self):
        """Test HTML text extraction with HTML entities"""
        html = "<p>Hello &lt;World&gt;</p>"
        text = EmailTemplateEngine._extract_text_from_html(html)
        assert "Hello" in text
        assert "<World>" in text

    def test_extract_text_from_html_removes_styles(self):
        """Test that CSS styles are removed from text"""
        html = "<style>body { color: red; }</style><p>Hello</p>"
        text = EmailTemplateEngine._extract_text_from_html(html)
        assert "color:" not in text
        assert "Hello" in text

    def test_extract_text_from_html_normalizes_whitespace(self):
        """Test whitespace normalization in HTML text extraction"""
        html = "<p>Hello    \n\n   World</p>"
        text = EmailTemplateEngine._extract_text_from_html(html)
        assert text == "Hello World"

    @pytest.mark.asyncio
    async def test_html_autoescape_enabled(self, template_engine):
        """Test that HTML autoescape is enabled for security"""
        context = {
            "username": "<script>alert('xss')</script>",
            "to_email": "test@example.com",
            "from_email": "noreply@codelab.local",
        }
        message = await template_engine.render_template("welcome", context)
        # The username should be escaped in the HTML output
        assert "<script>" not in message.html_body or "&lt;script&gt;" in message.html_body
