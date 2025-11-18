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
    html_content: str
    text_content: Optional[str] = None


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
        # Remove personalization placeholders if no name available
        content = content.replace("{{name}}", "there")
        content = content.replace("{{first_name}}", "there")
        return content

    # Replace placeholders with actual values
    content = content.replace("{{name}}", recipient_name)
    content = content.replace("{{first_name}}", recipient_name.split()[0] if recipient_name else "there")

    return content


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    recipient_name: Optional[str] = None,
) -> EmailResult:
    """
    Send a single email

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        text_content: Plain text content (optional)
        recipient_name: Recipient name for personalization

    Returns:
        EmailResult with success status and details
    """
    try:
        _configure_resend()

        # Personalize the subject and content
        personalized_subject = _personalize_content(subject, recipient_name)
        personalized_html = _personalize_content(html_content, recipient_name)
        personalized_text = None
        if text_content:
            personalized_text = _personalize_content(text_content, recipient_name)

        # Prepare email parameters following official example pattern
        params = {
            "from": f"{settings.email_from_name} <{settings.email_from_address}>",
            "to": [to_email],
            "subject": personalized_subject,
            "html": personalized_html,
        }

        if personalized_text:
            params["text"] = personalized_text

        # Send email using Resend following official example
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
                    html_content=template.html_content,
                    text_content=template.text_content,
                    recipient_name=recipient.name or recipient.first_name,
                )

                # Small delay between individual emails
                await asyncio.sleep(DELAY_BETWEEN_EMAILS)
                return result

        # Send batch concurrently with rate limiting
        tasks = [send_with_delay(recipient) for recipient in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert any exceptions to failed results
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

        # Log batch summary
        batch_successful = sum(1 for r in batch_results if hasattr(r, 'success') and r.success)
        logger.info(f"Batch {i//BATCH_SIZE + 1} completed: {batch_successful}/{len(batch)} successful")

        # Delay between batches (except for last batch)
        if i + BATCH_SIZE < len(recipients):
            logger.info(f"Waiting {DELAY_BETWEEN_BATCHES} seconds before next batch...")
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    # Final summary
    total_successful = sum(1 for r in all_results if r.success)
    logger.info(f"All batches completed: {total_successful}/{len(recipients)} total emails sent successfully")

    return all_results


async def send_outreach_emails_to_leads(
    leads: List[Dict[str, Any]],
    template: EmailTemplate = None,
) -> List[EmailResult]:
    """
    Convenience function to send outreach emails to leads from database

    Args:
        leads: List of lead dictionaries with email, first_name, full_name etc.
        template: Email template to use (defaults to cold outreach)

    Returns:
        List of EmailResult objects
    """
    if template is None:
        template = DEFAULT_COLD_OUTREACH_TEMPLATE

    if not settings.resend_api_key:
        logger.error("Cannot send emails: RESEND_API_KEY not configured")
        return []

    # Convert leads to EmailRecipient objects
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

    # Send emails
    results = await send_bulk_emails(
        recipients=recipients,
        template=template
    )

    return results


# Template functions
def get_meeting_subject(recipient_name: str) -> str:
    """Generate meeting subject line"""
    return f"{recipient_name} x Ali - Meeting"


# Template constants for common outreach scenarios
DEFAULT_COLD_OUTREACH_EMAIL = """
Hi {{name}},

I'm a senior backend engineer with 4 years of work experience at Anghami and OSN, the biggest streaming platforms in the middle east, as a part of their early teams where I helped scale throughput of ingestion pipelines and platform apis to millions of users (30M+). Being a part of super lean teams, one of my strongest suits has been the ability to work across the stack from building cost efficient and scalable backend systems to high throughput data ingestion pipelines to prod ready frontend components.

Let's chat?

Ali Abbassi
alialabbassi2001@gmail.com
Beirut, Lebanon
linkedin.com/in/alialabbassi/
hoopaudio.com

---
If you'd prefer not to receive these emails, please reply with "unsubscribe".
"""

DEFAULT_COLD_OUTREACH_TEMPLATE = EmailTemplate(
    subject="Quick collaboration opportunity",
    html_content=f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        {DEFAULT_COLD_OUTREACH_EMAIL.replace(chr(10), '<br>')}
    </div>
    """,
    text_content=DEFAULT_COLD_OUTREACH_EMAIL
)

LINKEDIN_CONNECTION_TEMPLATE = EmailTemplate(
    subject="Follow-up on LinkedIn Connection Request",
    html_content="""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Hi {{name}},</h2>

        <p>I recently sent you a connection request on LinkedIn and wanted to follow up via email.</p>

        <p>I'm reaching out because I believe we could have some valuable discussions about opportunities in your industry. I'd love to learn more about your current projects and see if there are ways we might collaborate.</p>

        <p>Would you be open to a brief 15-minute call this week to explore potential synergies?</p>

        <p>Best regards,<br>
        <strong>{{sender_name}}</strong></p>

        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="font-size: 12px; color: #666;">
            This email was sent because you were identified as a potential connection through LinkedIn lead generation.
            If you'd prefer not to receive these emails, please reply with "unsubscribe".
        </p>
    </div>
    """,
    text_content="""
    Hi {{name}},

    I recently sent you a connection request on LinkedIn and wanted to follow up via email.

    I'm reaching out because I believe we could have some valuable discussions about opportunities in your industry. I'd love to learn more about your current projects and see if there are ways we might collaborate.

    Would you be open to a brief 15-minute call this week to explore potential synergies?

    Best regards,
    {{sender_name}}

    ---
    This email was sent because you were identified as a potential connection through LinkedIn lead generation.
    If you'd prefer not to receive these emails, please reply with "unsubscribe".
    """
)

COMPANY_LEADS_TEMPLATE = EmailTemplate(
    subject="Exploring Partnership Opportunities",
    html_content="""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Hello {{name}},</h2>

        <p>I hope this email finds you well. I came across your profile while researching professionals at {{company}} and was impressed by your background.</p>

        <p>I'm reaching out to explore potential partnership opportunities between our organizations. We specialize in [YOUR BUSINESS AREA] and have been looking to connect with innovative companies like {{company}}.</p>

        <p>Would you be interested in a brief conversation to discuss how we might work together? I believe there could be mutual benefits worth exploring.</p>

        <p>I'd be happy to schedule a 15-20 minute call at your convenience.</p>

        <p>Looking forward to your response.</p>

        <p>Best regards,<br>
        <strong>{{sender_name}}</strong></p>

        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="font-size: 12px; color: #666;">
            This email was sent because you were identified as a potential business contact.
            If you'd prefer not to receive these emails, please reply with "unsubscribe".
        </p>
    </div>
    """,
    text_content="""
    Hello {{name}},

    I hope this email finds you well. I came across your profile while researching professionals at {{company}} and was impressed by your background.

    I'm reaching out to explore potential partnership opportunities between our organizations. We specialize in [YOUR BUSINESS AREA] and have been looking to connect with innovative companies like {{company}}.

    Would you be interested in a brief conversation to discuss how we might work together? I believe there could be mutual benefits worth exploring.

    I'd be happy to schedule a 15-20 minute call at your convenience.

    Looking forward to your response.

    Best regards,
    {{sender_name}}

    ---
    This email was sent because you were identified as a potential business contact.
    If you'd prefer not to receive these emails, please reply with "unsubscribe".
    """
)