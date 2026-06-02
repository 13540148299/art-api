from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_operable_admin
from app.models.admin import Admin
from app.schemas.common import ApiResponse

router = APIRouter()

UPLOAD_ROOT = Path("uploads")
AVATAR_DIR = UPLOAD_ROOT / "avatars"
ARTWORK_DIR = UPLOAD_ROOT / "artworks"
MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_VIDEO_SIZE = 100 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
ALLOWED_VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}


@router.post("/avatars", response_model=ApiResponse[dict[str, str]])
async def upload_avatar(
    file: UploadFile = File(...),
    current_admin: Admin = Depends(get_current_operable_admin),
) -> ApiResponse[dict[str, str]]:
    """上传艺术家头像图片。

    该接口只允许已登录管理员访问，并把图片保存到本地 uploads/avatars 目录。
    当前阶段用于后台联调，生产环境建议替换为对象存储并补充图片审核、缩略图和清理策略。
    """
    file_extension = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if file_extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 jpg、png、webp、gif 图片",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件不能为空")
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图片大小不能超过 5MB")

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{file_extension}"
    target_path = AVATAR_DIR / filename
    target_path.write_bytes(content)

    return ApiResponse(data={"url": f"/uploads/avatars/{filename}"})


@router.post("/artworks", response_model=ApiResponse[dict[str, str]])
async def upload_artwork_media(
    file: UploadFile = File(...),
    current_admin: Admin = Depends(get_current_operable_admin),
) -> ApiResponse[dict[str, str]]:
    """上传作品展示资源。

    作品展示支持图片或视频；接口会根据 MIME 类型限制文件大小，避免误传超大文件影响服务稳定性。
    """
    content_type = file.content_type or ""
    media_type = "image" if content_type in ALLOWED_IMAGE_TYPES else "video" if content_type in ALLOWED_VIDEO_TYPES else None
    if media_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 jpg、png、webp、gif 图片或 mp4、webm、mov 视频",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传文件不能为空")
    max_size = MAX_IMAGE_SIZE if media_type == "image" else MAX_VIDEO_SIZE
    if len(content) > max_size:
        limit_text = "5MB" if media_type == "image" else "100MB"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"文件大小不能超过 {limit_text}")

    ARTWORK_DIR.mkdir(parents=True, exist_ok=True)
    file_extension = (
        ALLOWED_IMAGE_TYPES.get(content_type)
        if media_type == "image"
        else ALLOWED_VIDEO_TYPES.get(content_type)
    )
    filename = f"{uuid4().hex}{file_extension}"
    target_path = ARTWORK_DIR / filename
    target_path.write_bytes(content)

    return ApiResponse(data={"url": f"/uploads/artworks/{filename}", "media_type": media_type})

