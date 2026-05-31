from collections.abc import Generator

from fastapi.testclient import TestClient

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.main import app
from app.models.admin import Admin
from app.models.artwork import Artwork


class _ExecuteResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar(self) -> object:
        return self._value

    def all(self) -> list[object]:
        return self._value if isinstance(self._value, list) else []


class FakeSession:
    """用于后台工作台接口测试的轻量会话，避免依赖真实 PostgreSQL。"""

    def __init__(self, execute_results: list[object]) -> None:
        self.execute_results = execute_results

    def execute(self, statement: object) -> _ExecuteResult:
        return _ExecuteResult(self.execute_results.pop(0))


def _build_admin() -> Admin:
    return Admin(id=1, username="admin", password_hash="hash", role="super_admin", status="active")


def _override_dependencies(session: FakeSession) -> None:
    def get_test_db() -> Generator[FakeSession, None, None]:
        yield session

    def get_test_admin() -> Admin:
        return _build_admin()

    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_admin] = get_test_admin


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_admin_dashboard_requires_login() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/admin/dashboard")

    assert response.status_code == 401


def test_admin_dashboard_returns_counts_and_recent_artworks() -> None:
    recent_rows = [
        (
            Artwork(
                id=index,
                title=f"作品 {index}",
                artist_id=1,
                cover_url=None,
                material="布面油画",
                creation_year=2024,
                status="published",
            ),
            "林微",
        )
        for index in range(1, 6)
    ]
    session = FakeSession([12, 4, 6, 1, 2, recent_rows])
    _override_dependencies(session)
    client = TestClient(app)

    response = client.get("/api/v1/admin/dashboard")

    _clear_overrides()
    assert response.status_code == 200
    assert response.json()["data"]["public_artwork_count"] == 12
    assert response.json()["data"]["artist_count"] == 4
    assert response.json()["data"]["category_count"] == 6
    assert response.json()["data"]["hidden_count"] == 3
    assert len(response.json()["data"]["recent_artworks"]) == 5
    assert response.json()["data"]["recent_artworks"][0]["artist_name"] == "林微"
