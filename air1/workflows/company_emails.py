from ..services.linkedin.service import Service
import asyncio


async def run():
    print("workflow: company emails")
    company = "forsythbarnes"

    async with Service() as service:
        leads_saved = await service.scrape_and_save_company_leads(
            company, limit=1, headless=False
        )
        print(f"Workflow completed. Total leads saved: {leads_saved}")

    print("yeet")


if __name__ == "__main__":
    asyncio.run(run())
