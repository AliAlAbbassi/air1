"""
Tests for email service functionality
"""

import pytest
from unittest.mock import patch
from air1.services.outreach.email import (
    send_email,
    send_bulk_emails,
    EmailTemplate,
    EmailRecipient,
    EmailResult,
    send_outreach_emails_to_leads,
)


class TestEmailService:
    """Test cases for EmailService"""

    def test_email_template_creation(self):
        """Test EmailTemplate model validation"""
        template = EmailTemplate(subject="Test Subject", content="Test Content")

        assert template.subject == "Test Subject"
        assert template.content == "Test Content"

    def test_email_recipient_creation(self):
        """Test EmailRecipient model validation"""
        recipient = EmailRecipient(
            email="test@example.com",
            name="John Doe",
            first_name="John",
            company="Test Corp",
        )

        assert str(recipient.email) == "test@example.com"
        assert recipient.name == "John Doe"
        assert recipient.first_name == "John"
        assert recipient.company == "Test Corp"

    def test_email_recipient_validation(self):
        """Test EmailRecipient email validation"""
        with pytest.raises(ValueError):
            EmailRecipient(email="invalid-email")

    @patch("air1.services.outreach.email.settings.resend_api_key", None)
    @pytest.mark.asyncio
    async def test_send_email_missing_api_key(self):
        """Test send_email raises error when API key is missing"""
        with pytest.raises(
            ValueError, match="RESEND_API_KEY environment variable is required"
        ):
            await send_email("test@example.com", "Test", "Content")

    @patch("air1.services.outreach.email.settings.resend_api_key", "test-api-key")
    @patch("air1.services.outreach.email.resend")
    @pytest.mark.asyncio
    async def test_send_email_success(self, mock_resend):
        """Test successful email sending"""
        # Mock successful response
        mock_resend.Emails.send.return_value = {"id": "test-message-id"}

        result = await send_email(
            to_email="test@example.com",
            subject="Test Subject",
            content="Test content",
            recipient_name="John Doe",
        )

        assert result.success is True
        assert result.recipient == "test@example.com"
        assert result.message_id == "test-message-id"
        assert result.error is None

    @patch("air1.services.outreach.email.settings.resend_api_key", "test-api-key")
    @patch("air1.services.outreach.email.resend")
    @pytest.mark.asyncio
    async def test_send_email_failure(self, mock_resend):
        """Test email sending failure"""
        # Mock API failure
        mock_resend.Emails.send.side_effect = Exception("API Error")

        result = await send_email(
            to_email="test@example.com", subject="Test Subject", content="Test content"
        )

        assert result.success is False
        assert result.recipient == "test@example.com"
        assert result.message_id is None
        assert result.error is not None and "API Error" in result.error

    def test_personalize_content_with_name(self):
        """Test content personalization with name"""
        from air1.services.outreach.email import _personalize_content

        content = "Hello {{name}}, welcome to our service!"
        result = _personalize_content(content, "John Doe")

        assert result == "Hello John Doe, welcome to our service!"

    def test_personalize_content_with_first_name(self):
        """Test content personalization with first name"""
        from air1.services.outreach.email import _personalize_content

        content = "Hi {{first_name}}, how are you?"
        result = _personalize_content(content, "John Doe")

        assert result == "Hi John, how are you?"

    def test_personalize_content_without_name(self):
        """Test content personalization without name"""
        from air1.services.outreach.email import _personalize_content

        content = "Hello {{name}}, welcome to our service!"
        result = _personalize_content(content, None)

        assert result == "Hello there, welcome to our service!"

    @patch("air1.services.outreach.email.settings.resend_api_key", "test-api-key")
    @patch("air1.services.outreach.email.resend")
    @pytest.mark.asyncio
    async def test_bulk_email_sending(self, mock_resend):
        """Test bulk email sending functionality"""
        # Mock successful responses
        mock_resend.Emails.send.return_value = {"id": "test-message-id"}

        recipients = [
            EmailRecipient(email="test1@example.com", name="John Doe"),
            EmailRecipient(email="test2@example.com", name="Jane Smith"),
        ]

        template = EmailTemplate(subject="Test Subject", content="Hello {{name}}")

        results = await send_bulk_emails(recipients=recipients, template=template)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert {r.recipient for r in results} == {
            "test1@example.com",
            "test2@example.com",
        }


class TestEmailTemplates:
    """Test predefined email templates"""

    def test_template_functions_exist(self):
        """Test template functions exist and work"""
        from air1.services.outreach.templates import (
            get_meeting_subject,
            get_engineering_subject,
        )

        # Just test they don't crash, don't care about specific names
        meeting_subject = get_meeting_subject("TestPerson")
        engineering_subject = get_engineering_subject()

        assert "Ali" in meeting_subject
        assert "Ali" in engineering_subject


class TestEmailWorkflowFunctions:
    """Test workflow integration functions"""

    @patch("air1.services.outreach.email.settings.resend_api_key", None)
    @pytest.mark.asyncio
    async def test_send_outreach_emails_no_api_key(self):
        """Test that outreach emails return empty list when no API key"""
        template = EmailTemplate(subject="Test", content="Test content")
        leads = [{"email": "test@example.com", "first_name": "John"}]

        results = await send_outreach_emails_to_leads(leads, template)

        assert results == []

    @patch("air1.services.outreach.email.settings.resend_api_key", "test-api-key")
    @pytest.mark.asyncio
    async def test_send_outreach_emails_no_valid_emails(self):
        """Test outreach emails with no valid email addresses"""
        template = EmailTemplate(subject="Test", content="Test content")
        leads = [{"first_name": "John"}]  # No email field

        results = await send_outreach_emails_to_leads(leads, template)

        assert results == []

    @patch("air1.services.outreach.email.settings.resend_api_key", "test-api-key")
    @patch("air1.services.outreach.email.send_bulk_emails")
    @pytest.mark.asyncio
    async def test_send_outreach_emails_success(self, mock_send_bulk_emails):
        """Test successful outreach email sending"""
        # Mock send_bulk_emails function
        mock_send_bulk_emails.return_value = [
            EmailResult(success=True, recipient="test@example.com", message_id="123")
        ]

        template = EmailTemplate(subject="Test", content="Test content")
        leads = [
            {
                "email": "test@example.com",
                "first_name": "John",
                "full_name": "John Doe",
                "company_name": "Test Corp",
            }
        ]

        results = await send_outreach_emails_to_leads(leads, template)

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].recipient == "test@example.com"

        # Verify send_bulk_emails was called with correct parameters
        mock_send_bulk_emails.assert_called_once()
        call_args = mock_send_bulk_emails.call_args
        recipients = call_args[1]["recipients"]
        assert len(recipients) == 1
        assert str(recipients[0].email) == "test@example.com"
        assert recipients[0].name == "John Doe"
        assert recipients[0].first_name == "John"
        assert recipients[0].company == "Test Corp"
