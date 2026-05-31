from collections.abc import Generator

from fastapi.testclient import TestClient

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.main import app
from app.models.admin import Admin
from app.models.category import Category
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
    """用于后台分类接口测试的轻量会话，避免依赖真实 PostgreSQL。"""

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
            if isinstance(entity, Category) and entity.id is None:
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


def test_admin_categories_requires_login() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/admin/categories")

    assert response.status_code == 401


def test_list_admin_categories_returns_all_statuses() -> None:
    session = FakeSession(
        [
            [
                Category(id=1, name="绘画", description="绘画分类", parent_id=None, sort_order=1, status="active"),
                Category(id=2, name="隐藏分类", description=None, parent_id=None, sort_order=2, status="hidden"),
            ]
        ]
    )
    _override_dependencies(session)
    client = TestClient(app)

    response = client.get("/api/v1/admin/categories")

    _clear_overrides()
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 2
    assert response.json()["data"]["items"][1]["status"] == "hidden"


def test_create_admin_category_writes_operation_log() -> None:
    session = FakeSession()
    _override_dependencies(session)
    client = TestClient(app)

    response = client.post(
        "/api/v1/admin/categories",
        json={"name": " 油画 ", "description": " 以油彩为主要媒介 ", "parent_id": None, "sort_order": 3, "status": "active"},
    )

    _clear_overrides()
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "油画"
    assert response.json()["data"]["description"] == "以油彩为主要媒介"
    assert session.committed is True
    assert any(
        isinstance(entity, OperationLog) and entity.action == "create_category"
        for entity in session.added
    )


def test_get_admin_category_returns_detail() -> None:
    session = FakeSession(
        [Category(id=1, name="绘画", description="绘画分类", parent_id=None, sort_order=1, status="active")]
    )
    _override_dependencies(session)
    client = TestClient(app)

    response = client.get("/api/v1/admin/categories/1")

    _clear_overrides()
    assert response.status_code == 200
    assert response.json()["data"] == {
        "id": 1,
        "name": "绘画",
        "description": "绘画分类",
        "parent_id": None,
        "sort_order": 1,
        "status": "active",
    }


def test_update_admin_category_can_clear_parent_description_and_writes_operation_log() -> None:
    category = Category(id=2, name="油画", description="旧描述", parent_id=1, sort_order=1, status="active")
    session = FakeSession([category])
    _override_dependencies(session)
    client = TestClient(app)

    response = client.patch("/api/v1/admin/categories/2", json={"parent_id": None, "description": None})

    _clear_overrides()
    assert response.status_code == 200
    assert response.json()["data"]["parent_id"] is None
    assert response.json()["data"]["description"] is None
    assert category.parent_id is None
    assert category.description is None
    assert session.committed is True
    assert any(
        isinstance(entity, OperationLog) and entity.action == "update_category"
        for entity in session.added
    )


def test_delete_admin_category_rejects_child_category() -> None:
    category = Category(id=1, name="绘画", description=None, parent_id=None, sort_order=1, status="active")
    session = FakeSession([category, True])
    _override_dependencies(session)
    client = TestClient(app)

    response = client.delete("/api/v1/admin/categories/1")

    _clear_overrides()
    assert response.status_code == 400
    assert response.json()["detail"] == "分类下存在子分类，不能删除"
    assert session.deleted == []
    assert session.committed is False


def test_delete_admin_category_writes_operation_log() -> None:
    category = Category(id=1, name="绘画", description="绘画分类", parent_id=None, sort_order=1, status="active")
    session = FakeSession([category, False, False])
    _override_dependencies(session)
    client = TestClient(app)

    response = client.delete("/api/v1/admin/categories/1")

    _clear_overrides()
    assert response.status_code == 200
    assert response.json()["data"] == {"id": 1}
    assert session.deleted == [category]
    assert session.committed is True
    assert any(
        isinstance(entity, OperationLog) and entity.action == "delete_category"
        for entity in session.added
    )
