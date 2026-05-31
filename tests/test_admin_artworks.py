from collections.abc import Generator

from fastapi.testclient import TestClient

from app.api.deps import get_current_admin
from app.api.v1.endpoints.artworks import _build_artwork_filters
from app.db.session import get_db
from app.main import app
from app.models.admin import Admin
from app.models.artwork import Artwork
from app.models.operation_log import OperationLog


class _ExecuteResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar(self) -> object:
        return self._value

    def scalar_one_or_none(self) -> object | None:
        return self._value

    def one(self) -> object:
        return self._value

    def all(self) -> list[object]:
        return self._value if isinstance(self._value, list) else []


class FakeSession:
    """用于后台作品概览接口测试的轻量会话，避免依赖真实 PostgreSQL。"""

    def __init__(self, execute_results: list[object]) -> None:
        self.execute_results = execute_results
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
            if isinstance(entity, Artwork) and entity.id is None:
                entity.id = 10

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


def test_admin_artworks_requires_login() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/admin/artworks")

    assert response.status_code == 401


def test_keyword_filter_matches_title_artist_category_and_year() -> None:
    filters = _build_artwork_filters("2024", None, None, None)

    compiled_filter = str(filters[0].compile(compile_kwargs={"literal_binds": True}))
    assert "artworks.title" in compiled_filter
    assert "artists.name" in compiled_filter
    assert "categories.name" in compiled_filter
    assert "artworks.creation_year" in compiled_filter
    assert " OR " in compiled_filter


def test_list_admin_artworks_returns_paged_media_overview() -> None:
    session = FakeSession(
        [
            2,
            [
                (
                    Artwork(
                        id=1,
                        title="山水 No.1",
                        description="水墨作品",
                        artist_id=1,
                        category_id=1,
                        cover_url="/uploads/artworks/cover.jpg",
                        media_type="image",
                        media_url=None,
                        material="纸本水墨",
                        creation_year=2024,
                        status="published",
                        is_featured=False,
                        sort_order=0,
                        view_count=0,
                        like_count=0,
                        published_at=None,
                    ),
                    "林微",
                    "水墨",
                ),
                (
                    Artwork(
                        id=2,
                        title="Video Study",
                        description="影像作品",
                        artist_id=2,
                        category_id=2,
                        cover_url="/uploads/artworks/video-cover.jpg",
                        media_type="video",
                        media_url="/uploads/artworks/video.mp4",
                        material=None,
                        creation_year=2025,
                        status="draft",
                        is_featured=False,
                        sort_order=0,
                        view_count=0,
                        like_count=0,
                        published_at=None,
                    ),
                    "Chen Yu",
                    "影像",
                ),
            ],
        ]
    )
    _override_dependencies(session)
    client = TestClient(app)

    response = client.get(
        "/api/v1/admin/artworks",
        params={"page": 1, "page_size": 20, "keyword": "Study", "artist": "Chen", "category": "影像", "year": 2025},
    )

    app.dependency_overrides.clear()
    data = response.json()["data"]
    assert response.status_code == 200
    assert data["total"] == 2
    assert data["items"][0]["category_name"] == "水墨"
    assert data["items"][0]["display_url"] == "/uploads/artworks/cover.jpg"
    assert data["items"][1]["display_type"] == "video"
    assert data["items"][1]["display_url"] == "/uploads/artworks/video.mp4"


def test_create_admin_artwork_writes_operation_log() -> None:
    created_artwork_row = (
        Artwork(
            id=10,
            title="新作品",
            description="作品介绍",
            artist_id=1,
            category_id=2,
            cover_url="/uploads/artworks/new.jpg",
            media_type="image",
            media_url="/uploads/artworks/new.jpg",
            material="布面油画",
            creation_year=2026,
            status="draft",
            is_featured=False,
            sort_order=0,
            view_count=0,
            like_count=0,
            published_at=None,
        ),
        "林微",
        "油画",
    )
    session = FakeSession([1, 2, created_artwork_row])
    _override_dependencies(session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/admin/artworks",
        json={
            "title": " 新作品 ",
            "description": " 作品介绍 ",
            "artist_id": 1,
            "category_id": 2,
            "media_type": "image",
            "media_url": "/uploads/artworks/new.jpg",
            "material": " 布面油画 ",
            "creation_year": 2026,
            "status": "draft",
            "sort_order": 0,
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "新作品"
    assert session.committed is True
    assert any(isinstance(entity, OperationLog) and entity.action == "create_artwork" for entity in session.added)


def test_update_admin_artwork_can_publish() -> None:
    artwork = Artwork(
        id=1,
        title="旧作品",
        description=None,
        artist_id=None,
        category_id=None,
        cover_url=None,
        media_type="image",
        media_url=None,
        material=None,
        creation_year=None,
        status="draft",
        is_featured=False,
        sort_order=0,
        view_count=0,
        like_count=0,
        published_at=None,
    )
    updated_artwork_row = (
        artwork,
        "林微",
        "油画",
    )
    session = FakeSession([artwork, 1, 2, updated_artwork_row])
    _override_dependencies(session)
    client = TestClient(app)

    response = client.patch(
        "/api/v1/admin/artworks/1",
        json={"title": "已上架作品", "artist_id": 1, "category_id": 2, "status": "published"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert artwork.title == "已上架作品"
    assert artwork.status == "published"
    assert artwork.published_at is not None
    assert session.committed is True
    assert any(isinstance(entity, OperationLog) and entity.action == "update_artwork" for entity in session.added)


def test_delete_admin_artwork_writes_operation_log() -> None:
    artwork = Artwork(
        id=1,
        title="待删除作品",
        description=None,
        artist_id=None,
        category_id=None,
        cover_url=None,
        media_type="image",
        media_url=None,
        material=None,
        creation_year=None,
        status="draft",
        is_featured=False,
        sort_order=0,
        view_count=0,
        like_count=0,
        published_at=None,
    )
    session = FakeSession([artwork])
    _override_dependencies(session)
    client = TestClient(app)

    response = client.delete("/api/v1/admin/artworks/1")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["data"] == {"id": 1}
    assert session.deleted == [artwork]
    assert session.committed is True
    assert any(isinstance(entity, OperationLog) and entity.action == "delete_artwork" for entity in session.added)
