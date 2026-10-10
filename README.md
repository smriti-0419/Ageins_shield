# AgeinsShield – Fraud & Phishing Defense Console

Rule-based security console with: website security meter (1-100) + fraud alarm, AI-content detector, phishing-email detector, scan history, JWT login, and an embeddable chatbot (`<script>` tag) for any website.

## Folder structure
```
backend/
  server.py      FastAPI app: auth (JWT+bcrypt), scan APIs, chat API, history, serves widget.js
  analyzers.py   Rule engines: analyze_url, analyze_ai_text, analyze_email, chatbot_reply
  widget.js      Pure HTML/CSS/JS embeddable chatbot (served at /api/widget.js)
  .env           MONGO_URL, DB_NAME, JWT_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD, PUBLIC_API_URL
frontend/src/
  App.js                 Routes + protected console
  lib/api.js             Axios client (Bearer token), helpers
  context/AuthContext.js Login/register/logout state
  components/            Gauge (1-100 meter), AlarmBanner (flash + siren), ChatWidget, FlagList, Layout
  pages/                 Landing, AuthPage, Overview, UrlScanner, AiDetector, EmailDetector, History, Embed
```

## API
| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | /api/auth/register, /api/auth/login | - | returns {user, token} |
| GET | /api/auth/me | Bearer | current user |
| POST | /api/scan/url | optional | security score 1-100 + flags |
| POST | /api/scan/ai | optional | AI likelihood % |
| POST | /api/scan/email | optional | phishing risk + red flags |
| POST | /api/chat | public | chatbot reply (used by widget) |
| GET | /api/history, /api/stats | Bearer | user scans |
| GET | /api/widget.js | public | embeddable chatbot script |

## What to install (Windows / Mac)
1. **VS Code** + extensions: Python, Pylance, ES7 React snippets, Tailwind CSS IntelliSense
2. **Python 3.11+** (python.org – tick "Add to PATH")
3. **Node.js 20 LTS** (nodejs.org), then `npm install -g yarn`
4. **MongoDB Community Server** + **MongoDB Compass** (GUI, like SSMS for Mongo). Note: SSMS is for Microsoft SQL Server, not MySQL/MongoDB.
5. Git (optional)

## Run on localhost
```bash
# 1. Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install fastapi uvicorn motor pymongo python-dotenv bcrypt pyjwt "pydantic[email]"
```
Edit `backend/.env`:
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="aegisshield"
CORS_ORIGINS="http://localhost:3000"
JWT_SECRET="any-long-random-string"
ADMIN_EMAIL="admin@ageins.com"
ADMIN_PASSWORD="<choose-a-strong-password>"
PUBLIC_API_URL="http://localhost:8001"
```
```bash
uvicorn server:app --reload --port 8001
```
```bash
# 2. Frontend (new terminal)
cd frontend
yarn install
```
`frontend/.env`: `REACT_APP_BACKEND_URL=http://localhost:8001`
```bash
yarn start      # opens http://localhost:3000
```

## New features
- **Domain age check**: every URL scan looks up the domain's registration date (free RDAP service, needs internet). Brand-new or unregistered domains lose points.
- **PDF reports**: a Download PDF button on every result and history row (`GET /api/history/{id}/pdf`).
- **Deepfake scanner**: upload photos (up to 10 MB) or videos (up to 50 MB) from Console -> Deepfake Scanner. The backend scores images and sampled video frames; its first scan downloads the model (about 350 MB). Install the CPU model dependencies with `backend\\venv\\Scripts\\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu` and `backend\\venv\\Scripts\\python.exe -m pip install transformers opencv-python-headless==4.10.0.84`. Results are estimates, not proof; audio is not analyzed.
- **Admin user activity**: sign in with the account configured by `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `backend/.env`, then open Console -> User Activity to review registered accounts, scan totals, flagged threats, and each user's recent scan history. Admin API access is restricted to accounts with the `admin` role.
- **Chrome extension** (`/extension` folder, or download it from Console -> Extension): open chrome://extensions, turn on Developer mode, click Load unpacked, and pick the folder. Every site gets a 1-100 badge, and fraud sites trigger a red alarm bar, a siren and a desktop notification. Set the API URL (http://localhost:8001) in the popup Settings.
- **MySQL version**: `/backend_mysql` has the same API on MySQL. See `backend_mysql/README.md`. Run that instead of `/backend` if you want MySQL.

## Embed the chatbot on any website
```html
<script src="http://localhost:8001/api/widget.js" defer></script>
```
Place before `</body>`. It shows a floating shield chat, auto-scores the page 1-100 and shows a red alarm bar if the page looks fraudulent.
