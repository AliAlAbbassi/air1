import asyncio
import typer
from air1.services.browser.service import Service
from air1.services.browser.email import EmailService, EmailTemplate, EmailRecipient
from air1.db.db import close_pool

app = typer.Typer()


@app.command()
def hello(name: str):
    print(f"Hello {name}")


@app.command()
def company_leads(
        companies: list[str] = typer.Argument(..., help="Companies to scrape"),
        limit: int = typer.Option(10, "--limit", "-l")
):
    async def run():
        try:
            async with Service() as service:
                results = await service.scrape_company_leads(companies, limit=limit)
                for company, count in results.items():
                    print(f"{company}: {count} leads saved")
        finally:
            await close_pool()

    asyncio.run(run())


@app.command()
def send_test_email(
    to_email: str = typer.Argument(..., help="Recipient email address"),
    subject: str = typer.Option("Test Email from Air1", "--subject", "-s", help="Email subject"),
    name: str = typer.Option(None, "--name", "-n", help="Recipient name for personalization")
):
    """Send a test email using Resend API"""
    async def run():
        try:
            email_service = EmailService()

            template = EmailTemplate(
                subject=subject,
                html_content="""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2>Hello {{name}}!</h2>
                    <p>This is a test email sent from Air1 using Resend API.</p>
                    <p>If you received this email, the integration is working correctly!</p>
                    <p>Best regards,<br>Air1 Team</p>
                </div>
                """,
                text_content="""
                Hello {{name}}!

                This is a test email sent from Air1 using Resend API.
                If you received this email, the integration is working correctly!

                Best regards,
                Air1 Team
                """
            )

            result = await email_service.send_email(
                to_email=to_email,
                subject=template.subject,
                html_content=template.html_content,
                text_content=template.text_content,
                recipient_name=name
            )

            if result.success:
                print(f"✅ Email sent successfully to {to_email}")
                print(f"Message ID: {result.message_id}")
            else:
                print(f"❌ Failed to send email to {to_email}")
                print(f"Error: {result.error}")

        except Exception as e:
            print(f"❌ Error: {e}")

    asyncio.run(run())
