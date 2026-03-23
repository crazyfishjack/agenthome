# AgentHome

一个现代化的AI Agent对话平台，支持多Agent管理、对话交互、模型切换等功能。

## 功能特性

- 🤖 多Agent管理 - 支持创建和管理多个AI Agent
- 💬 实时对话 - 支持与Agent进行实时对话
- 📜 对话历史 - 自动保存和管理对话历史
- 🎨 现代UI - 简洁美观的Web界面
- 🖼️ 图片支持 - 支持拖入和粘贴图片
- 🔧 模型选择 - 支持本地和网络API模型
- 💾 本地存储 - 数据存储在浏览器缓存中

## 技术栈

### 后端
- Python 3.8+
- FastAPI - 高性能Web框架
- SQLAlchemy - ORM
- Pydantic - 数据验证

### 前端
- React 18 + TypeScript
- Vite - 构建工具
- Tailwind CSS - 样式框架
- Zustand - 状态管理
- Axios - HTTP客户端

## 快速开始

### 1. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt
```

### 2. 启动项目

```bash
# 一键启动整个项目（后端 + 前端）
python main.py
```

或使用启动脚本：

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
./start.sh
```

### 3. 访问应用

打开浏览器访问: http://localhost:3000

**服务说明：**
- 前端开发服务器: http://localhost:3000
- 后端API服务器: http://127.0.0.1:8000

**注意：** 首次启动时会自动检测并安装前端依赖（`npm install`），可能需要几分钟时间。

## 项目结构

```
agenthome/
├── main.py                 # 统一启动入口（后端 + 前端）
├── start.bat               # Windows启动脚本
├── start.sh                # Linux/Mac启动脚本
├── requirements.txt        # Python依赖
├── backend/               # 后端代码
│   ├── api/              # API路由
│   ├── core/             # 核心业务逻辑
│   ├── config/           # 配置管理
│   ├── models/           # 数据模型
│   ├── services/         # 业务服务
│   └── utils/            # 工具函数
├── frontend/             # 前端代码
│   ├── src/
│   │   ├── components/   # UI组件
│   │   ├── store/        # 状态管理
│   │   ├── api/          # API客户端
│   │   ├── types/        # TypeScript类型
│   │   └── utils/        # 工具函数
│   ├── vite.config.ts    # Vite配置
│   └── package.json
└── data/                 # 数据目录
```

## 使用说明

### 创建Agent

1. 点击左侧边栏的 "+ New Agent" 按钮
2. 填写Agent名称、描述和系统提示
3. 选择使用的模型
4. 保存Agent

### 开始对话

1. 在左侧Agent列表中选择一个Agent
2. 在右侧对话框中输入消息
3. 支持拖入或粘贴图片
4. 按Enter发送消息，Shift+Enter换行

### 切换模型

1. 点击顶部导航栏的设置图标
2. 在模型选择器中选择想要的模型
3. 配置API Key（如需要）

### 查看历史

1. 点击顶部导航栏的历史图标
2. 查看所有对话历史记录
3. 点击历史记录恢复对话

## 配置说明

### 环境变量

创建 `.env` 文件配置以下变量：

```env
# API配置
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1

# 服务器配置
HOST=127.0.0.1
PORT=8000
```

### 本地模型

如需使用本地模型，配置以下变量：

```env
LOCAL_MODEL_PATH=/path/to/your/model
```

## 未来计划

- [ ] MCP (Model Context Protocol) 支持
- [ ] Skill系统
- [ ] A2A (Agent-to-Agent) 通信
- [ ] 更多模型集成
- [ ] 插件系统
- [ ] 多语言支持

## 贡献指南

欢迎提交Issue和Pull Request！

## 许可证

MIT License
