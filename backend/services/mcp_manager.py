"""
MCP 管理器 - 标准化版本
基于 MCPClientState 实现完整的 MCP 协议握手流程
"""

from typing import Dict, List, Optional, Any
from langchain_core.tools import StructuredTool
import json
import asyncio
import threading

from backend.models.mcp_config import MCPConfig, MCPMode
from backend.services.mcp_client_state import MCPClientState


class AsyncExecutor:
    """异步执行器 - 在后台线程中运行事件循环
    
    用于解决 LangChain 同步工具与 MCP 异步客户端之间的调用问题。
    通过在后台线程中运行事件循环，可以满足 aiohttp 的 timeout 要求。
    """
    _instance = None
    _loop = None
    _thread = None
    _lock = threading.Lock()
    _ready = threading.Event()
    
    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._start_event_loop_thread()
        return cls._instance
    
    @classmethod
    def _start_event_loop_thread(cls):
        """启动事件循环线程"""
        def run_loop():
            cls._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls._loop)
            cls._ready.set()
            cls._loop.run_forever()
        
        cls._thread = threading.Thread(target=run_loop, daemon=True, name="MCPAsyncExecutor")
        cls._thread.start()
        cls._ready.wait(timeout=5)
        print(f"[DEBUG] AsyncExecutor - 事件循环线程已启动")
    
    @classmethod
    def run_coroutine(cls, coro, timeout=30):
        """在后台事件循环中运行协程
        
        Args:
            coro: 要运行的协程
            timeout: 超时时间（秒）
        
        Returns:
            协程的返回结果
        
        Raises:
            TimeoutError: 如果协程执行超时
            Exception: 如果协程执行失败
        """
        executor = cls.get_instance()
        future = asyncio.run_coroutine_threadsafe(coro, executor._loop)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise TimeoutError(f"协程执行超时（{timeout}秒）")
        except Exception as e:
            raise Exception(f"协程执行失败: {str(e)}")


class MCPManager:
    """MCP 管理器 - 标准化版本

    职责：
    - 管理 MCP 客户端状态（MCPClientState）
    - 将 MCP 工具转换为 LangChain 工具
    - 提供 MCP 连接测试和健康检查
    """

    def __init__(self):
        self.mcp_clients: Dict[str, MCPClientState] = {}  # mcp_id -> MCP 客户端状态
        self.mcp_tools: Dict[str, List[StructuredTool]] = {}  # mcp_id -> 工具列表

    def create_mcp_client(self, mcp_config: MCPConfig) -> Optional[MCPClientState]:
        """创建 MCP 客户端状态

        Args:
            mcp_config: MCP 配置

        Returns:
            MCP 客户端状态实例，如果失败返回 None
        """
        try:
            mcp_id = mcp_config.mcp_id
            mode = mcp_config.mode
            config = mcp_config.config

            print(f"[DEBUG] MCPManager - 创建 MCP 客户端状态: {mcp_id}, 模式: {mode}")

            # 创建客户端状态对象
            client_state = MCPClientState(mcp_config)

            # 存储客户端状态
            self.mcp_clients[mcp_id] = client_state
            print(f"[DEBUG] MCPManager - MCP 客户端状态创建成功: {mcp_id}")
            return client_state

        except Exception as e:
            print(f"[ERROR] MCPManager - 创建 MCP 客户端状态失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def get_mcp_tools(self, mcp_id: str, force_refresh: bool = False) -> List[StructuredTool]:
        """获取 MCP 的工具列表

        Args:
            mcp_id: MCP ID
            force_refresh: 是否强制刷新缓存

        Returns:
            工具列表
        """
        try:
            # 如果已缓存且不强制刷新，直接返回
            if not force_refresh and mcp_id in self.mcp_tools:
                print(f"[DEBUG] MCPManager - 使用缓存的工具: {mcp_id}, 工具数量: {len(self.mcp_tools[mcp_id])}")
                return self.mcp_tools[mcp_id]

            # 如果强制刷新，清除缓存
            if force_refresh and mcp_id in self.mcp_tools:
                del self.mcp_tools[mcp_id]
                print(f"[DEBUG] MCPManager - 清除缓存: {mcp_id}")

            # 获取 MCP 客户端状态
            if mcp_id not in self.mcp_clients:
                print(f"[ERROR] MCPManager - MCP 客户端不存在: {mcp_id}")
                return []

            client_state = self.mcp_clients[mcp_id]
            print(f"[DEBUG] MCPManager - 开始获取 MCP 工具: {mcp_id}")

            # 获取工具列表（自动处理初始化流程）
            tools_data = await client_state.get_tools()

            # 转换为 LangChain 工具
            tools = []
            for tool_data in tools_data:
                tool = self._convert_to_langchain_tool(
                    tool_data,
                    client_state,
                    client_state.mcp_config.description
                )
                if tool:
                    tools.append(tool)
                    print(f"[DEBUG] MCPManager - 成功转换工具: {tool.name}")

            # 缓存工具列表
            self.mcp_tools[mcp_id] = tools
            print(f"[DEBUG] MCPManager - 获取 MCP 工具成功: {mcp_id}, 工具数量: {len(tools)}")

            return tools

        except Exception as e:
            print(f"[ERROR] MCPManager - 获取 MCP 工具失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _convert_to_langchain_tool(self, tool_data: Dict[str, Any], client_state: MCPClientState, mcp_description: Optional[str] = None) -> Optional[StructuredTool]:
        """将 MCP 工具转换为 LangChain 工具

        Args:
            tool_data: MCP 工具数据
            client_state: 客户端状态
            mcp_description: MCP 配置中的描述（可选）

        Returns:
            LangChain StructuredTool
        """
        try:
            tool_name = tool_data.get("name")
            tool_description_from_server = tool_data.get("description", "")
            input_schema = tool_data.get("inputSchema", {})

            # 确定最终使用的描述，优先级：MCP配置的description > MCP工具返回的description > 默认描述
            final_description = ""
            description_source = ""

            if mcp_description and mcp_description.strip():
                # 使用 MCP 配置中的描述
                final_description = mcp_description.strip()
                description_source = "MCP配置"
            elif tool_description_from_server and tool_description_from_server.strip():
                # 使用 MCP 服务器返回的工具描述
                final_description = tool_description_from_server.strip()
                description_source = "MCP服务器"
            else:
                # 使用默认描述
                final_description = f"MCP工具: {tool_name}"
                description_source = "默认值"

            # 记录描述来源的详细日志
            print(f"[DEBUG] MCPManager - 工具描述处理: {tool_name}")
            print(f"[DEBUG] MCPManager -   MCP配置描述: {mcp_description if mcp_description else 'None'}")
            print(f"[DEBUG] MCPManager -   MCP服务器描述: {tool_description_from_server if tool_description_from_server else 'None'}")
            print(f"[DEBUG] MCPManager -   最终描述来源: {description_source}")
            print(f"[DEBUG] MCPManager -   最终描述内容: {final_description}")

            def execute_tool(**kwargs):
                """同步包装器，用于执行异步的 MCP 工具调用

                使用 AsyncExecutor 在后台事件循环中运行协程，满足 aiohttp 的 timeout 要求。
                """
                try:
                    print(f"[DEBUG] MCPManager - 开始执行工具: {tool_name}, 参数: {kwargs}")

                    # 使用 AsyncExecutor 在后台事件循环中运行协程
                    result = AsyncExecutor.run_coroutine(
                        client_state.call_tool(tool_name, kwargs),
                        timeout=60
                    )
                    print(f"[DEBUG] MCPManager - 工具执行完成: {tool_name}")

                    # 处理执行结果
                    if "error" in result:
                        print(f"[ERROR] MCPManager - 工具调用返回错误: {result['error']}")
                        raise Exception(result["error"])

                    result_str = str(result.get("result", ""))
                    print(f"[DEBUG] MCPManager - 工具执行成功: {tool_name}, 结果长度: {len(result_str)}")
                    return result_str

                except TimeoutError as e:
                    print(f"[ERROR] MCPManager - 工具执行超时: {tool_name}")
                    raise Exception(f"工具执行超时（60秒）: {tool_name}")
                except Exception as e:
                    print(f"[ERROR] MCPManager - 执行工具失败 [{tool_name}]: {e}")
                    import traceback
                    traceback.print_exc()
                    raise Exception(f"工具执行失败: {str(e)}")

            # 创建 StructuredTool
            tool = StructuredTool.from_function(
                func=execute_tool,  # 同步函数
                name=tool_name,
                description=final_description,
                args_schema=input_schema
            )

            print(f"[DEBUG] MCPManager - 成功创建 LangChain 工具: {tool_name}, 描述来源: {description_source}")
            return tool

        except Exception as e:
            print(f"[ERROR] MCPManager - 转换工具失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def execute_mcp_tool(self, mcp_id: str, tool_name: str, args: Dict[str, Any]) -> str:
        """执行 MCP 工具

        Args:
            mcp_id: MCP ID
            tool_name: 工具名称
            args: 工具参数

        Returns:
            执行结果
        """
        try:
            # 获取 MCP 客户端状态
            if mcp_id not in self.mcp_clients:
                print(f"[ERROR] MCPManager - MCP 客户端不存在: {mcp_id}")
                return f"MCP 客户端不存在: {mcp_id}"

            client_state = self.mcp_clients[mcp_id]

            # 调用工具
            result = await client_state.call_tool(tool_name, args)

            if "error" in result:
                print(f"[ERROR] MCPManager - 工具调用失败: {result['error']}")
                return f"工具调用失败: {result['error']}"

            return str(result.get("result", ""))

        except Exception as e:
            print(f"[ERROR] MCPManager - 执行工具失败: {e}")
            import traceback
            traceback.print_exc()
            return f"工具执行失败: {str(e)}"

    async def remove_mcp_client(self, mcp_id: str) -> bool:
        """移除 MCP 客户端（异步版本）

        Args:
            mcp_id: MCP ID

        Returns:
            是否移除成功
        """
        try:
            # 移除客户端
            if mcp_id in self.mcp_clients:
                # 使用 await 直接调用异步方法
                await self.mcp_clients[mcp_id].close()
                del self.mcp_clients[mcp_id]

            # 移除工具缓存
            if mcp_id in self.mcp_tools:
                del self.mcp_tools[mcp_id]

            print(f"[DEBUG] MCPManager - MCP 客户端已移除: {mcp_id}")
            return True

        except Exception as e:
            print(f"[ERROR] MCPManager - 移除 MCP 客户端失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_all_mcp_tools(self, mcp_configs: List[MCPConfig]) -> List[StructuredTool]:
        """获取所有 MCP 的工具列表（同步版本，用于向后兼容）

        Args:
            mcp_configs: MCP 配置列表

        Returns:
            所有工具列表
        """
        all_tools = []

        for mcp_config in mcp_configs:
            if not mcp_config.enabled:
                continue

            mcp_id = mcp_config.mcp_id

            # 如果工具已缓存，直接使用
            if mcp_id in self.mcp_tools:
                all_tools.extend(self.mcp_tools[mcp_id])
            else:
                # 创建客户端并获取工具
                self.create_mcp_client(mcp_config)
                # 注意：这里需要异步获取，暂时返回空列表
                # 实际使用时应该通过异步方法获取

        return all_tools

    async def test_mcp_connection(self, mcp_id: str) -> Dict[str, Any]:
        """测试 MCP 连接

        Args:
            mcp_id: MCP ID

        Returns:
            测试结果
        """
        try:
            if mcp_id not in self.mcp_clients:
                return {
                    "success": False,
                    "error": f"MCP 客户端不存在: {mcp_id}"
                }

            client_state = self.mcp_clients[mcp_id]

            # 测试初始化
            print(f"[DEBUG] MCPManager - 测试 MCP 初始化: {mcp_id}")
            if not await client_state.initialize():
                return {
                    "success": False,
                    "error": "初始化失败"
                }

            # 测试 initialized 通知
            print(f"[DEBUG] MCPManager - 测试 initialized 通知: {mcp_id}")
            if not await client_state.send_initialized_notification():
                return {
                    "success": False,
                    "error": "initialized 通知失败"
                }

            # 测试获取工具列表
            print(f"[DEBUG] MCPManager - 测试获取工具列表: {mcp_id}")
            tools_data = await client_state.get_tools()

            if not tools_data:
                return {
                    "success": False,
                    "error": "未发现任何工具"
                }

            # 测试工具调用（使用第一个工具）
            if tools_data:
                first_tool = tools_data[0]
                tool_name = first_tool.get("name")
                print(f"[DEBUG] MCPManager - 测试工具调用: {tool_name}")

                # 构造测试参数
                test_args = {}
                input_schema = first_tool.get("inputSchema", {})
                if "properties" in input_schema:
                    for prop_name, prop_info in input_schema["properties"].items():
                        if "default" in prop_info:
                            test_args[prop_name] = prop_info["default"]
                        elif prop_info.get("type") == "string":
                            test_args[prop_name] = "test"
                        elif prop_info.get("type") == "number":
                            test_args[prop_name] = 1

                result = await client_state.call_tool(tool_name, test_args)

                if "error" in result:
                    return {
                        "success": False,
                        "error": f"工具调用失败: {result['error']}"
                    }

            return {
                "success": True,
                "tools": tools_data,
                "tool_count": len(tools_data)
            }

        except Exception as e:
            print(f"[ERROR] MCPManager - 测试 MCP 连接失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    async def health_check(self, mcp_id: str) -> Dict[str, Any]:
        """健康检查

        Args:
            mcp_id: MCP ID

        Returns:
            健康状态
        """
        try:
            if mcp_id not in self.mcp_clients:
                return {
                    "healthy": False,
                    "error": "MCP 客户端不存在"
                }

            client_state = self.mcp_clients[mcp_id]

            # 检查连接是否过期
            if client_state.is_stale(max_age=3600):
                return {
                    "healthy": False,
                    "error": "连接已过期",
                    "stale": True
                }

            return {
                "healthy": True,
                "initialized": client_state.initialized,
                "session_id": client_state.session_id
            }

        except Exception as e:
            print(f"[ERROR] MCPManager - 健康检查失败: {e}")
            return {
                "healthy": False,
                "error": str(e)
            }


# 全局实例
mcp_manager = MCPManager()
