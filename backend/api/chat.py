from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, AsyncGenerator, Dict
from datetime import datetime
import json
import os
import asyncio
import uuid

from backend.core.chat_engine import chat_engine
from backend.services.langchain_service import langchain_service, get_output_dir, set_output_dir, interrupt_manager
from pathlib import Path

router = APIRouter()

CONFIG_FILE = "./data/model_configs.json"


class Message(BaseModel):
    id: str
    role: str
    content: str
    images: Optional[List[str]] = None
    timestamp: datetime


class ChatRequest(BaseModel):
    model_config_id: str
    message: str
    images: Optional[List[str]] = None
    model: Optional[str] = None
    history: Optional[List[Message]] = None
    school_id: Optional[str] = None  # 新增：school_id，用于标识是否使用school中的agent
    conversation_id: Optional[str] = None  # 新增：conversation_id，用于checkpoint隔离


class ChatResponse(BaseModel):
    id: str
    role: str
    content: str
    thinking: Optional[str] = None  # 深度思考内容
    timestamp: datetime


class CheckpointInfo(BaseModel):
    thread_id: str
    checkpoint_id: str
    parent_checkpoint_id: Optional[str] = None


class CopyCheckpointRequest(BaseModel):
    source_checkpoint_id: str
    target_thread_id: str


class SetOutputDirRequest(BaseModel):
    path: str


class InterruptDecisionRequest(BaseModel):
    thread_id: str
    decision: str  # "approve" or "reject"


def load_configs() -> List[dict]:
    """加载模型配置"""
    if not os.path.exists(CONFIG_FILE):
        return []
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        configs = data.get("configs", [])
        # 为旧配置添加system_prompt字段的兼容性处理
        for config in configs:
            if "system_prompt" not in config:
                config["system_prompt"] = None
        return configs


def get_config_by_id(config_id: str) -> Optional[dict]:
    """根据ID获取模型配置"""
    configs = load_configs()
    for config in configs:
        if config["id"] == config_id:
            return config
    return None


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()

# 任务管理器：存储任务ID和对应的取消标志
task_manager: Dict[str, bool] = {}


@router.post("/cancel")
async def cancel_task(task_id: str):
    """取消正在执行的任务"""
    if task_id not in task_manager:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )

    # 获取取消事件（可能是 bool 或 asyncio.Event）
    cancel_obj = task_manager[task_id]

    # 如果是 asyncio.Event，设置事件
    if isinstance(cancel_obj, asyncio.Event):
        cancel_obj.set()
    else:
        # 兼容旧的 bool 类型
        task_manager[task_id] = True

    return {"success": True, "message": f"Task {task_id} cancelled"}


@router.delete("/conversation/{agent_id}/{conversation_id}")
async def delete_conversation(agent_id: str, conversation_id: str):
    """删除指定会话及其checkpoint数据"""
    print(f"[DEBUG] chat.py - 删除会话: agent_id={agent_id}, conversation_id={conversation_id}")

    try:
        # 删除该会话的checkpoint数据
        success = langchain_service.delete_conversation_checkpoints(agent_id, conversation_id)

        if success:
            return {"success": True, "message": f"Conversation {conversation_id} deleted successfully"}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete conversation checkpoints"
            )
    except Exception as e:
        print(f"[ERROR] chat.py - 删除会话失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete conversation: {str(e)}"
        )


@router.get("/checkpoint/{agent_id}/latest")
async def get_latest_checkpoint(agent_id: str, conversation_id: str):
    """获取指定会话的最新checkpoint信息"""
    print(f"[DEBUG] chat.py - 获取最新checkpoint: agent_id={agent_id}, conversation_id={conversation_id}")

    try:
        checkpoint_info = langchain_service.get_latest_checkpoint_info(agent_id, conversation_id)

        if checkpoint_info:
            return {
                "success": True,
                "data": checkpoint_info
            }
        else:
            return {
                "success": False,
                "message": "No checkpoint found for this conversation"
            }
    except Exception as e:
        print(f"[ERROR] chat.py - 获取最新checkpoint失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get latest checkpoint: {str(e)}"
        )


@router.post("/checkpoint/{agent_id}/copy")
async def copy_checkpoint(agent_id: str, request: CopyCheckpointRequest):
    """添加checkpoint的记忆到目标会话"""
    print(f"[DEBUG] chat.py - 添加checkpoint记忆: agent_id={agent_id}, source_checkpoint_id={request.source_checkpoint_id}, target_thread_id={request.target_thread_id}")

    try:
        success = langchain_service.add_checkpoint_to_conversation(
            agent_id=agent_id,
            source_checkpoint_id=request.source_checkpoint_id,
            target_thread_id=request.target_thread_id
        )

        if success:
            return {
                "success": True,
                "message": "Checkpoint added successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to add checkpoint"
            )
    except Exception as e:
        print(f"[ERROR] chat.py - 添加checkpoint失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add checkpoint: {str(e)}"
        )


@router.get("/output-dir")
async def get_output_dir_endpoint():
    """获取当前配置的 output 目录路径"""
    try:
        output_dir = get_output_dir()
        return {
            "success": True,
            "path": str(output_dir)
        }
    except Exception as e:
        print(f"[ERROR] chat.py - 获取 output_dir 失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get output directory: {str(e)}"
        )


@router.post("/output-dir")
async def set_output_dir_endpoint(request: SetOutputDirRequest):
    """设置 output 目录路径

    Args:
        request: 包含 path 字段的请求体

    Returns:
        设置结果
    """
    try:
        # 验证路径
        path = request.path.strip()
        if not path:
            raise HTTPException(
                status_code=400,
                detail="Path cannot be empty"
            )

        # 尝试解析路径
        try:
            new_path = Path(path).resolve()
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid path: {str(e)}"
            )

        # 验证路径是否有效（尝试创建目录）
        try:
            os.makedirs(new_path, exist_ok=True)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot create directory at path: {str(e)}"
            )

        # 设置新的 output_dir
        success = set_output_dir(path)
        if success:
            return {
                "success": True,
                "message": f"Output directory updated to: {new_path}",
                "path": str(new_path)
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to update output directory"
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] chat.py - 设置 output_dir 失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set output directory: {str(e)}"
        )


@router.post("/interrupt-decision")
async def handle_interrupt_decision(request: InterruptDecisionRequest):
    """处理中断决策（approve/reject）

    Args:
        request: 包含 thread_id 和 decision 的请求体

    Returns:
        处理结果
    """
    print(f"[DEBUG] chat.py - 收到中断决策: thread_id={request.thread_id}, decision={request.decision}")

    try:
        # 验证决策值
        if request.decision not in ["approve", "reject"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid decision. Must be 'approve' or 'reject'"
            )

        # 检查是否存在中断事件
        if request.thread_id not in interrupt_manager:
            raise HTTPException(
                status_code=404,
                detail=f"No interrupt found for thread_id: {request.thread_id}"
            )

        # 设置用户决策
        interrupt_manager[request.thread_id]["decision"] = request.decision

        # 触发事件，恢复执行
        interrupt_manager[request.thread_id]["event"].set()

        print(f"[DEBUG] chat.py - 中断决策已处理: {request.decision}")

        return {
            "success": True,
            "message": f"Interrupt decision '{request.decision}' processed successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] chat.py - 处理中断决策失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process interrupt decision: {str(e)}"
        )


@router.post("/message")
async def send_message(request: ChatRequest):
    """发送消息并获取响应"""
    print(f"[DEBUG] chat.py - 收到请求: message={request.message}, images={request.images is not None}")
    if request.images:
        print(f"[DEBUG] chat.py - 图片数量: {len(request.images)}")
    
    # 根据model_config_id获取模型配置
    model_config = get_config_by_id(request.model_config_id)
    
    if not model_config:
        raise HTTPException(
            status_code=404,
            detail=f"Model config not found: {request.model_config_id}"
        )
    
    # 准备历史消息
    history = None
    if request.history:
        history = [
            {
                "role": msg.role,
                "content": msg.content,
                "images": msg.images
            }
            for msg in request.history
        ]
    
    # 调用chat_engine生成响应
    try:
        response = await chat_engine.send_message(
            model_config=model_config,
            message=request.message,
            images=request.images,
            history=history
        )
        
        return ChatResponse(**response)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate response: {str(e)}"
        )


async def stream_generator(
    model_config: dict,
    message: str,
    images: Optional[List[str]] = None,
    history: Optional[List[dict]] = None,
    school_id: Optional[str] = None,
    task_id: Optional[str] = None,
    conversation_id: Optional[str] = None  # 新增：conversation_id参数
) -> AsyncGenerator[str, None]:
    """流式生成响应的生成器"""
    try:
        print(f"[DEBUG] chat.py - stream_generator 开始")
        print(f"[DEBUG] chat.py - task_id: {task_id}")
        print(f"[DEBUG] chat.py - school_id: {school_id}")
        print(f"[DEBUG] chat.py - conversation_id: {conversation_id}")
        print(f"[DEBUG] chat.py - message: {message[:100]}")

        # 发送任务ID事件
        if task_id:
            task_event = f"data: {json.dumps({'type': 'task_id', 'task_id': task_id})}\n\n"
            print(f"[DEBUG] chat.py - 发送task_id事件: {task_event.strip()}")
            yield task_event

        # 如果提供了school_id，使用LangChain智能体
        if school_id:
            print(f"[DEBUG] chat.py - 使用LangChain智能体路径")
            async for chunk in langchain_service.execute_agent(
                agent_id=model_config["id"],
                message=message,
                history=history,
                images=images,
                task_id=task_id,
                conversation_id=conversation_id  # 传递conversation_id
            ):
                # 检查是否被取消（兼容 bool 和 asyncio.Event）
                if task_id and task_id in task_manager:
                    cancel_obj = task_manager[task_id]
                    if isinstance(cancel_obj, asyncio.Event):
                        if cancel_obj.is_set():
                            print(f"[DEBUG] chat.py - 任务被取消: {task_id}")
                            raise asyncio.CancelledError()
                    elif cancel_obj:
                        print(f"[DEBUG] chat.py - 任务被取消: {task_id}")
                        raise asyncio.CancelledError()
                # 将每个chunk作为SSE事件发送
                chunk_event = f"data: {json.dumps(chunk)}\n\n"
                print(f"[DEBUG] chat.py - 发送chunk事件 (LangChain): {chunk_event.strip()[:200]}")
                yield chunk_event
        else:
            # 使用原有的chat_engine
            print(f"[DEBUG] chat.py - 使用chat_engine路径")
            async for chunk in chat_engine.stream_message(
                model_config=model_config,
                message=message,
                images=images,
                history=history,
                task_id=task_id
            ):
                # 检查是否被取消（兼容 bool 和 asyncio.Event）
                if task_id and task_id in task_manager:
                    cancel_obj = task_manager[task_id]
                    if isinstance(cancel_obj, asyncio.Event):
                        if cancel_obj.is_set():
                            print(f"[DEBUG] chat.py - 任务被取消: {task_id}")
                            raise asyncio.CancelledError()
                    elif cancel_obj:
                        print(f"[DEBUG] chat.py - 任务被取消: {task_id}")
                        raise asyncio.CancelledError()
                # 将每个chunk作为SSE事件发送
                chunk_event = f"data: {json.dumps(chunk)}\n\n"
                print(f"[DEBUG] chat.py - 发送chunk事件 (ChatEngine): {chunk_event.strip()[:200]}")
                yield chunk_event

        print(f"[DEBUG] chat.py - stream_generator 完成")
    except asyncio.CancelledError:
        # 任务被取消
        print(f"[DEBUG] chat.py - 任务被取消，发送cancelled事件")
        cancel_event = f"data: {json.dumps({'type': 'cancelled', 'message': 'Task was cancelled'})}\n\n"
        yield cancel_event
        # 从任务管理器中移除
        if task_id and task_id in task_manager:
            del task_manager[task_id]
        raise
    except Exception as e:
        # 发送错误事件
        print(f"[ERROR] chat.py - stream_generator 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        error_event = f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        yield error_event
        # 从任务管理器中移除
        if task_id and task_id in task_manager:
            del task_manager[task_id]


@router.post("/stream")
async def stream_message(request: ChatRequest):
    """流式发送消息并获取响应"""
    print(f"[DEBUG] chat.py - 收到流式请求: message={request.message}, images={request.images is not None}, school_id={request.school_id}")

    # 根据model_config_id获取模型配置
    model_config = get_config_by_id(request.model_config_id)

    if not model_config:
        raise HTTPException(
            status_code=404,
            detail=f"Model config not found: {request.model_config_id}"
        )

    # 准备历史消息
    history = None
    if request.history:
        history = [
            {
                "role": msg.role,
                "content": msg.content,
                "images": msg.images
            }
            for msg in request.history
        ]

    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 将任务ID添加到任务管理器（初始状态为未取消）
    task_manager[task_id] = False

    # 返回流式响应
    return StreamingResponse(
        stream_generator(
            model_config=model_config,
            message=request.message,
            images=request.images,
            history=history,
            school_id=request.school_id,
            task_id=task_id,
            conversation_id=request.conversation_id  # 传递conversation_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
