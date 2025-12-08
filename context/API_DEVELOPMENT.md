# API Development Guide

This document provides patterns and instructions for creating new API endpoints in the Air1 codebase.

## Architecture Overview

```
air1/
├── api/
│   ├── models/          # Pydantic request/response models
│   └── routes/          # FastAPI route handlers
├── services/
│   └── outreach/
│       ├── service.py   # Main Service class (facade)
│       ├── *_repo.py    # Repository layer
│       └── *.py         # Business logic functions
├── db/
│   ├── query/           # SQL files (aiosql format)
│   └── migrations/      # Database migrations
└── config.py            # Settings via pydantic-settings
```

## Layer Responsibilities

### 1. API Models (`air1/api/models/`)

Pydantic models for request validation and response serialization.

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from enum import Enum

class MyEnum(str, Enum):
    OPTION_A = "option_a"
    OPTION_B = "option_b"

class MyRequest(BaseModel):
    # Use Field for validation and aliasing (camelCase for API, snake_case internally)
    name: str = Field(..., min_length=1)
    email_address: str = Field(..., alias="emailAddress")
    optional_field: Optional[str] = None
    
    model_config = {"populate_by_name": True}
    
    @field_validator("email_address")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v
    
    @model_validator(mode="after")
    def validate_model(self):
        # Cross-field validation
        return self

class MyResponse(BaseModel):
    id: str
    name: str
    
    model_config = {"populate_by_name": True, "by_alias": True}
```

### 2. Routes (`air1/api/routes/`)

FastAPI route handlers - thin layer that delegates to Service.

```python
from fastapi import APIRouter, HTTPException
from loguru import logger

from air1.api.models.my_feature import MyRequest, MyResponse, ErrorResponse
from air1.services.outreach.my_feature import MyCustomError
from air1.services.outreach.service import Service

router = APIRouter(prefix="/api/my-feature", tags=["my-feature"])

@router.post(
    "",
    response_model=MyResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        409: {"model": ErrorResponse, "description": "Conflict"},
    },
)
async def create_something(request: MyRequest):
    """Endpoint description for OpenAPI docs."""
    async with Service() as service:
        try:
            return await service.do_something(request)
        except MyCustomError:
            raise HTTPException(
                status_code=409,
                detail={"error": "ERROR_CODE", "message": "Human readable message"},
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise HTTPException(
                status_code=500,
                detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
            )
```

### 3. Service (`air1/services/outreach/service.py`)

Main facade class - add methods here that delegate to business logic.

```python
class Service(IService):
    # ... existing code ...
    
    async def do_something(self, request):
        """Do something with the request."""
        from air1.services.outreach.my_feature import do_something
        return await do_something(request)
```

### 4. Business Logic (`air1/services/outreach/*.py`)

Pure business logic functions - no HTTP concerns.

```python
"""Business logic for my feature."""
from typing import Optional
from pydantic import BaseModel
from loguru import logger

from air1.api.models.my_feature import MyRequest, MyResponse
from air1.services.outreach.my_feature_repo import (
    get_something,
    create_something,
)

class MyCustomError(Exception):
    """Raised when something specific fails."""
    pass

async def do_something(request: MyRequest) -> MyResponse:
    """Main business logic function."""
    # Check preconditions
    existing = await get_something(request.name)
    if existing:
        raise MyCustomError("Already exists")
    
    # Do the work
    result = await create_something(request)
    
    # Return response
    return MyResponse(id=str(result["id"]), name=request.name)
```

### 5. Repository (`air1/services/outreach/*_repo.py`)

Database operations using aiosql queries.

```python
"""Repository functions for my feature."""
from typing import Optional
from loguru import logger
from prisma.errors import PrismaError

from air1.db.prisma_client import get_prisma
from air1.db.sql_loader import my_feature_queries as queries

class SomethingExistsError(Exception):
    """Raised when record already exists."""
    pass

async def get_something(name: str) -> Optional[dict]:
    """Get something by name."""
    try:
        prisma = await get_prisma()
        return await queries.get_by_name(prisma, name=name)
    except PrismaError as e:
        logger.error(f"Database error: {e}")
        return None

async def create_something(data: dict) -> tuple[bool, Optional[int]]:
    """Create something in a transaction."""
    try:
        prisma = await get_prisma()
        
        async with prisma.tx() as tx:
            result = await queries.insert_something(tx, **data)
            if not result:
                raise SomethingExistsError("Already exists")
            return True, result["id"]
            
    except SomethingExistsError:
        raise
    except PrismaError as e:
        logger.error(f"Database error: {e}")
        return False, None
```

### 6. SQL Queries (`air1/db/query/*.sql`)

aiosql format with named parameters.

```sql
-- name: get_by_name^
-- Get record by name (^ = returns single row or None)
SELECT id, name, created_on
FROM my_table
WHERE name = :name;

-- name: insert_something<!
-- Insert and return ID (<! = returns single row)
INSERT INTO my_table (name, description)
VALUES (:name, :description)
ON CONFLICT (name) DO NOTHING
RETURNING id;

-- name: get_all
-- Get all records (no suffix = returns list)
SELECT id, name FROM my_table;
```

**Query suffixes:**
- `^` - Returns single row or None
- `<!` - Returns single row (for INSERT RETURNING)
- `!` - Execute only, no return
- (none) - Returns list of rows

### 7. Migrations (`air1/db/migrations/`)

Idempotent SQL migrations.

```sql
-- Migration: Add my_feature tables
-- Always use IF NOT EXISTS / IF EXISTS for idempotency

CREATE TABLE IF NOT EXISTS my_table (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    created_on TIMESTAMP DEFAULT NOW()
);

ALTER TABLE existing_table ADD COLUMN IF NOT EXISTS new_column TEXT;

CREATE INDEX IF NOT EXISTS idx_my_table_name ON my_table(name);
```

## Testing

### Test File Structure

```python
"""Tests for my feature."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Test fixtures in air1/conftest.py provide:
# - use_real_db: bool fixture
# - db_connection: connects to real DB if --use-real-db flag

class TestMyFeature:
    @pytest.mark.asyncio
    async def test_success(self, db_connection, test_uuid):
        """Test successful case."""
        if db_connection:
            # Real DB test
            result = await do_something(data)
            assert result is not None
        else:
            # Mocked test
            with patch("air1.services.outreach.my_feature_repo.get_prisma") as mock:
                # Setup mocks
                result = await do_something(data)
                assert result is not None
```

### Running Tests

```bash
# With mocks (fast, for CI)
uv run pytest air1/services/outreach/my_feature_test.py -v

# Against real database (for integration testing)
uv run pytest air1/services/outreach/my_feature_test.py --use-real-db -v
```

## Checklist for New API Endpoint

1. **Models** (`air1/api/models/my_feature.py`)
   - [ ] Request model with validation
   - [ ] Response model
   - [ ] Error response model
   - [ ] Use camelCase aliases for API, snake_case internally

2. **Routes** (`air1/api/routes/my_feature.py`)
   - [ ] Router with prefix and tags
   - [ ] Route handler delegating to Service
   - [ ] Proper HTTP status codes
   - [ ] Error handling with HTTPException

3. **Service** (`air1/services/outreach/service.py`)
   - [ ] Add method to IService interface
   - [ ] Add implementation to Service class

4. **Business Logic** (`air1/services/outreach/my_feature.py`)
   - [ ] Custom exception classes
   - [ ] Main logic function(s)
   - [ ] Input validation beyond Pydantic

5. **Repository** (`air1/services/outreach/my_feature_repo.py`)
   - [ ] Database operation functions
   - [ ] Transaction handling where needed
   - [ ] Error handling and logging

6. **SQL** (`air1/db/query/my_feature.sql`)
   - [ ] Named queries with proper suffixes
   - [ ] ON CONFLICT handling for upserts
   - [ ] RETURNING clauses for inserts

7. **Migration** (`air1/db/migrations/NNN_my_feature.sql`)
   - [ ] Idempotent DDL statements
   - [ ] IF NOT EXISTS / IF EXISTS

8. **Register Route** (`air1/app.py`)
   - [ ] Import router
   - [ ] Include router in app

9. **Tests** (`air1/services/outreach/my_feature_test.py`)
   - [ ] Unit tests with mocks
   - [ ] Integration tests with db_connection fixture
   - [ ] Test both success and error cases

## Common Patterns

### Password Hashing
```python
import hashlib
import secrets

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}:{hashed.hex()}"
```

### JWT Creation
```python
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

def create_jwt(user_id: int, email: str, secret: str, expiry_hours: int) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    
    signature = hmac.new(secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"
```

### External API Verification
```python
import httpx

async def verify_external_token(token: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://api.example.com/verify?token={token}")
            if resp.status_code == 200:
                return resp.json()
            return None
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return None
```

### Transaction with Multiple Inserts
```python
async def create_with_related(data: dict) -> tuple[bool, Optional[int]]:
    prisma = await get_prisma()
    
    async with prisma.tx() as tx:
        # Insert parent
        parent = await queries.insert_parent(tx, **parent_data)
        if not parent:
            raise ParentExistsError()
        
        parent_id = parent["id"]
        
        # Insert children
        await queries.insert_child(tx, parent_id=parent_id, **child_data)
        
        return True, parent_id
```
