import asyncio
from typing import Optional

import typer

from air1.db.prisma_client import disconnect_db

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
            from air1.services.outreach.service import Service

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
            from air1.services.outreach.email import send_email, EmailTemplate

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
    from air1.agents.research.crew import ResearchProspectCrew
    from air1.agents.research.models import ProspectInput, ICPProfile

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


@app.command()
def leadgen(
    software: str = typer.Option(..., "--software", "-s", help="Software slug to detect (e.g., 'cloudbeds')"),
    location: str = typer.Option(..., "--location", "-l", help="Location to search (e.g., 'Miami, FL')"),
    radius: float = typer.Option(25.0, "--radius", "-r", help="Search radius in km"),
    business_type: str = typer.Option("business", "--business-type", "-b", help="Business type to search for (e.g., 'hotel')"),
    concurrency: int = typer.Option(5, "--concurrency", "-c", help="Concurrent detection workers"),
    cell_size: float = typer.Option(2.0, "--cell-size", help="Grid cell size in km"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="Clerk user ID"),
):
    """
    Find businesses that use a specific software product.

    Examples:
        air1 leadgen -s cloudbeds -l "Miami, FL" -b hotel -r 10
        air1 leadgen -s shopify -l "San Francisco, CA" -b store
    """
    async def run():
        try:
            from air1.services.leadgen.flows import leadgen_search_flow

            # Geocode location to lat/lng
            lat, lng = await _geocode_location(location)
            print(f"Searching for '{software}' users near {location} ({lat:.4f}, {lng:.4f})")
            print(f"Radius: {radius}km | Business type: {business_type} | Concurrency: {concurrency}")
            print()

            result = await leadgen_search_flow(
                software_slug=software,
                center_lat=lat,
                center_lng=lng,
                radius_km=radius,
                business_type=business_type,
                cell_size_km=cell_size,
                concurrency=concurrency,
                user_id=user_id,
            )

            stats = result["stats"]
            print()
            print("=" * 50)
            print(f"Search #{result['search_id']} complete")
            print(f"  Businesses found:    {stats['businesses_found']}")
            print(f"  With websites:       {stats['businesses_with_website']}")
            print(f"  Software detected:   {stats['detected_count']}")
            print(f"  Not detected:        {stats['not_detected_count']}")
            print(f"  Detection errors:    {stats['detection_errors']}")
            print(f"  API calls used:      {stats['api_calls']}")
            print("=" * 50)
        except Exception as e:
            print(f"Error: {e}")
            raise
        finally:
            await disconnect_db()

    asyncio.run(run())


async def _geocode_location(location: str) -> tuple[float, float]:
    """Geocode a location string to (lat, lng) using Nominatim."""
    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": location, "format": "json", "limit": 1},
            headers={"User-Agent": "Air1 LeadGen/1.0"},
        )
        resp.raise_for_status()
        results = resp.json()

        if not results:
            raise ValueError(f"Could not geocode location: {location}")

        return float(results[0]["lat"]), float(results[0]["lon"])
