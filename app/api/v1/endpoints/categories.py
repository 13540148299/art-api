from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.category import Category
from app.schemas.category import CategoryListResponse, CategoryNode
from app.schemas.common import ApiResponse

router = APIRouter()


@router.get("", response_model=ApiResponse[CategoryListResponse])
def list_categories(db: Session = Depends(get_db)) -> ApiResponse[CategoryListResponse]:
    """查询小程序作品分类树。

    公开端只展示启用状态的分类，隐藏分类不会返回，避免前端误展示未开放的筛选项。
    """
    categories = (
        db.execute(
            select(Category)
            .where(Category.status == "active")
            .order_by(Category.sort_order.asc(), Category.id.asc())
        )
        .scalars()
        .all()
    )

    node_map = {
        category.id: CategoryNode(
            id=category.id,
            name=category.name,
            description=category.description,
            parent_id=category.parent_id,
            sort_order=category.sort_order,
        )
        for category in categories
    }

    roots: list[CategoryNode] = []
    for category in categories:
        node = node_map[category.id]
        parent = node_map.get(category.parent_id) if category.parent_id is not None else None
        if parent is None:
            roots.append(node)
            continue

        parent.children.append(node)

    return ApiResponse(data=CategoryListResponse(items=roots))
