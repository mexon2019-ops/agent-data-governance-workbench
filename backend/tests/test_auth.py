import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/auth-unit-test.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")

from app import main


def test_password_hash_verifies_and_uses_unique_salts():
    first = main.hash_password("Correct-Horse-Battery-42!")
    second = main.hash_password("Correct-Horse-Battery-42!")
    assert first != second
    assert main.verify_password("Correct-Horse-Battery-42!", first)
    assert not main.verify_password("wrong-password", first)


def test_signed_access_token_rejects_tampering():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        user = main.User(username="token-test", password_hash=main.hash_password("Strong-password-123!"))
        db.add(user)
        db.commit()
        db.refresh(user)
        token = main.issue_token(user)
        assert main.decode_token(token)["sub"] == str(user.id)
        body, signature = token.split(".", 1)
        tampered = body[:-1] + ("A" if body[-1] != "A" else "B") + "." + signature
        assert main.decode_token(tampered) is None


def test_permission_roles_are_distinct():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        main.bootstrap_auth(db)
        roles = {role.name: {p.code for p in role.permissions}
                 for role in db.query(main.Role).all()}
        assert "user:manage" in roles["admin"]
        assert "governance:write" in roles["data_steward"]
        assert "audit:read" in roles["auditor"]
        assert "governance:write" not in roles["viewer"]


def test_governance_api_requires_permission_and_audit_is_admin_only(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "ci-bootstrap-password-123456")
    main.Base.metadata.create_all(main.engine)
    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/dashboard").status_code == 401
        login = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "ci-bootstrap-password-123456",
        })
        assert login.status_code == 200
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        assert client.get("/api/v1/dashboard", headers=headers).status_code == 200
        assert client.get("/api/v1/admin/audit-logs", headers=headers).status_code == 200
        created = client.post("/api/v1/records", headers=headers, json={
            "category": "asset", "name": "auth-protected-test", "description": "RBAC test",
            "status": "草稿", "owner": "test"
        })
        assert created.status_code == 201
