# AgentHome

一个现代化的 AI Agent 对话平台，支持多 Agent 管理、实时对话、MCP 协议、Skill 系统、RAG 知识库等功能。

## 功能特性

-  **多 Agent 管理** - 支持创建和管理多个 AI Agent
-  **Agent 团队** - 支持创建 Agent 团队，实现多 Agent 协作
-  **Agent 学院** - 支持创建和管理 Agent 学校，批量配置 Agent
-  **实时对话** - 支持与 Agent 进行实时对话，支持 WebSocket 流式响应
-  **对话历史** - 自动保存和管理对话历史
-  **现代 UI** - 简洁美观的 Web 界面，基于 React + Tailwind CSS
-  **图片支持** - 支持拖入和粘贴图片进行对话
-  **模型选择** - 支持多种模型提供商（OpenAI、Ollama、阿里云等）
-  **MCP 支持** - 支持 Model Context Protocol，可连接外部 MCP 服务
-  **Skill 系统** - 支持动态加载和管理 Skill 插件
-  **RAG 知识库** - 支持基于 ChromaDB 的向量检索增强生成
-  **本地存储** - 数据存储在本地 SQLite 数据库中

## 技术栈

### 后端
- Python 3.12+
- FastAPI - 高性能 Web 框架
- Uvicorn - ASGI 服务器
- SQLAlchemy - ORM
- Pydantic - 数据验证
- LangChain / LangGraph - LLM 应用框架
- DeepAgents - Agent 框架
- ChromaDB - 向量数据库

### 前端
- React 18 + TypeScript
- Vite - 构建工具
- Tailwind CSS - 样式框架
- Zustand - 状态管理
- Axios - HTTP 客户端
- Lucide React - 图标库

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 20+
- npm 或 yarn

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend
npm install
cd ..
```

### 2. 配置环境变量

 `.env` 文件配置rag技能用阿里云apikey

### 3. 启动项目

#### 方式一：使用 main.py 一键启动

```bash
# 一键启动整个项目（后端 + 前端）
python main.py
```

#### 方式二：使用启动脚本

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
./start.sh
```

### 4. 访问应用

打开浏览器访问: http://localhost:3000

**服务说明：**
- 前端开发服务器: http://localhost:3000
- 后端 API 服务器: http://127.0.0.1:8000
- API 文档: http://127.0.0.1:8000/docs

**注意：** 首次启动时会自动检测并安装前端依赖（`npm install`），可能需要几分钟时间。

---

## Docker 部署

### 方式一：使用 Docker Compose（推荐）

#### 1. 进入 docker 目录

```bash
cd docker
```

#### 2. 构建并启动容器

```bash
docker-compose up -d
```

#### 3. 查看日志

```bash
docker-compose logs -f
```

#### 4. 停止容器

```bash
docker-compose down
```

#### 3. 停止并删除容器

```bash
docker stop agenthome
docker rm agenthome
```

---

## 项目结构

```
agenthome/
├── main.py                 # 统一启动入口（后端 + 前端）
├── start.bat               # Windows 启动脚本
├── start.sh                # Linux/Mac 启动脚本
├── requirements.txt        # Python 依赖
├── .env                    # 环境变量配置
├── README.md               # 项目说明
├── backend/                # 后端代码
│   ├── api/                # API 路由
│   │   ├── chat.py         # 对话相关 API
│   │   ├── mcp.py          # MCP 管理 API
│   │   ├── schools.py      # Agent 学院 API
│   │   ├── teams.py        # Agent 团队 API
│   │   └── tools.py        # 工具管理 API
│   ├── core/               # 核心业务逻辑
│   │   ├── chat_engine.py  # 对话引擎
│   │   └── model_provider.py # 模型提供商
│   ├── config/             # 配置管理
│   ├── models/             # 数据模型
│   ├── services/           # 业务服务
│   │   ├── mcp_manager.py  # MCP 管理器
│   │   └── langchain_service.py # LangChain 服务
│   ├── skills/             # Skill 系统
│   ├── tools/              # 工具集
│   └── db/                 # 数据库
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── components/     # UI 组件
│   │   ├── pages/          # 页面
│   │   ├── store/          # 状态管理
│   │   ├── api/            # API 客户端
│   │   └── types/          # TypeScript 类型
│   └── package.json
├── data/                   # 数据目录
│   ├── uploads/            # 上传文件
│   ├── mcps.json           # MCP 配置
│   └── *.json              # 其他配置文件
├── skills/                 # Skill 插件目录
│   └── installed/          # 已安装的 Skills
├── rag/                    # RAG 知识库
│   ├── chroma_db/          # ChromaDB 向量数据库
│   └── rag_document_lib/   # 文档库
└── docker/                 # Docker 配置
    ├── Dockerfile
    └── docker-compose.yml
```

## 使用说明

### 创建 Agent

1. 点击左侧边栏的 "+ New Agent" 按钮
2. 填写 Agent 名称、描述和系统提示
3. 选择使用的模型提供商和模型
4. 保存 Agent

### 开始对话

1. 在左侧 Agent 列表中选择一个 Agent
2. 在右侧对话框中输入消息
3. 支持拖入或粘贴图片
4. 按 Enter 发送消息，Shift+Enter 换行

### 创建 Agent 团队

1. 进入 "Agent Team" 页面
2. 点击 "新建团队" 按钮
3. 配置团队名称、描述和成员 Agent
4. 保存团队配置

### 使用 MCP

1. 进入 "MCP 配置" 页面
2. 添加 MCP 服务配置（SSE 或 Stdio 模式）
3. 启用需要的 MCP 服务
4. 在对话中 Agent 会自动调用 MCP 工具

### 使用 RAG 知识库

1. 将文档放入 `rag/rag_document_lib/` 目录
2. 系统会自动索引文档
3. 在对话中 Agent 会基于知识库回答问题

### 开发 Skill

1. 在 `skills/installed/` 目录下创建新的 Skill 目录
2. 编写 `SKILL.md` 描述 Skill 功能
3. 在 `scripts/` 目录下实现 Skill 逻辑
4. 系统会自动加载和识别 Skill

## 未来计划

- [ ] 更多模型集成
- [ ] 插件市场

欢迎提交 Issue 和 Pull Request！
