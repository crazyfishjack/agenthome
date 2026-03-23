"""
Task 拦截中间件

功能：
1. 注入提示词，引导 Agent 使用 task_pro 替代 task
2. 拦截 task 工具调用，返回提示信息
"""

from typing import Any, Callable, Awaitable
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import ToolMessage, SystemMessage
from langgraph.types import Command


class TaskInterceptorMiddleware(AgentMiddleware[Any, Any, Any]):
    """
    Task 工具拦截中间件
    
    功能：
    1. 注入提示词，引导 Agent 使用 task_pro 替代 task
    2. 拦截 task 工具调用，返回提示信息
    """
    
    name = "task_interceptor"
    
    # 提示词：告知 Agent 使用 task_pro
    TASK_PRO_GUIDANCE = """## 重要提示：Task 工具已升级

**注意**：`task` 工具已弃用，请使用 `task_pro` 工具替代。

`task_pro` 工具提供了以下增强功能：
- 实时查看 SUB agent 的思考过程
- 实时查看 SUB agent 的工具调用
- 更好的调试和监控能力

**使用方法**：
- 原：调用 `task` 工具
- 新：调用 `task_pro` 工具（参数完全相同）

可用参数：
- `description`: 任务描述（与 task 相同）
- `subagent_type`: SUB agent 类型（与 task 相同）
- `show_thinking`: 是否显示思考过程（可选，默认 true）
"""

    # 拦截响应：当 Agent 尝试调用 task 时返回
    TASK_INTERCEPT_MESSAGE = """`task` 工具已被拦截。

请使用 `task_pro` 工具替代，它提供了完全相同的参数：
- description: 任务描述
- subagent_type: SUB agent 类型

使用 `task_pro` 可以实时查看 SUB agent 的执行过程。"""

    def __init__(self):
        super().__init__()
        # 此中间件不添加新工具，只拦截现有工具
        self.tools = []
    
    def wrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
    ) -> ModelResponse[Any]:
        """
        包装模型调用，注入提示词
        
        在系统消息末尾添加 TASK_PRO_GUIDANCE
        使用 content_blocks 保持与其他中间件兼容
        """
        # 修改系统消息，添加引导提示
        if request.system_message is not None:
            new_system_content = [
                *request.system_message.content_blocks,
                {"type": "text", "text": f"\n\n{self.TASK_PRO_GUIDANCE}"},
            ]
            new_system_message = SystemMessage(content=new_system_content)
            request = request.override(system_message=new_system_message)
        
        return handler(request)
    
    async def awrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Callable[[ModelRequest[Any]], Awaitable[ModelResponse[Any]]],
    ) -> ModelResponse[Any]:
        """异步版本"""
        if request.system_message is not None:
            new_system_content = [
                *request.system_message.content_blocks,
                {"type": "text", "text": f"\n\n{self.TASK_PRO_GUIDANCE}"},
            ]
            new_system_message = SystemMessage(content=new_system_content)
            request = request.override(system_message=new_system_message)
        
        return await handler(request)
    
    def wrap_tool_call(
        self,
        request: "ToolCallRequest",
        handler: Callable[["ToolCallRequest"], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        """
        拦截工具调用
        
        如果调用的是 'task' 工具，返回提示信息而非执行
        """
        # 检查是否是 task 工具调用
        if request.tool_call.get("name") == "task":
            # 返回拦截消息
            return ToolMessage(
                content=self.TASK_INTERCEPT_MESSAGE,
                tool_call_id=request.tool_call.get("id", ""),
                name="task"
            )
        
        # 其他工具正常执行
        return handler(request)
    
    async def awrap_tool_call(
        self,
        request: "ToolCallRequest",
        handler: Callable[["ToolCallRequest"], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        """异步版本"""
        if request.tool_call.get("name") == "task":
            return ToolMessage(
                content=self.TASK_INTERCEPT_MESSAGE,
                tool_call_id=request.tool_call.get("id", ""),
                name="task"
            )
        
        return await handler(request)
