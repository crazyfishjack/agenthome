"""
Task Pro 工具 - 可视化 SUB agent 调用

基于官方 task 工具源码扩展，添加流式输出和可视化功能。
支持 Human-in-the-loop 中断恢复机制。
"""

import asyncio
import json
import uuid
import time
import threading
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable
from concurrent.futures import Future
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import StructuredTool
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

from backend.tools.tool_base import ToolBase
from backend.db.subagent_db import get_subagent_db


# 全局 SUB Agent 中断管理器
# key: execution_id, value: {"decision": "approve"/"reject", "event": threading.Event}
# 使用 threading.Event 实现线程间通信（因为 SUB agent 运行在新线程中）
subagent_interrupt_manager: Dict[str, Dict] = {}


# 输入参数 Schema
class TaskProInput(BaseModel):
    """Task Pro 工具输入参数"""
    description: str = Field(
        description="任务的详细描述，包含所有必要的上下文和期望的输出格式"
    )
    subagent_type: str = Field(
        description="要使用的 SUB agent 类型，必须是可用 agent 类型之一"
    )
    show_thinking: bool = Field(
        default=True,
        description="是否显示 SUB agent 的思考过程"
    )
    execution_id: str = Field(
        default="",
        description="pre_task_pro 工具返回的 execution_id，必须先调用 pre_task_pro 获取"
    )


# 被排除的状态键（与官方保持一致）
_EXCLUDED_STATE_KEYS = {
    "messages",
    "todos",
    "structured_response",
    "skills_metadata",
    "memory_contents"
}

class TaskProTool(ToolBase):
    """
    Task Pro 工具 - 增强版 SUB agent 调用工具

    特性：
    1. 流式执行 SUB agent，实时查看执行过程
    2. 支持思考过程、工具调用、中断事件的实时输出
    3. 与原版 task 工具完全兼容的参数接口
    4. 支持取消操作，可响应主 agent 的取消信号

    使用方式：
    ```
    task_pro(
        description="搜索关于 Python 异步编程的资料",
        subagent_type="general-purpose",
        show_thinking=True
    )
    ```
    """

    def __init__(self, subagent_registry: Optional[Dict[str, Runnable]] = None, cancel_event: Optional[asyncio.Event] = None):
        """
        初始化 Task Pro 工具

        Args:
            subagent_registry: SUB agent 注册表，{name: runnable}
            cancel_event: 取消事件，用于接收主 agent 的取消信号
        """
        super().__init__()
        self.subagent_registry = subagent_registry or {}
        self._stream_callback: Optional[Callable] = None
        self._cancel_event: Optional[asyncio.Event] = cancel_event

    @property
    def name(self) -> str:
        return "task_pro"

    @property
    def description(self) -> str:
        available_agents = ", ".join(self.subagent_registry.keys()) if self.subagent_registry else "暂无可用Sub Agent"
        return f"""【第二步】执行 Task Pro 任务，启动 SUB agent 处理复杂任务。

【前置要求 - 必须遵守】
⚠️ 必须先调用 pre_task_pro 工具获取 execution_id！
⚠️ 不要直接调用 task_pro，跳过 pre_task_pro！

【当前可用的 Sub Agent 名称】
{available_agents}

【使用流程】
1. 调用 pre_task_pro(description=..., subagent_type=...) 获取 execution_id
2. 调用 task_pro(description=..., subagent_type=..., execution_id=返回的id) 执行任务

【示例】
→ 调用 pre_task_pro(description="调研 AI 行业", subagent_type="researcher")
→ 获取 execution_id: "taskpro_xxx"
→ 【立即】调用 task_pro(description="调研 AI 行业", subagent_type="researcher", execution_id="taskpro_xxx")

⚠️ 重要提示：
- execution_id 参数必须提供，且必须来自 pre_task_pro 的返回值
- subagent_type 必须是上面列出的可用 Sub Agent 名称之一
- 其他参数必须与 pre_task_pro 调用的参数完全一致
- 此工具会同步执行，可能需要较长时间，请耐心等待
"""

    @property
    def parameter_requirements(self) -> str:
        return """- description: 任务的详细描述，包含上下文和期望输出（必须与 pre_task_pro 相同）
- subagent_type: SUB agent 类型（如 general-purpose, researcher, code-reviewer 等，必须与 pre_task_pro 相同）
- show_thinking: 是否显示思考过程（可选，默认 true，必须与 pre_task_pro 相同）
- execution_id: pre_task_pro 工具返回的执行 ID（必填！必须先调用 pre_task_pro 获取）"""

    @property
    def format_requirements(self) -> str:
        return """- description 应尽可能详细，包含所有必要上下文
- subagent_type 必须是可用的 agent 类型之一
- execution_id 必须来自 pre_task_pro 的返回值，不能为空
- 所有参数必须与 pre_task_pro 调用的参数完全一致"""

    @property
    def examples(self) -> List[str]:
        return [
            'task_pro(description="搜索 Python 异步编程资料", subagent_type="general-purpose", execution_id="taskpro_xxx")',
            'task_pro(description="分析代码中的 bug", subagent_type="code-reviewer", show_thinking=True, execution_id="taskpro_xxx")',
            'task_pro(description="调研 AI 行业现状", subagent_type="researcher", execution_id="taskpro_xxx")'
        ]

    @property
    def input_schema(self):
        return TaskProInput

    def set_stream_callback(self, callback: Callable):
        """
        设置流式输出回调函数

        Args:
            callback: 回调函数，接收 (event_type, data) 参数
        """
        self._stream_callback = callback

    def set_subagent_registry(self, subagent_registry: Dict[str, Runnable]):
        """
        设置 SUB agent 注册表

        Args:
            subagent_registry: SUB agent 注册表，{name: runnable}
        """
        self.subagent_registry = subagent_registry

    def set_cancel_event(self, cancel_event: Optional[asyncio.Event]):
        """
        设置取消事件

        Args:
            cancel_event: 取消事件，用于接收主 agent 的取消信号
        """
        self._cancel_event = cancel_event

    def _is_cancelled(self) -> bool:
        """
        检查是否已取消

        Returns:
            如果已取消返回 True，否则返回 False
        """
        return self._cancel_event is not None and self._cancel_event.is_set()

    async def _wait_for_user_decision(self, execution_id: str) -> str:
        """
        等待用户对 SUB Agent 中断的决策

        使用 threading.Event 实现线程间通信，因为 SUB agent 运行在新线程中，
        而 API 端点在主线程中执行。

        Args:
            execution_id: 执行 ID

        Returns:
            "approve" 或 "reject"
        """
        global subagent_interrupt_manager

        # 创建线程安全的中断事件
        interrupt_event = threading.Event()
        subagent_interrupt_manager[execution_id] = {
            "decision": None,
            "event": interrupt_event
        }

        print(f"[DEBUG] task_pro_tool.py - 等待用户决策: execution_id={execution_id}")

        try:
            # 等待用户决策（5分钟超时）
            # 使用 asyncio.to_thread 将同步的 threading.Event.wait() 包装为异步
            await asyncio.wait_for(
                asyncio.to_thread(interrupt_event.wait, timeout=300),
                timeout=300
            )

            # 检查是否超时（event.wait 返回 False 表示超时）
            if not interrupt_event.is_set():
                print(f"[DEBUG] task_pro_tool.py - 用户决策超时，自动拒绝: execution_id={execution_id}")
                return "reject"

            decision = subagent_interrupt_manager[execution_id]["decision"]
            print(f"[DEBUG] task_pro_tool.py - 收到用户决策: {decision}")
            return decision or "reject"  # 默认拒绝
        except asyncio.TimeoutError:
            print(f"[DEBUG] task_pro_tool.py - 用户决策超时，自动拒绝: execution_id={execution_id}")
            return "reject"
        except Exception as e:
            print(f"[ERROR] task_pro_tool.py - 等待决策异常: {e}")
            return "reject"
        finally:
            # 清理
            if execution_id in subagent_interrupt_manager:
                del subagent_interrupt_manager[execution_id]
                print(f"[DEBUG] task_pro_tool.py - 清理中断管理器: execution_id={execution_id}")

    async def _wait_for_user_decision_with_cancel(self, execution_id: str) -> str:
        """
        等待用户对 SUB Agent 中断的决策，同时检查取消信号

        与 _wait_for_user_decision 的区别是，此方法会同时监听取消事件，
        如果主 agent 发出取消信号，则返回 "cancelled"。

        Args:
            execution_id: 执行 ID

        Returns:
            "approve"、"reject" 或 "cancelled"
        """
        global subagent_interrupt_manager

        # 创建线程安全的中断事件
        interrupt_event = threading.Event()
        subagent_interrupt_manager[execution_id] = {
            "decision": None,
            "event": interrupt_event
        }

        print(f"[DEBUG] task_pro_tool.py - 等待用户决策（支持取消）: execution_id={execution_id}")

        try:
            # 循环等待，同时检查取消信号
            start_time = time.time()
            timeout = 300  # 5分钟超时

            while time.time() - start_time < timeout:
                # 检查是否被取消
                if self._is_cancelled():
                    print(f"[DEBUG] task_pro_tool.py - 等待决策时检测到取消信号: execution_id={execution_id}")
                    return "cancelled"

                # 检查用户是否已做出决策
                if interrupt_event.is_set():
                    decision = subagent_interrupt_manager[execution_id]["decision"]
                    print(f"[DEBUG] task_pro_tool.py - 收到用户决策: {decision}")
                    return decision or "reject"

                # 短暂等待后再次检查
                await asyncio.sleep(0.1)

            # 超时
            print(f"[DEBUG] task_pro_tool.py - 用户决策超时，自动拒绝: execution_id={execution_id}")
            return "reject"

        except Exception as e:
            print(f"[ERROR] task_pro_tool.py - 等待决策异常: {e}")
            return "reject"
        finally:
            # 清理
            if execution_id in subagent_interrupt_manager:
                del subagent_interrupt_manager[execution_id]
                print(f"[DEBUG] task_pro_tool.py - 清理中断管理器: execution_id={execution_id}")

    async def _stream_subagent_with_checkpoint(
        self,
        subagent: Runnable,
        subagent_state: Dict,
        show_thinking: bool,
        execution_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式执行 SUB agent，支持 Human-in-the-loop 中断恢复

        Args:
            subagent: SUB agent 的可运行对象
            subagent_state: 初始状态
            show_thinking: 是否显示思考过程
            execution_id: 执行 ID（用于 checkpoint 隔离）

        Yields:
            事件字典，包含 type 和 data
        """
        from deepagents import create_deep_agent

        # 创建内存 checkpoint（每个 execution 独立）
        memory_saver = MemorySaver()

        # 使用 execution_id 作为 thread_id
        thread_id = execution_id
        config = {"configurable": {"thread_id": thread_id}}

        print(f"[DEBUG] task_pro_tool.py - 创建带 checkpoint 的 SUB agent: execution_id={execution_id}")

        # 从原 subagent 中提取配置并重新创建带 checkpoint 的实例
        # 注意：CompiledSubAgent 内部包含了一个 runnable（deepagent）
        # 我们需要提取其配置并重新创建
        try:
            # 尝试获取原 subagent 的配置
            # CompiledSubAgent 结构: {name, description, runnable}
            if hasattr(subagent, 'runnable'):
                original_runnable = subagent.runnable
            else:
                original_runnable = subagent

            # 提取 LLM、tools、system_prompt 等配置
            # 这些配置通常在创建 deepagent 时设置
            # 由于无法直接提取，我们使用原始 subagent 的 astream 方法
            # 但通过包装器添加 checkpoint 支持

            # 创建包装函数，使用内存 checkpoint
            # 实际上我们需要重新编译 subagent
            # 这里我们直接使用原始 subagent，但在 config 中传入 checkpoint
            # 但原始 subagent 可能没有绑定 checkpoint

            # 替代方案：直接执行，但在检测到中断时暂停等待
            print(f"[DEBUG] task_pro_tool.py - 使用原始 subagent 执行（添加中断处理）")

        except Exception as e:
            print(f"[WARNING] task_pro_tool.py - 提取 subagent 配置失败: {e}")

        # 发送开始事件
        yield {
            "type": "subagent_start",
            "data": {"state_keys": list(subagent_state.keys()), "execution_id": execution_id}
        }

        # 收集完整消息历史
        all_messages = []
        final_state = {}

        # 执行状态跟踪
        is_interrupted = False
        input_data = subagent_state
        max_iterations = 10  # 防止无限循环
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            is_interrupted = False

            try:
                async for chunk in subagent.astream(input_data, config=config):
                    # 检查取消事件 - 在每次处理 chunk 前检查
                    if self._is_cancelled():
                        print(f"[DEBUG] task_pro_tool.py - SUB agent 检测到取消信号，停止执行: execution_id={execution_id}")
                        yield {
                            "type": "subagent_cancelled",
                            "data": {"message": "Task was cancelled by user", "execution_id": execution_id}
                        }
                        return

                    # 解析不同类型的 chunk

                    # 1. Model 节点输出（AI 思考/回复）
                    if 'model' in chunk and 'messages' in chunk['model']:
                        messages = chunk['model']['messages']
                        for msg in messages:
                            if isinstance(msg, AIMessage):
                                all_messages.append(msg)

                                # 检查是否有工具调用
                                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                    for tool_call in msg.tool_calls:
                                        yield {
                                            "type": "subagent_tool_call_request",
                                            "data": {
                                                "name": tool_call.get('name'),
                                                "args": tool_call.get('args')
                                            }
                                        }
                                elif show_thinking and msg.content:
                                    # AI 思考内容
                                    yield {
                                        "type": "subagent_thinking",
                                        "data": {"content": msg.content}
                                    }

                    # 2. Tools 节点输出（工具执行结果）
                    elif 'tools' in chunk:
                        tools_data = chunk['tools']

                        # 处理消息
                        if 'messages' in tools_data:
                            for msg in tools_data['messages']:
                                if isinstance(msg, ToolMessage):
                                    yield {
                                        "type": "subagent_tool_result",
                                        "data": {
                                            "name": msg.name,
                                            "content": msg.content if isinstance(msg.content, str) else str(msg.content)
                                        }
                                    }

                        # 处理 todos
                        if 'todos' in tools_data:
                            yield {
                                "type": "subagent_todos_update",
                                "data": {"todos": tools_data['todos']}
                            }

                    # 3. 中间件节点输出
                    elif 'TodoListMiddleware.after_model' in chunk:
                        todo_list = chunk.get('TodoListMiddleware.after_model')
                        if todo_list:
                            yield {
                                "type": "subagent_todos_update",
                                "data": {"todos": todo_list}
                            }

                    # 4. 中断事件 - 关键部分
                    elif '__interrupt__' in chunk:
                        interrupt_obj = chunk.get('__interrupt__')
                        if isinstance(interrupt_obj, tuple) and len(interrupt_obj) > 0:
                            interrupt_obj = interrupt_obj[0]

                        if interrupt_obj and hasattr(interrupt_obj, 'value'):
                            interrupt_value = interrupt_obj.value
                            print(f"[DEBUG] task_pro_tool.py - 检测到中断事件: execution_id={execution_id}")

                            # 发送中断事件到前端
                            yield {
                                "type": "subagent_interrupt",
                                "data": interrupt_value
                            }

                            # 等待用户决策（同时检查取消）
                            decision = await self._wait_for_user_decision_with_cancel(execution_id)

                            # 如果取消，直接退出
                            if decision == "cancelled":
                                print(f"[DEBUG] task_pro_tool.py - 用户取消，停止执行: execution_id={execution_id}")
                                yield {
                                    "type": "subagent_cancelled",
                                    "data": {"message": "Task was cancelled by user", "execution_id": execution_id}
                                }
                                return

                            # 根据决策准备恢复命令
                            if decision == "approve":
                                print(f"[DEBUG] task_pro_tool.py - 用户同意，准备恢复执行")
                                yield {
                                    "type": "subagent_thinking",
                                    "data": {"content": "用户同意了工具执行"}
                                }
                                resume_value = {"decisions": [{"type": "approve"}]}
                            else:
                                print(f"[DEBUG] task_pro_tool.py - 用户拒绝，准备恢复执行")
                                yield {
                                    "type": "subagent_thinking",
                                    "data": {"content": "用户拒绝了工具执行"}
                                }
                                resume_value = {"decisions": [{"type": "reject", "message": "用户拒绝了工具执行"}]}

                            # 使用 Command 恢复执行
                            input_data = Command(resume=resume_value)
                            is_interrupted = True
                            break  # 跳出 for 循环，使用新的 input_data 重新开始

                    # 收集状态更新
                    for key, value in chunk.items():
                        if key not in ['model', 'tools', '__interrupt__']:
                            final_state[key] = value

            except Exception as e:
                print(f"[ERROR] task_pro_tool.py - 流式执行异常: {e}")
                import traceback
                traceback.print_exc()
                yield {
                    "type": "subagent_error",
                    "data": {"error": str(e)}
                }
                return

            # 检查取消事件 - 在每次循环迭代结束时检查
            if self._is_cancelled():
                print(f"[DEBUG] task_pro_tool.py - SUB agent 检测到取消信号（循环结束），停止执行: execution_id={execution_id}")
                yield {
                    "type": "subagent_cancelled",
                    "data": {"message": "Task was cancelled by user", "execution_id": execution_id}
                }
                return

            # 如果没有中断，正常完成
            if not is_interrupted:
                break

        # 发送完成事件
        yield {
            "type": "subagent_complete",
            "data": {
                "messages_count": len(all_messages),
                "final_state_keys": list(final_state.keys())
            }
        }

        # 返回最终结果
        yield {
            "type": "subagent_result",
            "data": {
                "messages": all_messages,
                "final_state": final_state
            }
        }

    async def _stream_subagent(
        self,
        subagent: Runnable,
        subagent_state: Dict,
        show_thinking: bool
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式执行 SUB agent，实时产生事件（兼容旧版本）

        Args:
            subagent: SUB agent 的可运行对象
            subagent_state: 初始状态
            show_thinking: 是否显示思考过程

        Yields:
            事件字典，包含 type 和 data
        """
        # 发送开始事件
        yield {
            "type": "subagent_start",
            "data": {"state_keys": list(subagent_state.keys())}
        }

        # 收集完整消息历史
        all_messages = []
        final_state = {}

        # 流式执行
        try:
            async for chunk in subagent.astream(subagent_state):
                # 解析不同类型的 chunk

                # 1. Model 节点输出（AI 思考/回复）
                if 'model' in chunk and 'messages' in chunk['model']:
                    messages = chunk['model']['messages']
                    for msg in messages:
                        if isinstance(msg, AIMessage):
                            all_messages.append(msg)

                            # 检查是否有工具调用
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                for tool_call in msg.tool_calls:
                                    yield {
                                        "type": "subagent_tool_call_request",
                                        "data": {
                                            "name": tool_call.get('name'),
                                            "args": tool_call.get('args')
                                        }
                                    }
                            elif show_thinking and msg.content:
                                # AI 思考内容
                                yield {
                                    "type": "subagent_thinking",
                                    "data": {"content": msg.content}
                                }

                # 2. Tools 节点输出（工具执行结果）
                elif 'tools' in chunk:
                    tools_data = chunk['tools']

                    # 处理消息
                    if 'messages' in tools_data:
                        for msg in tools_data['messages']:
                            if isinstance(msg, ToolMessage):
                                yield {
                                    "type": "subagent_tool_result",
                                    "data": {
                                        "name": msg.name,
                                        "content": msg.content if isinstance(msg.content, str) else str(msg.content)
                                    }
                                }

                    # 处理 todos
                    if 'todos' in tools_data:
                        yield {
                            "type": "subagent_todos_update",
                            "data": {"todos": tools_data['todos']}
                        }

                # 3. 中间件节点输出
                elif 'TodoListMiddleware.after_model' in chunk:
                    todo_list = chunk.get('TodoListMiddleware.after_model')
                    if todo_list:
                        yield {
                            "type": "subagent_todos_update",
                            "data": {"todos": todo_list}
                        }

                # 4. 中断事件
                elif '__interrupt__' in chunk:
                    interrupt_obj = chunk.get('__interrupt__')
                    if isinstance(interrupt_obj, tuple) and len(interrupt_obj) > 0:
                        interrupt_obj = interrupt_obj[0]

                    if interrupt_obj and hasattr(interrupt_obj, 'value'):
                        yield {
                            "type": "subagent_interrupt",
                            "data": interrupt_obj.value
                        }

                # 收集状态更新
                for key, value in chunk.items():
                    if key not in ['model', 'tools', '__interrupt__']:
                        final_state[key] = value

        except Exception as e:
            yield {
                "type": "subagent_error",
                "data": {"error": str(e)}
            }
            return

        # 发送完成事件
        yield {
            "type": "subagent_complete",
            "data": {
                "messages_count": len(all_messages),
                "final_state_keys": list(final_state.keys())
            }
        }

        # 返回最终结果
        yield {
            "type": "subagent_result",
            "data": {
                "messages": all_messages,
                "final_state": final_state
            }
        }

    async def execute_stream(
        self,
        description: str,
        subagent_type: str,
        show_thinking: bool = True,
        runtime_state: Optional[Dict] = None,
        tool_call_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式执行 Task Pro

        这是主要的执行入口，产生流式输出事件。
        支持 Human-in-the-loop 中断恢复机制。

        Args:
            description: 任务描述
            subagent_type: SUB agent 类型
            show_thinking: 是否显示思考过程
            runtime_state: 运行时状态（包含父 agent 的状态）
            tool_call_id: 工具调用 ID
            execution_id: 执行 ID（用于 checkpoint 隔离和中断管理）

        Yields:
            事件字典，包含 type 和 data
        """
        # 1. 验证 subagent 类型
        if subagent_type not in self.subagent_registry:
            available = ", ".join(self.subagent_registry.keys())
            error_msg = f"未知的 subagent 类型: {subagent_type}。可用类型: {available}"
            yield {
                "type": "subagent_error",
                "data": {"error": error_msg}
            }
            return

        # 2. 获取 subagent
        subagent = self.subagent_registry[subagent_type]

        # 3. 准备状态（与官方 task 保持一致）
        subagent_state = {}
        if runtime_state:
            # 复制状态，排除特定键
            subagent_state = {
                k: v for k, v in runtime_state.items()
                if k not in _EXCLUDED_STATE_KEYS
            }

        # 创建新的消息列表
        subagent_state["messages"] = [HumanMessage(content=description)]

        # 4. 发送准备就绪事件
        yield {
            "type": "subagent_ready",
            "data": {
                "subagent_type": subagent_type,
                "description_preview": description[:100] + "..." if len(description) > 100 else description,
                "execution_id": execution_id
            }
        }

        # 5. 流式执行（使用带 checkpoint 的版本，如果提供了 execution_id）
        result_data = None

        # 根据是否有 execution_id 选择执行方式
        # 有 execution_id 时，使用带 Human-in-the-loop 支持的版本
        if execution_id:
            print(f"[DEBUG] task_pro_tool.py - 使用带 checkpoint 的执行方式: execution_id={execution_id}")
            stream_generator = self._stream_subagent_with_checkpoint(
                subagent, subagent_state, show_thinking, execution_id
            )
        else:
            print(f"[DEBUG] task_pro_tool.py - 使用普通执行方式（无 checkpoint）")
            stream_generator = self._stream_subagent(subagent, subagent_state, show_thinking)

        async for event in stream_generator:
            # 通过回调发送实时事件
            if self._stream_callback:
                try:
                    if asyncio.iscoroutinefunction(self._stream_callback):
                        await self._stream_callback(event['type'], event['data'])
                    else:
                        self._stream_callback(event['type'], event['data'])
                except Exception as e:
                    print(f"[WARNING] task_pro_tool.py - 流式回调失败: {e}")

            # 保存结果事件
            if event['type'] == 'subagent_result':
                result_data = event['data']

            # Yield 事件
            yield event

        # 6. 构建最终返回结果
        if result_data and result_data.get('messages'):
            messages = result_data['messages']
            if messages:
                # 取最后一条 AI 消息作为结果
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage) and msg.content:
                        final_result = msg.content.rstrip()
                        yield {
                            "type": "subagent_final_result",
                            "data": {"result": final_result}
                        }
                        break

    def execute(self, input_str: str) -> str:
        """
        同步执行（不推荐，仅用于兼容）

        Task Pro 主要设计为异步流式执行，同步方法仅返回提示信息。
        """
        return "Task Pro 工具需要异步流式执行，请使用 execute_stream 方法。"

    def _execute_with_schema(self, **kwargs) -> str:
        """
        使用 Pydantic schema 执行（流式版本）

        使用 pre_task_pro 返回的 execution_id，
        在新线程中流式执行 SUB Agent，
        实时将事件保存到数据库供前端轮询显示，
        返回最终结果字符串（LangGraph会自动包装成ToolMessage）。

        Args:
            **kwargs: 工具参数，包含 description, subagent_type, show_thinking, execution_id

        Returns:
            执行结果字符串
        """
        description = kwargs.get('description', '')
        subagent_type = kwargs.get('subagent_type', '')
        show_thinking = kwargs.get('show_thinking', True)
        execution_id = kwargs.get('execution_id', '')

        # 验证 execution_id
        if not execution_id:
            return """错误：缺少 execution_id 参数！

必须先调用 pre_task_pro 工具获取 execution_id，再调用 task_pro。

正确流程：
1. 调用 pre_task_pro(description=..., subagent_type=...)
2. 获取返回的 execution_id
3. 调用 task_pro(..., execution_id=获取的id)

请立即调用 pre_task_pro 工具！
"""

        # 验证 execution_id 是否存在
        db = get_subagent_db()
        execution = db.get_execution(execution_id)
        if not execution:
            return f"错误：找不到 execution_id={execution_id} 的执行记录！\n\n请先调用 pre_task_pro 工具创建执行记录。"

        # 更新状态为 running
        db.update_execution_status(execution_id, 'running')
        print(f"[DEBUG] task_pro_tool.py - 更新状态为 running: {execution_id}")

        # 验证 subagent 类型
        if subagent_type not in self.subagent_registry:
            available = ", ".join(self.subagent_registry.keys())
            error_msg = f"未知的 subagent 类型: {subagent_type}。可用类型: {available}"

            # 添加错误事件
            db.add_event(execution_id, 'subagent_error', {'error': error_msg})
            db.update_execution_status(execution_id, 'error', error=error_msg)
            return error_msg

        # 定义异步流式执行函数
        async def run_stream():
            final_result = ""

            # 使用现有的 execute_stream 方法进行流式执行
            # 传入 execution_id 以启用 Human-in-the-loop 支持
            async for event in self.execute_stream(
                description=description,
                subagent_type=subagent_type,
                show_thinking=show_thinking,
                runtime_state=None,
                tool_call_id=None,
                execution_id=execution_id  # 传入 execution_id 启用 checkpoint 和中断恢复
            ):
                # 实时保存事件到数据库
                event_type = event.get('type')
                event_data = event.get('data', {})

                # 保存到数据库（实时）
                db.add_event(execution_id, event_type, event_data)
                print(f"[DEBUG] task_pro_tool.py - 实时添加事件: {event_type}")

                # 收集最终结果
                if event_type == 'subagent_final_result':
                    final_result = event_data.get('result', '')

            return final_result

        # 在新线程中运行异步代码（避免阻塞 LangGraph 的事件循环）
        # 同时支持取消操作
        result_container = []
        exception_container = []
        cancelled_container = [False]

        def run_in_thread():
            """在新线程中运行事件循环"""
            # 创建新的事件循环（独立于主线程）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # 运行异步流式执行
                result = loop.run_until_complete(run_stream())
                result_container.append(result)
            except Exception as e:
                exception_container.append(e)
            finally:
                loop.close()

        # 启动新线程
        print(f"[DEBUG] task_pro_tool.py - 启动流式执行线程: {execution_id}")
        thread = threading.Thread(target=run_in_thread)
        thread.start()

        # 等待线程完成，同时检查取消信号
        # 使用轮询方式而不是 thread.join()，以便能够响应取消
        while thread.is_alive():
            # 检查是否被取消
            if self._is_cancelled():
                print(f"[DEBUG] task_pro_tool.py - 检测到取消信号，等待线程结束: {execution_id}")
                cancelled_container[0] = True
                # 注意：由于线程正在运行，我们无法强制终止它
                # 但线程内部的取消检查会让它尽快退出
                # 这里我们等待线程自然结束（最多等待5秒）
                thread.join(timeout=5.0)
                break

            # 短暂等待后再次检查
            time.sleep(0.1)

        # 如果线程仍在运行，再次等待（给线程一些时间响应取消）
        if thread.is_alive():
            print(f"[DEBUG] task_pro_tool.py - 线程仍在运行，等待其结束: {execution_id}")
            thread.join(timeout=10.0)  # 最多再等待10秒

        print(f"[DEBUG] task_pro_tool.py - 流式执行线程完成: {execution_id}, cancelled={cancelled_container[0]}")

        # 如果被取消，更新状态并返回
        if cancelled_container[0]:
            print(f"[DEBUG] task_pro_tool.py - 任务被取消: {execution_id}")
            db.add_event(execution_id, 'subagent_cancelled', {'message': 'Task was cancelled by user'})
            db.update_execution_status(execution_id, 'cancelled', error='Task was cancelled by user')
            return "任务已被用户取消"

        # 检查是否有异常
        if exception_container:
            error_msg = str(exception_container[0])
            print(f"[ERROR] task_pro_tool.py - 流式执行异常: {error_msg}")
            # 确保错误事件被保存
            db.add_event(execution_id, 'subagent_error', {'error': error_msg})
            db.update_execution_status(execution_id, 'error', error=error_msg)
            return f"执行错误: {error_msg}"

        # 更新状态为完成（如果还没有更新）
        execution_info = db.get_execution(execution_id)
        if execution_info and execution_info.get('status') not in ['completed', 'error', 'cancelled']:
            final_result = result_container[0] if result_container else ""
            db.update_execution_status(execution_id, 'completed', result=final_result)
            print(f"[DEBUG] task_pro_tool.py - 更新状态为 completed: {execution_id}")

        return result_container[0] if result_container else ""




def create_task_pro_tool(
    subagent_registry: Optional[Dict[str, Runnable]] = None,
    stream_callback: Optional[Callable] = None,
    cancel_event: Optional[asyncio.Event] = None
) -> TaskProTool:
    """
    创建 Task Pro 工具实例

    Args:
        subagent_registry: SUB agent 注册表
        stream_callback: 流式输出回调
        cancel_event: 取消事件，用于接收主 agent 的取消信号

    Returns:
        TaskProTool 实例
    """
    tool_instance = TaskProTool(subagent_registry, cancel_event=cancel_event)
    if stream_callback:
        tool_instance.set_stream_callback(stream_callback)

    return tool_instance
