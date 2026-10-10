# PRD – AgeinsShield

## Original problem
Website with chatbot assistant embeddable via JS snippet on any site; chatbot checks fraud & gives 1-100 security meter; own site has alarm system for fraud sites, AI-content check, phishing-email detection. Similar to phishing-shield-40 reference. User wanted HTML/CSS/JS + Python + MySQL; agreed to React + FastAPI + MongoDB.

## User choices
Rule-based logic (no AI), JWT email/password auth, React + FastAPI + MongoDB.

## Implemented (2026-06)
- JWT auth (register/login/logout/me, bcrypt, brute-force lockout, admin seed)
- URL fraud scanner: 15+ rules, gauge 1-100, flashing alarm + Web Audio siren, presets
- AI content detector: burstiness, vocab, AI phrases, contractions, sentence heatmap
- Phishing email detector: sender spoofing, Reply-To mismatch, urgency, credentials, money bait, link scan
- Scan history (filter/search/delete), overview stats
- In-app chatbot + embeddable vanilla JS widget (/api/widget.js) with auto page scoring + alarm bar; embed page with copy + live iframe preview
- README with localhost/VS Code setup
- Tests: 21/21 backend, all frontend flows pass

## Iteration 2 (2026-06)
- Domain age via RDAP in URL scoring (unregistered / <30d / <180d / <1y penalties)
- PDF reports (reportlab) per scan, buttons on results + history
- Chrome MV3 extension (/app/extension), served as /api/extension.zip with API base injected; badge, alarm bar, siren, notification, popup settings
- MySQL backend (/app/backend_mysql, SQLAlchemy+PyMySQL), verified on MariaDB
- Tests: 36/36 backend, all frontend flows pass

## Backlog
- P1: Live threat-intel lookups (Google Safe Browsing / domain age WHOIS)
- P2: PDF export of scan reports
