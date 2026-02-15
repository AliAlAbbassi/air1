"""Abstract base class for business discovery sources."""

from abc import ABC, abstractmethod

from air1.services.leadgen.models import DiscoveredBusiness, SearchParams


class DiscoverySource(ABC):
    """Base class for business discovery sources.

    Implementations: SerperMapsSource, (future) SerperWebSource, CommonCrawlSource, etc.
    """

    @abstractmethod
    async def discover(self, params: SearchParams) -> list[DiscoveredBusiness]:
        """Discover businesses matching the search parameters.

        Returns a deduplicated list of businesses found in the search area.
        """
        ...
