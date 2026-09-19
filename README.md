# MushroomShed-01 · 菇房出菇台账

食用菌菇房「出菇室环境记录与采收台账」种子项目（非库存 / 电商 / 医院 / 考勤）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.11 · Flask · SQLAlchemy 2 · Marshmallow · Flask-JWT-Extended · passlib(bcrypt) · gunicorn |
| 前端 | SolidJS · Vite · TypeScript · @solidjs/router |
| 数据库 | MySQL 8（协议兼容原 MariaDB 设计） |
| 部署 | docker-compose · 前端 Nginx 反代 `/api` |

## 端口与账号

| 服务 | 端口 |
| --- | --- |
| 前端 | **3800** |
| 后端 API | **8800** |
| MySQL | **3310** |

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | admin（场长） |
| `fruiter` | `123456` | fruiter（出菇员） |

数据库：`mushroomshed` / `mushroomshed`，库名 `mushroomshed`。JWT 密钥环境变量 **`JWT_SECRET`**。

## 一键启动

```bash
cd MushroomShed-01
docker compose up --build
```

启动后访问：

- 前端：http://localhost:3800
- 后端健康检查：http://localhost:8800/api/health

后端 entrypoint 流程：等待 MySQL 就绪 → `create_all` 建表 → seed 初始数据 → 启动 gunicorn。

## 功能模块

1. **Auth**：JWT 登录（OAuth2 表单或 JSON），`/api/auth/login`、`/api/auth/me`，`Authorization: Bearer`
2. **Shed 菇房**：`name`、`location`、`notes`
3. **Room 出菇室**：`shedId`、`roomCode`、`species`、`capacityBags`、`status(fruiting|idle|sanitize)`；同菇房 `roomCode` 唯一；列表额外返回 `activeSanitizeOrderId`（进行中消杀工单标记，无则 `null`）
4. **ClimateLog 环境记录**：`roomId`、`recordedAt`、`tempC`、`humidityPct`、`co2Ppm`、`notes`；`humidityPct ∈ [1,100]`，否则 **400**
5. **FlushHarvest 采收**：`roomId`、`harvestedAt`、`flushNo(≥1)`、`weightKg`、`grade(A|B|C)`、`operatorName`；`weightKg > 0`，否则 **400**
6. **SanitizeOrder 消杀工单**：`roomId`、`method(uv|chemical)`、`status(open|doing|done|void)`、`operatorName`、`plannedAt`、`startedAt(可空)`、`finishedAt(可空)`
7. **Dashboard**：`shedTotal`、`fruitingRoomCount`、`climateLast24h`、`harvestKgLast7d`

各实体 API：`GET/POST` 列表与创建、`DELETE` 按 ID 删除。消杀工单不提供删除，通过流转接口 `POST /api/sanitize-orders/:id/transition`（body `{"toStatus":"doing|done|void"}`）推进状态机。

## 消杀工单状态机与联锁

状态机与校验集中在 `backend/app/sanitize.py`，工单流转、采收创建、出菇室列表标记**共用同一份校验**：

- **状态机**：`open → doing → done`；`open`/`doing`（非终态）可 `void`；`done`/`void` 为终态不可再流转。非法流转返回 **409**。
- **同室唯一**：同一出菇室同时只允许一个 `open`/`doing` 工单，新建冲突返回 **409**。
- **开工联锁**：`open → doing` 时记录 `startedAt`；若该 Room 非 `sanitize`，服务端自动将其改为 `sanitize`。
- **完工联锁**：`doing → done` 时，该室在 `startedAt` 与当前时间之间必须至少有一条 `ClimateLog`，否则返回 **409**。
- **采收联锁**：出菇室存在 `open`/`doing` 工单时禁止新建 `FlushHarvest`，返回 **409**。
- Seed 内置两张 `doing` 工单：`R-02`（窗口内有环境记录，可完工）与 `V-02`（缺环境记录，完工必 409）。

## 前端页面

Login · Dashboard · Sheds · Rooms（含进行中消杀单标记） · ClimateLogs · FlushHarvests · SanitizeOrders 消杀工单（侧边栏布局）

## 本地开发（可选）

```bash
# 数据库（或用 compose 只起 db）
docker compose up -d db

# 后端
cd backend
pip install -r requirements.txt
set DATABASE_URL=mysql+pymysql://mushroomshed:mushroomshed@localhost:3310/mushroomshed
set JWT_SECRET=local-dev-secret
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"
python -c "from app.seed import seed; seed()"
gunicorn wsgi:app --bind 0.0.0.0:8800 --reload

# 前端
cd frontend
npm install
npm run dev
```

## 目录结构

```
MushroomShed-01/
├── docker-compose.yml
├── README.md
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   ├── wsgi.py
│   └── app/
│       ├── __init__.py
│       ├── config.py
│       ├── database.py
│       ├── auth.py
│       ├── seed.py
│       ├── utils.py
│       ├── models/
│       ├── schemas/
│       └── routes/
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── pages/
        ├── components/
        └── api/
```
