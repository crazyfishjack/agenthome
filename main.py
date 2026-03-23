import os
import sys
import uvicorn
import subprocess
import threading
import time
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config.settings import settings
from backend.api.router import api_router
from backend.services.mcp_manager import mcp_manager


class WebSocketCORSMiddleware(BaseHTTPMiddleware):
    """自定义中间件处理 WebSocket 的 CORS"""
    async def dispatch(self, request: Request, call_next):
        # 检查是否是 WebSocket 升级请求
        if request.headers.get("upgrade", "").lower() == "websocket":
            # 允许所有 WebSocket 连接
            print(f"[DEBUG] WebSocket 请求: {request.url.path}, Origin: {request.headers.get('origin', 'None')}")
        response = await call_next(request)
        return response


def create_app():
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI Agent Home - Modern AI Chat Platform"
    )

    # 首先添加 WebSocket CORS 中间件（最先执行）
    app.add_middleware(WebSocketCORSMiddleware)

    # CORS 配置 - 明确列出允许的源，确保 WebSocket 正常工作
    cors_origins = settings.CORS_ORIGINS
    if cors_origins == ["*"]:
        # 对于 WebSocket，明确指定允许的源比通配符更可靠
        cors_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "*"
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600,
    )
    
    app.include_router(api_router, prefix="/api")
    
    # 应用启动事件：加载所有 MCP 配置并创建客户端
    @app.on_event("startup")
    async def startup_event():
        import asyncio
        import json
        from pathlib import Path
        from backend.models.mcp_config import MCPConfig

        async def load_mcp_configs():
            """异步加载 MCP 配置"""
            try:
                mcp_file = Path("./data/mcps.json")
                if not mcp_file.exists():
                    print("[INFO] MCP 配置文件不存在，跳过 MCP 加载")
                    return

                with open(mcp_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    mcps = data.get("mcps", [])

                    print(f"[INFO] Loading {len(mcps)} MCP configurations...")

                    for mcp_dict in mcps:
                        try:
                            mcp_config = MCPConfig(**mcp_dict)
                            client = mcp_manager.create_mcp_client(mcp_config)
                            if client:
                                print(f"[INFO] MCP client created: {mcp_config.mcp_id} - {mcp_config.name}")
                            else:
                                print(f"[WARNING] Failed to create MCP client: {mcp_config.mcp_id} - {mcp_config.name}")
                        except Exception as e:
                            print(f"[ERROR] Failed to load MCP {mcp_dict.get('mcp_id')}: {e}")
                            import traceback
                            traceback.print_exc()

                    print(f"[INFO] MCP initialization complete")
            except Exception as e:
                print(f"[ERROR] Failed to load MCP configurations: {e}")
                import traceback
                traceback.print_exc()

        # 使用 asyncio.create_task() 创建后台任务，避免阻塞启动事件
        asyncio.create_task(load_mcp_configs())
        print("[INFO] MCP 加载任务已启动（后台异步执行）")
    
    return app


app = create_app()


def start_frontend_dev_server():
    """在后台启动前端开发服务器"""
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
    
    # 检查 node_modules 是否存在
    node_modules_dir = os.path.join(frontend_dir, "node_modules")
    if not os.path.exists(node_modules_dir):
        print("检测到前端依赖未安装,正在安装...")
        try:
            subprocess.run(
                "npm install",
                cwd=frontend_dir,
                check=True,
                shell=True
            )
            print("前端依赖安装完成")
        except subprocess.CalledProcessError as e:
            print(f"前端依赖安装失败: {e}")
            return
    
    # 启动前端开发服务器
    print("正在启动前端开发服务器...")
    try:
        subprocess.run(
            "npm run dev",
            cwd=frontend_dir,
            shell=True
        )
    except KeyboardInterrupt:
        print("前端开发服务器已停止")


if __name__ == "__main__":
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(settings.DATABASE_URL.replace("sqlite:///", "")), exist_ok=True)
    
    # 在后台线程中启动前端开发服务器
    frontend_thread = threading.Thread(target=start_frontend_dev_server, daemon=True)
    frontend_thread.start()
    
    # 等待前端服务器启动
    time.sleep(2)
    
    print("=" * 60)
    print(f"后端 API 服务器运行在: http://{settings.HOST}:{settings.PORT}")
    print("前端开发服务器运行在: http://localhost:3000")
    print("=" * 60)
    
    # 获取项目根目录
    project_root = Path(os.path.dirname(os.path.abspath(__file__)))
    
    # 配置需要监控的目录（排除 output、data、skills 等动态目录）
    reload_dirs = [
        str(project_root / "backend"),
        str(project_root / "main.py"),
    ]
    
    # 配置需要忽略的目录和文件
    reload_excludes = [
        "output/*",
        "data/*",
        "skills/*",
        ".venv/*",
        "frontend/node_modules/*",
        "frontend/dist/*",
        "*.pyc",
        "__pycache__/*",
        ".git/*",
        "*.db",
        "*.db-shm",
        "*.db-wal",
    ]
    
    # 启动后端 API 服务器
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        reload_dirs=reload_dirs,
        reload_excludes=reload_excludes,
        log_level="info"
    )
