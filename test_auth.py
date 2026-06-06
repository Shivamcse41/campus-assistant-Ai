"""
test_auth.py
─────────────
End-to-end test for Task 2 JWT authentication.
Run with: .venv\Scripts\python.exe test_auth.py
"""
import urllib.request
import json
import sys

BASE = "http://localhost:8000"


def post(path, data):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        r = urllib.request.urlopen(req)
        return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code


def get_with_token(path, token):
    req = urllib.request.Request(
        BASE + path,
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        r = urllib.request.urlopen(req)
        return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code


def get_no_token(path):
    req = urllib.request.Request(BASE + path)
    try:
        r = urllib.request.urlopen(req)
        return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code


passed = 0
failed = 0


def check(label, condition, got):
    global passed, failed
    status = "PASS" if condition else "FAIL"
    if condition:
        passed += 1
    else:
        failed += 1
    print(f"  [{status}] {label}")
    if not condition:
        print(f"         Got: {got}")


print()
print("=" * 55)
print("  CampConnect SaaS — Task 2 Auth Test Suite")
print("=" * 55)

# ── TEST 1: Register ──────────────────────────────────────────
print("\nTEST 1: POST /auth/register")
res, code = post("/auth/register", {
    "business_name": "Test Corp",
    "email": "testcorp@campconnect.dev",
    "password": "secret123",
})
check("Status 201 Created", code == 201, code)
check("Has client_id", "client_id" in res, res)
check("Has business_name", res.get("business_name") == "Test Corp", res)
client_id = res.get("client_id", "")
print(f"  client_id: {client_id}")

# ── TEST 2: Duplicate registration ────────────────────────────
print("\nTEST 2: POST /auth/register (duplicate email)")
res2, code2 = post("/auth/register", {
    "business_name": "Dupe Corp",
    "email": "testcorp@campconnect.dev",
    "password": "secret123",
})
check("Status 409 Conflict", code2 == 409, code2)

# ── TEST 3: Login ─────────────────────────────────────────────
print("\nTEST 3: POST /auth/login")
res3, code3 = post("/auth/login", {
    "email": "testcorp@campconnect.dev",
    "password": "secret123",
})
check("Status 200 OK", code3 == 200, code3)
check("Has access_token", "access_token" in res3, res3)
check("token_type is bearer", res3.get("token_type") == "bearer", res3)
check("client_id matches", res3.get("client_id") == client_id, res3)
token = res3.get("access_token", "")
print(f"  Token preview: {token[:50]}...")

# ── TEST 4: Wrong password ────────────────────────────────────
print("\nTEST 4: POST /auth/login (wrong password)")
res4, code4 = post("/auth/login", {
    "email": "testcorp@campconnect.dev",
    "password": "wrongpassword",
})
check("Status 401 Unauthorized", code4 == 401, code4)

# ── TEST 5: GET /auth/me (with token) ────────────────────────
print("\nTEST 5: GET /auth/me (with valid token)")
res5, code5 = get_with_token("/auth/me", token)
check("Status 200 OK", code5 == 200, code5)
check("Email matches", res5.get("email") == "testcorp@campconnect.dev", res5)
check("client_id matches", res5.get("client_id") == client_id, res5)

# ── TEST 6: Protected route without token ────────────────────
print("\nTEST 6: GET /api/clients (NO token)")
res6, code6 = get_no_token("/api/clients")
check("Status 403 Forbidden", code6 == 403, code6)

# ── TEST 7: Protected route WITH token ───────────────────────
print("\nTEST 7: GET /api/clients (with valid token)")
res7, code7 = get_with_token("/api/clients", token)
check("Status 200 OK", code7 == 200, code7)
check("Returns list", isinstance(res7, list), type(res7))

# ── TEST 8: Invalid/tampered token ───────────────────────────
print("\nTEST 8: GET /api/clients (invalid/tampered token)")
res8, code8 = get_with_token("/api/clients", token + "tampered")
check("Status 403 Forbidden", code8 == 403, code8)

# ── Summary ───────────────────────────────────────────────────
print()
print("=" * 55)
print(f"  Results: {passed} passed, {failed} failed")
print("=" * 55)
print()

sys.exit(0 if failed == 0 else 1)
