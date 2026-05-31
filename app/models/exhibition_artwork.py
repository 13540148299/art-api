from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ExhibitionArtwork(Base):
    """展览专题与作品关联表。

    ERD 关系：
    - exhibitions 与 artworks 是多对多关系。
    - 本表保存专题下包含哪些作品，以及作品在专题里的展示顺序。
    """

    __tablename__ = "exhibition_artworks"
    __table_args__ = (
        UniqueConstraint("exhibition_id", "artwork_id", name="uq_exhibition_artworks_pair"),
    )

    # 关联记录主键。
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # 专题 ID。
    exhibition_id: Mapped[int] = mapped_column(ForeignKey("exhibitions.id"), index=True)

    # 作品 ID。
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id"), index=True)

    # 作品在专题中的排序权重。
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
