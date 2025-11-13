import asyncio
import typer
from air1.services.linkedin.service import Service

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
        async with Service() as service:
            results = await service.scrape_company_leads(companies, limit=limit)
            for company, count in results.items():
                print(f"{company}: {count} leads saved")

    asyncio.run(run())
