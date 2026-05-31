from pydantic import BaseModel

from app.schemas.artwork import ArtworkDetail


class AdminDashboardResponse(BaseModel):
    """后台工作台概览响应。"""

    # 已公开作品数量，仅统计 published 状态作品。
    public_artwork_count: int

    # 艺术家总数量。
    artist_count: int

    # 分类总数量。
    category_count: int

    # 隐藏数据数量，当前统计隐藏艺术家和隐藏分类。
    hidden_count: int

    # 最近公开作品，最多返回 5 条用于工作台概览。
    recent_artworks: list[ArtworkDetail]
