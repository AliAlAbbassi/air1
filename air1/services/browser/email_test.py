"""
Tests for email service functionality
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from air1.services.browser.email import (
    EmailService,
    EmailTemplate,
    EmailRecipient,
    EmailResult,
    LINKEDIN_CONNECTION_TEMPLATE,
    send_outreach_emails_to_leads
)


class TestEmailService:
    """Test cases for EmailService"""

    def test_email_template_creation(self):
        """Test EmailTemplate model validation"""
        template = EmailTemplate(
            subject="Test Subject",
            html_content="<h1>Test HTML</h1>",
            text_content="Test Text"
        )

        assert template.subject == "Test Subject"
        assert template.html_content == "<h1>Test HTML</h1>"
        assert template.text_content == "Test Text"

    def test_email_recipient_creation(self):
        """Test EmailRecipient model validation"""
        recipient = EmailRecipient(
            email="test@example.com",
            name="John Doe",
            first_name="John",
            company="Test Corp"
        )

        assert str(recipient.email) == "test@example.com"
        assert recipient.name == "John Doe"
        assert recipient.first_name == "John"
        assert recipient.company == "Test Corp"

    def test_email_recipient_validation(self):
        """Test EmailRecipient email validation"""
        with pytest.raises(ValueError):
            EmailRecipient(email="invalid-email")

    @patch('air1.services.browser.email.settings.resend_api_key', 'test-api-key')
    @patch('air1.services.browser.email.resend')
    def test_email_service_initialization(self, mock_resend):
        """Test EmailService initialization"""
        service = EmailService()
        assert mock_resend.api_key == 'test-api-key'

    @patch('air1.services.browser.email.settings.resend_api_key', None)
    def test_email_service_missing_api_key(self):
        """Test EmailService raises error when API key is missing"""
        with pytest.raises(ValueError, match="RESEND_API_KEY environment variable is required"):
            EmailService()

    @patch('air1.services.browser.email.settings.resend_api_key', 'test-api-key')
    @patch('air1.services.browser.email.resend')
    @pytest.mark.asyncio
    async def test_send_email_success(self, mock_resend):
        """Test successful email sending"""
        # Mock successful response
        mock_resend.Emails.send.return_value = {'id': 'test-message-id'}

        service = EmailService()
        result = await service.send_email(
            to_email="test@example.com",
            subject="Test Subject",
            html_content="<h1>Test</h1>",
            recipient_name="John Doe"
        )

        assert result.success is True
        assert result.recipient == "test@example.com"
        assert result.message_id == "test-message-id"
        assert result.error is None

    @patch('air1.services.browser.email.settings.resend_api_key', 'test-api-key')
    @patch('air1.services.browser.email.resend')
    @pytest.mark.asyncio
    async def test_send_email_failure(self, mock_resend):
        """Test email sending failure"""
        # Mock API failure
        mock_resend.Emails.send.side_effect = Exception("API Error")

        service = EmailService()
        result = await service.send_email(
            to_email="test@example.com",
            subject="Test Subject",
            html_content="<h1>Test</h1>"
        )

        assert result.success is False
        assert result.recipient == "test@example.com"
        assert result.message_id is None
        assert "API Error" in result.error

    def test_personalize_content_with_name(self):
        """Test content personalization with name"""
        service = EmailService.__new__(EmailService)  # Skip __init__

        content = "Hello {{name}}, welcome to our service!"
        result = service._personalize_content(content, "John Doe")

        assert result == "Hello John Doe, welcome to our service!"

    def test_personalize_content_with_first_name(self):
        """Test content personalization with first name"""
        service = EmailService.__new__(EmailService)  # Skip __init__

        content = "Hi {{first_name}}, how are you?"
        result = service._personalize_content(content, "John Doe")

        assert result == "Hi John, how are you?"

    def test_personalize_content_without_name(self):
        """Test content personalization without name"""
        service = EmailService.__new__(EmailService)  # Skip __init__

        content = "Hello {{name}}, welcome to our service!"
        result = service._personalize_content(content, None)

        assert result == "Hello there, welcome to our service!"

    @patch('air1.services.browser.email.settings.resend_api_key', 'test-api-key')
    @patch('air1.services.browser.email.resend')
    @pytest.mark.asyncio
    async def test_bulk_email_sending(self, mock_resend):
        """Test bulk email sending functionality"""
        # Mock successful responses
        mock_resend.Emails.send.return_value = {'id': 'test-message-id'}

        recipients = [
            EmailRecipient(email="test1@example.com", name="John Doe"),
            EmailRecipient(email="test2@example.com", name="Jane Smith")
        ]

        template = EmailTemplate(
            subject="Test Subject",
            html_content="<h1>Hello {{name}}</h1>"
        )

        service = EmailService()
        results = await service.send_bulk_emails(
            recipients=recipients,
            template=template,
            delay_between_emails=0.1,  # Short delay for testing
            max_concurrent=2
        )

        assert len(results) == 2
        assert all(r.success for r in results)
        assert {r.recipient for r in results} == {"test1@example.com", "test2@example.com"}


class TestEmailTemplates:
    """Test predefined email templates"""

    def test_linkedin_connection_template(self):
        """Test LinkedIn connection template structure"""
        template = LINKEDIN_CONNECTION_TEMPLATE

        assert "LinkedIn" in template.subject
        assert "{{name}}" in template.html_content
        assert "{{name}}" in template.text_content
        assert "unsubscribe" in template.html_content.lower()


class TestEmailWorkflowFunctions:
    """Test workflow integration functions"""

    @patch('air1.services.browser.email.settings.resend_api_key', None)
    @pytest.mark.asyncio
    async def test_send_outreach_emails_no_api_key(self):
        """Test that outreach emails return empty list when no API key"""
        leads = [{"email": "test@example.com", "first_name": "John"}]

        results = await send_outreach_emails_to_leads(leads)

        assert results == []

    @patch('air1.services.browser.email.settings.resend_api_key', 'test-api-key')
    @pytest.mark.asyncio
    async def test_send_outreach_emails_no_valid_emails(self):
        """Test outreach emails with no valid email addresses"""
        leads = [{"first_name": "John"}]  # No email field

        results = await send_outreach_emails_to_leads(leads)

        assert results == []

    @patch('air1.services.browser.email.settings.resend_api_key', 'test-api-key')
    @patch('air1.services.browser.email.EmailService')
    @pytest.mark.asyncio
    async def test_send_outreach_emails_success(self, mock_email_service_class):
        """Test successful outreach email sending"""
        # Mock EmailService instance
        mock_service = AsyncMock()
        mock_service.send_bulk_emails.return_value = [
            EmailResult(success=True, recipient="test@example.com", message_id="123")
        ]
        mock_email_service_class.return_value = mock_service

        leads = [
            {
                "email": "test@example.com",
                "first_name": "John",
                "full_name": "John Doe",
                "company_name": "Test Corp"
            }
        ]

        results = await send_outreach_emails_to_leads(leads)

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].recipient == "test@example.com"

        # Verify EmailService was called with correct parameters
        mock_service.send_bulk_emails.assert_called_once()
        call_args = mock_service.send_bulk_emails.call_args
        recipients = call_args[1]['recipients']
        assert len(recipients) == 1
        assert str(recipients[0].email) == "test@example.com"
        assert recipients[0].name == "John Doe"
        assert recipients[0].first_name == "John"
        assert recipients[0].company == "Test Corp"