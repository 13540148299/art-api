from collections.abc import Generator

from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.main import app
from app.models.admin import Admin
from app.models.operation_log import OperationLog


class _ScalarResult:
    def __init__(self, admin: Admin | None) -> None:
        self._admin = admin

    def scalar_one_or_none(self) -> Admin | None:
        return self._admin


class FakeSession:
    """用于登录接口测试的轻量会话，避免依赖真实 PostgreSQL。"""

    def __init__(self, admin: Admin | None, execute_results: list[Admin | None] | None = None) -> None:
        self.admin = admin
        self.execute_results = execute_results or []
        self.added: list[object] = []
        self.committed = False
        self.rolled_back = False

    def execute(self, statement: object) -> _ScalarResult:
        if self.execute_results:
            return _ScalarResult(self.execute_results.pop(0))
        return _ScalarResult(self.admin)

    def add(self, entity: object) -> None:
        self.added.append(entity)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def _override_db(session: FakeSession) -> None:
    def get_test_db() -> Generator[FakeSession, None, None]:
        yield session

    app.dependency_overrides[get_db] = get_test_db


def _build_admin(status: str = "active") -> Admin:
    return Admin(
        id=1,
        username="admin",
        avatar_url=None,
        password_hash=get_password_hash("correct-password"),
        role="super_admin",
        status=status,
    )


def test_admin_login_success() -> None:
    session = FakeSession(_build_admin())
    _override_db(session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "correct-password"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["admin_username"] == "admin"
    token_payload = jwt.decode(
        body["data"]["access_token"],
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    assert token_payload["sub"] == "1"
    assert token_payload["role"] == "super_admin"
    assert session.admin is not None
    assert session.admin.last_login_at is not None
    assert session.committed is True
    assert any(isinstance(entity, OperationLog) for entity in session.added)


def test_admin_login_rejects_wrong_password() -> None:
    session = FakeSession(_build_admin())
    _override_db(session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 401
    assert response.json()["detail"] == "账号或密码错误"
    assert session.committed is False
    assert session.added == []


def test_admin_login_rejects_disabled_admin() -> None:
    session = FakeSession(_build_admin(status="disabled"))
    _override_db(session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "correct-password"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 403
    assert response.json()["detail"] == "管理员账号已被禁用"
    assert session.committed is False


def test_admin_me_returns_current_admin() -> None:
    session = FakeSession(_build_admin())
    _override_db(session)
    client = TestClient(app)
    token = create_access_token(subject="1", claims={"role": "super_admin"})

    response = client.get(
        "/api/v1/admin/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["data"] == {
        "id": 1,
        "username": "admin",
        "avatar_url": None,
        "role": "super_admin",
        "status": "active",
        "must_change_password": False,
    }


def test_admin_update_me_updates_profile_and_password() -> None:
    admin = _build_admin()
    session = FakeSession(admin, execute_results=[admin, None])
    _override_db(session)
    client = TestClient(app)
    token = create_access_token(subject="1", claims={"role": "super_admin"})

    response = client.patch(
        "/api/v1/admin/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": "operator",
            "avatar_url": "/uploads/avatars/admin.png",
            "current_password": "correct-password",
            "new_password": "new-password",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["data"]["username"] == "operator"
    assert response.json()["data"]["avatar_url"] == "/uploads/avatars/admin.png"
    assert response.json()["data"]["must_change_password"] is False
    assert admin.username == "operator"
    assert admin.avatar_url == "/uploads/avatars/admin.png"
    assert verify_password("new-password", admin.password_hash)
    assert session.committed is True
    assert any(isinstance(entity, OperationLog) for entity in session.added)


def test_admin_update_me_rejects_wrong_current_password() -> None:
    admin = _build_admin()
    session = FakeSession(admin, execute_results=[admin])
    _override_db(session)
    client = TestClient(app)
    token = create_access_token(subject="1", claims={"role": "super_admin"})

    response = client.patch(
        "/api/v1/admin/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "wrong-password", "new_password": "new-password"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert response.json()["detail"] == "当前密码不正确"
    assert session.committed is False


def test_admin_update_me_clears_initial_password_flag() -> None:
    admin = _build_admin()
    admin.must_change_password = True
    session = FakeSession(admin, execute_results=[admin])
    _override_db(session)
    client = TestClient(app)
    token = create_access_token(subject="1", claims={"role": "operator"})

    response = client.patch(
        "/api/v1/admin/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "correct-password", "new_password": "new-password"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["data"]["must_change_password"] is False
    assert admin.must_change_password is False


def test_admin_me_rejects_missing_token() -> None:
    session = FakeSession(_build_admin())
    _override_db(session)
    client = TestClient(app)

    response = client.get("/api/v1/admin/auth/me")

    app.dependency_overrides.clear()
    assert response.status_code == 401


def test_admin_me_rejects_invalid_token() -> None:
    session = FakeSession(_build_admin())
    _override_db(session)
    client = TestClient(app)

    response = client.get(
        "/api/v1/admin/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 401
    assert response.json()["detail"] == "登录凭证无效或已过期"


def test_admin_me_rejects_disabled_admin() -> None:
    session = FakeSession(_build_admin(status="disabled"))
    _override_db(session)
    client = TestClient(app)
    token = create_access_token(subject="1", claims={"role": "super_admin"})

    response = client.get(
        "/api/v1/admin/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 403
    assert response.json()["detail"] == "管理员账号已被禁用"
