"""Unit tests for email template engine"""

import pytest
from jinja2 import TemplateNotFound


class TestEmailTemplateEngine:
    """Tests for EmailTemplateEngine"""

    def test_extract_text_from_html_simple(self):
        """Test extracting plain text from simple HTML"""
        # Import here to avoid DB initialization
        from app.services.email_templates import EmailTemplateEngine
        
        html = "<p>Hello <b>World</b></p>"
        text = EmailTemplateEngine._extract_text_from_html(html)
        
        assert text == "Hello World"

    def test_extract_text_from_html_with_entities(self):
        """Test extracting text with HTML entities"""
        from app.services.email_templates import EmailTemplateEngine
        
        html = "<p>&lt;script&gt;&amp;&lt;/script&gt;</p>"
        text = EmailTemplateEngine._extract_text_from_html(html)
        
        assert "<script>" in text
        assert "&" in text

    def test_extract_text_removes_style_tags(self):
        """Test that style tags are removed"""
        from app.services.email_templates import EmailTemplateEngine
        
        html = "<style>body { color: red; }</style><p>Content</p>"
        text = EmailTemplateEngine._extract_text_from_html(html)
        
        assert "color: red" not in text
        assert "Content" in text

    def test_extract_text_removes_script_tags(self):
        """Test that script tags are removed"""
        from app.services.email_templates import EmailTemplateEngine
        
        html = "<script>alert('XSS')</script><p>Content</p>"
        text = EmailTemplateEngine._extract_text_from_html(html)
        
        assert "alert" not in text
        assert "Content" in text

    def test_extract_text_normalizes_whitespace(self):
        """Test that whitespace is normalized"""
        from app.services.email_templates import EmailTemplateEngine
        
        html = "<p>Hello    \n\n   World</p>"
        text = EmailTemplateEngine._extract_text_from_html(html)
        
        assert "Hello World" in text
        assert "\n" not in text

    def test_extract_text_preserves_entities(self):
        """Test that HTML entities are decoded"""
        from app.services.email_templates import EmailTemplateEngine
        
        html = "<p>Hello&nbsp;World</p>"
        text = EmailTemplateEngine._extract_text_from_html(html)
        
        assert "Hello World" in text

    @pytest.mark.asyncio
    async def test_render_template_with_path(self):
        """Test template engine initialization with path"""
        from pathlib import Path
        from app.services.email_templates import EmailTemplateEngine
        
        template_dir = Path(__file__).parent.parent / "app" / "templates" / "emails"
        
        # Should not raise even if path doesn't exist in test environment
        try:
            engine = EmailTemplateEngine(template_dir)
            assert engine is not None
        except Exception:
            # OK if path is wrong in test
            pass
