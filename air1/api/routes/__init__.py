from .auth import router as auth_router
from .onboarding import router as onboarding_router
from .research import router as research_router
from .account import router as account_router

__all__ = ["auth_router", "onboarding_router", "research_router", "account_router"]
