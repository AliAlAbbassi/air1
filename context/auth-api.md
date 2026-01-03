# Auth API (Clerk Integration)

Authentication is handled by [Clerk](https://clerk.com). The backend verifies Clerk session tokens on protected endpoints.

## Setup

### Environment Variables

```bash
# .env
CLERK_SECRET_KEY=sk_test_xxxxx  # From Clerk Dashboard → API Keys
```

### Frontend

The frontend uses `@clerk/nextjs` to handle sign-in/sign-up. See [Clerk Next.js docs](https://clerk.com/docs/quickstarts/nextjs).

---

## How Authentication Works

1. User signs in via Clerk on the frontend
2. Clerk creates a session and provides a token
3. Frontend includes token in API requests: `Authorization: Bearer <token>`
4. Backend verifies the token with Clerk's SDK
5. If valid, the request proceeds; if not, returns 401

---

## Protected Endpoints

All endpoints under `/api/*` (except health checks) require authentication.

### Request Format

Include the Clerk session token in the Authorization header:

```
GET /api/account
Authorization: Bearer <clerk_session_token>
```

### Error Response (401 Unauthorized)

```json
{
  "error": "UNAUTHORIZED",
  "message": "Authentication required"
}
```

---

## Testing with curl

### Get a session token

In your frontend, you can get the token using Clerk's `useAuth` hook:

```typescript
const { getToken } = useAuth();
const token = await getToken();
```

### Test authenticated endpoint

```bash
# Replace <TOKEN> with the session token from your frontend
curl http://localhost:8000/api/account \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Frontend Integration

### Getting the token for API calls

```typescript
import { useAuth } from '@clerk/nextjs';

function MyComponent() {
  const { getToken } = useAuth();

  async function fetchAccount() {
    const token = await getToken();
    
    const response = await fetch('/api/account', {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    return response.json();
  }
}
```

### Using with fetch wrapper

```typescript
// lib/api.ts
import { auth } from '@clerk/nextjs';

export async function apiClient(endpoint: string, options: RequestInit = {}) {
  const { getToken } = auth();
  const token = await getToken();

  return fetch(`${process.env.NEXT_PUBLIC_API_URL}${endpoint}`, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });
}
```

---

## User ID Mapping

Clerk uses string IDs (e.g., `user_2NNEqL2nrIRdJ194ndJqAHwEfxC`). 

The `AuthUser` object returned by `get_current_user` contains:
- `user_id`: Clerk user ID (string)
- `email`: User's email (optional)

If your database uses integer user IDs, you'll need to map Clerk IDs to internal IDs. See the user provisioning section in the codebase.
