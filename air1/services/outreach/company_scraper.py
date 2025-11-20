from playwright.async_api import Page
from .linkedin_profile import CompanyPeople
from loguru import logger


class CompanyScraper:
    """Handles LinkedIn company members extraction"""

    @staticmethod
    async def extract_company_members(
        page: Page, company_id: str, limit: int = 10
    ) -> CompanyPeople:
        """Extract profile IDs of people working at a company"""
        try:
            await page.locator(
                ".org-people-profile-card__profile-card-spacing"
            ).first.wait_for(timeout=10000)

            profile_ids = set()
            clicks = 0

            while clicks < limit:
                profile_links = await page.locator('a[href*="/in/"]').all()

                for link in profile_links:
                    href = await link.get_attribute("href")
                    if href and "/in/" in href:
                        profile_id = href.split("/in/")[1].split("?")[0]
                        if profile_id:
                            profile_ids.add(profile_id)

                show_more_button = page.locator(
                    'button:has-text("Show more results")'
                ).first

                if (
                    await show_more_button.count() > 0
                    and await show_more_button.is_visible()
                ):
                    await show_more_button.click()
                    clicks += 1
                    await page.wait_for_timeout(2000)
                else:
                    break

            logger.info(f"Found {len(profile_ids)} profiles for company {company_id}")
            return CompanyPeople(profile_ids=profile_ids)

        except Exception as e:
            logger.error(f"Error scraping company profiles: {str(e)}")
            return CompanyPeople(profile_ids=set())
