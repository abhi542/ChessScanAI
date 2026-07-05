# ChessLensAI - Terms & Conditions (T&C) Mobile Integration Guide

This document outlines the required steps for the Flutter developer to implement the new mandatory Terms and Conditions flow.

> [!WARNING]
> **CRITICAL SECURITY UPDATE**
> The backend now enforces a strict Terms and Conditions block. If a user has not accepted the T&C via the `/api/users/accept-terms` endpoint, ALL authenticated endpoints (`/api/upload`, `/api/review`, `/api/games`, etc.) will instantly reject their requests with an `HTTP 403: TERMS_NOT_ACCEPTED` error.

---

## 1. Updated Login Flow

When the user signs in with Google, you must check if they have already accepted the Terms and Conditions.

### Step 1: Call Google Auth API
Send the Google ID Token to the backend as usual.

**`POST /api/auth/google`**
```json
{
  "token": "<GOOGLE_ID_TOKEN>"
}
```

### Step 2: Parse the Response
The backend response now includes a new `terms_accepted` boolean flag inside the `user` object.

```json
{
  "access_token": "eyJhb...",
  "refresh_token": "eyJhb...",
  "token_type": "bearer",
  "user": {
    "id": "6a22c9...",
    "email": "user@example.com",
    "name": "John Doe",
    "picture": "https://...",
    "terms_accepted": false 
  }
}
```

### Step 3: Branch the UX Flow
*   **If `terms_accepted` is `true`:** Proceed as normal. Store the tokens and navigate to the Home screen.
*   **If `terms_accepted` is `false`:** 
    *   Do **NOT** navigate to the Home screen yet.
    *   Display a full-screen Terms & Conditions modal or dedicated screen.
    *   The user must not be able to bypass this screen.

---

## 2. Accepting the Terms

When the user clicks the "I Accept" button on your T&C screen, you must notify the backend to stamp their database record.

**`POST /api/users/accept-terms`**
*   **Headers:** `Authorization: Bearer <access_token>`
*   **Body:** (Empty)

### Expected Response
```json
{
  "status": "success",
  "message": "Terms accepted"
}
```

### Next Steps After Acceptance
Once you receive the 200 OK success response from this endpoint:
1. Update your local user profile state (e.g., in your `AuthService` or secure storage) to reflect that terms have been accepted.
2. Dismiss the T&C screen.
3. Navigate the user to the Home screen.

---

## 3. Global Error Handling (403 Fallback)

As a safety net, you should update your global Dio Interceptor (or HTTP client) to listen for `HTTP 403 Forbidden` responses. 

If any API call fails with `HTTP 403` and the detail contains `"TERMS_NOT_ACCEPTED"`, you should forcefully log the user out or immediately show the T&C screen. This prevents the app from crashing if they somehow slip through the login gate.

```json
{
  "detail": "TERMS_NOT_ACCEPTED"
}
```

---

## 4. Updated MongoDB User Schema Reference

For your context, the backend database now stores the timestamp of when they clicked Accept. You do not need to parse this date directly on the mobile app (just use the boolean in the login response), but this is what the DB looks like now:

```json
{
  "_id": { "$oid": "6a22c958fa1d102437df28d6" },
  "email": "abhinavmbhatt@gmail.com",
  "name": "Abhinav Bhatt",
  "plan": "free",
  "terms_accepted_at": { "$date": "2026-07-05T11:22:11.352Z" },
  "created_at": { "$date": "2026-07-05T10:00:00.000Z" },
  "updated_at": { "$date": "2026-07-05T10:00:00.000Z" }
}
```
