from collections.abc import Generator

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models.category import Category


class _ScalarResult:
    def __init__(self, categories: list[Category]) -> None:
        self._categories = categories

    def all(self) -> list[Category]:
        return self._categories


class _ExecuteResult:
    def __init__(self, categories: list[Category]) -> None:
        self._categories = categories

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self._categories)


class FakeSession:
    """用于分类接口测试的轻量会话，避免依赖真实 PostgreSQL。"""

    def __init__(self, categories: list[Category]) -> None:
        self.categories = categories

    def execute(self, statement: object) -> _ExecuteResult:
        return _ExecuteResult(self.categories)


def _override_db(session: FakeSession) -> None:
    def get_test_db() -> Generator[FakeSession, None, None]:
        yield session

    app.dependency_overrides[get_db] = get_test_db


def test_list_categories_returns_tree() -> None:
    session = FakeSession(
        [
            Category(id=1, name="绘画", description="绘画分类", parent_id=None, sort_order=1, status="active"),
            Category(id=2, name="油画", description="油画分类", parent_id=1, sort_order=1, status="active"),
            Category(id=3, name="雕塑", description=None, parent_id=None, sort_order=2, status="active"),
        ]
    )
    _override_db(session)
    client = TestClient(app)

    response = client.get("/api/v1/categories")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["data"]["items"] == [
        {
            "id": 1,
            "name": "绘画",
            "description": "绘画分类",
            "parent_id": None,
            "sort_order": 1,
            "children": [
                {
                    "id": 2,
                    "name": "油画",
                    "description": "油画分类",
                    "parent_id": 1,
                    "sort_order": 1,
                    "children": [],
                }
            ],
        },
        {
            "id": 3,
            "name": "雕塑",
            "description": None,
            "parent_id": None,
            "sort_order": 2,
            "children": [],
        },
    ]


def test_list_categories_handles_orphan_as_root() -> None:
    session = FakeSession(
        [
            Category(id=2, name="油画", description=None, parent_id=999, sort_order=1, status="active"),
        ]
    )
    _override_db(session)
    client = TestClient(app)

    response = client.get("/api/v1/categories")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["data"]["items"] == [
        {
            "id": 2,
            "name": "油画",
            "description": None,
            "parent_id": 999,
            "sort_order": 1,
            "children": [],
        }
    ]
