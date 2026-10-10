from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import Response as RawResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from starlette.middleware.cors import CORSMiddleware

from analyzers import analyze_ai_text, analyze_email, chatbot_reply, full_url_scan, normalize_domain
from database import Base, LoginAttempt, SafeSite, Scan, SessionLocal, User, engine
from reports import build_extension_zip, build_pdf

EXTENSION_DIR = ROOT_DIR.parent / "extension"
JWT_ALGORITHM = "HS256"
app = FastAPI(title="AgeinsShield API (MySQL)")
api = APIRouter(prefix="/api")


class RegisterIn(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=6)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UrlIn(BaseModel):
    url: str = Field(min_length=1)


class TextIn(BaseModel):
    text: str = Field(min_length=1)


class EmailIn(BaseModel):
    content: str = Field(min_length=1)
    sender: str = ""


class ChatIn(BaseModel):
    message: str = Field(min_length=1)
    page_url: str = ""


class SafeSiteIn(BaseModel):
    domain: str = Field(min_length=3, max_length=255)


class BulkIn(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=25)


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_password(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p, h):
    return bcrypt.checkpw(p.encode(), h.encode())


def make_token(user: User):
    payload = {"sub": str(user.id), "email": user.email, "type": "access",
               "exp": datetime.now(timezone.utc) + timedelta(hours=12)}
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def optional_user(request: Request, db=Depends(get_db)) -> Optional[User]:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = jwt.decode(auth[7:], os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        return None
    return db.get(User, int(payload["sub"]))


def current_user(user: Optional[User] = Depends(optional_user)) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def save_scan(db, user, kind, inp, score, level, verdict, result):
    if not user:
        return None
    scan = Scan(user_id=user.id, type=kind, input=inp[:500], score=score, level=level, verdict=verdict,
                result=result, created_at=utcnow())
    db.add(scan)
    db.commit()
    return str(scan.id)


@api.get("/")
def root():
    return {"message": "AgeinsShield API (MySQL) online"}


@api.post("/auth/register")
def register(body: RegisterIn, db=Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=email, name=body.name, role="user", password_hash=hash_password(body.password), created_at=utcnow())
    db.add(user)
    db.commit()
    return {"user": user.to_dict(), "token": make_token(user)}


@api.post("/auth/login")
def login(body: LoginIn, request: Request, db=Depends(get_db)):
    email = body.email.lower()
    ident = f"{request.client.host if request.client else 'x'}:{email}"
    attempt = db.get(LoginAttempt, ident)
    if attempt and attempt.count >= 5:
        if utcnow() - attempt.last < timedelta(minutes=15):
            raise HTTPException(status_code=429, detail="Too many attempts. Try again in 15 minutes.")
        db.delete(attempt)
        db.commit()
        attempt = None
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(body.password, user.password_hash):
        attempt = attempt or LoginAttempt(identifier=ident, count=0)
        attempt.count += 1
        attempt.last = utcnow()
        db.merge(attempt)
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if attempt:
        db.delete(attempt)
        db.commit()
    return {"user": user.to_dict(), "token": make_token(user)}


@api.post("/auth/logout")
def logout():
    return {"ok": True}


@api.get("/auth/me")
def me(user: User = Depends(current_user)):
    return user.to_dict()


def safe_domains(db, user):
    if not user:
        return set()
    return set(db.scalars(select(SafeSite.domain).where(SafeSite.user_id == user.id)))


def apply_safe(r, domains):
    r["user_trusted"] = bool(r.get("host")) and (r.get("root_domain") in domains or r["host"] in domains)
    if r["user_trusted"]:
        r["flags"].append({"title": "On your Safe Sites list",
                           "detail": "You marked this domain as trusted, so the fraud alarm is suppressed.", "severity": "low"})
        r.update(score=max(r["score"], 90), level="safe", verdict="Trusted by you", is_fraud=False)
    return r


@api.post("/scan/url")
async def scan_url(body: UrlIn, user=Depends(optional_user), db=Depends(get_db)):
    r = apply_safe(await full_url_scan(body.url), safe_domains(db, user))
    r["scan_id"] = save_scan(db, user, "url", body.url, r["score"], r["level"], r["verdict"], dict(r))
    return r


@api.post("/scan/bulk")
async def scan_bulk(body: BulkIn, user=Depends(optional_user), db=Depends(get_db)):
    urls = list(dict.fromkeys(u.strip() for u in body.urls if u.strip()))
    if not urls:
        raise HTTPException(status_code=400, detail="Add at least one link")
    domains = safe_domains(db, user)
    results = [apply_safe(r, domains) for r in await asyncio.gather(*(full_url_scan(u) for u in urls))]
    for u, r in zip(urls, results):
        r["scan_id"] = save_scan(db, user, "url", u, r["score"], r["level"], r["verdict"], dict(r))
    summary = {lvl: sum(1 for r in results if r["level"] == lvl) for lvl in ("safe", "moderate", "danger")}
    return {"total": len(results), "summary": summary, "results": results}


@api.get("/safe-sites")
def list_safe_sites(user: User = Depends(current_user), db=Depends(get_db)):
    rows = db.scalars(select(SafeSite).where(SafeSite.user_id == user.id).order_by(SafeSite.created_at.desc()))
    return [s.to_dict() for s in rows]


@api.post("/safe-sites")
def add_safe_site(body: SafeSiteIn, user: User = Depends(current_user), db=Depends(get_db)):
    domain = normalize_domain(body.domain)
    if not domain:
        raise HTTPException(status_code=400, detail="Enter a valid domain like example.com")
    if db.scalar(select(SafeSite).where(SafeSite.user_id == user.id, SafeSite.domain == domain)):
        raise HTTPException(status_code=400, detail=f"{domain} is already on your Safe Sites list")
    site = SafeSite(user_id=user.id, domain=domain, created_at=utcnow())
    db.add(site)
    db.commit()
    return site.to_dict()


@api.delete("/safe-sites/{site_id}")
def delete_safe_site(site_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    site = db.get(SafeSite, int(site_id)) if site_id.isdigit() else None
    if site and site.user_id == user.id:
        db.delete(site)
        db.commit()
    return {"ok": True}


@api.post("/scan/ai")
def scan_ai(body: TextIn, user=Depends(optional_user), db=Depends(get_db)):
    r = analyze_ai_text(body.text)
    r["scan_id"] = None
    if r["level"] != "insufficient":
        r["scan_id"] = save_scan(db, user, "ai", body.text, r["ai_probability"], r["level"], r["verdict"], dict(r))
    return r


@api.post("/scan/email")
def scan_email(body: EmailIn, user=Depends(optional_user), db=Depends(get_db)):
    r = analyze_email(body.content, body.sender)
    r["scan_id"] = save_scan(db, user, "email", body.content, r["risk_score"], r["level"], r["verdict"], dict(r))
    return r


@api.post("/chat")
async def chat(body: ChatIn):
    return await chatbot_reply(body.message, body.page_url)


@api.get("/history")
def history(user: User = Depends(current_user), db=Depends(get_db)):
    rows = db.scalars(select(Scan).where(Scan.user_id == user.id).order_by(Scan.created_at.desc()).limit(200))
    return [s.to_dict() for s in rows]


def _own_scan(db, scan_id, user):
    scan = db.get(Scan, int(scan_id)) if scan_id.isdigit() else None
    if not scan or scan.user_id != user.id:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@api.delete("/history/{scan_id}")
def delete_scan(scan_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    db.delete(_own_scan(db, scan_id, user))
    db.commit()
    return {"ok": True}


@api.get("/history/{scan_id}/pdf")
def scan_pdf(scan_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    scan = _own_scan(db, scan_id, user)
    return RawResponse(build_pdf(scan.to_dict()), media_type="application/pdf",
                       headers={"Content-Disposition": f'attachment; filename="ageinsshield-{scan.type}-report-{scan.id}.pdf"'})


@api.get("/stats")
def stats(user: User = Depends(current_user), db=Depends(get_db)):
    rows = list(db.scalars(select(Scan).where(Scan.user_id == user.id)))
    by_type = {t: sum(1 for s in rows if s.type == t) for t in ("url", "ai", "email")}
    return {"total": len(rows), "threats": sum(1 for s in rows if s.level in ("danger", "ai")), "by_type": by_type}


def _public_base(request: Request):
    return os.environ.get("PUBLIC_API_URL") or str(request.base_url).rstrip("/")


@api.get("/widget.js")
def widget_js(request: Request):
    js = (ROOT_DIR / "widget.js").read_text().replace("__API_BASE__", _public_base(request))
    return RawResponse(js, media_type="application/javascript")


@api.get("/extension.zip")
def extension_zip(request: Request):
    return RawResponse(build_extension_zip(EXTENSION_DIR, _public_base(request)), media_type="application/zip",
                       headers={"Content-Disposition": 'attachment; filename="ageinsshield-extension.zip"'})


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    admin_email = os.environ["ADMIN_EMAIL"].lower()
    admin_pw = os.environ["ADMIN_PASSWORD"]
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == admin_email))
        if not admin:
            db.add(User(email=admin_email, name="Admin", role="admin", password_hash=hash_password(admin_pw), created_at=utcnow()))
        elif not verify_password(admin_pw, admin.password_hash):
            admin.password_hash = hash_password(admin_pw)
        db.commit()
