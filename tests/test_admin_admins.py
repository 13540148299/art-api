from collections.abc import Generator

from fastapi.testclient import TestClient

from app.api.deps import get_current_super_admin
from app.db.session import get_db
from app.main import app
from app.models.admin import Admin


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value

    def all(self) -> list[object]:
        return self._value if isinstance(self._value, list) else []


class _ScalarsResult:
    def __init__(self, value: list[object]) -> None:
        self._value = value

    def all(self) -> list[object]:
        return self._value


class _ExecuteResult(_ScalarResult):
    def scalars(self) -> _ScalarsResult:
        return _ScalarsResult(self._value if isinstance(self._value, list) else [])


class FakeSession:
    """用于管理员管理接口测试的轻量会话，避免依赖真实 PostgreSQL。"""

    def __init__(self, execute_results: list[object]) -> None:
        self.execute_results = execute_results
        self.added: list[object] = []
        self.committed = False
        self.rolled_back = False

    def execute(self, statement: object) -> _ExecuteResult:
        return _ExecuteResult(self.execute_results.pop(0))

    def add(self, entity: object) -> None:
        self.added.append(entity)

    def flush(self) -> None:
        for entity in self.added:
            if isinstance(entity, Admin) and entity.id is None:
                entity.id = 2

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def refresh(self, entity: object) -> None:
        return None


def _build_super_admin() -> Admin:
    return Admin(
        id=1,
        username="root",
        avatar_url=None,
        password_hash="hash",
        role="super_admin",
        status="active",
        must_change_password=False,
    )


def _override_dependencies(session: FakeSession) -> None:
    def get_test_db() -> Generator[FakeSession, None, None]:
        yield session

    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_super_admin] = _build_super_admin


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_super_admin_lists_operator_admins() -> None:
    operator = Admin(
        id=2,
        username="operator",
        avatar_url=None,
        password_hash="hash",
        role="operator",
        status="active",
        must_change_password=True,
    )
    session = FakeSession([[operator]])
    _override_dependencies(session)
    client = TestClient(app)

    response = client.get("/api/v1/admin/admins")

    _clear_overrides()
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1
    assert response.json()["data"]["items"][0]["username"] == "operator"
    assert response.json()["data"]["items"][0]["must_change_password"] is True


def test_super_admin_creates_operator_with_initial_password_flag() -> None:
    session = FakeSession([None])
    _override_dependencies(session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/admin/admins",
        json={"username": "operator", "password": "initial123", "status": "active"},
    )

    _clear_overrides()
    assert response.status_code == 200
    assert response.json()["data"]["role"] == "operator"
    assert response.json()["data"]["must_change_password"] is True
    created_admin = next(entity for entity in session.added if isinstance(entity, Admin))
    assert created_admin.username == "operator"
    assert created_admin.must_change_password is True
    assert session.committed is True
