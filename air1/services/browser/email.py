"""
Email functionality for outreach campaigns using Resend API.
"""

import os
import asyncio
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr
from loguru import logger
import resend
from air1.config import settings


class EmailTemplate(BaseModel):
    """Email template model"""
    subject: str
    content: str


class EmailRecipient(BaseModel):
    """Email recipient model"""
    email: EmailStr
    name: Optional[str] = None
    first_name: Optional[str] = None
    company: Optional[str] = None


class EmailResult(BaseModel):
    """Result of sending an email"""
    success: bool
    recipient: str
    message_id: Optional[str] = None
    error: Optional[str] = None


def _configure_resend():
    """Configure Resend API key"""
    if not settings.resend_api_key:
        raise ValueError("RESEND_API_KEY environment variable is required")
    resend.api_key = settings.resend_api_key


def _personalize_content(content: str, recipient_name: Optional[str]) -> str:
    """
    Personalize email content with recipient information

    Args:
        content: Original content
        recipient_name: Recipient's name

    Returns:
        Personalized content
    """
    if not recipient_name:
        content = content.replace("{{name}}", "there")
        content = content.replace("{{first_name}}", "there")
        return content

    content = content.replace("{{name}}", recipient_name)
    content = content.replace("{{first_name}}", recipient_name.split()[0] if recipient_name else "there")

    return content


async def send_email(
    to_email: str,
    subject: str,
    content: str,
    recipient_name: Optional[str] = None,
) -> EmailResult:
    """
    Send a single email

    Args:
        to_email: Recipient email address
        subject: Email subject
        content: Email content (plain text)
        recipient_name: Recipient name for personalization

    Returns:
        EmailResult with success status and details
    """
    try:
        _configure_resend()

        personalized_subject = _personalize_content(subject, recipient_name)
        personalized_content = _personalize_content(content, recipient_name)

        params = {
            "from": f"{settings.email_from_name} <{settings.email_from_address}>",
            "to": [to_email],
            "subject": personalized_subject,
            "text": personalized_content,
        }

        response = resend.Emails.send(params)

        logger.info(f"Email sent successfully to {to_email}, ID: {response.get('id')}")

        return EmailResult(
            success=True,
            recipient=to_email,
            message_id=response.get('id')
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to send email to {to_email}: {error_msg}")

        return EmailResult(
            success=False,
            recipient=to_email,
            error=error_msg
        )


async def send_bulk_emails(
    recipients: List[EmailRecipient],
    template: EmailTemplate,
) -> List[EmailResult]:
    """
    Send emails to multiple recipients with smart batching and rate limiting

    Args:
        recipients: List of email recipients
        template: Email template to use

    Returns:
        List of EmailResult objects
    """
    BATCH_SIZE = 50
    DELAY_BETWEEN_BATCHES = 60  # 1 minute delay between batches
    DELAY_BETWEEN_EMAILS = 2   # 2 seconds between individual emails
    MAX_CONCURRENT = 5

    all_results = []

    # Process in batches of 50
    for i in range(0, len(recipients), BATCH_SIZE):
        batch = recipients[i:i + BATCH_SIZE]
        logger.info(f"Sending batch {i//BATCH_SIZE + 1}: {len(batch)} emails")

        semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        async def send_with_delay(recipient: EmailRecipient) -> EmailResult:
            async with semaphore:
                result = await send_email(
                    to_email=str(recipient.email),
                    subject=template.subject,
                    content=template.content,
                    recipient_name=recipient.name or recipient.first_name,
                )

                await asyncio.sleep(DELAY_BETWEEN_EMAILS)
                return result

        tasks = [send_with_delay(recipient) for recipient in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for j, result in enumerate(batch_results):
            if isinstance(result, Exception):
                all_results.append(
                    EmailResult(
                        success=False,
                        recipient=str(batch[j].email),
                        error=str(result)
                    )
                )
            else:
                all_results.append(result)

        batch_successful = sum(1 for r in batch_results if hasattr(r, 'success') and r.success)
        logger.info(f"Batch {i//BATCH_SIZE + 1} completed: {batch_successful}/{len(batch)} successful")

        if i + BATCH_SIZE < len(recipients):
            logger.info(f"Waiting {DELAY_BETWEEN_BATCHES} seconds before next batch...")
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    total_successful = sum(1 for r in all_results if r.success)
    logger.info(f"All batches completed: {total_successful}/{len(recipients)} total emails sent successfully")

    return all_results


async def send_outreach_emails_to_leads(
    leads: List[Dict[str, Any]],
    template: EmailTemplate,
) -> List[EmailResult]:
    """
    Convenience function to send outreach emails to leads from database

    Args:
        leads: List of lead dictionaries with email, first_name, full_name etc.
        template: Email template to use

    Returns:
        List of EmailResult objects
    """

    if not settings.resend_api_key:
        logger.error("Cannot send emails: RESEND_API_KEY not configured")
        return []

    recipients = []
    for lead in leads:
        if lead.get('email'):
            recipient = EmailRecipient(
                email=lead['email'],
                name=lead.get('full_name') or lead.get('first_name'),
                first_name=lead.get('first_name'),
                company=lead.get('company_name')
            )
            recipients.append(recipient)

    if not recipients:
        logger.warning("No valid email addresses found in leads")
        return []

    results = await send_bulk_emails(
        recipients=recipients,
        template=template
    )

    return results




