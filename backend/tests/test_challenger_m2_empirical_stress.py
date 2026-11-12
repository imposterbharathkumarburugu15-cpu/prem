import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_bootstrap():
    """Ensure baseline platform data and roles are present."""
    resp = client.post("/api/v1/platform/auth/bootstrap")
    assert resp.status_code == 200


# ============================================================================
# EMPIRICAL EMAIL STRESS TESTS: DUPLICATES, CASE INSENSITIVITY, WHITESPACE
# ============================================================================

def test_duplicate_email_exact_returns_400_not_500():
    """Verify exact duplicate email returns HTTP 400, never HTTP 500."""
    rand_id = uuid.uuid4().hex[:8]
    email = f"exact_dup_{rand_id}@praman.org"

    u1 = {
        "username": f"exact_u1_{rand_id}",
        "email": email,
        "password": "Password@123",
        "full_name": "User 1",
        "role": "TRANSPORTER"
    }
    r1 = client.post("/api/v1/platform/admin/users", json=u1)
    assert r1.status_code == 200

    u2 = {
        "username": f"exact_u2_{rand_id}",
        "email": email,
        "password": "Password@123",
        "full_name": "User 2",
        "role": "RETAILER"
    }
    r2 = client.post("/api/v1/platform/admin/users", json=u2)
    assert r2.status_code == 400
    assert r2.status_code != 500
    assert "email" in r2.json()["detail"].lower()
    assert "already registered" in r2.json()["detail"].lower()


def test_duplicate_email_case_insensitivity_returns_400_not_500():
    """Verify duplicate email with mixed/upper/lower case returns HTTP 400, not 500."""
    rand_id = uuid.uuid4().hex[:8]
    email_lower = f"case_test_{rand_id}@praman.org"
    email_upper = f"CASE_TEST_{rand_id.upper()}@PRAMAN.ORG"
    email_mixed = f"cAsE_tEsT_{rand_id}@PrAmAn.OrG"

    # Register lower case
    u1 = {
        "username": f"case_u1_{rand_id}",
        "email": email_lower,
        "password": "Password@123",
        "full_name": "Case User 1",
        "role": "COLLECTION_CENTRE"
    }
    r1 = client.post("/api/v1/platform/admin/users", json=u1)
    assert r1.status_code == 200

    # Attempt registration with upper case
    u2 = {
        "username": f"case_u2_{rand_id}",
        "email": email_upper,
        "password": "Password@123",
        "full_name": "Case User 2",
        "role": "RETAILER"
    }
    r2 = client.post("/api/v1/platform/admin/users", json=u2)
    assert r2.status_code == 400, f"Expected 400 for uppercase duplicate, got {r2.status_code}: {r2.text}"
    assert r2.status_code != 500
    assert "already registered" in r2.json()["detail"].lower()

    # Attempt registration with mixed case
    u3 = {
        "username": f"case_u3_{rand_id}",
        "email": email_mixed,
        "password": "Password@123",
        "full_name": "Case User 3",
        "role": "TRANSPORTER"
    }
    r3 = client.post("/api/v1/platform/admin/users", json=u3)
    assert r3.status_code == 400, f"Expected 400 for mixed case duplicate, got {r3.status_code}: {r3.text}"
    assert r3.status_code != 500
    assert "already registered" in r3.json()["detail"].lower()


def test_duplicate_email_leading_trailing_whitespace_returns_400_not_500():
    """Verify duplicate email with leading/trailing spaces, tabs, newlines returns HTTP 400, not 500."""
    rand_id = uuid.uuid4().hex[:8]
    email_clean = f"ws_test_{rand_id}@praman.org"
    email_spaces = f"   {email_clean}   "
    email_tabs_newlines = f"\t\n  {email_clean}  \r\n"

    # Register clean email
    u1 = {
        "username": f"ws_u1_{rand_id}",
        "email": email_clean,
        "password": "Password@123",
        "full_name": "Whitespace User 1",
        "role": "TRANSPORTER"
    }
    r1 = client.post("/api/v1/platform/admin/users", json=u1)
    assert r1.status_code == 200

    # Attempt registration with space padding
    u2 = {
        "username": f"ws_u2_{rand_id}",
        "email": email_spaces,
        "password": "Password@123",
        "full_name": "Whitespace User 2",
        "role": "RETAILER"
    }
    r2 = client.post("/api/v1/platform/admin/users", json=u2)
    assert r2.status_code == 400, f"Expected 400 for spaces padding duplicate, got {r2.status_code}: {r2.text}"
    assert r2.status_code != 500
    assert "already registered" in r2.json()["detail"].lower()

    # Attempt registration with tabs/newlines padding
    u3 = {
        "username": f"ws_u3_{rand_id}",
        "email": email_tabs_newlines,
        "password": "Password@123",
        "full_name": "Whitespace User 3",
        "role": "COLLECTION_CENTRE"
    }
    r3 = client.post("/api/v1/platform/admin/users", json=u3)
    assert r3.status_code == 400, f"Expected 400 for tabs/newlines duplicate, got {r3.status_code}: {r3.text}"
    assert r3.status_code != 500
    assert "already registered" in r3.json()["detail"].lower()


def test_duplicate_email_reverse_padded_first_returns_400_not_500():
    """Verify user created with padded uppercase email blocks subsequent clean lowercase attempt with HTTP 400."""
    rand_id = uuid.uuid4().hex[:8]
    email_clean = f"rev_test_{rand_id}@praman.org"
    email_padded_upper = f"   REV_TEST_{rand_id.upper()}@PRAMAN.ORG   "

    # Register with padded uppercase
    u1 = {
        "username": f"rev_u1_{rand_id}",
        "email": email_padded_upper,
        "password": "Password@123",
        "full_name": "Reverse User 1",
        "role": "AUTHORITY"
    }
    r1 = client.post("/api/v1/platform/admin/users", json=u1)
    assert r1.status_code == 200
    assert r1.json()["email"] == email_clean  # Verified it is normalized on storage

    # Attempt to register clean lowercase
    u2 = {
        "username": f"rev_u2_{rand_id}",
        "email": email_clean,
        "password": "Password@123",
        "full_name": "Reverse User 2",
        "role": "ADMIN"
    }
    r2 = client.post("/api/v1/platform/admin/users", json=u2)
    assert r2.status_code == 400, f"Expected 400, got {r2.status_code}: {r2.text}"
    assert r2.status_code != 500
    assert "already registered" in r2.json()["detail"].lower()


# ============================================================================
# ENDPOINT COVERAGE: /platform/admin/organizations, /platform/admin/users, /platform/admin/stats
# ============================================================================

def test_admin_organizations_endpoint():
    """Stress test GET and POST /platform/admin/organizations."""
    # List organizations
    resp = client.get("/api/v1/platform/admin/organizations")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # Duplicate name should reject with 400
    rand_id = uuid.uuid4().hex[:8]
    org_name = f"Org Unique {rand_id}"
    resp1 = client.post("/api/v1/platform/admin/organizations", json={
        "name": org_name,
        "org_type": "TRANSPORTER"
    })
    assert resp1.status_code == 200

    resp2 = client.post("/api/v1/platform/admin/organizations", json={
        "name": org_name,
        "org_type": "RETAILER"
    })
    assert resp2.status_code == 400
    assert resp2.status_code != 500


def test_admin_stats_and_dashboard_endpoints():
    """Check availability and behavior of admin stats / dashboard."""
    # Check /platform/admin/dashboard
    dash_resp = client.get("/api/v1/platform/admin/dashboard")
    assert dash_resp.status_code == 200
    data = dash_resp.json()
    assert "metrics" in data
    assert "users" in data
    assert "organizations" in data

    # Check /platform/admin/stats (if mapped or if returning 404)
    stats_resp = client.get("/api/v1/platform/admin/stats")
    # Record actual response for /platform/admin/stats
    assert stats_resp.status_code in (200, 404)
