from .onboarding import router as onboarding_router
from .research import router as research_router
from .account import router as account_router
from .admin import router as admin_router

__all__ = ["onboarding_router", "research_router", "account_router", "admin_router"]
