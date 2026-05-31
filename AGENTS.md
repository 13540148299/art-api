# art-api 项目开发指南

> 后续进入 `art-api` 开发时，优先阅读本文件了解架构、业务模块和约定；只有在修改具体功能时再按需读取对应源码文件，避免一开始全量扫描项目。

## 项目定位

- 项目类型：Python 3.11 + FastAPI 后端服务。
- 服务对象：艺术作品展示小程序、后台管理系统。
- 数据库：PostgreSQL，使用 SQLAlchemy ORM。
- 数据库迁移：Alembic。
- 鉴权方式：后台管理接口使用 JWT Bearer Token。
- 默认交流、注释、接口说明、提交说明使用中文。

## 目录职责

- `app/main.py`：创建 FastAPI 应用，注册 CORS、API 路由和 `/uploads` 静态文件访问。
- `app/api/deps.py`：公共依赖，当前主要是后台管理员 JWT 鉴权。
- `app/api/v1/router.py`：v1 路由聚合入口，所有新增接口必须在这里挂载。
- `app/api/v1/endpoints/`：接口层，按业务拆分。
  - `health.py`：健康检查。
  - `artworks.py`：公开端作品列表和详情，仅返回公开展示需要的数据。
  - `categories.py`：公开端分类树。
  - `admin_auth.py`：后台登录、当前管理员信息。
  - `admin_dashboard.py`：后台首页统计和最近作品。
  - `admin_artists.py`：后台艺术家 CRUD。
  - `admin_categories.py`：后台分类 CRUD。
  - `admin_artworks.py`：后台作品 CRUD、分页搜索。
  - `admin_uploads.py`：后台上传，当前支持艺术家头像和作品图片/视频。
- `app/models/`：SQLAlchemy ORM 模型。
- `app/schemas/`：Pydantic 请求/响应模型。
- `app/core/`：配置、安全工具。
- `app/db/session.py`：数据库引擎和 Session 依赖。
- `alembic/versions/`：数据库迁移脚本。
- `tests/`：接口和业务测试，使用轻量 FakeSession 避免依赖真实 PostgreSQL。
- `uploads/`：本地开发上传文件目录，生产环境建议替换为对象存储。

## 核心业务模型

- `Admin`：后台管理员，字段包括 `username`、`password_hash`、`role`、`status`、`last_login_at`。
- `Artist`：艺术家，支持姓名、头像、简介、出生年份、国籍、状态。
- `Category`：作品分类，支持父子层级、描述、排序、状态。
- `Artwork`：作品核心表。
  - 作品 ID 由系统生成，前端仅用于定位记录，不作为界面可见列展示。
  - `title`：作品名称，后台创建/更新限制 1-100 字符，支持中英文。
  - `description`：作品介绍。
  - `artist_id`、`category_id`：关联艺术家和分类，允许为空以便草稿保存。
  - `cover_url`：封面图。
  - `media_type`：作品展示类型，`image` 或 `video`。
  - `media_url`：作品展示资源地址，图片或视频。
  - `creation_year`：创建年份。
  - `status`：`draft` 草稿、`published` 已上架、`offline` 已下架。
  - `published_at`：首次上架时写入，下架或草稿不清空历史发布时间。
- `ArtworkImage`：作品多图扩展表，当前列表优先使用 `Artwork.cover_url/media_url`。
- `OperationLog`：后台操作日志，新增/更新/删除后台资源时应记录。
- `Favorite`、`ArtworkView`、`Exhibition`、`ExhibitionArtwork`、`User`：为收藏、浏览、展览专题、小程序用户等后续能力预留。

## API 返回结构

所有业务接口默认返回统一结构：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

不要随意修改 `ApiResponse` 外层结构。新增接口应优先复用 `app/schemas/common.py` 中的 `ApiResponse`。

## 已有接口能力

公开端：

- `GET /api/v1/health`：健康检查。
- `GET /api/v1/artworks`：公开作品分页列表，默认只返回 `published` 状态作品，支持作品名、艺术家、分类、年份搜索。
- `GET /api/v1/artworks/{artwork_id}`：公开作品详情。
- `GET /api/v1/categories`：启用分类树。

后台端：

- `POST /api/v1/admin/auth/login`：管理员登录，成功返回 JWT。
- `GET /api/v1/admin/auth/me`：当前管理员信息。
- `GET /api/v1/admin/dashboard`：统计概览和最近作品。
- `GET/POST/PATCH/DELETE /api/v1/admin/artists`：艺术家管理。
- `GET/POST/PATCH/DELETE /api/v1/admin/categories`：分类管理。
- `GET/POST/PATCH/DELETE /api/v1/admin/artworks`：作品管理。
- `POST /api/v1/admin/uploads/avatars`：上传艺术家头像，仅支持图片，最大 5MB。
- `POST /api/v1/admin/uploads/artworks`：上传作品展示资源，支持图片最大 5MB，视频最大 100MB。

## 分层规则

- Endpoint 层负责参数接收、鉴权依赖、响应封装和少量编排。
- Schema 层负责请求和响应字段定义、基础校验。
- Model 层只定义 ORM 表结构和字段含义，不写业务流程。
- 数据库查询优先使用 SQLAlchemy `select`，避免拼接 SQL 字符串。
- 后台新增/编辑/删除资源时，应写入 `OperationLog`。
- 涉及数据库写入时使用统一提交方法，失败时 rollback 并返回明确错误。
- 不要在接口中打印密码、Token、Cookie 或上传文件原始内容。

## 数据库迁移规则

- 修改 ORM 表字段后必须新增 Alembic 迁移文件。
- 本地应用新迁移：

```powershell
alembic upgrade head
```

- 近期重要迁移：
  - `20260527_0002_add_category_description.py`：分类描述字段。
  - `20260528_0003_add_artwork_media_fields.py`：作品 `media_type/media_url` 字段。
- 如果接口报 `UndefinedColumn`，优先检查是否漏执行迁移。

## 测试与验证

- 后端全量测试：

```powershell
$env:PYTHONPATH='.'
pytest
```

- 重点测试文件：
  - `tests/test_admin_auth.py`
  - `tests/test_admin_artists.py`
  - `tests/test_admin_categories.py`
  - `tests/test_admin_artworks.py`
  - `tests/test_admin_dashboard.py`
  - `tests/test_categories.py`
  - `tests/test_health.py`
- 修改核心 CRUD、鉴权、分页搜索、上传逻辑时，优先补充或更新测试。

## 本地运行

```powershell
cd E:\AI-projects\art-api
$env:PYTHONPATH='.'
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

默认 API 地址：

- `http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`

本地默认管理员：

- 用户名：`admin`
- 密码：`Admin@123456`

## 开发注意事项

- 新增代码必须包含必要中文注释；不要写“这是一个函数”这类无意义注释。
- 公共方法、接口、核心类要有中文说明。
- 复杂业务逻辑要说明业务原因和边界条件。
- 不引入未经确认的新依赖。
- 不随意修改公共接口返回结构。
- 不删除已有兼容逻辑，除非需求明确要求。
- 涉及权限、文件上传、删除、状态流转时必须注意边界条件。

## 完成任务后的说明格式

每次修改完成后，按以下格式简要说明：

1. 改动内容
2. 关键实现
3. 风险点
4. 建议验证方式
