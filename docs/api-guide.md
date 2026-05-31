# API 接口说明

当前后端 API 统一挂载在 `/api/v1` 下，所有业务接口默认返回 `ApiResponse` 结构。

## 一、通用说明

### 统一响应结构

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

字段说明：

- `code`：业务状态码，`0` 表示成功。
- `message`：业务提示信息，成功时默认 `ok`。
- `data`：接口实际返回数据。

### 鉴权方式

后台管理接口需要管理员 Token：

```http
Authorization: Bearer <access_token>
```

未携带 Token 或 Token 无效时返回 `401`。管理员账号被禁用时返回 `403`。

### 状态枚举

- 艺术家状态：`active` 展示、`hidden` 隐藏。
- 分类状态：`active` 启用、`hidden` 隐藏。
- 作品状态：`draft` 草稿、`published` 已上架、`offline` 已下架。

## 二、基础接口

### GET /api/v1/health

用途：健康检查。

说明：

- 不访问数据库和 Redis。
- 用于确认服务进程是否启动成功。
- 适合作为部署平台或负载均衡的基础探活接口。

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "ok"
  }
}
```

## 三、小程序公开接口

### GET /api/v1/artworks

用途：查询小程序作品列表。

当前状态：

- 返回示例数据，便于前端先联调页面。

响应字段：

- `items`：作品数组。
- `page`：当前页码。
- `page_size`：每页数量。
- `total`：符合条件的总数。

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 1,
        "title": "Untitled No. 7",
        "artist_name": "Lin Wei",
        "cover_url": "",
        "material": "Oil on canvas",
        "creation_year": 2024
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

### GET /api/v1/artworks/{artwork_id}

用途：查询小程序作品详情。

路径参数：

- `artwork_id`：作品 ID，对应 `artworks.id`。

当前状态：

- 返回示例数据，便于前端先联调页面。

### GET /api/v1/categories

用途：查询小程序作品分类树。

说明：

- 只返回 `active` 状态分类。
- 按 `sort_order`、`id` 升序排序。
- 根据 `parent_id` 组装树结构。
- 无子分类时 `children` 返回空数组。

响应字段：

- `items`：分类树数组。
- `id`：分类 ID。
- `name`：分类名称。
- `parent_id`：父分类 ID，一级分类为 `null`。
- `sort_order`：排序权重。
- `children`：子分类数组。

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 1,
        "name": "绘画",
        "parent_id": null,
        "sort_order": 1,
        "children": [
          {
            "id": 2,
            "name": "油画",
            "parent_id": 1,
            "sort_order": 1,
            "children": []
          }
        ]
      }
    ]
  }
}
```

## 四、后台认证接口

### POST /api/v1/admin/auth/login

用途：后台管理员登录。

请求体：

```json
{
  "username": "admin",
  "password": "correct-password"
}
```

处理逻辑：

- 根据 `username` 查询管理员。
- 校验密码哈希。
- 检查管理员状态必须为 `active`。
- 签发 JWT access token。
- 更新 `last_login_at`。
- 写入 `operation_logs`，操作类型为 `admin_login`。

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "access_token": "jwt-token",
    "token_type": "bearer",
    "admin_username": "admin"
  }
}
```

错误说明：

- `401`：账号或密码错误。
- `403`：管理员账号已被禁用。
- `500`：登录状态保存失败，请稍后重试。

### GET /api/v1/admin/auth/me

用途：查询当前登录管理员信息。

请求头：

```http
Authorization: Bearer <access_token>
```

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 1,
    "username": "admin",
    "role": "super_admin",
    "status": "active"
  }
}
```

## 五、后台分类管理接口

后台分类管理接口统一需要管理员 Token。新增、更新、删除会写入 `operation_logs`，`resource_type` 为 `category`。

### GET /api/v1/admin/categories

用途：查询后台分类列表。

查询参数：

- `status`：可选，`active` 或 `hidden`。

说明：

- 不传 `status` 时返回全部分类。
- 按 `sort_order`、`id` 升序排序。

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 1,
        "name": "绘画",
        "parent_id": null,
        "sort_order": 1,
        "status": "active"
      }
    ],
    "total": 1
  }
}
```

### GET /api/v1/admin/categories/{category_id}

用途：查询后台分类详情。

路径参数：

- `category_id`：分类 ID。

错误说明：

- `404`：分类不存在。

### POST /api/v1/admin/categories

用途：创建分类。

请求体：

```json
{
  "name": "油画",
  "parent_id": 1,
  "sort_order": 10,
  "status": "active"
}
```

字段说明：

- `name`：必填，分类名称，不能只包含空白字符。
- `parent_id`：可选，父分类 ID，传 `null` 表示一级分类。
- `sort_order`：可选，排序权重，默认 `0`。
- `status`：可选，默认 `active`。

业务规则：

- 父分类必须存在。
- 写入操作日志，操作类型为 `create_category`。

### PATCH /api/v1/admin/categories/{category_id}

用途：更新分类。

请求体：

```json
{
  "name": "当代油画",
  "parent_id": null,
  "sort_order": 20,
  "status": "hidden"
}
```

说明：

- 所有字段均可选，但至少提供一个字段。
- `parent_id` 传 `null` 表示改为一级分类。

业务规则：

- 分类必须存在。
- 父分类必须存在。
- 父分类不能是自身。
- 父分类不能是自身子级，避免形成循环分类树。
- 写入操作日志，操作类型为 `update_category`，日志中保存变更前后字段。

错误说明：

- `400`：父分类不存在、父分类不能是自身、父分类不能是自身子级。
- `404`：分类不存在。

### DELETE /api/v1/admin/categories/{category_id}

用途：删除分类。

业务规则：

- 分类必须存在。
- 存在子分类时不允许删除。
- 存在关联作品时不允许删除。
- 写入操作日志，操作类型为 `delete_category`。

错误说明：

- `400`：分类下存在子分类，不能删除。
- `400`：分类下存在作品，不能删除。
- `404`：分类不存在。

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 1
  }
}
```

## 六、后台艺术家管理接口

后台艺术家管理接口统一需要管理员 Token。新增、更新、删除会写入 `operation_logs`，`resource_type` 为 `artist`。

### GET /api/v1/admin/artists

用途：查询后台艺术家列表。

查询参数：

- `status`：可选，`active` 或 `hidden`。
- `keyword`：可选，按艺术家姓名模糊搜索。

说明：

- 不传 `status` 时返回全部艺术家。
- 按 `id` 升序排序。

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 1,
        "name": "林微",
        "avatar_url": "https://example.com/avatar.jpg",
        "bio": "艺术家简介",
        "birth_year": 1988,
        "nationality": "China",
        "status": "active"
      }
    ],
    "total": 1
  }
}
```

### GET /api/v1/admin/artists/{artist_id}

用途：查询后台艺术家详情。

路径参数：

- `artist_id`：艺术家 ID。

错误说明：

- `404`：艺术家不存在。

### POST /api/v1/admin/artists

用途：创建艺术家。

请求体：

```json
{
  "name": "林微",
  "avatar_url": "https://example.com/avatar.jpg",
  "bio": "艺术家简介",
  "birth_year": 1988,
  "nationality": "China",
  "status": "active"
}
```

字段说明：

- `name`：必填，艺术家姓名，不能只包含空白字符。
- `avatar_url`：可选，头像或肖像图片 URL。
- `bio`：可选，艺术家简介、履历或创作理念。
- `birth_year`：可选，出生年份。
- `nationality`：可选，国籍或地区。
- `status`：可选，默认 `active`。

业务规则：

- 写入操作日志，操作类型为 `create_artist`。

### PATCH /api/v1/admin/artists/{artist_id}

用途：更新艺术家。

请求体：

```json
{
  "name": "林微",
  "avatar_url": null,
  "bio": "更新后的简介",
  "birth_year": 1988,
  "nationality": "China",
  "status": "hidden"
}
```

说明：

- 所有字段均可选，但至少提供一个字段。
- 可选字段传 `null` 表示清空。

业务规则：

- 艺术家必须存在。
- `name` 不能只包含空白字符。
- 写入操作日志，操作类型为 `update_artist`，日志中保存变更前后字段。

错误说明：

- `404`：艺术家不存在。

### DELETE /api/v1/admin/artists/{artist_id}

用途：删除艺术家。

业务规则：

- 艺术家必须存在。
- 存在关联作品时不允许删除，避免作品丢失作者信息。
- 写入操作日志，操作类型为 `delete_artist`。

错误说明：

- `400`：艺术家下存在作品，不能删除。
- `404`：艺术家不存在。

响应示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 1
  }
}
```

## 七、后续建议实现接口

```text
GET    /api/v1/admin/artworks
POST   /api/v1/admin/artworks
PATCH  /api/v1/admin/artworks/{id}
PATCH  /api/v1/admin/artworks/{id}/status
DELETE /api/v1/admin/artworks/{id}

POST   /api/v1/admin/uploads/presign
POST   /api/v1/admin/uploads/confirm
```

## 八、接口设计原则

- 小程序公开接口默认不要求登录，但只返回可公开展示的数据。
- 用户收藏、点赞、浏览记录等行为接口需要用户 Token。
- 后台管理接口必须要求管理员 Token。
- 后台写操作需要记录 `operation_logs`。
- 列表接口后续数据量变大后建议补充分页参数，避免一次性返回大量数据。
