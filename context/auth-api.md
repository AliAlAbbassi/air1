# Auth API

## POST /api/auth/login

Authenticate a user with email and password. Returns a JWT token for use with protected endpoints.

### Request

```
POST /api/auth/login
Content-Type: application/json
```

**Body:**

| Field      | Type   | Required | Description          |
|------------|--------|----------|----------------------|
| `email`    | string | Yes      | User's email address |
| `password` | string | Yes      | User's password      |

### Response

**Success (200 OK):**

```json
{
  "authToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "userId": "123",
  "email": "user@example.com"
}
```

**Error (401 Unauthorized):**

```json
{
  "error": "UNAUTHORIZED",
  "message": "Invalid email or password"
}
```

**Error (422 Validation Error):**

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid request body",
  "details": [
    { "field": "body.email", "message": "value is not a valid email address" }
  ]
}
```

---

## Usage

### Store the token

After successful login, store `authToken` and include it in the `Authorization` header for all protected API calls:

```
Authorization: Bearer <authToken>
```

### Token expiry

Tokens expire after **7 days** (168 hours). After expiry, the user must log in again.

---

## Testing with curl

### Successful login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "yourpassword"}'
```

### Invalid credentials

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "wrongpassword"}'
```

### Missing fields

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

### Invalid email format

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "not-an-email", "password": "test123"}'
```

### Using the token

Once you have the token, use it to access protected endpoints like `/api/account`:

```bash
# First, login and save the token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "yourpassword"}' \
  | jq -r '.authToken')

# Then use the token for authenticated requests
curl http://localhost:8000/api/account \
  -H "Authorization: Bearer $TOKEN"
```

---

## Frontend Integration Example

```typescript
async function login(email: string, password: string) {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message);
  }

  const { authToken, userId, email: userEmail } = await response.json();
  
  // Store token (e.g., in localStorage or secure cookie)
  localStorage.setItem('authToken', authToken);
  
  return { userId, email: userEmail };
}

// Using the token for authenticated requests
async function fetchAccount() {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch('/api/account', {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (response.status === 401) {
    // Token expired or invalid - redirect to login
    localStorage.removeItem('authToken');
    window.location.href = '/login';
    return;
  }

  return response.json();
}
```

