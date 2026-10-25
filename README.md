# Smart AI Surveillance for Lost Person Detection in Crowds

Project ID 2023CSEPID15 - ABES Institute of Technology

```
 Browser (React, :5173)
    |   login, register person, dashboard                 live video (MJPEG)
    v                                                          ^
 Flask backend (:5000) ---- start/stop camera, photo ---> AI service (:5001)
    |   users, persons, alerts, CSV export                  YOLOv8 -> ArcFace -> match
    |                                                          |  reads the 4 cameras
    +------------------- PostgreSQL + pgvector <---------------+
                         persons.embedding vector(512)
```

| Folder | What it is |
|---|---|
| `frontend/` | React + Vite + Tailwind. Landing page, role-based login, Operator and Reporter dashboards |
| `backend/` | Flask REST API: login (JWT), persons, alerts, cameras, audit-log CSV |
| `ai_service/` | The AI: reads the 4 cameras, YOLOv8 finds people, ArcFace reads faces, pgvector finds the match |
| `docker-compose.yml` | Starts the database only |

## Database: PostgreSQL + pgvector (instead of SQLite)

SQLite locks the whole file on every write, so 4 camera threads writing alerts would block each other,
and it cannot search by vector similarity. PostgreSQL handles concurrent writes, and the `pgvector`
extension stores each face as a `vector(512)` column and finds the nearest face in SQL
(`ORDER BY embedding <=> query`). That replaces **both** SQLite and the separate FAISS index, so there is
no index file to keep in sync. Tables: `users`, `persons` (with the face vector), `cameras`, `alerts` (= audit log).

## Setup (about 20 minutes, most of it downloads)

You need: Python 3.10 - 3.12, Node.js 18+, Docker Desktop.

**1. Database**
```
docker compose up -d
```

**2. Backend** (new terminal)
```
cd backend
python -m venv venv
venv\Scripts\activate              (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env             (Mac/Linux: cp .env.example .env)
python init_db.py                  creates tables, the 4 cameras and 2 demo accounts
python run.py
```

**3. AI service** (new terminal)
```
cd ai_service
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt    large download (PyTorch) - be patient
copy .env.example .env
python app.py
```
The first start downloads the YOLOv8 and ArcFace model files (about 300 MB), so it is slow once.
`INTERNAL_API_KEY` and `JWT_SECRET_KEY` in `ai_service/.env` **must be identical** to `backend/.env`.

**4. Frontend** (new terminal)
```
cd frontend
npm install
copy .env.example .env
npm run dev
```
Open http://localhost:5173

Demo accounts (created by `init_db.py`, password `password123`): `operator@demo.com`, `reporter@demo.com`.
New operators need the access code in `backend/.env` (`OPERATOR_SIGNUP_CODE`); reporters can sign up freely.

## Using the 4 cameras

Your team has 4 members, so the database has exactly 4 cameras: CAM-01 to CAM-04. Each camera has a
**source**. Open **Camera Feeds -> the gear icon** on a camera, type the source, press Save, then Start.

| Source | What to type | Good for |
|---|---|---|
| Laptop webcam | `0` (a second USB webcam is `1`) | CAM-01 |
| Phone as a camera | `http://PHONE-IP:8080/video` | CAM-02, 03, 04 |
| Video file | `videos/cam3.mp4` | demos without cameras |
| IP / CCTV camera | `rtsp://user:password@192.168.1.20:554/stream1` | real CCTV |

**Phone as a camera (Android):** install the free app **IP Webcam**, put the phone on the same Wi-Fi
as the computer running the AI service, tap *Start server*, and use the address it shows, e.g.
`http://192.168.1.7:8080/video`. Open that address in the computer's browser first to check it works.
Any app that serves an MJPEG or RTSP stream works the same way.

**Important:** the AI service opens the cameras, so it must run on the computer the webcams are plugged
into and on the same network as the phones. The browser can be on any computer that can reach it
(set `VITE_AI_SERVICE_URL` in `frontend/.env` to that computer's address).

**No cameras yet?** Make a fake camera from any photo with several faces:
```
cd ai_service
python tools/make_demo_video.py my_group_photo.jpg videos/cam3.mp4 --seconds 20
```

## Trying it end to end
1. Log in as **reporter**, *Register Person*, upload a clear front-facing photo -> *Submit report*.
   The backend sends the photo to the AI service, which stores the face vector in PostgreSQL.
   If no face is found you get a clear error instead.
2. Log out, log in as **operator**, *Camera Feeds*, press **Start** on a camera.
3. When that person walks in front of the camera you get a green box in the live video, an entry under
   *Live Alerts* with a snapshot, and the reporter's report changes to *Spotted*.
4. *Track Person* shows which cameras saw them in order. *Audit Log* has the *Export CSV* button.

## How matching works
`frame -> YOLOv8 finds people -> crop each person -> ArcFace makes a 512-number face vector ->
PostgreSQL returns the closest registered face -> if similarity >= MATCH_THRESHOLD, raise an alert`.
The same person is not alerted again on the same camera for 15 seconds (`ALERT_COOLDOWN_SECONDS`).

**About the 0.85 in the presentation:** ArcFace similarity is a cosine score. Different people score
close to 0 and the same person usually 0.4 to 0.7 when photos differ in light and angle. A threshold of
0.85 would miss almost everyone, so the default is **0.5** (`MATCH_THRESHOLD`, set it in both `.env`
files). Please change the slide too. Raise it if you see wrong matches, lower it if real matches are missed.

## What was tested, and what was not
Tested on Linux with Python 3.13, PostgreSQL 16 and pgvector 0.6:
- all API routes, role checks (a reporter cannot see operator data or another reporter's reports), photo
  with no face rejected, operator signup code, CSV export
- registering a person from a cropped face photo, then a camera playing a video of the original group
  photo: only that person matched (similarity 0.98), the other 5 faces scored 0.14 or less
- cooldown (alerts exactly 15 s apart), unreachable camera retries instead of crashing, stream rejects
  missing or reporter tokens
- the React app in a real browser (Chromium): login errors, live stream, start/stop, CSV download,
  no-face error, reporter and operator screens

**Not tested:** real webcams, phones, RTSP/CCTV cameras (the sandbox has none; they use the same
OpenCV code path as the video file), Windows or macOS, Docker, GPU, and matching two *different*
photos of one person. The 0.98 above is optimistic because the reference was cut from the same photo
as the video. Test with your own team's photos and tune `MATCH_THRESHOLD`.

## Speed
Measured on a 2-core CPU: about **2 seconds per frame** with 6 people in view. The live video stays smooth
(it is read separately), but AI checks happen less often. All 4 cameras share one AI model, so on a CPU
each camera is checked every few seconds. To go faster: lower `MAX_PEOPLE_PER_FRAME` and
`MAX_FRAME_WIDTH`, raise `PROCESS_INTERVAL` in `ai_service/.env`, or use an NVIDIA GPU (install
`onnxruntime-gpu` and a CUDA build of PyTorch; the code uses the GPU automatically when available).

## Not built (in the presentation but not in this code)
- **Attribute extractor** (clothes, height, movement) and body-appearance re-identification. Tracking
  across cameras here is face-based: the same registered person seen on different cameras forms a timeline.
- **Match for people whose face is not visible** (back to camera, mask): no face means no match.
- **FAISS and SQLite**: replaced by pgvector / PostgreSQL as explained above. Update slides 4 and 5.

## Security notes (fine for a college demo, fix before real use)
Change every secret in the `.env` files. Reference photos and snapshots are served by random file names
rather than by login. Face photos are biometric data: only register people who agreed. Serve everything
over HTTPS in a real deployment (the live-stream login token is passed in the URL).

## Troubleshooting
| Problem | Fix |
|---|---|
| `pip install insightface` fails on Windows | Install "Microsoft C++ Build Tools" (Desktop development with C++), then retry |
| "The AI service is not running" when registering | Start `ai_service` (step 3) and wait for it to print the Flask address |
| Camera stuck on "Stream not available" | Press Stop then Start; check the source works (open a phone URL in the browser) |
| Camera never goes online | The status says `reconnecting`; the source is wrong or the camera is busy in another app |
| Login works but pages say "Please log in" | `JWT_SECRET_KEY` differs between backend and AI service, or the token expired |
| `extension "vector" is not available` | You are not using the Docker image above; install pgvector or use Docker |
