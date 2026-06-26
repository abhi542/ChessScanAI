# ChessLensAI - Firebase Analytics Taxonomy

This document defines the exact Firebase Analytics events, parameters, and user properties that the Flutter developer needs to implement. This ensures clean, organized tracking of user growth, feature usage, and drop-offs.

---

## 1. User Properties
Set these globally as soon as the user logs in. This allows you to segment your data later (e.g., "Do people with a high Elo rating use the AI Coach more often?").

| Property Name | Example Values | Description |
| :--- | :--- | :--- |
| `subscription_plan` | `"free"`, `"premium"` | The user's current billing tier. |
| `auth_method` | `"google"` | How the user logged in. |

---

## 2. Authentication Flow
Track the funnel to see where users drop off before actually logging in.

| Event Name | Parameters | Description |
| :--- | :--- | :--- |
| `signup_started` | `method`: `"google"` | User clicks the "Sign in with Google" button. |
| `login_success` | `method`: `"google"` | User successfully receives JWT from the backend. |
| `login_failed` | `error_code`: `"network_error"` | Login attempt failed (network error, user cancelled, etc). |

---

## 3. Core Product Flow (Scanning & Saving)
This tracks the heart of ChessLensAI. It tells you exactly how successfully people are digitizing their physical scoresheets.

| Event Name | Parameters | Description |
| :--- | :--- | :--- |
| `scan_initiated` | `input_type`: `"camera"`, `"gallery"` | User opens the camera/gallery to pick a scoresheet. |
| `scan_completed` | `moves_detected`: `42` | The `/api/upload` endpoint successfully returns the raw moves. |
| `scan_failed` | `error`: `"timeout"` | The Groq OCR failed or timed out. |
| `manual_edit_made` | `move_number`: `15` | **Crucial:** Tracks if the user had to tap a red move to fix a typo. Helps you measure OCR accuracy! |
| `game_saved` | `total_moves`: `42`, `result`: `"1-0"` | User successfully hits `/api/games` and saves it to MongoDB. |

---

## 4. Dual-Architecture & AI Coaching
Track how much compute users are utilizing and how engaging the Groq LLM Coach actually is.

| Event Name | Parameters | Description |
| :--- | :--- | :--- |
| `local_analysis_started` | `engine_depth`: `15` | Flutter starts running local Stockfish on the phone. |
| `local_analysis_done` | `duration_seconds`: `4` | Local Stockfish finishes evaluation. |
| `ai_coach_requested`| `game_id`: `"6a22..."` | User hits `/api/review-summary` for the Groq LLM Summary. |
| `ai_coach_viewed` | `game_id`: `"6a22..."` | User successfully reads the 3-sentence summary on screen. |
| `review_shared` | `platform`: `"whatsapp"` | User clicks "Share" to send the AI summary/PGN to a friend. |

---

## 5. Monetization & Limits (For Future Growth)
Track how often users hit the 1,000/day Groq limits and if they click the upgrade button.

| Event Name | Parameters | Description |
| :--- | :--- | :--- |
| `limit_reached` | `feature`: `"ocr"`, `"review"` | User hit the daily free-tier limit in `usage_metrics`. |
| `paywall_viewed` | `entry_point`: `"coach_button"` | User sees the "Upgrade to Pro" screen. |
| `checkout_started` | `plan_id`: `"monthly_pro"` | User clicks "Subscribe". |
| `purchase_completed` | `value`: `4.99`, `currency`: `"USD"` | Successful payment. |

---

## Implementation Notes for Flutter Developer
1. **Never** track Personally Identifiable Information (PII) like email addresses or real names in Firebase Events.
2. Use the official `firebase_analytics` package.
3. Use `FirebaseAnalytics.instance.logEvent(name: 'event_name', parameters: {...})`.
4. Run the app in Firebase DebugView before shipping to production to ensure all events are firing with the correct parameters.
