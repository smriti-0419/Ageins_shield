"""Phase 3 tests: look-alike detection, Safe Sites, Bulk scanner, Settings/Digest, Cron."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phishing-guard-61.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin@aegisshield.com"
ADMIN_PASSWORD = "admin123"
DIGEST_EMAIL = "delivered@resend.dev"
DIGEST_PASSWORD = "test1234"
CRON_SECRET = "c7f2e91b4a6d3058e1f9b2c4d7a60e38f5b19c2d4e7a8b0f"


def _login_or_register(email, password, name="Tester"):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password})
    if r.status_code == 200:
        return r.json()["token"]
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": password, "name": name})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_headers():
    tok = _login_or_register(ADMIN_EMAIL, ADMIN_PASSWORD, "Admin")
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def digest_headers():
    tok = _login_or_register(DIGEST_EMAIL, DIGEST_PASSWORD, "Delivered")
    return {"Authorization": f"Bearer {tok}"}


# ---------------- Look-alike detection ----------------
LOOKALIKE_HITS = ["paypa1.com", "arnazon.com", "g00gle.net", "amzaon.com", "faceb00k.co"]
LEGIT = ["paypal.com", "github.com", "amazing.com"]


@pytest.mark.parametrize("host", LOOKALIKE_HITS)
def test_lookalike_flagged(host):
    r = requests.post(f"{API}/scan/url", json={"url": f"https://{host}/login"})
    assert r.status_code == 200
    titles = [f["title"] for f in r.json()["flags"]]
    assert any("Look-alike" in t for t in titles), f"{host}: {titles}"


@pytest.mark.parametrize("host", LEGIT)
def test_legit_not_lookalike(host):
    r = requests.post(f"{API}/scan/url", json={"url": f"https://{host}/"})
    assert r.status_code == 200
    titles = [f["title"] for f in r.json()["flags"]]
    assert not any("Look-alike" in t for t in titles), f"{host} wrongly flagged: {titles}"


def test_lookalike_sender_in_email():
    payload = {"content": "From: billing@paypa1.com\nSubject: urgent\n\nPlease verify your account now.", "sender": ""}
    r = requests.post(f"{API}/scan/email", json=payload)
    assert r.status_code == 200
    titles = [f["title"] for f in r.json()["flags"]]
    assert any("Look-alike sender domain" == t for t in titles), titles


# ---------------- Safe Sites ----------------
def test_safe_sites_add_normalize_and_dedupe(admin_headers):
    # choose a unique domain
    rnd = uuid.uuid4().hex[:8]
    domain_root = f"test{rnd}.xyz"
    inp = f"https://www.shop.{domain_root}/path?q=1"
    r = requests.post(f"{API}/safe-sites", json={"domain": inp}, headers=admin_headers)
    assert r.status_code == 200, r.text
    added = r.json()
    assert added["domain"] == domain_root
    site_id = added["id"]
    try:
        # duplicate
        r2 = requests.post(f"{API}/safe-sites", json={"domain": domain_root}, headers=admin_headers)
        assert r2.status_code == 400
        assert "already" in r2.json()["detail"].lower()

        # list contains it
        lst = requests.get(f"{API}/safe-sites", headers=admin_headers).json()
        assert any(s["domain"] == domain_root for s in lst)

        # scanning a subdomain of trusted domain -> user_trusted
        scan = requests.post(f"{API}/scan/url", json={"url": f"https://login.{domain_root}/x"}, headers=admin_headers)
        assert scan.status_code == 200
        sd = scan.json()
        assert sd["user_trusted"] is True
        assert sd["score"] >= 90
        assert sd["verdict"] == "Trusted by you"
        assert sd["is_fraud"] is False
    finally:
        requests.delete(f"{API}/safe-sites/{site_id}", headers=admin_headers)


def test_safe_sites_invalid_domain(admin_headers):
    r = requests.post(f"{API}/safe-sites", json={"domain": "not a domain!!"}, headers=admin_headers)
    assert r.status_code == 400


def test_safe_sites_requires_auth():
    r = requests.get(f"{API}/safe-sites")
    assert r.status_code == 401


# ---------------- Bulk scanner ----------------
def test_bulk_scan_basic():
    urls = ["https://github.com", "paypa1.com/login", "https://github.com", "   ", "http://arnazon-deals.top/claim"]
    r = requests.post(f"{API}/scan/bulk", json={"urls": urls})
    assert r.status_code == 200
    d = r.json()
    # dedupe + blank stripped -> 3 results
    assert d["total"] == 3
    assert set(d["summary"].keys()) == {"safe", "moderate", "danger"}
    assert sum(d["summary"].values()) == d["total"]
    # each result has scan_id key (null for anonymous)
    for r_ in d["results"]:
        assert "scan_id" in r_


def test_bulk_scan_all_blank_400():
    r = requests.post(f"{API}/scan/bulk", json={"urls": ["   ", "", "\t"]})
    assert r.status_code == 400


def test_bulk_scan_over_limit_422():
    urls = [f"https://x{i}.example.com" for i in range(26)]
    r = requests.post(f"{API}/scan/bulk", json={"urls": urls})
    assert r.status_code == 422


# ---------------- Settings ----------------
def test_settings_get_and_toggle(admin_headers):
    g = requests.get(f"{API}/settings", headers=admin_headers)
    assert g.status_code == 200
    assert "weekly_email" in g.json() and "email" in g.json()

    # toggle on
    p = requests.put(f"{API}/settings", json={"weekly_email": True}, headers=admin_headers)
    assert p.status_code == 200 and p.json()["weekly_email"] is True
    g2 = requests.get(f"{API}/settings", headers=admin_headers).json()
    assert g2["weekly_email"] is True

    # toggle off (admin must end up False per review request)
    p2 = requests.put(f"{API}/settings", json={"weekly_email": False}, headers=admin_headers)
    assert p2.status_code == 200 and p2.json()["weekly_email"] is False


def test_settings_requires_auth():
    assert requests.get(f"{API}/settings").status_code == 401
    assert requests.put(f"{API}/settings", json={"weekly_email": True}).status_code == 401


# ---------------- Digest preview (real send to delivered@resend.dev) ----------------
def test_digest_preview_send_then_429(digest_headers):
    # make sure not blocked by prior last_digest_at (may 429 if ran recently -> accept 429 and skip rest)
    r = requests.post(f"{API}/digest/preview", headers=digest_headers)
    if r.status_code == 429:
        pytest.skip("Digest preview throttled from previous run; cannot reset without DB access")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "sent"
    assert body["to"] == DIGEST_EMAIL
    # 2nd immediate call -> 429
    r2 = requests.post(f"{API}/digest/preview", headers=digest_headers)
    assert r2.status_code == 429


def test_digest_preview_requires_auth():
    assert requests.post(f"{API}/digest/preview").status_code == 401


# ---------------- Cron weekly digest ----------------
def test_cron_requires_bearer():
    r = requests.post(f"{API}/cron/weekly-digest", json={})
    assert r.status_code == 401


def test_cron_wrong_secret():
    r = requests.post(f"{API}/cron/weekly-digest", json={},
                      headers={"Authorization": "Bearer wrong_secret"})
    assert r.status_code == 401


def test_cron_prepare_admin_off_delivered_on(admin_headers, digest_headers):
    # Make sure admin.weekly_email = false; delivered@resend.dev weekly_email = true
    requests.put(f"{API}/settings", json={"weekly_email": False}, headers=admin_headers)
    requests.put(f"{API}/settings", json={"weekly_email": True}, headers=digest_headers)
    a = requests.get(f"{API}/settings", headers=admin_headers).json()
    d = requests.get(f"{API}/settings", headers=digest_headers).json()
    assert a["weekly_email"] is False
    assert d["weekly_email"] is True


def test_cron_accepted_then_duplicate():
    run_id = f"test-run-{uuid.uuid4().hex}"
    h = {"Authorization": f"Bearer {CRON_SECRET}", "X-Webhook-Id": run_id, "Content-Type": "application/json"}
    r = requests.post(f"{API}/cron/weekly-digest", json={}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json() == {"status": "accepted"}
    # same id again
    r2 = requests.post(f"{API}/cron/weekly-digest", json={}, headers=h)
    assert r2.status_code == 200
    assert r2.json() == {"status": "duplicate"}


def test_cron_missing_run_id():
    h = {"Authorization": f"Bearer {CRON_SECRET}", "Content-Type": "application/json"}
    r = requests.post(f"{API}/cron/weekly-digest", json={}, headers=h)
    assert r.status_code == 400
