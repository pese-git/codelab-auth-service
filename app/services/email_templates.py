"""Email template engine for rendering email messages with Jinja2"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

logger = logging.getLogger("auth-service")


@dataclass
class EmailMessage:
    """Email message with subject, HTML and text body"""

    subject: str
    """Email subject line"""

    html_body: str
    """HTML version of the email"""

    text_body: str
    """Plain text version of the email"""

    to: str
    """Recipient email address"""

    from_: str
    """Sender email address"""

    template_name: str
    """Name of template used for logging"""

    def as_string(self) -> str:
        """Convert message to string for SMTP transmission

        Returns:
            Formatted email string suitable for SMTP
        """
        headers = f"From: {self.from_}\r\nTo: {self.to}\r\nSubject: {self.subject}\r\n"
        return f"{headers}\r\n{self.html_body}"


class EmailTemplateEngine:
    """Jinja2-based email template engine with autoescape for security"""

    def __init__(self, template_dir: Path | str):
        """Initialize template engine

        Args:
            template_dir: Path to directory containing email templates

        Example:
            >>> engine = EmailTemplateEngine(Path("app/templates/emails"))
            >>> message = engine.render_template("welcome", {"username": "john"})
        """
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(
                enabled_extensions=("html", "txt"),
                default_for_string=True,
            ),
        )

    async def render_template(
        self, template_name: str, context: dict
    ) -> EmailMessage:
        """Render email template with given context

        Loads and renders both HTML (template.html) and text (subject.txt)
        versions of a template.

        Args:
            template_name: Name of template directory (e.g., "welcome")
            context: Dictionary with variables for template rendering

        Returns:
            EmailMessage with rendered content

        Raises:
            TemplateNotFound: If template files don't exist
            ValueError: If template_name is invalid

        Example:
            >>> context = {
            ...     "username": "john",
            ...     "activation_link": "https://example.com/confirm?token=abc"
            ... }
            >>> message = await engine.render_template("welcome", context)
            >>> message.subject
            'Welcome to CodeLab'
        """
        if not template_name or "/" in template_name or "\\" in template_name:
            raise ValueError(f"Invalid template name: {template_name}")

        try:
            # Load subject from text file
            subject_template = self.env.get_template(
                f"{template_name}/subject.txt"
            )
            subject = subject_template.render(**context).strip()

            # Load HTML body
            html_template = self.env.get_template(
                f"{template_name}/template.html"
            )
            html_body = html_template.render(**context)

            # Create text version by stripping HTML tags (basic)
            text_body = self._extract_text_from_html(html_body)

            # Get sender and recipient from context
            from_email = context.get("from_email", "noreply@codelab.local")
            to_email = context.get("to_email")

            if not to_email:
                raise ValueError("to_email must be provided in context")

            return EmailMessage(
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                to=to_email,
                from_=from_email,
                template_name=template_name,
            )
        except TemplateNotFound as e:
            logger.error(
                f"Template not found: {template_name}. Error: {e}"
            )
            raise

    @staticmethod
    def _extract_text_from_html(html: str) -> str:
        """Extract plain text from HTML content

        Simple implementation that removes common HTML tags
        and preserves text content.

        Args:
            html: HTML string

        Returns:
            Plain text version

        Example:
            >>> html = "<p>Hello <b>World</b></p>"
            >>> EmailTemplateEngine._extract_text_from_html(html)
            'Hello World'
        """
        import re

        # Remove style and script tags
        text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
        text = re.sub(
            r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL
        )

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Decode HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&amp;", "&")

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text
