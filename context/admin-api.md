# Admin API

## Overview

API endpoints for agency administration. These endpoints require the authenticated user to have an `admin` or `owner` role.

All endpoints require a valid Clerk JWT token in the Authorization header:
```
Authorization: Bearer <clerk_token>
```

---

## Agency Team Management

### GET /api/admin/team

Returns all team members in the agency.

#### Success Response

**Status: 200 OK**

```json
{
  "members": [
    {
      "id": "string",
      "name": "string",
      "email": "string",
      "role": "owner | admin | manager",
      "status": "active | pending",
      "avatarUrl": "string | null",
      "invitedAt": "ISO8601 timestamp",
      "joinedAt": "ISO8601 timestamp | null"
    }
  ],
  "totalSeats": "number",
  "usedSeats": "number"
}
```

#### Example Response

```json
{
  "members": [
    {
      "id": "mem_abc123",
      "name": "Agency Owner",
      "email": "owner@agency.com",
      "role": "owner",
      "status": "active",
      "avatarUrl": null,
      "invitedAt": "2024-01-01T00:00:00Z",
      "joinedAt": "2024-01-01T00:00:00Z"
    },
    {
      "id": "mem_def456",
      "name": "Pending User",
      "email": "pending@agency.com",
      "role": "manager",
      "status": "pending",
      "avatarUrl": null,
      "invitedAt": "2024-06-15T10:30:00Z",
      "joinedAt": null
    }
  ],
  "totalSeats": 10,
  "usedSeats": 2
}
```

---

### POST /api/admin/team/invite

Invite a new team member to the agency.

#### Request Body

```json
{
  "email": "string",
  "role": "admin | manager"
}
```

#### Success Response

**Status: 201 Created**

```json
{
  "id": "string",
  "email": "string",
  "role": "string",
  "status": "pending",
  "invitedAt": "ISO8601 timestamp"
}
```

#### Error Responses

**Status: 400 Bad Request**
```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid email address"
}
```

**Status: 409 Conflict**
```json
{
  "error": "ALREADY_INVITED",
  "message": "This email has already been invited"
}
```

**Status: 402 Payment Required**
```json
{
  "error": "SEAT_LIMIT_REACHED",
  "message": "No available seats. Please upgrade your plan."
}
```

---

### DELETE /api/admin/team/:memberId

Remove a team member from the agency.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `memberId` | string | The ID of the member to remove |

#### Success Response

**Status: 200 OK**

```json
{
  "success": true,
  "message": "Team member removed"
}
```

#### Error Responses

**Status: 403 Forbidden**
```json
{
  "error": "CANNOT_REMOVE_OWNER",
  "message": "Cannot remove the agency owner"
}
```

**Status: 404 Not Found**
```json
{
  "error": "MEMBER_NOT_FOUND",
  "message": "Team member not found"
}
```

---

### POST /api/admin/team/:memberId/resend-invite

Resend invitation email to a pending team member.

#### Success Response

**Status: 200 OK**

```json
{
  "success": true,
  "message": "Invitation resent"
}
```

---

### PATCH /api/admin/team/:memberId/role

Update a team member's role.

#### Request Body

```json
{
  "role": "admin | manager"
}
```

#### Success Response

**Status: 200 OK**

```json
{
  "id": "string",
  "role": "string",
  "updatedAt": "ISO8601 timestamp"
}
```

---

## Client Accounts Management

### GET /api/admin/clients

Returns all client accounts managed by the agency.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status: `active`, `onboarding`, `all` (default: `all`) |
| `search` | string | Search by client name or email |

#### Success Response

**Status: 200 OK**

```json
{
  "clients": [
    {
      "id": "string",
      "name": "string",
      "adminEmail": "string",
      "status": "active | onboarding",
      "linkedinConnected": "boolean",
      "plan": "starter | pro | enterprise",
      "lastActive": "ISO8601 timestamp",
      "createdAt": "ISO8601 timestamp"
    }
  ],
  "total": "number"
}
```

#### Example Response

```json
{
  "clients": [
    {
      "id": "cli_abc123",
      "name": "Acme Corp",
      "adminEmail": "jim@acme.com",
      "status": "active",
      "linkedinConnected": true,
      "plan": "pro",
      "lastActive": "2024-06-20T14:30:00Z",
      "createdAt": "2024-03-15T09:00:00Z"
    }
  ],
  "total": 1
}
```

---

### POST /api/admin/clients

Create a new client account under the agency.

#### Request Body

```json
{
  "name": "string",
  "adminEmail": "string",
  "plan": "starter | pro | enterprise"
}
```

#### Success Response

**Status: 201 Created**

```json
{
  "id": "string",
  "name": "string",
  "adminEmail": "string",
  "status": "onboarding",
  "linkedinConnected": false,
  "plan": "string",
  "createdAt": "ISO8601 timestamp",
  "inviteLink": "string"
}
```

The `inviteLink` is a one-time link to send to the client admin to set up their account.

---

### GET /api/admin/clients/:clientId

Get detailed information about a specific client.

#### Success Response

**Status: 200 OK**

```json
{
  "id": "string",
  "name": "string",
  "adminEmail": "string",
  "status": "active | onboarding",
  "linkedinConnected": "boolean",
  "linkedinProfileUrl": "string | null",
  "plan": "starter | pro | enterprise",
  "lastActive": "ISO8601 timestamp",
  "createdAt": "ISO8601 timestamp",
  "stats": {
    "totalCampaigns": "number",
    "totalProspects": "number",
    "meetingsBooked": "number"
  },
  "team": [
    {
      "id": "string",
      "name": "string",
      "email": "string",
      "role": "string"
    }
  ]
}
```

---

### PATCH /api/admin/clients/:clientId

Update client account settings.

#### Request Body

```json
{
  "name": "string",
  "plan": "starter | pro | enterprise"
}
```

#### Success Response

**Status: 200 OK**

Returns the updated client object.

---

### DELETE /api/admin/clients/:clientId

Remove a client account from the agency.

#### Success Response

**Status: 200 OK**

```json
{
  "success": true,
  "message": "Client account removed"
}
```

---

### POST /api/admin/clients/:clientId/impersonate

Generate a temporary token to log in as the client (for support purposes).

#### Success Response

**Status: 200 OK**

```json
{
  "impersonationUrl": "string",
  "expiresAt": "ISO8601 timestamp"
}
```

The `impersonationUrl` is a one-time link that logs the agency admin into the client's workspace.

---

## Authorization

All admin endpoints check:

1. **Authentication**: Valid Clerk JWT token
2. **Authorization**: User must have `owner` or `admin` role in the agency

Example authorization check (backend pseudocode):

```typescript
// Verify Clerk token and get userId
const { userId } = await auth()

// Look up user's agency membership
const membership = await db.agencyMembers.findFirst({
  where: { userId, agencyId }
})

// Check role
if (!membership || !['owner', 'admin'].includes(membership.role)) {
  return Response.json({ error: 'FORBIDDEN' }, { status: 403 })
}
```

---

## Error Responses

All endpoints may return these common errors:

**Status: 401 Unauthorized**
```json
{
  "error": "UNAUTHORIZED",
  "message": "Authentication required"
}
```

**Status: 403 Forbidden**
```json
{
  "error": "FORBIDDEN",
  "message": "You don't have permission to access this resource"
}
```

**Status: 500 Internal Server Error**
```json
{
  "error": "INTERNAL_ERROR",
  "message": "An unexpected error occurred"
}
```

