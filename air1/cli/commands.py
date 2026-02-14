import asyncio
import typer
from air1.services.outreach.service import Service
from air1.services.outreach.email import send_email, EmailTemplate
from air1.db.prisma_client import disconnect_db
from air1.agents.research.crew import ResearchProspectCrew
from air1.agents.research.models import ProspectInput, ICPProfile

app = typer.Typer()


@app.command()
def hello(name: str):
    print(f"Hello {name}")


@app.command()
def company_leads(
    companies: list[str] = typer.Argument(..., help="Companies to scrape"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum number of pages to load"),
    keywords: str = typer.Option(None, "--keywords", "-k", help="Comma-separated keywords to filter by headline (e.g., 'talent,recruitment')"),
):
    """
    Scrape LinkedIn company members and save as leads.

    Examples:
        # Scrape all members
        air1 company-leads aavelabs

        # Filter by single keyword
        air1 company-leads aavelabs --keywords talent

        # Filter by multiple keywords
        air1 company-leads aavelabs --keywords "talent,recruitment,hr"
    """
    async def run():
        try:
            # Parse keywords if provided
            keywords_list = None
            if keywords:
                keywords_list = [k.strip() for k in keywords.split(",")]
                print(f"Filtering by keywords: {keywords_list}")

            async with Service() as service:
                results = await service.scrape_company_leads(
                    companies, limit=limit, keywords=keywords_list
                )
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


@app.command()
def research_prospect(
    linkedin_username: str = typer.Argument(..., help="LinkedIn username to research"),
    company: str = typer.Option(None, "--company", "-c", help="Company name"),
    name: str = typer.Option(None, "--name", "-n", help="Full name of the prospect"),
    headline: str = typer.Option(None, "--headline", "-h", help="LinkedIn headline"),
    target_titles: str = typer.Option("", "--titles", "-t", help="Comma-separated target job titles"),
    target_industries: str = typer.Option("", "--industries", "-i", help="Comma-separated target industries"),
    product: str = typer.Option("", "--product", "-p", help="Product description"),
    value_prop: str = typer.Option("", "--value-prop", "-v", help="Value proposition"),
    quick: bool = typer.Option(False, "--quick", "-q", help="Run quick research only"),
):
    """
    Research a prospect using AI agents.
    
    Examples:
        air1 research-prospect johndoe --company "Acme" --titles "VP Sales,Director Sales"
        air1 research-prospect johndoe --quick
    """
    prospect = ProspectInput(
        linkedin_username=linkedin_username,
        company_name=company,
        full_name=name,
        headline=headline,
    )
    
    icp_profile = ICPProfile(
        target_titles=[t.strip() for t in target_titles.split(",") if t.strip()],
        target_industries=[i.strip() for i in target_industries.split(",") if i.strip()],
        product_description=product,
        value_proposition=value_prop,
    )
    
    crew = ResearchProspectCrew(icp_profile=icp_profile)
    
    print(f"🔍 Researching prospect: {linkedin_username}")
    
    if quick:
        result = crew.quick_research(prospect)
    else:
        result = crew.research_prospect(prospect)
    
    print("\n" + "=" * 50)
    print("📊 Research Results")
    print("=" * 50)
    print(f"Prospect: {result.prospect.linkedin_username}")
    
    if result.icp_score:
        print("\n📈 ICP Score:")
        print(f"  Overall: {result.icp_score.overall}/100")
        print(f"  Problem Intensity: {result.icp_score.problem_intensity}/100")
        print(f"  Relevance: {result.icp_score.relevance}/100")
        print(f"  Likelihood to Respond: {result.icp_score.likelihood_to_respond}/100")
        print(f"  Recommendation: {result.icp_score.recommendation}")
    
    if result.pain_points:
        print("\n🎯 Pain Points:")
        for i, pp in enumerate(result.pain_points, 1):
            print(f"  {i}. {pp.description} (Intensity: {pp.intensity}/10)")
    
    if result.talking_points:
        print("\n💬 Talking Points:")
        for i, tp in enumerate(result.talking_points, 1):
            print(f"  {i}. {tp.point}")
    
    print("\n✅ Research complete!")


