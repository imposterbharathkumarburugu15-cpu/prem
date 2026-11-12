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
# 1. ORGANIZATION GOVERNANCE EMPIRICAL STRESS TESTS
# ============================================================================

@pytest.mark.parametrize("org_type", [
    "TRANSPORTER",
    "COLLECTION_CENTRE",
    "RETAILER",
    "AUTHORITY",
    "ADMIN"
])
def test_create_organization_all_valid_types(org_type):
    """Stress-test organization creation across all 5 valid enum types."""
    rand_id = uuid.uuid4().hex[:8]
    org_payload = {
        "name": f"Stress Org {org_type} {rand_id}",
        "org_type": org_type,
        "registration_number": f"REG-{org_type[:3]}-{rand_id}",
        "contact_phone": "+91 98765 43210",
        "contact_email": f"contact_{rand_id}@{org_type.lower()}.org",
        "address": f"Plot {rand_id}, Industrial Corridor",
        "district": "Warangal",
        "state": "Telangana"
    }

    resp = client.post("/api/v1/platform/admin/organizations", json=org_payload)
    assert resp.status_code == 200, f"Failed for org_type {org_type}: {resp.text}"
    data = resp.json()
    assert data["status"] == "SUCCESS"
    org = data["organization"]
    assert org["name"] == org_payload["name"]
    assert org["org_type"] == org_type
    assert org["district"] == "Warangal"
    assert org["state"] == "Telangana"
    assert org["is_active"] is True
    assert "id" in org

    # Verify presence in GET /platform/admin/organizations
    list_resp = client.get("/api/v1/platform/admin/organizations")
    assert list_resp.status_code == 200
    all_orgs = list_resp.json()
    matched = [o for o in all_orgs if o["id"] == org["id"]]
    assert len(matched) == 1
    assert matched[0]["name"] == org_payload["name"]
    assert matched[0]["org_type"] == org_type
    assert "member_count" in matched[0]


def test_create_organization_duplicate_name_rejected_400():
    """Duplicate organization name must be rejected with HTTP 400."""
    rand_id = uuid.uuid4().hex[:8]
    org_payload = {
        "name": f"Duplicate Test Org {rand_id}",
        "org_type": "TRANSPORTER",
        "registration_number": f"REG-DUP-{rand_id}"
    }

    # First creation should succeed
    resp1 = client.post("/api/v1/platform/admin/organizations", json=org_payload)
    assert resp1.status_code == 200

    # Second creation with identical name must fail with HTTP 400
    resp2 = client.post("/api/v1/platform/admin/organizations", json=org_payload)
    assert resp2.status_code == 400
    assert f"already exists" in resp2.json()["detail"].lower()


def test_create_organization_missing_name_rejected_422():
    """Missing required 'name' field must be rejected with HTTP 422 Unprocessable Entity."""
    payload = {
        "org_type": "RETAILER",
        "registration_number": "REG-MISSING-NAME"
    }
    resp = client.post("/api/v1/platform/admin/organizations", json=payload)
    assert resp.status_code == 422


def test_create_organization_missing_org_type_rejected_422():
    """Missing required 'org_type' field must be rejected with HTTP 422 Unprocessable Entity."""
    payload = {
        "name": f"Missing Type Org {uuid.uuid4().hex[:6]}"
    }
    resp = client.post("/api/v1/platform/admin/organizations", json=payload)
    assert resp.status_code == 422


def test_create_organization_invalid_org_type_enum_rejected_422():
    """Invalid org_type outside allowed Literal enum must be rejected with HTTP 422."""
    payload = {
        "name": f"Invalid Enum Org {uuid.uuid4().hex[:6]}",
        "org_type": "INVALID_TYPE_XYZ"
    }
    resp = client.post("/api/v1/platform/admin/organizations", json=payload)
    assert resp.status_code == 422


def test_create_organization_empty_whitespace_name_rejected_400():
    """Empty or all-whitespace organization name must be rejected with HTTP 400."""
    payload = {
        "name": "   ",
        "org_type": "TRANSPORTER"
    }
    resp = client.post("/api/v1/platform/admin/organizations", json=payload)
    assert resp.status_code == 400
    assert "required" in resp.json()["detail"].lower()


# ============================================================================
# 2. USER-TO-ORGANIZATION BINDING STRESS TESTS
# ============================================================================

def test_user_creation_with_valid_organization_binding():
    """Valid user creation with valid organization_id binds successfully."""
    rand_id = uuid.uuid4().hex[:8]

    # Create an organization first
    org_resp = client.post("/api/v1/platform/admin/organizations", json={
        "name": f"Binding Target Org {rand_id}",
        "org_type": "COLLECTION_CENTRE"
    })
    assert org_resp.status_code == 200
    org_id = org_resp.json()["organization"]["id"]

    # Create user bound to this organization
    user_payload = {
        "username": f"bound_user_{rand_id}",
        "email": f"bound_{rand_id}@praman.org",
        "password": "StrongPassword@2026",
        "full_name": f"Bound User {rand_id}",
        "role": "COLLECTION_CENTRE",
        "organization_id": org_id
    }
    user_resp = client.post("/api/v1/platform/admin/users", json=user_payload)
    assert user_resp.status_code == 200
    u_data = user_resp.json()
    assert u_data["status"] == "SUCCESS"
    assert u_data["username"] == user_payload["username"]
    assert u_data["organization_id"] == org_id
    assert u_data["organization_name"] == f"Binding Target Org {rand_id}"

    # Verify user appears under dashboard metrics and users table
    dash_resp = client.get("/api/v1/platform/admin/dashboard")
    assert dash_resp.status_code == 200
    dash_users = dash_resp.json()["users"]
    found_user = [u for u in dash_users if u["id"] == u_data["id"]]
    assert len(found_user) == 1
    assert found_user[0]["organization_id"] == org_id
    assert found_user[0]["organization"] == f"Binding Target Org {rand_id}"


def test_user_creation_nonexistent_organization_rejected_400():
    """Non-existent organization_id must be rejected with HTTP 400."""
    fake_org_id = f"nonexistent-org-{uuid.uuid4().hex}"
    user_payload = {
        "username": f"orphan_user_{uuid.uuid4().hex[:6]}",
        "email": f"orphan_{uuid.uuid4().hex[:6]}@praman.org",
        "password": "StrongPassword@2026",
        "full_name": "Orphan User",
        "role": "TRANSPORTER",
        "organization_id": fake_org_id
    }
    resp = client.post("/api/v1/platform/admin/users", json=user_payload)
    assert resp.status_code == 400
    assert "not found" in resp.json()["detail"].lower()


def test_user_creation_duplicate_username_rejected_400():
    """Duplicate username must be rejected with HTTP 400."""
    rand_id = uuid.uuid4().hex[:8]
    user_payload = {
        "username": f"dup_user_{rand_id}",
        "email": f"dup_{rand_id}@praman.org",
        "password": "StrongPassword@2026",
        "full_name": "Duplicate User Test",
        "role": "RETAILER"
    }

    # First user succeeds
    r1 = client.post("/api/v1/platform/admin/users", json=user_payload)
    assert r1.status_code == 200

    # Second user with same username must fail with HTTP 400
    user_payload2 = {
        "username": f"dup_user_{rand_id}",
        "email": f"diff_email_{rand_id}@praman.org",
        "password": "StrongPassword@2026",
        "full_name": "Different Full Name",
        "role": "RETAILER"
    }
    r2 = client.post("/api/v1/platform/admin/users", json=user_payload2)
    assert r2.status_code == 400
    assert "already exists" in r2.json()["detail"].lower()


def test_user_creation_duplicate_email_rejected_400():
    """Duplicate email must be rejected with HTTP 400."""
    rand_id = uuid.uuid4().hex[:8]
    email = f"shared_email_{rand_id}@praman.org"

    user1 = {
        "username": f"first_user_{rand_id}",
        "email": email,
        "password": "StrongPassword@2026",
        "full_name": "First User",
        "role": "RETAILER"
    }
    r1 = client.post("/api/v1/platform/admin/users", json=user1)
    assert r1.status_code == 200

    user2 = {
        "username": f"second_user_{rand_id}",
        "email": email,
        "password": "StrongPassword@2026",
        "full_name": "Second User",
        "role": "RETAILER"
    }
    r2 = client.post("/api/v1/platform/admin/users", json=user2)
    assert r2.status_code == 400, f"Expected 400 for duplicate email, got {r2.status_code}: {r2.text}"
    assert "email" in r2.json()["detail"].lower()


# ============================================================================
# 3. SYSTEM HEALTH TELEMETRY TESTS
# ============================================================================

def test_system_health_telemetry_schema_and_authenticity():
    """Verify /api/v1/health response schema and dynamic real telemetry."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()

    # Core health status
    assert data["status"] in ("HEALTHY", "DEGRADED")
    assert "version" in data
    assert data["database"] in ("CONNECTED", "DISCONNECTED")
    assert data["storage"] in ("READY", "ERROR")
    assert data["ai_dispatcher"] in ("RUNNING", "IDLE")

    # Subsystem components
    assert "components" in data
    comp = data["components"]

    # Database component
    assert "database" in comp
    db_c = comp["database"]
    assert db_c["status"] in ("UP", "DOWN")
    assert db_c["port"] == 1234
    assert db_c["database"] == "praman"

    # Storage component
    assert "storage" in comp
    st_c = comp["storage"]
    assert st_c["status"] in ("UP", "DOWN")
    assert "base_dir" in st_c
    assert isinstance(st_c["writable"], bool)

    # AI dispatcher component
    assert "ai_dispatcher" in comp
    ai_c = comp["ai_dispatcher"]
    assert "queue_depth" in ai_c


def test_admin_dashboard_metrics_and_health_integration():
    """Verify Platform Admin dashboard returns live dynamic metrics."""
    dash_resp = client.get("/api/v1/platform/admin/dashboard")
    assert dash_resp.status_code == 200
    data = dash_resp.json()

    assert "metrics" in data
    metrics = data["metrics"]
    assert "total_users" in metrics
    assert "total_organizations" in metrics
    assert "total_evidence_records" in metrics
    assert metrics["total_users"] > 0
    assert metrics["total_organizations"] > 0

    assert "users" in data
    assert len(data["users"]) == metrics["total_users"]

    assert "organizations" in data
    assert len(data["organizations"]) == metrics["total_organizations"]
