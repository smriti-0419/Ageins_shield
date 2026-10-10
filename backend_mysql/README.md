# AgeinsShield – MySQL backend

This backend works the same way as the MongoDB one in `/backend`, with the same API routes, but it stores data in **MySQL**. The React frontend works with either backend without any changes.

## Files
| File | Purpose |
|---|---|
| server.py | FastAPI app: JWT auth, scans, chat, history, PDF reports, widget.js, extension.zip |
| database.py | SQLAlchemy engine + `users`, `scans`, `login_attempts` tables |
| schema.sql | Same tables as plain SQL (optional – tables are auto-created at startup) |
| analyzers.py | Rule engines (URL + domain age, AI text, phishing email, chatbot) – copy of /backend |
| reports.py | PDF report + extension ZIP builders – copy of /backend |
| widget.js | Embeddable chatbot script |

## Setup (Windows)
1. Install **MySQL Server 8** and **MySQL Workbench** (https://dev.mysql.com/downloads/installer/). Remember the root password.
   *SQL Server Management Studio (SSMS) is for Microsoft SQL Server, not MySQL. Use MySQL Workbench instead.*
2. In MySQL Workbench, open and run `schema.sql`. This creates the `aegisshield` database.
3. In VS Code terminal:
```bash
cd backend_mysql
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # then put your MySQL password in DATABASE_URL
uvicorn server:app --reload --port 8001
```
4. Start the frontend (`cd frontend && yarn install && yarn start`) with `REACT_APP_BACKEND_URL=http://localhost:8001`.

Admin login: use the administrator email and password configured in the backend environment.
