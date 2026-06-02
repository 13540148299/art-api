from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_artists,
    admin_artworks,
    admin_admins,
    admin_auth,
    admin_categories,
    admin_dashboard,
    admin_uploads,
    artworks,
    cart,
    categories,
    health,
    orders,
    users,
)

api_router = APIRouter()

# 健康检查接口：用于本地开发、部署探活和负载均衡健康检查。
api_router.include_router(health.router, tags=["health"])

# 小程序公开作品接口：第一阶段先提供列表和详情，后续扩展搜索、筛选、收藏、点赞。
api_router.include_router(artworks.router, prefix="/artworks", tags=["artworks"])

# 小程序公开作品分类接口：返回启用分类树，用于作品列表筛选和分类导航。
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])

# 小程序用户接口：提供登录、资料维护、收藏、点赞和作品互动状态。
api_router.include_router(users.router, prefix="/users", tags=["users"])

# 小程序购物车接口：登录后管理作品购物车，价格和库存以服务端实时数据为准。
api_router.include_router(cart.router, prefix="/users/cart", tags=["cart"])

# 小程序订单接口：从购物车创建订单，并提供订单列表、详情和状态流转能力。
api_router.include_router(orders.router, prefix="/users/orders", tags=["orders"])

# 后台管理员认证接口：后台登录、刷新当前用户等能力放在这个分组。
api_router.include_router(admin_auth.router, prefix="/admin/auth", tags=["admin-auth"])

# 后台管理员账号管理接口：仅超级管理员可以维护普通管理员。
api_router.include_router(admin_admins.router, prefix="/admin/admins", tags=["admin-admins"])

# 后台工作台概览接口：只返回首页统计和少量最近作品，避免后台首页加载完整管理列表。
api_router.include_router(admin_dashboard.router, prefix="/admin/dashboard", tags=["admin-dashboard"])

# 后台作品分类管理接口：提供分类增删改查，并通过 JWT 管理员身份控制访问。
api_router.include_router(admin_categories.router, prefix="/admin/categories", tags=["admin-categories"])

# 后台艺术家管理接口：提供艺术家增删改查，并通过 JWT 管理员身份控制访问。
api_router.include_router(admin_artists.router, prefix="/admin/artists", tags=["admin-artists"])

# 后台作品概览接口：提供作品后端分页、懒加载和多条件搜索能力。
api_router.include_router(admin_artworks.router, prefix="/admin/artworks", tags=["admin-artworks"])

# 后台上传接口：当前用于艺术家头像上传，后续可扩展作品图片、展览封面等上传能力。
api_router.include_router(admin_uploads.router, prefix="/admin/uploads", tags=["admin-uploads"])
