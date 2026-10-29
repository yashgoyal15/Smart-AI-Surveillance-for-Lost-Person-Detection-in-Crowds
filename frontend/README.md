# Smart AI Surveillance for Lost Person Detection in Crowds — Frontend

React + Vite + Tailwind frontend for the project. This repo only contains the
UI; the actual detection pipeline (OpenCV, YOLOv8, ArcFace, FAISS) and the
database run on a separate backend.

## Getting started

```bash
npm install
cp .env.example .env
npm run dev
```

## Flow

1. **Landing page (`/`)** — public homepage with a "Sign In" button.
2. **Login page (`/login`)** — pick your role (Operator or Reporter), then
   sign in. This maps to the two human actors in the use case diagram.
3. **Dashboard (`/dashboard`)** — protected route. Shows a different
   dashboard depending on role:
   - **Operator (Security Staff):** live stats, alerts, camera feeds, audit log.
   - **Reporter (Police/Family):** register a missing person, track report status.

## Project structure

```
src/
  assets/      images, icons, static files
  components/  small reusable UI pieces (Sidebar, StatCard, AlertRow, ...)
  context/     AuthContext - who is logged in and their role
  pages/       one folder per route, operator/ and reporter/ hold their sub-views
  services/    mock API calls - swap these for real fetch() calls to the backend
```

## Swapping in the real backend

Right now `src/services/*.js` return hardcoded/mock data so the UI can be
demoed without a backend. Once the Flask/Node API is ready (using
PostgreSQL + pgvector instead of SQLite), replace the bodies of those
functions with real `fetch()` calls using `VITE_API_BASE_URL` from `.env`.
