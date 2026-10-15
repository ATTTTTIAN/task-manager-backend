# Task Manager Backend



基于 FastAPI 开发的任务管理后端系统，支持用户认证、任务增删改查、分页查询、条件筛选、Redis 缓存和 Docker Compose 容器化部署。



## 1. 技术栈



| 分类 | 技术 |

| --- | --- |

| 开发语言 | Python 3.12 |

| Web 框架 | FastAPI |

| 数据库 | MySQL 8.0 |

| ORM | SQLAlchemy |

| 数据库驱动 | PyMySQL |

| 用户认证 | JWT（PyJWT） |

| 密码安全 | Argon2 |

| 缓存 | Redis 7 |

| 自动化测试 | pytest |

| 容器化部署 | Docker、Docker Compose |



## 2. 核心功能



### 用户认证



\- 用户注册与登录

\- JWT 身份认证

\- 获取当前登录用户信息

\- 不同用户之间的任务数据隔离



### 任务管理



\- 创建任务

\- 查询任务列表

\- 查询任务详情

\- 修改任务

\- 删除任务

\- 按任务完成状态筛选

\- 根据任务标题进行关键词搜索

\- 分页查询

\- 按创建时间或任务 ID 排序



### Redis 缓存



\- 对任务列表查询结果进行缓存

\- 根据用户 ID 和查询参数生成缓存键

\- 使用 SHA-256 摘要区分不同查询条件

\- 默认缓存过期时间为 60 秒

\- 通过缓存版本号实现缓存失效

\- Redis 读取异常时回退到数据库查询



### 容器化部署



\- Dockerfile 构建 FastAPI 镜像

\- Docker Compose 编排 FastAPI、MySQL、Redis

\- MySQL 和 Redis 健康检查

\- 使用 Docker Volume 持久化数据

\- API 启动前自动创建数据库表



## 3. 系统架构



```text

客户端 / Swagger UI

        |

        v

    FastAPI

        |

        +---- JWT 身份认证

        |

        +---- SQLAlchemy ---- MySQL

        |

        +---- Redis 缓存

```



## 4. Docker Compose 部署

项目使用 Docker Compose 编排 FastAPI、MySQL 8.0 和 Redis 7。



### 配置环境变量



在项目根目录创建 `.env.docker`，设置数据库连接信息、`MYSQL\_ROOT\_PASSWORD`、`JWT\_SECRET\_KEY` 等环境变量。不要将真实密码或密钥提交到 GitHub。



### 构建并启动



在安装 Docker 的 Linux 环境执行：



```bash

docker build -t task-manager-api:day6 .

docker compose --env-file .env.docker up -d

docker compose --env-file .env.docker ps

```



访问 Swagger API 文档：



`http://localhost:8000/docs`



查看日志：



```bash

docker compose --env-file .env.docker logs -f api

```



停止服务：



```bash

docker compose --env-file .env.docker down

```



## 5. API 接口



| 方法 | 路径 | 功能 |

| --- | --- | --- |

| GET | `/health` | 健康检查 |

| POST | `/auth/register` | 用户注册 |

| POST | `/auth/login` | 用户登录 |

| GET | `/auth/me` | 获取当前用户 |

| POST | `/tasks` | 创建任务 |

| GET | `/tasks` | 查询任务列表 |

| GET | `/tasks/{task\_id}` | 查询任务详情 |

| PATCH | `/tasks/{task\_id}` | 修改任务 |

| DELETE | `/tasks/{task\_id}` | 删除任务 |



任务列表支持完成状态筛选、标题关键词搜索、分页和排序。



## 6. Redis 缓存设计



任务列表缓存使用用户 ID、缓存版本号及查询参数摘要生成缓存键。



\- 默认缓存有效期为 60 秒。

\- 使用 SHA-256 摘要区分查询条件。

\- 通过递增用户缓存版本号使旧缓存失效。

\- Redis 读取失败时，回退到 MySQL 查询。



## 7. 自动化测试



项目使用 pytest 编写 API、用户认证、缓存及分页测试。



```bash

python -m pytest -q

```



## 8. 项目亮点



\- 使用 FastAPI 和 SQLAlchemy 开发 RESTful API。

\- 基于 JWT 实现用户认证及任务数据隔离。

\- 支持任务筛选、关键词搜索、分页与排序。

\- 使用 Redis 实现任务列表缓存。

\- 使用 Docker Compose 编排 FastAPI、MySQL 和 Redis 服务。

\- 使用 pytest 对核心业务功能进行测试。



## 9. 项目地址



https://github.com/ATTTTTIAN/task-manager-backend


