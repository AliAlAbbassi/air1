import random

from loguru import logger
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .exceptions import CompanyScrapingError
from .linkedin_profile import CompanyPeople

# Exception handling note:
# AttributeError is caught as expected because Playwright locator operations can raise
# it when elements are detached from the DOM or when accessing properties on stale elements.


class CompanyScraper:
    """Handles LinkedIn company members extraction."""

    @staticmethod
    async def extract_company_members(
        page: Page, company_id: str, limit: int = 10
    ) -> CompanyPeople:
        """Extract profile IDs of people working at a company.

        Args:
            page: Playwright page with LinkedIn company people page loaded.
            company_id: LinkedIn company identifier.
            limit: Maximum number of "Show more" clicks to perform.

        Returns:
            CompanyPeople with extracted profile IDs, or empty set on expected
            scraping failures (timeouts, missing elements, parse errors).

        Raises:
            CompanyScrapingError: On unexpected errors requiring investigation.
        """
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
                    # Random delay between 2-5 seconds to emulate human scrolling
                    delay = random.uniform(2000, 5000)
                    await page.wait_for_timeout(delay)
                else:
                    break

            logger.info(f"Found {len(profile_ids)} profiles for company {company_id}")
            return CompanyPeople(profile_ids=profile_ids)

        except PlaywrightTimeoutError as e:
            # Expected: page didn't load in time or elements not found
            logger.error(f"Timeout while scraping company {company_id}: {str(e)}")
            return CompanyPeople(profile_ids=set())
        except (AttributeError, ValueError) as e:
            # Expected: DOM elements detached or href parsing failed
            logger.error(f"Failed to parse company {company_id} page: {str(e)}")
            return CompanyPeople(profile_ids=set())
        except Exception as e:
            logger.error(f"Unexpected error scraping company {company_id}: {str(e)}")
            raise CompanyScrapingError(
                f"Unexpected error scraping company {company_id}: {str(e)}"
            ) from e

    @staticmethod
    async def extract_company_info(page: Page, company_id: str) -> dict:
        """Extract company information from the about page.

        Args:
            page: Playwright page with LinkedIn company about page loaded.
            company_id: LinkedIn company identifier.

        Returns:
            Dictionary with company details (name, description, website, industry, logo)
        """
        data = {
            "name": "",
            "description": "",
            "website": "",
            "industry": "",
            "logo": None,
        }

        try:
            # Wait for main content
            try:
                await page.wait_for_selector("main", timeout=10000)
            except Exception:
                logger.warning(f"Timeout waiting for main content for {company_id}")

            # Extract Name
            name_selectors = ["h1", ".org-top-card-summary__title"]
            for selector in name_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.count() > 0:
                        name = await elem.text_content()
                        if name:
                            data["name"] = name.strip()
                            break
                except Exception:
                    continue

            # Extract Description
            desc_selectors = [
                "p.break-words",
                ".org-page-details-module__description",
                "section.artdeco-card p",
            ]
            for selector in desc_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.count() > 0:
                        desc = await elem.text_content()
                        if desc:
                            data["description"] = desc.strip()
                            break
                except Exception:
                    continue

            # Extract Website
            website_selectors = [
                ".org-page-details-module__website-link",
                "a[href^='http']:has-text('Visit website')",
                "dt:has-text('Website') + dd a",
            ]
            for selector in website_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.count() > 0:
                        href = await elem.get_attribute("href")
                        if href:
                            data["website"] = href.strip()
                            break
                except Exception:
                    continue

            # Extract Industry
            industry_selectors = [
                ".org-top-card-summary-info-list__info-item:first-child",
                "dt:has-text('Industry') + dd",
            ]
            for selector in industry_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.count() > 0:
                        industry = await elem.text_content()
                        if industry:
                            data["industry"] = industry.strip()
                            break
                except Exception:
                    continue

            # Extract Logo
            logo_selectors = [
                ".org-top-card-primary-content__logo-container img",
                "img.org-top-card-primary-content__logo",
            ]
            for selector in logo_selectors:
                try:
                    elem = page.locator(selector).first
                    if await elem.count() > 0:
                        src = await elem.get_attribute("src")
                        if src:
                            data["logo"] = src.strip()
                            break
                except Exception:
                    continue

            return data

        except Exception as e:
            logger.error(f"Error scraping company info for {company_id}: {e}")
            return data
