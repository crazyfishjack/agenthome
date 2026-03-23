"""
MCP 客户端状态管理
实现完整的 MCP 协议握手流程
"""

from typing import Dict, List, Optional, Any
import json
import asyncio
import httpx
from datetime import datetime

from backend.models.mcp_config import MCPConfig, MCPMode


class MCPClientState:
    """MCP 客户端状态管理类

    实现 MCP 协议的完整握手流程：
    1. initialize: 初始化连接
    2. notifications/initialized: 确认初始化
    3. tools/list: 获取工具列表
    4. tools/call: 调用工具
    """

    def __init__(self, mcp_config: MCPConfig):
        """初始化 MCP 客户端状态

        Args:
            mcp_config: MCP 配置
        """
        self.mcp_config = mcp_config
        self.mcp_id = mcp_config.mcp_id
        self.mode = mcp_config.mode
        self.config = mcp_config.config

        # 连接状态
        self.session_id: Optional[str] = None
        self.initialized: bool = False
        self.request_id: int = 0

        # HTTP 客户端（仅用于 remote 模式）
        self._http_client: Optional[httpx.AsyncClient] = None

        # 工具缓存
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
        self._tools_cache_time: Optional[datetime] = None

        print(f"[DEBUG] MCPClientState - 初始化: {self.mcp_id}, 模式: {self.mode}")

    async def initialize(self) -> bool:
        """初始化 MCP 连接

        Returns:
            是否初始化成功
        """
        try:
            if self.initialized:
                print(f"[DEBUG] MCPClientState - 已初始化: {self.mcp_id}")
                return True

            print(f"[DEBUG] MCPClientState - 开始初始化: {self.mcp_id}")

            if self.mode == MCPMode.REMOTE:
                success = await self._initialize_remote()
            elif self.mode == MCPMode.STDIO:
                success = await self._initialize_stdio()
            else:
                print(f"[ERROR] MCPClientState - 不支持的 MCP 模式: {self.mode}")
                return False

            if success:
                self.initialized = True
                print(f"[DEBUG] MCPClientState - 初始化成功: {self.mcp_id}")
            else:
                print(f"[ERROR] MCPClientState - 初始化失败: {self.mcp_id}")

            return success

        except Exception as e:
            print(f"[ERROR] MCPClientState - 初始化异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _initialize_remote(self) -> bool:
        """初始化 Remote 模式连接

        Returns:
            是否初始化成功
        """
        try:
            url = self.config.get("url")
            if not url:
                print(f"[ERROR] MCPClientState - Remote 模式缺少 url 配置")
                return False

            # 注意：不在这里创建 HTTP 客户端
            # HTTP 客户端将在第一次调用时在正确的事件循环中创建
            # 这样可以避免跨事件循环使用 aiohttp.ClientSession 的问题
            self._http_session = None

            # 构建 initialize 请求
            request = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "python-mcp-client",
                        "version": "1.0.0"
                    }
                }
            }

            # 发送请求
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }

            # 获取或创建 HTTP 客户端
            session = await self._get_http_session()
            response = await session.post(url, headers=headers, json=request)
            
            print(f"[DEBUG] MCPClientState - initialize 响应状态: {response.status_code}")

            if response.status_code != 200:
                error_text = response.text
                print(f"[ERROR] MCPClientState - initialize 失败: HTTP {response.status_code}, {error_text}")
                return False

            # 从响应头中获取 session ID
            self.session_id = response.headers.get('mcp-session-id')
            print(f"[DEBUG] MCPClientState - Session ID: {self.session_id}")

            # 解析响应
            result = response.json()
            print(f"[DEBUG] MCPClientState - initialize 响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

            return True

        except Exception as e:
            print(f"[ERROR] MCPClientState - Remote 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _initialize_stdio(self) -> bool:
        """初始化 Stdio 模式连接

        Returns:
            是否初始化成功
        """
        try:
            command = self.config.get("command")
            args = self.config.get("args", [])
            if not command:
                print(f"[ERROR] MCPClientState - Stdio 模式缺少 command 配置")
                return False

            # 启动进程
            import platform
            use_shell = platform.system() == "Windows"
            
            if use_shell:
                # Windows 上使用 shell 模式执行命令（支持 npx 等需要 shell 的命令）
                cmd_str = f"{command} {' '.join(args)}"
                self._process = await asyncio.create_subprocess_shell(
                    cmd_str,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                # 非 Windows 系统使用 exec 模式
                self._process = await asyncio.create_subprocess_exec(
                    command,
                    *args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

            # 构建 initialize 请求
            request = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "python-mcp-client",
                        "version": "1.0.0"
                    }
                }
            }

            # 发送请求
            request_json = json.dumps(request) + "\n"
            self._process.stdin.write(request_json.encode())
            await self._process.stdin.drain()

            # 读取响应
            response_line = await self._process.stdout.readline()
            response = json.loads(response_line.decode())

            print(f"[DEBUG] MCPClientState - initialize 响应: {json.dumps(response, indent=2, ensure_ascii=False)}")

            return True
        except Exception as e:
            print(f"[ERROR] MCPClientState - Stdio 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def send_initialized_notification(self) -> bool:
        """发送 initialized 通知

        Returns:
            是否发送成功
        """
        try:
            print(f"[DEBUG] MCPClientState - 发送 initialized 通知: {self.mcp_id}")

            request = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }

            if self.mode == MCPMode.REMOTE:
                success = await self._send_remote_notification(request)
            elif self.mode == MCPMode.STDIO:
                success = await self._send_stdio_notification(request)
            else:
                print(f"[ERROR] MCPClientState - 不支持的 MCP 模式: {self.mode}")
                return False

            if success:
                print(f"[DEBUG] MCPClientState - initialized 通知发送成功: {self.mcp_id}")

            return success

        except Exception as e:
            print(f"[ERROR] MCPClientState - 发送 initialized 通知失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _send_remote_notification(self, request: Dict[str, Any]) -> bool:
        """发送 Remote 模式通知

        Args:
            request: 请求对象

        Returns:
            是否发送成功
        """
        try:
            url = self.config.get("url")

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }

            # 添加 session ID
            if self.session_id:
                headers["mcp-session-id"] = self.session_id

            session = await self._get_http_session()
            response = await session.post(url, headers=headers, json=request)
            
            print(f"[DEBUG] MCPClientState - 通知响应状态: {response.status_code}")
            return response.status_code == 200

        except Exception as e:
            print(f"[ERROR] MCPClientState - 发送 Remote 通知失败: {e}")
            return False

    async def _send_stdio_notification(self, request: Dict[str, Any]) -> bool:
        """发送 Stdio 模式通知

        Args:
            request: 请求对象

        Returns:
            是否发送成功
        """
        try:
            request_json = json.dumps(request) + "\n"
            self._process.stdin.write(request_json.encode())
            await self._process.stdin.drain()

            return True

        except Exception as e:
            print(f"[ERROR] MCPClientState - 发送 Stdio 通知失败: {e}")
            return False

    async def get_tools(self) -> List[Dict[str, Any]]:
        """获取工具列表

        Returns:
            工具列表
        """
        try:
            # 确保已初始化
            if not self.initialized:
                if not await self.initialize():
                    print(f"[ERROR] MCPClientState - 无法获取工具，初始化失败: {self.mcp_id}")
                    return []

            # 发送 initialized 通知
            if not await self.send_initialized_notification():
                print(f"[WARNING] MCPClientState - initialized 通知发送失败，继续获取工具: {self.mcp_id}")

            print(f"[DEBUG] MCPClientState - 获取工具列表: {self.mcp_id}")

            # 构建 tools/list 请求
            request = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/list"
            }

            if self.mode == MCPMode.REMOTE:
                tools_data = await self._get_remote_tools(request)
            elif self.mode == MCPMode.STDIO:
                tools_data = await self._get_stdio_tools(request)
            else:
                print(f"[ERROR] MCPClientState - 不支持的 MCP 模式: {self.mode}")
                return []

            # 缓存工具列表
            self._tools_cache = tools_data
            self._tools_cache_time = datetime.now()

            print(f"[DEBUG] MCPClientState - 获取到 {len(tools_data)} 个工具: {self.mcp_id}")
            return tools_data

        except Exception as e:
            print(f"[ERROR] MCPClientState - 获取工具列表失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _get_remote_tools(self, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取 Remote 模式的工具列表

        Args:
            request: 请求对象

        Returns:
            工具列表
        """
        try:
            url = self.config.get("url")

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }

            # 添加 session ID
            if self.session_id:
                headers["mcp-session-id"] = self.session_id

            session = await self._get_http_session()
            response = await session.post(url, headers=headers, json=request)
            
            print(f"[DEBUG] MCPClientState - tools/list 响应状态: {response.status_code}")

            if response.status_code != 200:
                error_text = response.text
                print(f"[ERROR] MCPClientState - tools/list 失败: HTTP {response.status_code}, {error_text}")
                return []

            result = response.json()
            tools_data = result.get("result", {}).get("tools", [])

            print(f"[DEBUG] MCPClientState - 获取到 {len(tools_data)} 个工具")
            return tools_data

        except Exception as e:
            print(f"[ERROR] MCPClientState - 获取 Remote 工具失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _get_stdio_tools(self, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取 Stdio 模式的工具列表

        Args:
            request: 请求对象

        Returns:
            工具列表
        """
        try:
            request_json = json.dumps(request) + "\n"
            self._process.stdin.write(request_json.encode())
            await self._process.stdin.drain()

            response_line = await self._process.stdout.readline()
            response = json.loads(response_line.decode())

            tools_data = response.get("result", {}).get("tools", [])

            print(f"[DEBUG] MCPClientState - 获取到 {len(tools_data)} 个工具")
            return tools_data

        except Exception as e:
            print(f"[ERROR] MCPClientState - 获取 Stdio 工具失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            调用结果
        """
        try:
            # 确保已初始化
            if not self.initialized:
                if not await self.initialize():
                    return {"error": f"MCP 客户端未初始化: {self.mcp_id}"}

            print(f"[DEBUG] MCPClientState - 调用工具: {self.mcp_id}.{tool_name}")

            # 构建 tools/call 请求
            request = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            if self.mode == MCPMode.REMOTE:
                result = await self._call_remote_tool(request)
            elif self.mode == MCPMode.STDIO:
                result = await self._call_stdio_tool(request)
            else:
                return {"error": f"不支持的 MCP 模式: {self.mode}"}

            return result

        except Exception as e:
            print(f"[ERROR] MCPClientState - 调用工具失败: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    async def _call_remote_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """调用 Remote 模式的工具

        Args:
            request: 请求对象

        Returns:
            调用结果
        """
        max_retries = 10
        last_error = None

        for attempt in range(max_retries):
            try:
                url = self.config.get("url")

                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }

                # 添加 session ID
                if self.session_id:
                    headers["mcp-session-id"] = self.session_id

                session = await self._get_http_session()
                response = await session.post(url, headers=headers, json=request)

                print(f"[DEBUG] MCPClientState - tools/call 响应状态: {response.status_code}")

                if response.status_code != 200:
                    error_text = response.text
                    print(f"[ERROR] MCPClientState - tools/call 失败: HTTP {response.status_code}, {error_text}")
                    last_error = f"HTTP {response.status_code}: {error_text}"
                    
                    # 如果不是最后一次尝试，则进行重试
                    if attempt < max_retries - 1:
                        print(f"[RETRY] MCPClientState - 第 {attempt + 1}/{max_retries} 次重试，立即重试...")
                        continue
                    else:
                        return {"error": last_error}

                result = response.json()

                if "error" in result:
                    print(f"[ERROR] MCPClientState - 工具调用错误: {result['error']}")
                    last_error = result["error"]
                    
                    # 如果不是最后一次尝试，则进行重试
                    if attempt < max_retries - 1:
                        print(f"[RETRY] MCPClientState - 第 {attempt + 1}/{max_retries} 次重试，立即重试...")
                        continue
                    else:
                        return {"error": last_error}

                # 成功调用，返回结果
                print(f"[DEBUG] MCPClientState - 工具调用成功")
                return result

            except Exception as e:
                print(f"[ERROR] MCPClientState - 调用 Remote 工具失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                last_error = str(e)
                import traceback
                traceback.print_exc()
                
                # 如果不是最后一次尝试，则进行重试
                if attempt < max_retries - 1:
                    print(f"[RETRY] MCPClientState - 第 {attempt + 1}/{max_retries} 次重试，立即重试...")
                else:
                    print(f"[ERROR] MCPClientState - 已达到最大重试次数 {max_retries}，放弃重试")
                    return {"error": last_error}

        # 理论上不会执行到这里，但为了安全起见
        return {"error": last_error}

    async def _call_stdio_tool(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """调用 Stdio 模式的工具

        Args:
            request: 请求对象

        Returns:
            调用结果
        """
        try:
            request_json = json.dumps(request) + "\n"
            self._process.stdin.write(request_json.encode())
            await self._process.stdin.drain()

            response_line = await self._process.stdout.readline()
            response = json.loads(response_line.decode())

            if "error" in response:
                print(f"[ERROR] MCPClientState - 工具调用错误: {response['error']}")
                return {"error": response["error"]}

            return response

        except Exception as e:
            print(f"[ERROR] MCPClientState - 调用 Stdio 工具失败: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    async def close(self) -> None:
        """关闭连接"""
        try:
            print(f"[DEBUG] MCPClientState - 关闭连接: {self.mcp_id}")

            # 关闭 HTTP 客户端
            if self._http_client:
                await self._http_client.aclose()
                self._http_client = None

            # 关闭进程
            if hasattr(self, '_process') and self._process:
                self._process.terminate()
                await self._process.wait()

            # 重置状态
            self.session_id = None
            self.initialized = False
            self._tools_cache = None
            self._tools_cache_time = None

            print(f"[DEBUG] MCPClientState - 连接已关闭: {self.mcp_id}")

        except Exception as e:
            print(f"[ERROR] MCPClientState - 关闭连接失败: {e}")
            import traceback
            traceback.print_exc()

    async def _get_http_session(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端
        
        确保在当前事件循环中创建 client，避免跨事件循环使用的问题。
        使用 httpx 替代 aiohttp，因为 httpx 对跨事件循环使用更友好。
        
        Returns:
            httpx.AsyncClient 实例
        """
        if self._http_client is None:
            # 设置超时时间为10秒
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=10.0,
                    read=10.0,
                    write=10.0,
                    pool=10.0
                )
            )
            print(f"[DEBUG] MCPClientState - 创建新的 HTTP client，超时时间: 10秒")
        return self._http_client

    def is_stale(self, max_age: int = 3600) -> bool:
        """检查连接是否过期

        Args:
            max_age: 最大存活时间（秒），默认 1 小时

        Returns:
            是否过期
        """
        if not self._tools_cache_time:
            return True

        age = (datetime.now() - self._tools_cache_time).total_seconds()
        return age > max_age

    def _next_id(self) -> int:
        """生成下一个请求 ID

        Returns:
            请求 ID
        """
        self.request_id += 1
        return self.request_id
