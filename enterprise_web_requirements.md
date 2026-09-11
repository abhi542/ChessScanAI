# ChessLensAI Enterprise Web Platform Requirements

## 1. Executive Summary
This document outlines the detailed requirements for building the standalone web platform for the ChessLensAI Enterprise Model (Coach View). The web platform will consume the REST APIs provided by the ChessLensAI backend. The primary audience for this platform is Chess Coaches and Academy Administrators.

## 2. Core Entities & Relationships
- **User (`player`)**: Can belong to exactly ONE Academy (or none). Can be assigned ONE Coach.
- **User (`coach`)**: A coach can have many students.
- **User (`admin`)**: Owns and manages the Academy, billing, and invites.
- **Academy**: Has one `admin`, multiple `coaches`, and multiple `players` (students).

## 3. Web UI Architecture & Navigation

### 3.1. Authentication
- Must use Google OAuth 2.0 (matching the mobile app).
- Upon successful login, the web frontend calls the backend to check the user's `roles`.
- If the user is an `admin` or `coach`, they are routed to the Academy Dashboard.
- If the user is only a `player`, they are routed to a "My Progress" dashboard or prompted to join an academy.

### 3.2. Academy Admin Dashboard
- **Overview**: High-level metrics (Total Students, Total Games Scanned this month).
- **Roster Management**:
  - Invite new coaches or students via email.
  - View pending invites.
  - Remove users from the academy.
- **Billing**: Manage enterprise tier limits.

### 3.3. Coach Dashboard (The "Deep Insights" View)
- **Student Roster**: A table listing all assigned students, their current Lichess/Chess.com rating (if linked), and last active date.
- **Student Drill-Down (Coach View)**: Clicking a student opens their Deep Insights dashboard.

## 4. The "Deep Insights" Student Dashboard

This is the flagship feature of the web platform. It must be visually stunning (dark mode, glassmorphism, dynamic charts).

### 4.1. Accuracy by Phase
- **Data**: Provided by backend as percentages for Opening, Middlegame, and Endgame.
- **UI Element**: Three horizontal progress bars or semi-circle gauges. Green for >80%, Yellow for 60-80%, Red for <60%.

### 4.2. Problematic Pieces
- **Data**: Backend determines which pieces are most frequently lost or blundered based on Stockfish centipawn evaluations.
- **UI Element**: A grid showing the 6 piece types (King, Queen, Rook, Bishop, Knight, Pawn). Highlights the pieces causing the most trouble with error counts.

### 4.3. Mistakes by Category (Tactical Motifs)
- **Data**: Using math and engine analysis, the backend classifies mistakes into the 38 Tactical Motifs (e.g., Hanging Piece, Missed Mate, Fork).
- **UI Element**: A horizontal bar chart ranking the top 3-5 mistake categories.
- **Interactivity**: Clicking a mistake category (e.g., "Pin") should open a modal with 10 recommended puzzles targeting that specific motif.

### 4.4. Error Heatmap
- **Data**: Backend provides the most frequently blundered squares (e.g., `d4`, `f7`).
- **UI Element**: A 2D Chessboard rendering with heatmap overlays on the problematic squares.

### 4.5. Playing Style Profile
- **Data**: Calculated dynamically after the first 10 games, and updated strictly every 15 games thereafter (25, 40, etc.). It classifies the user (e.g., "Aggressive / Tactical").
- **UI Element**: A stylish text block summarizing their style, strengths, and weaknesses.

### 4.6. Progress Tracking / Report Card
- **Data**: Timeframe-based comparison (e.g., Last 30 days vs Previous 30 days).
- **UI Element**: A line chart showing Average Centipawn Loss (ACPL) or Accuracy over time.

## 5. API Integration Requirements (Backend Contract)

The web team will need to consume the following endpoints (to be built on the Python backend):

### Authentication & Context
- `GET /api/users/me` -> Returns `roles`, `academy_id`, `coach_id`.

### Academy Management
- `POST /api/enterprise/academy` -> Create academy.
- `POST /api/enterprise/academy/{academy_id}/invite` -> Send email invite.
- `GET /api/enterprise/academy/{academy_id}/members` -> List roster.
- `POST /api/enterprise/user/{user_id}/assign_coach` -> Link student to coach.

### Dashboard Data
- `GET /api/coach/students` -> Returns list of students for the logged-in coach.
- `GET /api/coach/students/{student_id}/dashboard?timeframe=all`
  - **Payload includes**: `accuracy`, `problematic_pieces`, `mistakes_by_category`, `top_blundered_squares`, `playing_style`.

## 6. Technical & Aesthetic Guidelines
1. **Framework**: React (Next.js) or Vue (Nuxt) recommended for fast, SEO-friendly rendering.
2. **Styling**: TailwindCSS or Vanilla CSS with heavy emphasis on modern design (gradients, subtle shadows, animations).
3. **Charts**: Chart.js or Recharts for data visualization.
4. **Chessboard**: `react-chessboard` or custom SVG rendering for the heatmap.
5. **Responsiveness**: Must work flawlessly on Desktop (primary for coaches) and Tablets.

## 7. Next Steps for Web Team
1. Review this document and the `static/coach_dashboard.html` mockup.
2. Setup the frontend repository.
3. Integrate Google OAuth.
4. Begin building UI components with mock data while backend APIs are being developed.
