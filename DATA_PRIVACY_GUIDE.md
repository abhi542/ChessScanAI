# ChessLensAI - Data Collection & Privacy Guide

This document outlines exactly what data is collected, stored, and processed by the ChessLensAI backend. You can use this information to draft your official **Privacy Policy** and **Terms of Service**.

---

## 1. Personal Identifiable Information (PII)
We collect minimal personal data, strictly for authentication and user profile management.

*   **Google Auth Data:** When a user signs in with Google, we collect and store:
    *   **Email Address:** Used as the primary unique identifier.
    *   **Full Name:** Displayed in the app UI.
    *   **Profile Picture URL:** Displayed in the app UI.
*   **What we DO NOT collect:**
    *   We **do not** collect or store passwords (Google handles authentication via OAuth2).
    *   We **do not** collect phone numbers or physical addresses.

## 2. User Generated Content & Chess Data
This is the core data required for the app to function.

*   **Scanned Game Data:** When a user decides to save a game to their profile, they manually enter, review, or edit the following data before it is saved:
    *   **Metadata:** Player names (White/Black), Event Name, Date, Site, Round, and Game Result.
    *   **Chess Moves (PGN/FEN):** The exact sequence of moves played in the game and their corresponding board states (FEN strings).
    *   **Validation Status:** Whether the moves were legal or contained OCR errors.
*   **AI Analysis & Reviews:** 
    *   We store the Stockfish engine evaluations (blunders, accuracy, eval graphs).
    *   We store the LLM-generated coaching summaries (text paragraphs).

## 3. Uploaded Images (Camera/Gallery)
*   **Temporary Processing:** When a user uploads a photo of a chess scoresheet, it is temporarily saved on the server for a few seconds to process the OCR.
*   **Immediate Deletion:** Once the AI finishes extracting the text, the image file is **immediately and permanently deleted** from the server's hard drive.
*   **Privacy Stance:** We **do not** store, keep, or train models on user-uploaded photos.

## 4. Usage Metrics & Telemetry
To prevent abuse and manage API costs, we track how much users use the AI features.

*   **Quota Tracking:** We store numerical counts of:
    *   How many images a user has scanned (`ocr_count`).
    *   How many full game analyses they have requested (`analysis_count`).
    *   How many LLM coaching summaries they have generated (`review_count`).
*   **Timestamps:** We track account creation dates (`created_at`), last login/update times (`updated_at`), and the exact time the user accepted the Terms and Conditions (`terms_accepted_at`).

## 5. Third-Party Data Sharing
You should mention in your privacy policy that data is sent to third-party providers for processing:
*   **AI/LLM Providers:** The raw text of chess moves and game metadata is sent to third-party AI APIs to generate OCR results and coaching summaries. (Note: No personal user data like email, name, or profile picture is sent to these AI providers; they only see the chess data).
*   **Cloud Database Provider:** The database provider where your data is securely hosted (e.g., MongoDB Atlas).

---

### Suggested Clauses for your Terms & Conditions
1. **Acceptable Use:** Users agree to use the camera/upload feature strictly for scanning chess scoresheets. Uploading inappropriate or illegal imagery is forbidden (and our backend automatically rejects non-chess imagery).
2. **Account Limits & Subscriptions:** Free tier usage is subject to rate limits (scans/reviews per day) which may change at the developer's discretion. Premium plans (if applicable) are billed according to specific terms.
3. **Data Ownership:** Users retain ownership of their recorded chess games, but grant ChessLensAI a non-exclusive license to store, process, and display them to provide the service.
4. **Age Restrictions (COPPA/GDPR):** The service is intended for users who are at least 13 years old (or older, depending on local jurisdiction). We do not knowingly collect PII from children without parental consent.
5. **No Warranty & Limitation of Liability:** The app (including AI analysis) is provided "AS IS". We do not guarantee 100% accuracy of OCR extraction or AI coaching. We are not liable for any lost data (e.g., if a saved game is accidentally deleted).
6. **Account Termination:** We reserve the right to suspend or terminate accounts that abuse the API limits, attempt to hack the backend, or upload prohibited content.
7. **Modifications to Terms:** We reserve the right to update these terms. Continued use of the app after updates implies acceptance of the new terms.

---

## 6. Security & Device Processing 
Useful technical details to reassure users in your Privacy Policy:

*   **Encryption in Transit:** All data sent between the mobile app/website and our servers is encrypted using standard HTTPS/TLS protocols.
*   **Local Storage & Cookies:** The web application uses `localStorage` to securely store JWT authentication tokens. We do not use third-party tracking or advertising cookies.
*   **Local Device Processing (Mobile App):** For certain features (like in-depth chess analysis), the mobile app utilizes the device's own processor (Local Stockfish) rather than sending board positions to our servers. This enhances privacy and reduces data transmission.
*   **Data Deletion Rights:** Users have the right to request the deletion of their account and all associated games. (Note: You may need to implement a "Delete Account" button or provide a contact email for these requests).
