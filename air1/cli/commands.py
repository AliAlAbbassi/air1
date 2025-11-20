import asyncio
import typer
from air1.services.outreach.service import Service
from air1.services.outreach.email import send_email, EmailTemplate
from air1.db.prisma_client import disconnect_db

app = typer.Typer()


@app.command()
def hello(name: str):
    print(f"Hello {name}")


@app.command()
def company_leads(
    companies: list[str] = typer.Argument(..., help="Companies to scrape"),
    limit: int = typer.Option(10, "--limit", "-l"),
):
    async def run():
        try:
            async with Service() as service:
                results = await service.scrape_company_leads(companies, limit=limit)
                for company, count in results.items():
                    print(f"{company}: {count} leads saved")
        finally:
            await disconnect_db()

    asyncio.run(run())


@app.command()
def send_test_email(
    to_email: str = typer.Argument(..., help="Recipient email address"),
    subject: str = typer.Option(
        "Test Email from Air1", "--subject", "-s", help="Email subject"
    ),
    name: str = typer.Option(
        None, "--name", "-n", help="Recipient name for personalization"
    ),
):
    """Send a test email using Resend API"""

    async def run():
        try:
            template = EmailTemplate(
                subject=subject,
                content="""
Hello {{name}}!

This is a test email sent from Air1 using Resend API.
If you received this email, the integration is working correctly!

Best regards,
Air1 Team
                """,
            )

            result = await send_email(
                to_email=to_email,
                subject=template.subject,
                content=template.content,
                recipient_name=name,
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
