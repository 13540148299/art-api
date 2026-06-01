# Art API

Python FastAPI 后端项目，服务于艺术作品展示小程序和后台管理系统。

## 运行要求

- Python 3.11+
- PostgreSQL
- Redis

## 本地开发

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
uvicorn app.main:app --reload
```

API 文档启动后访问：

- http://localhost:8000/docs
- http://localhost:8000/redoc

## 手动启动本地服务

本地开发环境使用 Docker Desktop 运行 PostgreSQL，后端服务使用 Uvicorn 启动。

### 1. 启动 Docker Desktop

先打开 Docker Desktop，等待界面显示 Docker 正在运行。

也可以在 PowerShell 中执行：

```powershell
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

### 2. 启动 PostgreSQL 容器

```powershell
docker start art-postgres
```

确认容器正在运行：

```powershell
docker ps --filter "name=art-postgres"
```

确认本机 5432 端口可用：

```powershell
Test-NetConnection localhost -Port 5432
```

如果输出中 `TcpTestSucceeded` 为 `True`，说明数据库已经可以连接。

### 3. 启动后端服务

```powershell
cd E:\AI-projects\art-api
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

0.0.0.0 表示允许局域网内其他设备访问。开发调试没问题，但不要在无鉴权接口、敏感接口上长期这样暴露
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3.1 真机联调放通 Windows 防火墙

如果小程序真机联调出现 `ERR_CONNECTION_TIMED_OUT`，通常是手机无法访问电脑的 `8000` 入站端口。
请用“以管理员身份运行”的 PowerShell 执行：

```powershell
cd E:\AI-projects\art-api
.\scripts\allow-miniapp-lan.ps1
```

脚本会完成：

- 将 WLAN 网络从公共网络切换为专用网络。
- 放通本机 TCP `8000` 入站端口。
- 输出小程序应使用的局域网接口地址。

执行后再用 `0.0.0.0` 启动后端，并在手机浏览器打开脚本输出的 `/api/v1/health` 地址验证。

后端服务地址：

- http://127.0.0.1:8000
- http://127.0.0.1:8000/docs

### 4. 验证管理员登录

本地默认管理员账号：

- 用户名：admin
- 密码：Admin@123456
- 角色：super_admin
- 状态：active

在 PowerShell 中执行：

```powershell
$body = @{
  username = "admin"
  password = "Admin@123456"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/admin/auth/login" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

成功时会返回 `access_token`，后续后台接口请求可使用 `Authorization: Bearer <access_token>`。

### 5. 验证 JWT 鉴权

#### 5.1 启动后端服务

如果后端服务尚未启动，先在 PowerShell 中执行：

```powershell
cd E:\AI-projects\art-api
$env:PYTHONPATH='.'
uvicorn app.main:app --reload
```

#### 5.2 登录并获取 access_token

```powershell
$loginResult = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v1/admin/auth/login" `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"Admin@123456"}'

$token = $loginResult.data.access_token
$token
```

预期结果：命令会输出一段 JWT 字符串，后续请求需要放到 `Authorization: Bearer <access_token>` 请求头中。

#### 5.3 使用 JWT 访问受保护接口

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/api/v1/admin/auth/me" `
  -Headers @{ Authorization = "Bearer $token" }
```

预期结果：接口返回当前管理员信息，包含 `id`、`username`、`role`、`status` 等字段。

#### 5.4 验证异常鉴权场景

不携带 JWT 访问受保护接口：

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/api/v1/admin/auth/me"
```

预期结果：返回 `401`，表示未登录不能访问。

携带非法 JWT 访问受保护接口：

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/api/v1/admin/auth/me" `
  -Headers @{ Authorization = "Bearer invalid-token" }
```

预期结果：返回 `401`，提示登录凭证无效或已过期。

### 6. 停止服务

停止后端服务：在运行 Uvicorn 的窗口按 `Ctrl + C`。

停止 PostgreSQL 容器：

```powershell
docker stop art-postgres
```

## 数据库迁移

本项目使用 Alembic 管理 PostgreSQL 表结构迁移。

执行迁移前，请确保 `.env` 中的 `DATABASE_URL` 指向可访问的 PostgreSQL 数据库，并且数据库已经创建。

执行全部迁移：

```powershell
alembic upgrade head
```

生成新的迁移文件：

```powershell
alembic revision --autogenerate -m "描述本次表结构变更"
```

回滚上一个迁移：

```powershell
alembic downgrade -1
```

当前首个迁移文件会创建艺术作品平台的完整初始表结构，包含：

- 管理员、用户
- 艺术家、分类、作品、作品图片
- 收藏、浏览记录
- 展览专题、专题作品关联
- 后台操作日志

## 中文开发说明

- [数据库 ERD 说明](docs/database-erd.md)
- [API 接口说明](docs/api-guide.md)

代码中的 API、ORM 模型、Schema、配置和数据库会话已经补充中文注释，后续新增业务逻辑时请保持同样的注释风格：

- 接口函数说明接口用途、参数、鉴权要求和正式实现逻辑。
- ORM 模型说明表用途、ERD 关系和关键字段含义。
- 复杂逻辑说明业务原因，不只描述代码动作。
