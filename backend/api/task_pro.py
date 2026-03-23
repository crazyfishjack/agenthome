"""
Task Pro API 模块
提供 SUB agent 执行的 HTTP 查询接口（轮询方式）
支持 Human-in-the-loop 中断决策
"""

import json
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.tools.task_pro_tool import TaskProTool, subagent_interrupt_manager
from backend.services.langchain_service import langchain_service
from backend.db.subagent_db import get_subagent_db

# 全局 pending_executions 存储（用于向后兼容，仅 API 模块内部使用）
pending_executions: Dict[str, Dict[str, Any]] = {}

router = APIRouter()


class TaskProPollResponse(BaseModel):
    """Task Pro 轮询响应"""
    execution_id: str
    status: str
    events: List[Dict[str, Any]]
    result: Optional[str] = None
    error: Optional[str] = None
    events_count: int
    latest_timestamp: Optional[float] = None


class TaskProExecuteResponse(BaseModel):
    """Task Pro 执行响应"""
    execution_id: str
    status: str
    message: str


class TaskProResultResponse(BaseModel):
    """Task Pro 结果响应"""
    execution_id: str
    status: str
    result: Optional[str] = None
    events_count: int


class TaskProEventsResponse(BaseModel):
    """Task Pro 事件列表响应"""
    execution_id: str
    events: List[Dict[str, Any]]
    total_count: int


class CreateExecutionRequest(BaseModel):
    """创建 Execution 请求"""
    execution_id: str
    description: str
    subagent_type: str
    show_thinking: bool = True


class CreateExecutionResponse(BaseModel):
    """创建 Execution 响应"""
    execution_id: str
    status: str
    message: str


def get_task_pro_tool() -> Optional[TaskProTool]:
    """
    获取 TaskProTool 实例

    遍历所有 agent 查找包含 task_pro_tool 的实例
    """
    for agent_id, agent_data in langchain_service.agent_deepagents.items():
        if "task_pro_tool" in agent_data:
            return agent_data["task_pro_tool"]
    return None


@router.post("/create", response_model=CreateExecutionResponse)
async def create_execution(request: CreateExecutionRequest):
    """
    创建新的 Execution 记录

    用于测试或手动创建 execution 记录，然后可以通过 HTTP 轮询获取实时输出。
    """
    execution_id = request.execution_id

    if execution_id in pending_executions:
        return CreateExecutionResponse(
            execution_id=execution_id,
            status="exists",
            message="Execution already exists"
        )

    # 获取数据库实例
    db = get_subagent_db()

    # 创建 execution 记录到数据库
    db.create_execution(
        execution_id=execution_id,
        description=request.description,
        subagent_type=request.subagent_type,
        show_thinking=request.show_thinking
    )

    # 创建 execution 记录到内存（用于向后兼容）
    pending_executions[execution_id] = {
        'execution_id': execution_id,
        'description': request.description,
        'subagent_type': request.subagent_type,
        'show_thinking': request.show_thinking,
        'created_at': 0,  # 将在数据库中记录
        'status': 'pending'
    }

    print(f"[DEBUG] task_pro.py - 创建 execution: {execution_id}")

    return CreateExecutionResponse(
        execution_id=execution_id,
        status="pending",
        message="Execution created, use /api/task-pro/poll/{execution_id} for updates"
    )


@router.post("/{execution_id}/execute", response_model=TaskProExecuteResponse)
async def start_execution(execution_id: str):
    """
    启动 SUB agent 执行（非流式，仅返回确认）

    实际执行需要通过 HTTP 轮询端点 /api/task-pro/poll/{execution_id} 获取实时输出
    """
    # 获取数据库实例
    db = get_subagent_db()

    execution_info = db.get_execution(execution_id)
    if not execution_info:
        raise HTTPException(status_code=404, detail="Execution not found")

    # 如果已经在执行中，返回状态
    if execution_info.get('status') == 'running':
        return TaskProExecuteResponse(
            execution_id=execution_id,
            status="running",
            message="Execution is already running"
        )

    # 如果已经完成，返回完成状态
    if execution_info.get('status') == 'completed':
        return TaskProExecuteResponse(
            execution_id=execution_id,
            status="completed",
            message="Execution already completed"
        )

    return TaskProExecuteResponse(
        execution_id=execution_id,
        status="pending",
        message="Execution ready, use /api/task-pro/poll/{execution_id} for live updates"
    )


@router.get("/{execution_id}/poll", response_model=TaskProPollResponse)
async def poll_execution(
    execution_id: str,
    since_timestamp: Optional[float] = None,
    limit: int = 100
):
    """
    轮询执行状态和事件

    这是前端主要的查询接口，每 1 秒调用一次获取最新事件。

    Args:
        execution_id: 执行 ID
        since_timestamp: 起始时间戳（可选），只返回此时间之后的事件
        limit: 返回事件数量限制

    Returns:
        执行状态和事件列表
    """
    # 获取数据库实例
    db = get_subagent_db()

    # 获取执行记录
    execution_info = db.get_execution(execution_id)
    if not execution_info:
        raise HTTPException(status_code=404, detail="Execution not found")

    # 获取事件列表
    events = db.get_events(execution_id, since_timestamp=since_timestamp, limit=limit)

    # 获取最新时间戳
    latest_timestamp = db.get_latest_timestamp(execution_id)

    # 获取事件总数
    events_count = db.get_events_count(execution_id)

    return TaskProPollResponse(
        execution_id=execution_id,
        status=execution_info.get('status', 'unknown'),
        events=events,
        result=execution_info.get('result'),
        error=execution_info.get('error'),
        events_count=events_count,
        latest_timestamp=latest_timestamp
    )


@router.get("/{execution_id}/result", response_model=TaskProResultResponse)
async def get_execution_result(execution_id: str):
    """
    获取 SUB agent 执行结果

    返回执行状态和最终结果
    """
    # 获取数据库实例
    db = get_subagent_db()

    execution_info = db.get_execution(execution_id)
    if not execution_info:
        raise HTTPException(status_code=404, detail="Execution not found")

    events_count = db.get_events_count(execution_id)

    return TaskProResultResponse(
        execution_id=execution_id,
        status=execution_info.get('status', 'unknown'),
        result=execution_info.get('result'),
        events_count=events_count
    )


@router.get("/{execution_id}/events", response_model=TaskProEventsResponse)
async def get_execution_events(
    execution_id: str,
    offset: int = 0,
    limit: int = 100
):
    """
    获取已生成的执行事件列表（分页）

    Args:
        execution_id: 执行 ID
        offset: 起始位置
        limit: 返回事件数量限制

    Returns:
        事件列表
    """
    # 获取数据库实例
    db = get_subagent_db()

    execution_info = db.get_execution(execution_id)
    if not execution_info:
        raise HTTPException(status_code=404, detail="Execution not found")

    events = db.get_events(execution_id, limit=limit)
    total_count = db.get_events_count(execution_id)

    # 应用 offset
    paginated_events = events[offset:offset + limit]

    return TaskProEventsResponse(
        execution_id=execution_id,
        events=paginated_events,
        total_count=total_count
    )


@router.delete("/{execution_id}")
async def cleanup_execution(execution_id: str):
    """
    清理执行数据（从数据库删除）

    客户端在关闭弹窗后可以调用此接口清理数据
    """
    # 获取数据库实例
    db = get_subagent_db()

    # 从数据库删除
    db.delete_execution(execution_id)

    # 从内存删除（用于向后兼容）
    if execution_id in pending_executions:
        del pending_executions[execution_id]

    return {"success": True, "message": f"Execution {execution_id} cleaned up"}


@router.get("/executions")
async def list_executions():
    """
    列出所有执行（调试用）
    """
    # 获取数据库实例
    db = get_subagent_db()

    executions = db.list_executions(limit=100)

    return {"executions": executions}


class SubAgentInterruptDecisionRequest(BaseModel):
    """SUB Agent 中断决策请求"""
    decision: str  # "approve" 或 "reject"


@router.post("/{execution_id}/interrupt-decision")
async def handle_subagent_interrupt_decision(
    execution_id: str,
    request: SubAgentInterruptDecisionRequest
):
    """
    处理 SUB Agent 的中断决策

    当 SUB Agent 触发 Human-in-the-loop 中断时，前端调用此接口发送用户的决策（同意或拒绝）。

    Args:
        execution_id: 执行 ID
        request: 包含 decision 的请求体

    Returns:
        处理结果
    """
    print(f"[DEBUG] task_pro.py - 收到 SUB Agent 中断决策: execution_id={execution_id}, decision={request.decision}")

    # 验证决策值
    if request.decision not in ["approve", "reject"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid decision. Must be 'approve' or 'reject'"
        )

    # 检查是否存在中断事件
    if execution_id not in subagent_interrupt_manager:
        raise HTTPException(
            status_code=404,
            detail=f"No interrupt found for execution_id: {execution_id}. The interrupt may have timed out or already been processed."
        )

    # 设置用户决策
    subagent_interrupt_manager[execution_id]["decision"] = request.decision

    # 触发事件，恢复执行
    subagent_interrupt_manager[execution_id]["event"].set()

    print(f"[DEBUG] task_pro.py - SUB Agent 中断决策已处理: execution_id={execution_id}, decision={request.decision}")

    return {
        "success": True,
        "message": f"Interrupt decision '{request.decision}' processed successfully",
        "execution_id": execution_id
    }
