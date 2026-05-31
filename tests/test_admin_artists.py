from collections.abc import Generator

from fastapi.testclient import TestClient

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.main import app
from app.models.admin import Admin
from app.models.artist import Artist
from app.models.operation_log import OperationLog


class _ScalarRows:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class _ExecuteResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value

    def scalars(self) -> _ScalarRows:
        return _ScalarRows(self._value if isinstance(self._value, list) else [])

    def scalar(self) -> object:
        return self._value


class FakeSession:
    """用于后台艺术家接口测试的轻量会话，避免依赖真实 PostgreSQL。"""

    def __init__(self, execute_results: list[object] | None = None) -> None:
        self.execute_results = execute_results or []
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.committed = False
        self.rolled_back = False

    def execute(self, statement: object) -> _ExecuteResult:
        return _ExecuteResult(self.execute_results.pop(0))

    def add(self, entity: object) -> None:
        self.added.append(entity)

    def delete(self, entity: object) -> None:
        self.deleted.append(entity)

    def flush(self) -> None:
        for entity in self.added:
            if isinstance(entity, Artist) and entity.id is None:
                entity.id = 10

    def refresh(self, entity: object) -> None:
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


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


def test_admin_artists_requires_login() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/admin/artists")

    assert response.status_code == 401


def test_list_admin_artists_returns_all_statuses() -> None:
    session = FakeSession(
        [
            [
                Artist(id=1, name="林微", avatar_url=None, bio=None, birth_year=1988, nationality="China", status="active"),
                Artist(id=2, name="陈宇", avatar_url=None, bio=None, birth_year=None, nationality=None, status="hidden"),
            ]
        ]
    )
    _override_dependencies(session)
    client = TestClient(app)

    response = client.get("/api/v1/admin/artists")

    _clear_overrides()
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 2
    assert response.json()["data"]["items"][1]["status"] == "hidden"


def test_create_admin_artist_writes_operation_log() -> None:
    session = FakeSession()
    _override_dependencies(session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/admin/artists",
        json={
            "name": " 林微 ",
            "avatar_url": "https://example.com/avatar.jpg",
            "bio": "艺术家简介",
            "birth_year": 1988,
            "nationality": "China",
            "status": "active",
        },
    )

    _clear_overrides()
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "林微"
    assert session.committed is True
    assert any(
        isinstance(entity, OperationLog) and entity.action == "create_artist"
        for entity in session.added
    )


def test_get_admin_artist_returns_detail() -> None:
    session = FakeSession(
        [Artist(id=1, name="林微", avatar_url=None, bio="简介", birth_year=1988, nationality="China", status="active")]
    )
    _override_dependencies(session)
    client = TestClient(app)

    response = client.get("/api/v1/admin/artists/1")

    _clear_overrides()
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "林微"
    assert response.json()["data"]["bio"] == "简介"


def test_update_admin_artist_can_clear_optional_fields_and_writes_operation_log() -> None:
    artist = Artist(
        id=1,
        name="林微",
        avatar_url="https://example.com/avatar.jpg",
        bio="简介",
        birth_year=1988,
        nationality="China",
        status="active",
    )
    session = FakeSession([artist])
    _override_dependencies(session)
    client = TestClient(app)

    response = client.patch("/api/v1/admin/artists/1", json={"avatar_url": None, "bio": None})

    _clear_overrides()
    assert response.status_code == 200
    assert response.json()["data"]["avatar_url"] is None
    assert artist.avatar_url is None
    assert artist.bio is None
    assert session.committed is True
    assert any(
        isinstance(entity, OperationLog) and entity.action == "update_artist"
        for entity in session.added
    )


def test_delete_admin_artist_rejects_related_artwork() -> None:
    artist = Artist(id=1, name="林微", avatar_url=None, bio=None, birth_year=None, nationality=None, status="active")
    session = FakeSession([artist, True])
    _override_dependencies(session)
    client = TestClient(app)

    response = client.delete("/api/v1/admin/artists/1")

    _clear_overrides()
    assert response.status_code == 400
    assert response.json()["detail"] == "艺术家下存在作品，不能删除"
    assert session.deleted == []
    assert session.committed is False


def test_delete_admin_artist_writes_operation_log() -> None:
    artist = Artist(id=1, name="林微", avatar_url=None, bio=None, birth_year=None, nationality=None, status="active")
    session = FakeSession([artist, False])
    _override_dependencies(session)
    client = TestClient(app)

    response = client.delete("/api/v1/admin/artists/1")

    _clear_overrides()
    assert response.status_code == 200
    assert response.json()["data"] == {"id": 1}
    assert session.deleted == [artist]
    assert session.committed is True
    assert any(
        isinstance(entity, OperationLog) and entity.action == "delete_artist"
        for entity in session.added
    )
