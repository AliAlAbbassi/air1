from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from loguru import logger

from air1.api.routes import onboarding_router, research_router, account_router, admin_router, leadgen_router
from air1.db.prisma_client import disconnect_db
from air1.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    await disconnect_db()


app = FastAPI(
    title="Hodhod API",
    description="Hodhod Lead Generation API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(onboarding_router)
app.include_router(research_router)
app.include_router(account_router)
app.include_router(admin_router)
app.include_router(leadgen_router)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors (422)."""
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        details.append({"field": field, "message": error["msg"]})
    
    logger.error(f"Validation error on {request.method} {request.url.path}: {details}")
    
    return JSONResponse(
        status_code= 422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Invalid request body",
            "details": details,
        },
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        details.append({"field": field, "message": error["msg"]})
    
    logger.error(f"Pydantic validation error on {request.method} {request.url.path}: {details}")
    
    return JSONResponse(
        status_code=400,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Invalid request body",
            "details": details,
        },
    )


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
