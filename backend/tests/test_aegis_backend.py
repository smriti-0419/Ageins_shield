"""AegisShield backend API tests (pytest). Covers auth, scans, chat, history, stats, widget."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phishing-guard-61.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin@aegisshield.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and "user" in data
    assert data["user"]["email"] == ADMIN_EMAIL
    return data["token"]


@pytest.fixture(scope="session")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# -------- Health / root --------
def test_root():
    r = requests.get(f"{API}/")
    assert r.status_code == 200
    assert "AegisShield" in r.json()["message"]


# -------- Auth --------
def test_register_duplicate_rejected():
    r = requests.post(f"{API}/auth/register", json={"name": "x", "email": ADMIN_EMAIL, "password": "whatever"})
    assert r.status_code == 400


def test_register_new_user_and_me():
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{API}/auth/register", json={"name": "Tester", "email": email, "password": "secret123"})
    assert r.status_code == 200, r.text
    data = r.json()
    tok = data["token"]
    assert data["user"]["email"] == email
    me = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_login_invalid_password():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong-pw"})
    assert r.status_code in (401, 429)


def test_me_requires_auth():
    r = requests.get(f"{API}/auth/me")
    assert r.status_code == 401


# -------- URL scan --------
def test_scan_url_github_safe():
    r = requests.post(f"{API}/scan/url", json={"url": "https://github.com"})
    assert r.status_code == 200
    d = r.json()
    assert d["score"] >= 80
    assert d["level"] == "safe"
    assert "Looks safe" in d["verdict"]


def test_scan_url_phishing():
    r = requests.post(f"{API}/scan/url", json={"url": "http://paypal-verify-login.xyz/secure/account"})
    assert r.status_code == 200
    d = r.json()
    assert d["score"] < 50
    assert d["level"] == "danger"
    assert d["is_fraud"] is True
    assert len(d["flags"]) > 0


def test_scan_url_moderate():
    r = requests.post(f"{API}/scan/url", json={"url": "http://some-random-site.com/login"})
    assert r.status_code == 200
    d = r.json()
    assert 1 <= d["score"] <= 100


# -------- AI detector --------
def test_scan_ai_insufficient():
    r = requests.post(f"{API}/scan/ai", json={"text": "too short text here"})
    assert r.status_code == 200
    assert r.json()["level"] == "insufficient"


def test_scan_ai_ai_like():
    text = ("In today's fast-paced landscape, it is important to note that we must leverage robust, "
            "seamless and holistic solutions. Furthermore, this plays a crucial role in the ever-evolving realm. "
            "Moreover, we should foster comprehensive strategies to navigate the multifaceted challenges. "
            "In conclusion, delve deeper to unlock the pivotal value of this paramount approach.")
    r = requests.post(f"{API}/scan/ai", json={"text": text})
    assert r.status_code == 200
    d = r.json()
    assert d["ai_probability"] >= 65
    assert d["level"] == "ai"


def test_scan_ai_human_like():
    text = ("Yesterday I grabbed coffee with Sam and we didn't stop laughing. He's got this weird habit "
            "of adding too much sugar lol. Anyway, I'm gonna call mom tonight. Can't wait, honestly! "
            "I think we'll watch that movie I keep bugging her about.")
    r = requests.post(f"{API}/scan/ai", json={"text": text})
    assert r.status_code == 200
    d = r.json()
    assert d["ai_probability"] < 65


# -------- Email detector --------
def test_scan_email_phishing():
    content = ("From: security@paypa1-support.com\nSubject: URGENT: your account is suspended\n\n"
               "Dear customer, your account has been locked. Verify your account immediately and confirm your "
               "password and OTP within 24 hours or it will be suspended. Click http://paypal-verify.xyz/login")
    r = requests.post(f"{API}/scan/email", json={"content": content, "sender": "security@paypa1-support.com"})
    assert r.status_code == 200
    d = r.json()
    assert d["is_phishing"] is True
    assert d["level"] == "danger"
    assert len(d["flags"]) > 0


def test_scan_email_legit_github_receipt():
    content = ("From: receipts@github.com\nSubject: Your GitHub receipt\n\n"
               "Hi Alex, thanks for your recent GitHub subscription. Your invoice is attached as a PDF. "
               "No action is needed. See your billing settings at https://github.com/settings/billing")
    r = requests.post(f"{API}/scan/email", json={"content": content, "sender": "receipts@github.com"})
    assert r.status_code == 200
    d = r.json()
    assert d["level"] in ("safe", "moderate")


# -------- Chat --------
def test_chat_hello():
    r = requests.post(f"{API}/chat", json={"message": "hello"})
    assert r.status_code == 200
    assert "Aegis" in r.json()["reply"]


def test_chat_phishing():
    r = requests.post(f"{API}/chat", json={"message": "tell me about phishing"})
    assert r.status_code == 200
    assert "phishing" in r.json()["reply"].lower() or "red flag" in r.json()["reply"].lower()


def test_chat_password():
    r = requests.post(f"{API}/chat", json={"message": "password tips"})
    assert r.status_code == 200
    assert "password" in r.json()["reply"].lower() or "2fa" in r.json()["reply"].lower()


def test_chat_with_url():
    r = requests.post(f"{API}/chat", json={"message": "is https://github.com safe?"})
    assert r.status_code == 200
    d = r.json()
    assert "scan" in d
    assert d["scan"]["score"] >= 80


# -------- History & stats --------
def test_history_requires_auth():
    r = requests.get(f"{API}/history")
    assert r.status_code == 401


def test_history_and_delete_flow(auth_headers):
    # create a scan as admin
    sc = requests.post(f"{API}/scan/url", json={"url": "https://github.com"}, headers=auth_headers)
    assert sc.status_code == 200
    h = requests.get(f"{API}/history", headers=auth_headers)
    assert h.status_code == 200
    items = h.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    first = items[0]
    assert "id" in first and first["type"] == "url"
    # delete
    d = requests.delete(f"{API}/history/{first['id']}", headers=auth_headers)
    assert d.status_code == 200


def test_stats(auth_headers):
    # ensure at least one of each type
    requests.post(f"{API}/scan/url", json={"url": "https://github.com"}, headers=auth_headers)
    requests.post(f"{API}/scan/email", json={"content": "From: a@b.com\nhello world body"}, headers=auth_headers)
    r = requests.get(f"{API}/stats", headers=auth_headers)
    assert r.status_code == 200
    d = r.json()
    assert "total" in d and "threats" in d and "by_type" in d
    assert set(d["by_type"].keys()) == {"url", "ai", "email"}


# -------- Widget JS --------
def test_widget_js():
    r = requests.get(f"{API}/widget.js")
    assert r.status_code == 200
    assert "application/javascript" in r.headers.get("content-type", "")
    body = r.text
    assert "__API_BASE__" not in body  # placeholder replaced
    assert "/api/chat" in body or "chat" in body
