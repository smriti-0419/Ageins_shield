from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import hmac
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional, Any, Literal

import bcrypt
import jwt
from bson import ObjectId
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, BackgroundTasks
from fastapi.responses import Response as RawResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field
from pymongo.errors import DuplicateKeyError
from starlette.middleware.cors import CORSMiddleware

from analyzers import full_url_scan, analyze_ai_text, analyze_email, chatbot_reply, normalize_domain
from reports import build_pdf, build_extension_zip
from emailer import send_email, build_digest

logger = logging.getLogger("aegis")

EXTENSION_DIR = ROOT_DIR.parent / "extension"

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
app = FastAPI(title="AgeinsShield API")
api = APIRouter(prefix="/api")
JWT_ALGORITHM = "HS256"

PyObjectId = Annotated[str, BeforeValidator(lambda v: str(v) if isinstance(v, ObjectId) else v)]


class BaseDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    @classmethod
    def from_mongo(cls, doc):
        return cls.model_validate(doc)

    def to_mongo(self):
        d = self.model_dump(by_alias=True, exclude_none=True)
        d.pop("_id", None)
        return d


class User(BaseDocument):
    email: str
    name: str
    role: str = "user"
    created_at: str
    weekly_email: bool = False


class SafeSite(BaseDocument):
    user_id: str
    domain: str
    created_at: str


class SafeSiteIn(BaseModel):
    domain: str = Field(min_length=3, max_length=255)


class BulkIn(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=25)


class SettingsIn(BaseModel):
    weekly_email: bool

class Scan(BaseDocument):
    user_id: str
    type: str
    input: str
    score: int
    level: str
    verdict: str
    result: dict[str, Any]
    created_at: str


class RegisterIn(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=6)


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    portal: Literal["admin", "user"] = "user"


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


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def hash_password(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p, h):
    return bcrypt.checkpw(p.encode(), h.encode())


def make_token(user_id, email, kind, delta):
    payload = {"sub": user_id, "email": email, "type": kind, "exp": datetime.now(timezone.utc) + delta}
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


def issue_tokens(response: Response, user_id, email):
    access = make_token(user_id, email, "access", timedelta(hours=12))
    refresh = make_token(user_id, email, "refresh", timedelta(days=7))
    response.set_cookie("access_token", access, httponly=True, secure=True, samesite="none", max_age=43200, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=True, samesite="none", max_age=604800, path="/")
    return access


async def _user_from_request(request: Request):
    token = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    token = token or request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        return None
    if payload.get("type") != "access":
        return None
    doc = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    return User.from_mongo(doc) if doc else None


async def current_user(request: Request) -> User:
    user = await _user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def optional_user(request: Request) -> Optional[User]:
    return await _user_from_request(request)


async def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@api.get("/")
async def root():
    return {"message": "AgeinsShield API online"}


@api.post("/auth/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=email, name=body.name, created_at=now_iso())
    doc = user.to_mongo() | {"password_hash": hash_password(body.password)}
    res = await db.users.insert_one(doc)
    user.id = str(res.inserted_id)
    token = issue_tokens(response, user.id, email)
    return {"user": user.model_dump(), "token": token}


@api.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.lower()
    ident = f"{request.client.host if request.client else 'x'}:{email}"
    attempt = await db.login_attempts.find_one({"identifier": ident})
    if attempt and attempt.get("count", 0) >= 5:
        locked_at = datetime.fromisoformat(attempt["last"])
        if datetime.now(timezone.utc) - locked_at < timedelta(minutes=15):
            raise HTTPException(status_code=429, detail="Too many attempts. Try again in 15 minutes.")
        await db.login_attempts.delete_one({"identifier": ident})
    doc = await db.users.find_one({"email": email})
    if not doc or not verify_password(body.password, doc["password_hash"]) or doc.get("role", "user") != body.portal:
        await db.login_attempts.update_one({"identifier": ident}, {"$inc": {"count": 1}, "$set": {"last": now_iso()}}, upsert=True)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await db.login_attempts.delete_one({"identifier": ident})
    user = User.from_mongo(doc)
    token = issue_tokens(response, user.id, email)
    return {"user": user.model_dump(), "token": token}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user: User = Depends(current_user)):
    return user.model_dump()


async def save_scan(user: Optional[User], kind, inp, score, level, verdict, result):
    if not user:
        return None
    scan = Scan(user_id=user.id, type=kind, input=inp[:500], score=score, level=level,
                verdict=verdict, result=result, created_at=now_iso())
    res = await db.scans.insert_one(scan.to_mongo())
    return str(res.inserted_id)


async def safe_domains(user: Optional[User]) -> set:
    if not user:
        return set()
    return {d["domain"] for d in await db.safe_sites.find({"user_id": user.id}, {"domain": 1}).to_list(1000)}


def apply_safe(r: dict, domains: set) -> dict:
    r["user_trusted"] = bool(r.get("host")) and (r.get("root_domain") in domains or r["host"] in domains)
    if r["user_trusted"]:
        r["flags"].append({"title": "On your Safe Sites list",
                           "detail": "You marked this domain as trusted, so the fraud alarm is suppressed.", "severity": "low"})
        r.update(score=max(r["score"], 90), level="safe", verdict="Trusted by you", is_fraud=False)
    return r


async def scan_one_url(url: str, user: Optional[User], domains: set) -> dict:
    r = apply_safe(await full_url_scan(url), domains)
    r["scan_id"] = await save_scan(user, "url", url, r["score"], r["level"], r["verdict"], dict(r))
    return r


@api.post("/scan/url")
async def scan_url(body: UrlIn, user: Optional[User] = Depends(optional_user)):
    return await scan_one_url(body.url, user, await safe_domains(user))


@api.post("/scan/bulk")
async def scan_bulk(body: BulkIn, user: Optional[User] = Depends(optional_user)):
    urls = list(dict.fromkeys(u.strip() for u in body.urls if u.strip()))
    if not urls:
        raise HTTPException(status_code=400, detail="Add at least one link")
    domains = await safe_domains(user)
    results = await asyncio.gather(*(scan_one_url(u, user, domains) for u in urls))
    summary = {lvl: sum(1 for r in results if r["level"] == lvl) for lvl in ("safe", "moderate", "danger")}
    return {"total": len(results), "summary": summary, "results": results}


@api.get("/safe-sites")
async def list_safe_sites(user: User = Depends(current_user)):
    docs = await db.safe_sites.find({"user_id": user.id}).sort("created_at", -1).to_list(1000)
    return [SafeSite.from_mongo(d).model_dump() for d in docs]


@api.post("/safe-sites")
async def add_safe_site(body: SafeSiteIn, user: User = Depends(current_user)):
    domain = normalize_domain(body.domain)
    if not domain:
        raise HTTPException(status_code=400, detail="Enter a valid domain like example.com")
    site = SafeSite(user_id=user.id, domain=domain, created_at=now_iso())
    try:
        res = await db.safe_sites.insert_one(site.to_mongo())
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail=f"{domain} is already on your Safe Sites list")
    site.id = str(res.inserted_id)
    return site.model_dump()


@api.delete("/safe-sites/{site_id}")
async def delete_safe_site(site_id: str, user: User = Depends(current_user)):
    await db.safe_sites.delete_one({"_id": ObjectId(site_id), "user_id": user.id})
    return {"ok": True}


@api.get("/settings")
async def get_settings(user: User = Depends(current_user)):
    return {"weekly_email": user.weekly_email, "email": user.email}


@api.put("/settings")
async def update_settings(body: SettingsIn, user: User = Depends(current_user)):
    await db.users.update_one({"_id": ObjectId(user.id)}, {"$set": {"weekly_email": body.weekly_email}})
    return {"weekly_email": body.weekly_email, "email": user.email}


async def send_digest(user_doc: dict) -> str:
    user_id = str(user_doc["_id"])
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    docs = await db.scans.find({"user_id": user_id, "created_at": {"$gte": since}}).to_list(2000)
    scans = [Scan.from_mongo(d).model_dump() for d in docs]
    subject, html = build_digest(user_doc["name"], scans, f"{os.environ['FRONTEND_URL']}/console/history")
    email_id = await send_email(to=user_doc["email"], subject=subject, html=html)
    await db.users.update_one({"_id": user_doc["_id"]}, {"$set": {"last_digest_at": now_iso()}})
    return email_id


@api.post("/digest/preview")
async def digest_preview(user: User = Depends(current_user)):
    doc = await db.users.find_one({"_id": ObjectId(user.id)})
    last = doc.get("last_digest_at")
    if last and datetime.now(timezone.utc) - datetime.fromisoformat(last) < timedelta(minutes=1):
        raise HTTPException(status_code=429, detail="Please wait a minute before sending another summary")
    try:
        email_id = await send_digest(doc)
    except Exception as e:
        logger.error("Digest preview failed: %s", e)
        raise HTTPException(status_code=502, detail="Could not send the email. Please try again later.")
    return {"status": "sent", "email_id": email_id, "to": doc["email"]}


async def run_weekly_digest():
    async for doc in db.users.find({"weekly_email": True}):
        try:
            await send_digest(doc)
        except Exception as e:
            logger.error("Weekly digest failed for %s: %s", doc["_id"], e)


@api.post("/cron/weekly-digest")
async def cron_weekly_digest(request: Request, background: BackgroundTasks):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:], os.environ["WEBHOOK_CRON_SECRET"]):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        envelope = await request.json()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid body")
    run_id = request.headers.get("X-Webhook-Id") or (envelope or {}).get("run_id")
    if not run_id:
        raise HTTPException(status_code=400, detail="Missing run id")
    try:
        await db.cron_runs.insert_one({"_id": run_id, "name": "weekly-digest", "at": now_iso()})
    except DuplicateKeyError:
        return {"status": "duplicate"}
    background.add_task(run_weekly_digest)
    return {"status": "accepted"}


@api.post("/scan/ai")
async def scan_ai(body: TextIn, user: Optional[User] = Depends(optional_user)):
    r = analyze_ai_text(body.text)
    r["scan_id"] = None
    if r["level"] != "insufficient":
        r["scan_id"] = await save_scan(user, "ai", body.text, r["ai_probability"], r["level"], r["verdict"], dict(r))
    return r


@api.post("/scan/email")
async def scan_email(body: EmailIn, user: Optional[User] = Depends(optional_user)):
    r = analyze_email(body.content, body.sender)
    r["scan_id"] = await save_scan(user, "email", body.content, r["risk_score"], r["level"], r["verdict"], dict(r))
    return r


@api.post("/chat")
async def chat(body: ChatIn):
    return await chatbot_reply(body.message, body.page_url)


@api.get("/history/{scan_id}/pdf")
async def scan_pdf(scan_id: str, user: User = Depends(current_user)):
    doc = await db.scans.find_one({"_id": ObjectId(scan_id), "user_id": user.id})
    if not doc:
        raise HTTPException(status_code=404, detail="Scan not found")
    pdf = build_pdf(Scan.from_mongo(doc).model_dump())
    return RawResponse(pdf, media_type="application/pdf",
                       headers={"Content-Disposition": f'attachment; filename="ageinsshield-{doc["type"]}-report-{scan_id}.pdf"'})


@api.get("/extension.zip")
async def extension_zip(request: Request):
    base = os.environ.get("PUBLIC_API_URL") or str(request.base_url).rstrip("/")
    return RawResponse(build_extension_zip(EXTENSION_DIR, base), media_type="application/zip",
                       headers={"Content-Disposition": 'attachment; filename="ageinsshield-extension.zip"'})


@api.get("/history")
async def history(user: User = Depends(current_user)):
    docs = await db.scans.find({"user_id": user.id}).sort("created_at", -1).to_list(200)
    return [Scan.from_mongo(d).model_dump() for d in docs]


@api.delete("/history/{scan_id}")
async def delete_scan(scan_id: str, user: User = Depends(current_user)):
    await db.scans.delete_one({"_id": ObjectId(scan_id), "user_id": user.id})
    return {"ok": True}


@api.get("/stats")
async def stats(user: User = Depends(current_user)):
    docs = await db.scans.find({"user_id": user.id}).to_list(1000)
    by_type = {t: sum(1 for d in docs if d["type"] == t) for t in ("url", "ai", "email")}
    threats = sum(1 for d in docs if d["level"] in ("danger", "ai"))
    return {"total": len(docs), "threats": threats, "by_type": by_type}


@api.get("/admin/users")
async def admin_users(_: User = Depends(require_admin)):
    activity = {}
    pipeline = [
        {"$group": {
            "_id": "$user_id",
            "scan_count": {"$sum": 1},
            "threats": {"$sum": {"$cond": [{"$in": ["$level", ["danger", "ai"]]}, 1, 0]}},
            "last_scan": {"$max": "$created_at"},
        }}
    ]
    async for row in db.scans.aggregate(pipeline):
        activity[row["_id"]] = {
            "scan_count": row["scan_count"],
            "threats": row["threats"],
            "last_scan": row.get("last_scan"),
        }

    users = []
    async for doc in db.users.find().sort("created_at", -1):
        user = User.from_mongo(doc).model_dump()
        user["activity"] = activity.get(user["id"], {"scan_count": 0, "threats": 0, "last_scan": None})
        users.append(user)
    return {
        "users": users,
        "total_users": len(users),
        "total_scans": sum(u["activity"]["scan_count"] for u in users),
        "total_threats": sum(u["activity"]["threats"] for u in users),
    }


@api.get("/admin/users/{user_id}/scans")
async def admin_user_scans(user_id: str, _: User = Depends(require_admin)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user id")
    if not await db.users.find_one({"_id": ObjectId(user_id)}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="User not found")
    docs = await db.scans.find({"user_id": user_id}).sort("created_at", -1).to_list(200)
    return [Scan.from_mongo(doc).model_dump() for doc in docs]


@api.get("/widget.js")
async def widget_js(request: Request):
    js = (ROOT_DIR / "widget.js").read_text()
    base = os.environ.get("PUBLIC_API_URL") or str(request.base_url).rstrip("/")
    return RawResponse(js.replace("__API_BASE__", base), media_type="application/javascript")


app.include_router(api)
from deepfake import router as deepfake_router
app.include_router(deepfake_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.scans.create_index([("user_id", 1), ("created_at", -1)])
    await db.safe_sites.create_index([("user_id", 1), ("domain", 1)], unique=True)
    admin_email = os.environ["ADMIN_EMAIL"].lower()
    admin_pw = os.environ["ADMIN_PASSWORD"]
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        existing = await db.users.find_one({"role": "admin"})
    if not existing:
        await db.users.insert_one({"email": admin_email, "name": "Admin", "role": "admin",
                                   "created_at": now_iso(), "password_hash": hash_password(admin_pw)})
    else:
        await db.users.update_one({"_id": existing["_id"]}, {"$set": {
            "email": admin_email, "name": "Admin", "role": "admin", "password_hash": hash_password(admin_pw),
        }})
    await db.users.update_many(
        {"role": "admin", "email": {"$ne": admin_email}},
        {"$set": {"role": "user"}},
    )


@app.on_event("shutdown")
async def shutdown():
    client.close()
