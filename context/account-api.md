# Account API

## Overview

API endpoint to fetch and update the current user's account data. Used by the dashboard ("Welcome Ali" greeting, LinkedIn status badges) and settings pages (profile tab).

---

## Endpoints

### GET /api/account

Returns the authenticated user's account data.

#### Success Response

**Status: 200 OK**

```json
{
  "user": {
    "id": "string",
    "email": "string",
    "firstName": "string",
    "lastName": "string",
    "avatarUrl": "string | null",
    "timezone": "string",
    "meetingLink": "string"
  },
  "linkedin": {
    "connected": "boolean",
    "profileUrl": "string | null",
    "dailyLimits": {
      "connections": "number",
      "inmails": "number"
    }
  },
  "company": {
    "id": "string",
    "name": "string",
    "logo": "string | null",
    "plan": "free | pro | enterprise"
  }
}
```

#### Example Response

```json
{
  "user": {
    "id": "usr_abc123",
    "email": "ali@hodhod.ai",
    "firstName": "Ali",
    "lastName": "Abbassi",
    "avatarUrl": "/profile.jpeg",
    "timezone": "EST",
    "meetingLink": "https://cal.com/ali/30min"
  },
  "linkedin": {
    "connected": true,
    "profileUrl": "https://linkedin.com/in/ali-hassan",
    "dailyLimits": {
      "connections": 25,
      "inmails": 40
    }
  },
  "company": {
    "id": "org_xyz789",
    "name": "HODHOD",
    "logo": null,
    "plan": "pro"
  }
}
```

#### Error Responses

**Status: 401 Unauthorized**

```json
{
  "error": "UNAUTHORIZED",
  "message": "Authentication required"
}
```

---

### PATCH /api/account

Updates the authenticated user's profile settings. Supports partial updates.

#### Request Body

All fields are optional. Only include fields you want to update.

```json
{
  "firstName": "string",
  "lastName": "string",
  "timezone": "string",
  "meetingLink": "string"
}
```

#### Field Details

| Field | Type | Description |
|-------|------|-------------|
| `firstName` | string | User's first name |
| `lastName` | string | User's last name |
| `timezone` | string | Timezone code (e.g., `EST`, `PST`, `GMT`) |
| `meetingLink` | string | Calendar booking URL |

#### Success Response

**Status: 200 OK**

Returns the updated account object (same shape as GET response).

#### Error Responses

**Status: 400 Bad Request**

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid request body",
  "details": [
    { "field": "meetingLink", "message": "Invalid URL format" }
  ]
}
```

**Status: 401 Unauthorized**

```json
{
  "error": "UNAUTHORIZED",
  "message": "Authentication required"
}
```

---

## Authentication

All endpoints require a valid JWT token in the Authorization header:

```
Authorization: Bearer <token>
```

---

## Usage Examples

### Dashboard Header

```tsx
const { data: account } = useAccount();

<h1>Welcome {account.user.firstName}</h1>
```

### LinkedIn Status Badges

```tsx
<Badge>{account.linkedin.connected ? "LinkedIn Connected" : "Connect LinkedIn"}</Badge>
<Badge>{account.linkedin.dailyLimits.connections}/day</Badge>
<Badge>{account.linkedin.dailyLimits.inmails}/day</Badge>
```

### Settings Profile Tab

```tsx
const { data: account, mutate } = useAccount();

<Input value={`${account.user.firstName} ${account.user.lastName}`} />
<Select value={account.user.timezone} />
<Input value={account.user.meetingLink} />
```

### Sidebar Team Switcher

```tsx
<TeamSwitcher 
  name={account.company.name} 
  plan={account.company.plan} 
/>
```

---

## Example Requests

### Fetch Account

```bash
curl -X GET https://api.hodhod.ai/api/account \
  -H "Authorization: Bearer <token>"
```

### Update Profile

```bash
curl -X PATCH https://api.hodhod.ai/api/account \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "Ali",
    "lastName": "Hassan",
    "timezone": "PST"
  }'
```
