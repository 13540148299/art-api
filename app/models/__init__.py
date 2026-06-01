"""集中导入 ORM 模型，确保 Alembic 自动迁移能发现全部表。"""

from app.models.admin import Admin
from app.models.artist import Artist
from app.models.artwork import Artwork
from app.models.artwork_image import ArtworkImage
from app.models.artwork_like import ArtworkLike
from app.models.artwork_view import ArtworkView
from app.models.category import Category
from app.models.cart_item import CartItem
from app.models.exhibition import Exhibition
from app.models.exhibition_artwork import ExhibitionArtwork
from app.models.favorite import Favorite
from app.models.operation_log import OperationLog
from app.models.order import Order, OrderItem
from app.models.user import User

__all__ = [
    "Admin",
    "Artist",
    "Artwork",
    "ArtworkImage",
    "ArtworkLike",
    "ArtworkView",
    "Category",
    "CartItem",
    "Exhibition",
    "ExhibitionArtwork",
    "Favorite",
    "OperationLog",
    "Order",
    "OrderItem",
    "User",
]
