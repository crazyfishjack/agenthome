"""
LangChain Agent服务
使用 DeepAgent 框架实现计划-执行模式的智能体创建和管理
重构说明：
- 每个school维护独立的deepagent实例
- deepagent实例只包含该school配置的工具
- agent使用其所属school的deepagent实例
"""
from typing import Dict, Optional, Any, AsyncGenerator, List
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field
import json
import asyncio
import re
import os
import time
import sqlite3
import shutil
from pathlib import Path

# 导入DeepAgent
from deepagents import create_deep_agent

# 导入LangGraph Checkpoint
from langgraph.checkpoint.sqlite import SqliteSaver

# 导入FilesystemBackend
from deepagents.backends import FilesystemBackend

# 导入SummarizationMiddleware
from langchain.agents.middleware import SummarizationMiddleware

# 导入 HumanInTheLoopMiddleware
from langchain.agents.middleware import HumanInTheLoopMiddleware

# 导入工具模块
from backend.tools import get_all_tools, TaskProTool

# 导入 MCP 管理器
from backend.services.mcp_manager import mcp_manager

# 导入 CompositeBackend
from backend.services.composite_backend import CompositeBackend

# 导入 Skills 模块
from backend.skills import SkillsMiddleware

# 导入 TaskInterceptorMiddleware
from backend.middleware.task_interceptor import TaskInterceptorMiddleware

# 全局配置：skills_dir 和 output_dir
# skills_dir 使用相对路径（从 langchain_service.py 文件位置计算）
_current_file_path = Path(__file__).resolve()
_skills_dir = _current_file_path.parent.parent.parent / "skills" / "installed"
_output_dir = _current_file_path.parent.parent.parent / "output"


def get_skills_dir() -> Path:
    """获取 skills 目录路径"""
    return _skills_dir


def get_output_dir() -> Path:
    """获取 output 目录路径"""
    return _output_dir


def set_output_dir(path: str) -> bool:
    """设置 output 目录路径

    Args:
        path: 新的 output 目录路径（绝对路径或相对路径）

    Returns:
        是否设置成功
    """
    global _output_dir
    try:
        new_path = Path(path).resolve()
        # 尝试创建目录，验证路径是否有效
        os.makedirs(new_path, exist_ok=True)
        _output_dir = new_path
        print(f"[DEBUG] langchain_service.py - 全局 output_dir 已更新为: {_output_dir}")

        # 更新所有已存在的 agent 的 output_dir
        try:
            from backend.services.langchain_service import langchain_service
            print(f"[DEBUG] langchain_service.py - 开始更新所有已存在 agent 的 output_dir")
            print(f"[DEBUG] langchain_service.py - 当前 agent_deepagents 数量: {len(langchain_service.agent_deepagents)}")

            # 遍历所有已存在的 agent_deepagents (包含普通agent和team)
            updated_count = 0
            for agent_id, agent_deepagent_data in langchain_service.agent_deepagents.items():
                if "composite_backend" in agent_deepagent_data:
                    composite_backend = agent_deepagent_data["composite_backend"]
                    if hasattr(composite_backend, "update_output_dir"):
                        print(f"[DEBUG] langchain_service.py - 更新 agent/team {agent_id} 的 output_dir")
                        composite_backend.update_output_dir(str(_output_dir))
                        updated_count += 1
                    else:
                        print(f"[WARNING] langchain_service.py - agent/team {agent_id} 的 composite_backend 没有 update_output_dir 方法")
                else:
                    print(f"[WARNING] langchain_service.py - agent/team {agent_id} 没有 composite_backend")

            print(f"[DEBUG] langchain_service.py - 已更新 {updated_count} 个 agent/team 的 output_dir")
        except Exception as e:
            print(f"[WARNING] langchain_service.py - 更新所有 agent 的 output_dir 失败（但全局 output_dir 已更新）: {e}")
            import traceback
            traceback.print_exc()

        return True
    except Exception as e:
        print(f"[ERROR] langchain_service.py - 设置 output_dir 失败: {e}")
        return False


def update_all_agents_output_dir(new_output_dir: str) -> bool:
    """更新所有已存在的 agent 的 output_dir

    Args:
        new_output_dir: 新的 output 目录路径

    Returns:
        是否更新成功
    """
    try:
        # 获取全局服务实例
        from backend.services.langchain_service import langchain_service

        print(f"[DEBUG] langchain_service.py - 开始更新所有 agent 的 output_dir")
        print(f"[DEBUG] langchain_service.py - 新 output_dir: {new_output_dir}")
        print(f"[DEBUG] langchain_service.py - 当前 agent_deepagents 数量: {len(langchain_service.agent_deepagents)}")

        # 遍历所有已存在的 agent_deepagents
        updated_count = 0
        for agent_id, agent_deepagent_data in langchain_service.agent_deepagents.items():
            if "composite_backend" in agent_deepagent_data:
                composite_backend = agent_deepagent_data["composite_backend"]
                if hasattr(composite_backend, "update_output_dir"):
                    print(f"[DEBUG] langchain_service.py - 更新 agent {agent_id} 的 output_dir")
                    composite_backend.update_output_dir(new_output_dir)
                    updated_count += 1
                else:
                    print(f"[WARNING] langchain_service.py - agent {agent_id} 的 composite_backend 没有 update_output_dir 方法")
            else:
                print(f"[WARNING] langchain_service.py - agent {agent_id} 没有 composite_backend")

        print(f"[DEBUG] langchain_service.py - 已更新 {updated_count} 个 agent 的 output_dir")
        return True
    except Exception as e:
        print(f"[ERROR] langchain_service.py - 更新所有 agent 的 output_dir 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


class LangChainAgentService:
    """LangChain智能体服务 - 使用 DeepAgent 实现计划-执行模式
    
    重构说明：
    - 每个school维护独立的deepagent实例
    - deepagent实例只包含该school配置的工具
    - agent使用其所属school的deepagent实例
    """

    def __init__(self):
        self.agents: Dict[str, Any] = {}  # agent_id -> agent_data
        self.school_deepagents: Dict[str, Dict[str, Any]] = {}  # school_id -> deepagent_instance_data
        self.agent_deepagents: Dict[str, Dict[str, Any]] = {}  # agent_id -> deepagent_instance_data
        self.llm_cache: Dict[str, ChatOpenAI] = {}  # LLM配置缓存，key为配置的hash值
        self.agent_checkpointers: Dict[str, SqliteSaver] = {}  # agent_id -> checkpointer实例
        self.agents_base_path = "./data/agents"  # agents文件夹基础路径
        self.skills_middleware = SkillsMiddleware()  # Skills 中间件
        self.subagent_registries: Dict[str, Dict[str, Runnable]] = {}  # agent_id -> subagent_registry
        self._current_stream_queue: Optional[asyncio.Queue] = None  # 当前流式输出队列

    def _load_schools(self) -> List[Dict]:
        """加载所有School数据"""
        schools_file = "./data/schools.json"
        if not os.path.exists(schools_file):
            return []
        with open(schools_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("schools", [])

    def _get_agent_memory_path(self, agent_id: str) -> str:
        """获取agent的memory文件夹路径
        
        Args:
            agent_id: Agent ID
            
        Returns:
            memory文件夹的绝对路径
        """
        agent_path = os.path.join(self.agents_base_path, agent_id)
        memory_path = os.path.join(agent_path, "memory")
        return memory_path

    def _get_agent_checkpoint_db_path(self, agent_id: str) -> str:
        """获取agent的checkpoint数据库路径
        
        Args:
            agent_id: Agent ID
            
        Returns:
            checkpoints.db的绝对路径
        """
        memory_path = self._get_agent_memory_path(agent_id)
        db_path = os.path.join(memory_path, "checkpoints.db")
        return db_path

    def _create_agent_folder_structure(self, agent_id: str) -> bool:
        """创建agent的文件夹结构
        
        Args:
            agent_id: Agent ID
            
        Returns:
            是否创建成功
        """
        try:
            memory_path = self._get_agent_memory_path(agent_id)
            os.makedirs(memory_path, exist_ok=True)
            print(f"[DEBUG] langchain_service.py - 创建agent文件夹结构: {memory_path}")
            return True
        except Exception as e:
            print(f"[ERROR] langchain_service.py - 创建agent文件夹结构失败: {e}")
            return False

    def _delete_agent_folder(self, agent_id: str) -> bool:
        """删除agent的整个文件夹
        
        Args:
            agent_id: Agent ID
            
        Returns:
            是否删除成功
        """
        try:
            agent_path = os.path.join(self.agents_base_path, agent_id)
            if os.path.exists(agent_path):
                shutil.rmtree(agent_path)
                print(f"[DEBUG] langchain_service.py - 删除agent文件夹: {agent_path}")
            return True
        except Exception as e:
            print(f"[ERROR] langchain_service.py - 删除agent文件夹失败: {e}")
            return False

    def _get_agent_checkpointer(self, agent_id: str) -> Optional[SqliteSaver]:
        """获取或创建agent的checkpointer
        
        Args:
            agent_id: Agent ID
            
        Returns:
            SqliteSaver实例，如果失败返回None
        """
        # 如果已存在，直接返回
        if agent_id in self.agent_checkpointers:
            print(f"[DEBUG] langchain_service.py - 使用已存在的checkpointer: {agent_id}")
            return self.agent_checkpointers[agent_id]
        
        try:
            # 创建文件夹结构
            if not self._create_agent_folder_structure(agent_id):
                print(f"[ERROR] langchain_service.py - 创建agent文件夹结构失败")
                return None
            
            # 获取数据库路径
            db_path = self._get_agent_checkpoint_db_path(agent_id)
            print(f"[DEBUG] langchain_service.py - 创建checkpointer，数据库路径: {db_path}")
            
            # 创建SQLite连接和SqliteSaver（同步版本）
            conn = sqlite3.connect(db_path, check_same_thread=False)
            checkpointer = SqliteSaver(conn)
            
            # 保存到字典
            self.agent_checkpointers[agent_id] = checkpointer
            print(f"[DEBUG] langchain_service.py - Checkpointer创建成功: {agent_id}")
            
            return checkpointer
        except Exception as e:
            print(f"[ERROR] langchain_service.py - 创建checkpointer失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _limit_checkpoints(self, agent_id: str, thread_id: str, max_checkpoints: int = 50) -> bool:
        """限制每个会话的checkpoint数量，超过时删除最旧的
        
        Args:
            agent_id: Agent ID
            thread_id: 会话ID（conversation_id）
            max_checkpoints: 最大checkpoint数量，默认50
            
        Returns:
            是否执行成功
        """
        try:
            db_path = self._get_agent_checkpoint_db_path(agent_id)
            if not os.path.exists(db_path):
                return True
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 查询该thread_id的checkpoint数量
            cursor.execute("SELECT COUNT(*) FROM checkpoints WHERE thread_id = ?", (thread_id,))
            count = cursor.fetchone()[0]
            
            print(f"[DEBUG] langchain_service.py - Agent {agent_id}, Thread {thread_id}, 当前checkpoint数量: {count}")
            
            if count > max_checkpoints:
                # 获取需要删除的checkpoint ID（保留最新的max_checkpoints个）
                cursor.execute("""
                    SELECT checkpoint_id FROM checkpoints 
                    WHERE thread_id = ? 
                    ORDER BY checkpoint_id ASC 
                    LIMIT ?
                """, (thread_id, count - max_checkpoints))
                
                checkpoint_ids_to_delete = [row[0] for row in cursor.fetchall()]
                
                if checkpoint_ids_to_delete:
                    # 删除checkpoint记录
                    placeholders = ','.join(['?' for _ in checkpoint_ids_to_delete])
                    cursor.execute(f"""
                        DELETE FROM checkpoints 
                        WHERE checkpoint_id IN ({placeholders})
                    """, checkpoint_ids_to_delete)
                    
                    conn.commit()
                    print(f"[DEBUG] langchain_service.py - 删除了 {len(checkpoint_ids_to_delete)} 个旧checkpoint")
            
            conn.close()
            return True
        except Exception as e:
            print(f"[ERROR] langchain_service.py - 限制checkpoint数量失败: {e}")
            return False

    def _delete_conversation_checkpoints(self, agent_id: str, thread_id: str) -> bool:
        """删除指定会话的所有checkpoint
        
        Args:
            agent_id: Agent ID
            thread_id: 会话ID（conversation_id）
            
        Returns:
            是否删除成功
        """
        try:
            db_path = self._get_agent_checkpoint_db_path(agent_id)
            if not os.path.exists(db_path):
                print(f"[DEBUG] langchain_service.py - 数据库不存在，无需删除: {db_path}")
                return True
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 删除该thread_id的所有checkpoint
            cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            print(f"[DEBUG] langchain_service.py - 删除会话 {thread_id} 的 {deleted_count} 个checkpoint")
            return True
        except Exception as e:
            print(f"[ERROR] langchain_service.py - 删除会话checkpoint失败: {e}")
            return False

    def _get_school_by_id(self, school_id: str) -> Optional[Dict]:
        """根据ID获取School"""
        schools = self._load_schools()
        for school in schools:
            if school["id"] == school_id:
                return school
        return None

    # ==================== 公共辅助方法 ====================

    def _safe_str(self, value: Any, default: str = "") -> str:
        """安全地转换为字符串"""
        return str(value) if value is not None else default

    def _parse_json_response(self, response: str) -> dict:
        """解析LLM返回的JSON响应"""
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response)
        except Exception as parse_error:
            print(f"[WARNING] langchain_service.py - JSON解析失败: {parse_error}")
            return {}

    def _build_tools_description(self, tools: List) -> str:
        """构建工具描述字符串"""
        return "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])

    def _format_todo_list(self, todo_list: Any) -> str:
        """格式化任务清单内容

        Args:
            todo_list: 任务清单对象

        Returns:
            格式化后的字符串
        """
        try:
            print(f"[DEBUG] _format_todo_list - 输入数据: {todo_list}, 类型: {type(todo_list)}")
            
            if isinstance(todo_list, list):
                formatted = []
                for i, item in enumerate(todo_list, 1):
                    print(f"[DEBUG] _format_todo_list - 处理第 {i} 项: {item}, 类型: {type(item)}")
                    if isinstance(item, dict):
                        # 只支持新格式 {'content': 'xxx', 'status': 'completed/in_progress/pending'}
                        content = item.get('content', str(item))
                        status = item.get('status', 'pending')
                        # 状态图标映射
                        status_icons = {
                            'completed': '✅',
                            'in_progress': '🔄',
                            'pending': '⬜'
                        }
                        status_icon = status_icons.get(status, '⬜')
                        formatted.append(f"  {status_icon} {i}. {content}")
                        print(f"[DEBUG] _format_todo_list - 格式化结果: {formatted[-1]}")
                    else:
                        # 非字典格式，使用默认 pending 状态
                        formatted.append(f"  ⬜ {i}. {str(item)}")
                        print(f"[DEBUG] _format_todo_list - 非字典格式: {formatted[-1]}")
                result = "\n".join(formatted) if formatted else "  (空)"
                print(f"[DEBUG] _format_todo_list - 最终结果: {result}")
                return result
            elif isinstance(todo_list, dict):
                formatted = []
                for key, value in todo_list.items():
                    formatted.append(f"  • {key}: {value}")
                return "\n".join(formatted) if formatted else "  (空)"
            else:
                return f"  {str(todo_list)}"
        except Exception as e:
            print(f"[WARNING] langchain_service.py - 格式化任务清单失败: {e}")
            import traceback
            traceback.print_exc()
            return f"  {str(todo_list)}"

    def _parse_tool_calls(self, response: BaseMessage) -> List[dict]:
        """解析 LLM 返回的 tool_calls
        
        Args:
            response: LLM 返回的消息
            
        Returns:
            tool_calls 列表，每个元素包含 id, name, arguments
        """
        tool_calls = []
        
        # 检查是否有 tool_calls 属性
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_calls.append({
                    "id": tool_call.get("id", ""),
                    "name": tool_call.get("name", ""),
                    "arguments": tool_call.get("args", {})
                })
        
        # 如果没有 tool_calls，尝试从 content 中解析（向后兼容）
        elif hasattr(response, 'content') and response.content:
            content = self._safe_str(response.content)
            # 尝试解析 JSON 格式的 tool_calls
            try:
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    parsed = json.loads(json_match.group())
                    if "tool_calls" in parsed:
                        for tc in parsed["tool_calls"]:
                            tool_calls.append({
                                "id": tc.get("id", ""),
                                "name": tc.get("function", {}).get("name", ""),
                                "arguments": json.loads(tc.get("function", {}).get("arguments", "{}"))
                            })
            except Exception as e:
                print(f"[WARNING] langchain_service.py - 解析 tool_calls 失败: {e}")
        
        return tool_calls

    def _detect_and_load_skill(self, tool_name: str, tool_args: dict) -> Optional[Dict[str, Any]]:
        """检测 load_skill 工具调用并加载 skill 内容

        Args:
            tool_name: 工具名称
            tool_args: 工具参数

        Returns:
            Skill 内容字典，如果不是 load_skill 工具则返回 None
        """
        if tool_name != "load_skill":
            return None

        print(f"[DEBUG] langchain_service.py - 检测到 load_skill 工具调用: {tool_args}")

        skill_id = tool_args.get("skill_id")
        disclosure_level = tool_args.get("disclosure_level", "body")

        if not skill_id:
            print(f"[WARNING] langchain_service.py - load_skill 缺少 skill_id 参数")
            return None

        # 使用 skills_middleware 加载 skill
        skill_context = self.skills_middleware.load_skill_for_context(skill_id, disclosure_level)

        if not skill_context:
            print(f"[WARNING] langchain_service.py - 未找到 Skill: {skill_id}")
            return None

        print(f"[DEBUG] langchain_service.py - 成功加载 Skill: {skill_id}, 披露级别: {disclosure_level}")
        return skill_context

    def _inject_skill_context_to_messages(self, messages: list, skill_context: Dict[str, Any]) -> list:
        """将 Skill 内容注入到消息上下文中

        Args:
            messages: 原始消息列表
            skill_context: Skill 上下文

        Returns:
            更新后的消息列表
        """
        # 在 system_prompt 之后、用户消息之前插入 skill 内容
        updated_messages = []

        for msg in messages:
            updated_messages.append(msg)

            # 在 system 消息之后插入 skill 内容
            if msg.get("role") == "system" and "context_text" in skill_context:
                skill_message = {
                    "role": "system",
                    "content": f"\n\n{skill_context['context_text']}"
                }
                updated_messages.append(skill_message)
                print(f"[DEBUG] langchain_service.py - 已将 Skill 内容注入到上下文: {skill_context['skill_id']}")

        return updated_messages

    def _inject_skill_to_graph_state(self, deepagent, thread_id: str, skill_context: Dict[str, Any]) -> bool:
        """将 Skill 内容注入到 LangGraph 状态中

        Args:
            deepagent: DeepAgent 实例
            thread_id: 会话ID
            skill_context: Skill 上下文

        Returns:
            是否注入成功
        """
        try:
            # 获取 deepagent 的 graph 实例
            graph = deepagent if hasattr(deepagent, 'update_state') else deepagent.graph

            # 构建 SystemMessage 包含 skill 内容
            from langchain_core.messages import SystemMessage
            skill_message = SystemMessage(content=skill_context['context_text'])

            # 使用 update_state 将 skill 消息注入到状态中
            config = {"configurable": {"thread_id": thread_id}}
            graph.update_state(config, {"messages": [skill_message]})

            print(f"[DEBUG] langchain_service.py - 成功将 Skill 内容注入到 graph 状态: {skill_context['skill_id']}")
            return True
        except Exception as e:
            print(f"[ERROR] langchain_service.py - 注入 Skill 到 graph 状态失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _execute_tool_call(self, tool, tool_args: dict, queue: asyncio.Queue) -> tuple[str, bool]:
        """执行工具调用（使用 Function Calling 格式）
        
        Args:
            tool: StructuredTool 对象
            tool_args: 工具参数（字典格式）
            queue: 回调队列
            
        Returns:
            (执行结果, 是否成功)
        """
        try:
            # 检测是否是 load_skill 工具调用
            tool_name = getattr(tool, 'name', '')
            skill_context = self._detect_and_load_skill(tool_name, tool_args)

            # 如果是 load_skill 工具，返回 skill 内容
            if skill_context:
                await self._send_queue_event(queue, f"\n工具调用完成\n已加载 Skill: {skill_context['skill_id']} (披露级别: {skill_context['disclosure_level']})")
                return skill_context['context_text'], True

            # 执行其他工具
            tool_result = await tool.ainvoke(tool_args) if hasattr(tool, 'ainvoke') else tool.invoke(tool_args)
            safe_tool_result = self._safe_str(tool_result)
            await self._send_queue_event(queue, f"\n工具调用完成\n输出: {safe_tool_result}")
            return safe_tool_result, True
        except Exception as tool_error:
            print(f"[ERROR] _execute_tool_call - 工具调用失败: {tool_error}")
            error_result = f"工具调用失败: {str(tool_error)}"
            await self._send_queue_event(queue, f"\n工具调用失败\n输出: {error_result}")
            return error_result, False

    def _safe_system_prompt(self, system_prompt: Optional[str], default: str = "你是一个有用的AI助手。") -> str:
        """安全地获取 system_prompt"""
        if system_prompt is None or not isinstance(system_prompt, str) or system_prompt.strip() == "":
            print(f"[WARNING] langchain_service.py - system_prompt 为空或无效，使用默认值")
            return default
        return system_prompt

    def _build_multimodal_content(self, text: str, images: Optional[List[str]] = None) -> Any:
        """构建多模态消息内容"""
        if images and len(images) > 0:
            return [{"type": "text", "text": text}, *[{"type": "image_url", "image_url": {"url": img}} for img in images]]
        return text

    def _build_messages(self, system_prompt: str, user_content: Any, chat_history: Optional[list] = None) -> list:
        """构建消息列表"""
        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            for msg in chat_history:
                if isinstance(msg, tuple) and len(msg) == 2:
                    role, content = msg
                    safe_content = self._safe_str(content)
                    if role == "human":
                        messages.append({"role": "user", "content": safe_content})
                    elif role == "ai":
                        messages.append({"role": "assistant", "content": safe_content})
        messages.append({"role": "user", "content": user_content})
        return messages

    async def _call_llm(self, llm: ChatOpenAI, messages: list) -> str:
        """调用 LLM 并返回结果"""
        response = await llm.ainvoke(messages)
        return response.content if hasattr(response, 'content') and response.content is not None else str(response)

    async def _send_queue_event(self, queue: asyncio.Queue, content: str) -> None:
        """发送事件到队列"""
        await queue.put({"type": "thinking_content", "content": content})

    async def _get_or_create_school_deepagent(self, school_id: str, agent_config: Dict) -> Dict[str, Any]:
        """获取或创建school的deepagent实例

        Args:
            school_id: School ID
            agent_config: Agent配置（用于创建LLM）

        Returns:
            包含deepagent实例相关数据的字典
        """
        # 如果已存在该school的deepagent实例，直接返回
        if school_id in self.school_deepagents:
            print(f"[DEBUG] langchain_service.py - 使用已存在的school deepagent实例: {school_id}")
            return self.school_deepagents[school_id]

        # 创建新的school deepagent实例
        print(f"[DEBUG] langchain_service.py - 创建新的school deepagent实例: {school_id}")

        llm = self._create_llm(agent_config)
        print(f"[DEBUG] langchain_service.py - LLM创建成功: {llm}")

        # 使用school_id过滤工具（异步）
        tools = await self._create_tools(school_id)
        print(f"[DEBUG] langchain_service.py - 工具创建成功: {len(tools)}个工具")

        # 配置 Composite Backend（支持 /skills/ 和 /output/ 路由）
        skills_dir = get_skills_dir()
        output_dir = get_output_dir()
        print(f"[DEBUG] langchain_service.py - 配置 Composite Backend，skills 目录: {skills_dir}, output 目录: {output_dir}")

        # 创建 CompositeBackend 实例
        composite_backend = CompositeBackend(
            skills_dir=str(skills_dir),
            output_dir=str(output_dir),
            virtual_mode=True
        )
        print(f"[DEBUG] langchain_service.py - CompositeBackend 创建成功")

        # 获取system_prompt（不包含输出目录信息）
        system_prompt = agent_config.get("system_prompt")

        # 获取school配置的 skills 列表
        school = self._get_school_by_id(school_id)
        school_skills_config = school.get("skills", []) if school else []
        enabled_skill_ids = []
        for skill_config in school_skills_config:
            if skill_config.get("enabled", True):
                enabled_skill_ids.append(skill_config.get("skill_id"))

        # 设置披露级别为 metadata（渐进式披露：启动时只加载元数据）
        self.skills_middleware.set_disclosure_level("metadata")

        # 格式化 skills 为提示词（只包含元数据）
        skills_prompt = self.skills_middleware.format_skills_for_prompt(enabled_skill_ids)

        # 将 skills 信息添加到 system_prompt
        if skills_prompt:
            if system_prompt:
                system_prompt = f"{system_prompt}\n\n{skills_prompt}"
            else:
                system_prompt = skills_prompt

        deepagent = create_deep_agent(
            model=llm,
            tools=tools,
            system_prompt=system_prompt,
            backend=composite_backend,
            middleware=[
                # 使用 create_deep_agent 内置的 SummarizationMiddleware
                # 它会自动将历史记录卸载到 backend 的 conversation_history 目录
                HumanInTheLoopMiddleware(
                    interrupt_on={
                        "SandboxExecute": {
                            "allowed_decisions": ["approve", "reject"]
                        }
                    }
                )
            ]
        )
        print(f"[DEBUG] langchain_service.py - DeepAgent创建成功（带 Composite Backend 和自动总结）")

        # 保存school deepagent实例
        deepagent_data = {
            "deepagent": deepagent,
            "tools": tools,
            "llm": llm,
            "created_at": agent_config.get("created_at"),
            "school_id": school_id,
            "composite_backend": composite_backend
        }
        self.school_deepagents[school_id] = deepagent_data

        print(f"[DEBUG] langchain_service.py - School deepagent实例已保存，当前school数量: {len(self.school_deepagents)}")
        return deepagent_data

    async def _update_school_deepagent(self, school_id: str) -> bool:
        """更新school的deepagent实例（当school的工具配置变化时调用）
        同时更新该school下所有agent的工具列表

        Args:
            school_id: School ID

        Returns:
            是否更新成功
        """
        print(f"[DEBUG] langchain_service.py - 更新school {school_id} 的工具配置")

        # 更新该school下所有agent的工具列表
        updated_agents = []
        for agent_id, agent_data in self.agents.items():
            if agent_data.get("school_id") == school_id:
                if agent_id in self.agent_deepagents:
                    print(f"[DEBUG] langchain_service.py - 更新agent {agent_id} 的工具列表")

                    # 获取agent配置
                    agent_config = agent_data.get("config")

                    # 创建新的工具列表（异步）
                    new_tools = await self._create_tools(school_id)

                    # 配置 Composite Backend（支持 /skills/ 和 /output/ 路由）
                    skills_dir = get_skills_dir()
                    output_dir = get_output_dir()
                    print(f"[DEBUG] langchain_service.py - 配置 Composite Backend，skills 目录: {skills_dir}, output 目录: {output_dir}")

                    # 创建 CompositeBackend 实例
                    composite_backend = CompositeBackend(
                        skills_dir=str(skills_dir),
                        output_dir=str(output_dir),
                        virtual_mode=True
                    )
                    print(f"[DEBUG] langchain_service.py - CompositeBackend 创建成功")

                    # 获取system_prompt（不包含输出目录信息）
                    system_prompt = agent_config.get("system_prompt")

                    # 获取最新的 school 配置
                    school = self._get_school_by_id(school_id)

                    # 获取school配置的 skills 列表
                    school_skills_config = school.get("skills", []) if school else []
                    enabled_skill_ids = []
                    for skill_config in school_skills_config:
                        if skill_config.get("enabled", True):
                            enabled_skill_ids.append(skill_config.get("skill_id"))

                    # 设置披露级别为 metadata（渐进式披露：启动时只加载元数据）
                    self.skills_middleware.set_disclosure_level("metadata")

                    # 格式化 skills 为提示词（只包含元数据）
                    skills_prompt = self.skills_middleware.format_skills_for_prompt(enabled_skill_ids)

                    # 将 skills 信息添加到 system_prompt
                    if skills_prompt:
                        if system_prompt:
                            system_prompt = f"{system_prompt}\n\n{skills_prompt}"
                        else:
                            system_prompt = skills_prompt

                    # 重新创建deepagent实例（使用新的工具列表）
                    llm = self._create_llm(agent_config)
                    deepagent = create_deep_agent(
                        model=llm,
                        tools=new_tools,
                        system_prompt=system_prompt,
                        backend=composite_backend,
                        middleware=[
                            # 使用 create_deep_agent 内置的 SummarizationMiddleware
                            HumanInTheLoopMiddleware(
                                interrupt_on={
                                    "SandboxExecute": {
                                        "allowed_decisions": ["approve", "reject"]
                                    }
                                }
                            )
                        ]
                    )

                    # 更新agent的deepagent实例
                    agent_deepagent_data = {
                        "deepagent": deepagent,
                        "tools": new_tools,
                        "llm": llm,
                        "created_at": agent_config.get("created_at"),
                        "school_id": school_id,
                        "composite_backend": composite_backend
                    }
                    self.agent_deepagents[agent_id] = agent_deepagent_data
                    updated_agents.append(agent_id)

        print(f"[DEBUG] langchain_service.py - School {school_id} 下已更新 {len(updated_agents)} 个agent的工具列表: {updated_agents}")
        return len(updated_agents) > 0

    async def remove_mcp_from_all_agents(self, mcp_id: str) -> bool:
        """从所有agent中移除指定的MCP（当MCP被删除时调用）

        Args:
            mcp_id: MCP ID

        Returns:
            是否更新成功
        """
        print(f"[DEBUG] langchain_service.py - 从所有agent中移除MCP: {mcp_id}")

        # 找到所有配置了该MCP的school
        schools = self._load_schools()
        affected_schools = []
        for school in schools:
            if "mcps" in school:
                for mcp_config in school["mcps"]:
                    if mcp_config.get("mcp_id") == mcp_id:
                        affected_schools.append(school["id"])
                        break

        print(f"[DEBUG] langchain_service.py - 找到 {len(affected_schools)} 个school配置了该MCP: {affected_schools}")

        # 更新这些school的deepagent实例
        updated = False
        for school_id in affected_schools:
            if await self._update_school_deepagent(school_id):
                updated = True

        return updated

    # ==================== 创建智能体相关方法 ====================

    async def create_agent(self, agent_id: str, agent_config: Dict, school_id: str) -> Dict:
        """创建LangChain智能体（使用DeepAgent）

        Args:
            agent_id: Agent ID
            agent_config: Agent配置
            school_id: School ID

        Returns:
            创建结果
        """
        print(f"[DEBUG] langchain_service.py - 创建智能体: agent_id={agent_id}, school_id={school_id}")
        try:
            # 为该agent创建独立的deepagent实例
            print(f"[DEBUG] langchain_service.py - 为agent {agent_id} 创建独立的deepagent实例")

            llm = self._create_llm(agent_config)
            print(f"[DEBUG] langchain_service.py - LLM创建成功: {llm}")

            # 使用school_id过滤工具（异步）
            tools = await self._create_tools(school_id)
            print(f"[DEBUG] langchain_service.py - 工具创建成功: {len(tools)}个工具")

            # 创建agent的checkpointer
            checkpointer = self._get_agent_checkpointer(agent_id)
            if not checkpointer:
                print(f"[ERROR] langchain_service.py - 创建checkpointer失败")
                return {
                    "success": False,
                    "agent_id": agent_id,
                    "error": "Failed to create checkpointer",
                    "message": "Failed to create checkpointer for agent"
                }

            # 配置 Composite Backend（支持 /skills/ 和 /output/ 路由）
            skills_dir = get_skills_dir()
            output_dir = get_output_dir()
            print(f"[DEBUG] langchain_service.py - 配置 Composite Backend，skills 目录: {skills_dir}, output 目录: {output_dir}")

            # 创建 CompositeBackend 实例
            composite_backend = CompositeBackend(
                skills_dir=str(skills_dir),
                output_dir=str(output_dir),
                virtual_mode=True
            )
            print(f"[DEBUG] langchain_service.py - CompositeBackend 创建成功")

            # 获取system_prompt（不包含输出目录信息）
            system_prompt = agent_config.get("system_prompt")

            # 获取school配置的 skills 列表
            school = self._get_school_by_id(school_id)
            school_skills_config = school.get("skills", []) if school else []
            enabled_skill_ids = []
            for skill_config in school_skills_config:
                if skill_config.get("enabled", True):
                    enabled_skill_ids.append(skill_config.get("skill_id"))

            # 设置披露级别为 metadata（渐进式披露：启动时只加载元数据）
            self.skills_middleware.set_disclosure_level("metadata")

            # 格式化 skills 为提示词（只包含元数据）
            skills_prompt = self.skills_middleware.format_skills_for_prompt(enabled_skill_ids)

            # 将 skills 信息添加到 system_prompt
            if skills_prompt:
                if system_prompt:
                    system_prompt = f"{system_prompt}\n\n{skills_prompt}"
                else:
                    system_prompt = skills_prompt

            deepagent = create_deep_agent(
                model=llm,
                tools=tools,
                system_prompt=system_prompt,
                backend=composite_backend,
                checkpointer=checkpointer,
                middleware=[
                    # 使用 create_deep_agent 内置的 SummarizationMiddleware
                    HumanInTheLoopMiddleware(
                        interrupt_on={
                            "SandboxExecute": {
                                "allowed_decisions": ["approve", "reject"]
                            }
                        }
                    )
                ]
            )
            print(f"[DEBUG] langchain_service.py - DeepAgent创建成功（带 Composite Backend、checkpointer 和自动总结）")

            # 保存agent的独立deepagent实例
            agent_deepagent_data = {
                "deepagent": deepagent,
                "tools": tools,
                "llm": llm,
                "created_at": agent_config.get("created_at"),
                "school_id": school_id,
                "composite_backend": composite_backend
            }
            self.agent_deepagents[agent_id] = agent_deepagent_data

            # 保存agent信息
            self.agents[agent_id] = {
                "config": agent_config,
                "school_id": school_id,
                "created_at": agent_config.get("created_at"),
            }
            print(f"[DEBUG] langchain_service.py - 智能体已保存，当前智能体数量: {len(self.agents)}")
            print(f"[DEBUG] langchain_service.py - Agent deepagent实例已保存，当前agent deepagent数量: {len(self.agent_deepagents)}")
            print(f"[DEBUG] langchain_service.py - Agent checkpointer已保存，当前agent checkpointer数量: {len(self.agent_checkpointers)}")

            return {
                "success": True,
                "agent_id": agent_id,
                "school_id": school_id,
                "message": f"DeepAgent created successfully for {agent_config.get('name')} in school {school_id} with Filesystem Backend"
            }
        except Exception as e:
            print(f"[ERROR] langchain_service.py - 创建智能体失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "agent_id": agent_id,
                "error": str(e),
                "message": f"Failed to create DeepAgent: {str(e)}"
            }

    async def create_agent_with_subagents(self, agent_id: str, agent_config: Dict, school_id: str, subagents: List) -> Dict:
        """创建带有SubAgents的LangChain智能体（用于Team功能）

        Args:
            agent_id: Agent ID
            agent_config: Agent配置
            school_id: School ID
            subagents: CompiledSubAgent列表

        Returns:
            创建结果
        """
        print(f"[DEBUG] langchain_service.py - 创建带SubAgents的智能体: agent_id={agent_id}, school_id={school_id}, subagents数量={len(subagents)}")
        try:
            # 为该agent创建独立的deepagent实例
            print(f"[DEBUG] langchain_service.py - 为agent {agent_id} 创建带SubAgents的deepagent实例")

            llm = self._create_llm(agent_config)
            print(f"[DEBUG] langchain_service.py - LLM创建成功: {llm}")

            # 使用school_id过滤工具（异步）
            tools = await self._create_tools(school_id)
            print(f"[DEBUG] langchain_service.py - 工具创建成功: {len(tools)}个工具")

            # 创建agent的checkpointer
            checkpointer = self._get_agent_checkpointer(agent_id)
            if not checkpointer:
                print(f"[ERROR] langchain_service.py - 创建checkpointer失败")
                return {
                    "success": False,
                    "agent_id": agent_id,
                    "error": "Failed to create checkpointer",
                    "message": "Failed to create checkpointer for agent"
                }

            # 配置 Composite Backend（支持 /skills/ 和 /output/ 路由）
            skills_dir = get_skills_dir()
            output_dir = get_output_dir()
            print(f"[DEBUG] langchain_service.py - 配置 Composite Backend，skills 目录: {skills_dir}, output 目录: {output_dir}")

            # 创建 CompositeBackend 实例
            composite_backend = CompositeBackend(
                skills_dir=str(skills_dir),
                output_dir=str(output_dir),
                virtual_mode=True
            )
            print(f"[DEBUG] langchain_service.py - CompositeBackend 创建成功")

            # 获取system_prompt（不包含输出目录信息）
            system_prompt = agent_config.get("system_prompt")

            # 获取school配置的 skills 列表
            school = self._get_school_by_id(school_id)
            school_skills_config = school.get("skills", []) if school else []
            enabled_skill_ids = []
            for skill_config in school_skills_config:
                if skill_config.get("enabled", True):
                    enabled_skill_ids.append(skill_config.get("skill_id"))

            # 设置披露级别为 metadata（渐进式披露：启动时只加载元数据）
            self.skills_middleware.set_disclosure_level("metadata")

            # 格式化 skills 为提示词（只包含元数据）
            skills_prompt = self.skills_middleware.format_skills_for_prompt(enabled_skill_ids)

            # 将 skills 信息添加到 system_prompt
            if skills_prompt:
                if system_prompt:
                    system_prompt = f"{system_prompt}\n\n{skills_prompt}"
                else:
                    system_prompt = skills_prompt

            # 构建 subagent 注册表（用于 TaskProTool）
            subagent_registry = {}
            for sub in subagents:
                if isinstance(sub, dict) and 'runnable' in sub:
                    subagent_registry[sub['name']] = sub['runnable']
                elif hasattr(sub, 'name') and hasattr(sub, 'runnable'):
                    subagent_registry[sub.name] = sub.runnable
            
            # 保存 subagent 注册表
            self.subagent_registries[agent_id] = subagent_registry
            print(f"[DEBUG] langchain_service.py - Subagent 注册表创建成功: {list(subagent_registry.keys())}")

            # 创建 TaskProTool 实例
            task_pro_tool = TaskProTool(subagent_registry)

            # 将 TaskProTool 添加到工具列表
            tools.append(task_pro_tool.structured_tool)
            print(f"[DEBUG] langchain_service.py - TaskProTool 已添加到工具列表")

            # 创建 PreTaskProTool 实例并添加到工具列表
            from backend.tools.pre_task_pro_tool import PreTaskProTool
            pre_task_pro_tool = PreTaskProTool()
            tools.append(pre_task_pro_tool.structured_tool)
            print(f"[DEBUG] langchain_service.py - PreTaskProTool 已添加到工具列表")

            # 创建DeepAgent实例，传入subagents参数
            deepagent = create_deep_agent(
                model=llm,
                tools=tools,
                system_prompt=system_prompt,
                backend=composite_backend,
                checkpointer=checkpointer,
                subagents=subagents,
                middleware=[
                    TaskInterceptorMiddleware(),  # 拦截 task 工具调用
                    # 使用 create_deep_agent 内置的 SummarizationMiddleware
                    HumanInTheLoopMiddleware(
                        interrupt_on={
                            "SandboxExecute": {
                                "allowed_decisions": ["approve", "reject"]
                            }
                        }
                    )
                ]
            )
            print(f"[DEBUG] langchain_service.py - DeepAgent创建成功（带 Composite Backend、checkpointer、自动总结和 {len(subagents)} 个subagents）")

            # 保存agent的独立deepagent实例
            agent_deepagent_data = {
                "deepagent": deepagent,
                "tools": tools,
                "llm": llm,
                "created_at": agent_config.get("created_at"),
                "school_id": school_id,
                "composite_backend": composite_backend,
                "subagents": subagents,
                "subagent_registry": subagent_registry,
                "task_pro_tool": task_pro_tool,
                "pre_task_pro_tool": pre_task_pro_tool
            }
            self.agent_deepagents[agent_id] = agent_deepagent_data

            # 保存agent信息
            self.agents[agent_id] = {
                "config": agent_config,
                "school_id": school_id,
                "created_at": agent_config.get("created_at"),
            }
            print(f"[DEBUG] langchain_service.py - 智能体已保存，当前智能体数量: {len(self.agents)}")
            print(f"[DEBUG] langchain_service.py - Agent deepagent实例已保存，当前agent deepagent数量: {len(self.agent_deepagents)}")
            print(f"[DEBUG] langchain_service.py - Agent checkpointer已保存，当前agent checkpointer数量: {len(self.agent_checkpointers)}")

            return {
                "success": True,
                "agent_id": agent_id,
                "school_id": school_id,
                "subagents_count": len(subagents),
                "message": f"DeepAgent with {len(subagents)} subagents created successfully for {agent_config.get('name')} in school {school_id}"
            }
        except Exception as e:
            print(f"[ERROR] langchain_service.py - 创建带SubAgents的智能体失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "agent_id": agent_id,
                "error": str(e),
                "message": f"Failed to create DeepAgent with subagents: {str(e)}"
            }

    async def hot_update_agent_with_subagents(self, agent_id: str, agent_config: Dict, school_id: str, subagents: List) -> Dict:
        """热更新带有SubAgents的LangChain智能体（用于Team更新功能）
        
        与create_agent_with_subagents的区别：
        - 保留原有的checkpointer（对话历史）
        - 只更新工具、技能、MCP配置
        - 更新subagents列表
        
        Args:
            agent_id: Agent ID
            agent_config: Agent配置
            school_id: School ID
            subagents: CompiledSubAgent列表

        Returns:
            更新结果
        """
        print(f"[DEBUG] langchain_service.py - 热更新带SubAgents的智能体: agent_id={agent_id}, school_id={school_id}, subagents数量={len(subagents)}")
        try:
            # 检查agent是否已存在
            if agent_id not in self.agents:
                print(f"[WARNING] langchain_service.py - Agent {agent_id} 不存在，将创建新实例")
                # 如果不存在，调用创建方法
                return await self.create_agent_with_subagents(agent_id, agent_config, school_id, subagents)

            # 获取原有的checkpointer（保留对话历史）
            checkpointer = self._get_agent_checkpointer(agent_id)
            if not checkpointer:
                print(f"[WARNING] langchain_service.py - 获取checkpointer失败，将创建新的checkpointer")
                checkpointer = self._get_agent_checkpointer(agent_id)
                if not checkpointer:
                    return {
                        "success": False,
                        "agent_id": agent_id,
                        "error": "Failed to get or create checkpointer",
                        "message": "Failed to get or create checkpointer for agent"
                    }

            print(f"[DEBUG] langchain_service.py - 保留原有checkpointer: {agent_id}")

            # 创建新的LLM实例
            llm = self._create_llm(agent_config)
            print(f"[DEBUG] langchain_service.py - LLM创建成功: {llm}")

            # 使用新的school_id过滤工具（异步）
            tools = await self._create_tools(school_id)
            print(f"[DEBUG] langchain_service.py - 工具创建成功: {len(tools)}个工具")

            # 配置 Composite Backend（支持 /skills/ 和 /output/ 路由）
            skills_dir = get_skills_dir()
            output_dir = get_output_dir()
            print(f"[DEBUG] langchain_service.py - 配置 Composite Backend，skills 目录: {skills_dir}, output 目录: {output_dir}")

            # 创建 CompositeBackend 实例
            composite_backend = CompositeBackend(
                skills_dir=str(skills_dir),
                output_dir=str(output_dir),
                virtual_mode=True
            )
            print(f"[DEBUG] langchain_service.py - CompositeBackend 创建成功")

            # 获取system_prompt（不包含输出目录信息）
            system_prompt = agent_config.get("system_prompt")

            # 获取school配置的 skills 列表
            school = self._get_school_by_id(school_id)
            school_skills_config = school.get("skills", []) if school else []
            enabled_skill_ids = []
            for skill_config in school_skills_config:
                if skill_config.get("enabled", True):
                    enabled_skill_ids.append(skill_config.get("skill_id"))

            # 设置披露级别为 metadata（渐进式披露：启动时只加载元数据）
            self.skills_middleware.set_disclosure_level("metadata")

            # 格式化 skills 为提示词（只包含元数据）
            skills_prompt = self.skills_middleware.format_skills_for_prompt(enabled_skill_ids)

            # 将 skills 信息添加到 system_prompt
            if skills_prompt:
                if system_prompt:
                    system_prompt = f"{system_prompt}\n\n{skills_prompt}"
                else:
                    system_prompt = skills_prompt

            # 构建 subagent 注册表（用于 TaskProTool）
            subagent_registry = {}
            for sub in subagents:
                if isinstance(sub, dict) and 'runnable' in sub:
                    subagent_registry[sub['name']] = sub['runnable']
                elif hasattr(sub, 'name') and hasattr(sub, 'runnable'):
                    subagent_registry[sub.name] = sub.runnable
            
            # 保存 subagent 注册表
            self.subagent_registries[agent_id] = subagent_registry
            print(f"[DEBUG] langchain_service.py - Subagent 注册表更新成功: {list(subagent_registry.keys())}")

            # 创建 TaskProTool 实例
            task_pro_tool = TaskProTool(subagent_registry)

            # 将 TaskProTool 添加到工具列表
            tools.append(task_pro_tool.structured_tool)
            print(f"[DEBUG] langchain_service.py - TaskProTool 已添加到工具列表")

            # 创建 PreTaskProTool 实例并添加到工具列表
            from backend.tools.pre_task_pro_tool import PreTaskProTool
            pre_task_pro_tool = PreTaskProTool()
            tools.append(pre_task_pro_tool.structured_tool)
            print(f"[DEBUG] langchain_service.py - PreTaskProTool 已添加到工具列表")

            # 创建新的DeepAgent实例，传入subagents参数和保留的checkpointer
            deepagent = create_deep_agent(
                model=llm,
                tools=tools,
                system_prompt=system_prompt,
                backend=composite_backend,
                checkpointer=checkpointer,
                subagents=subagents,
                middleware=[
                    TaskInterceptorMiddleware(),  # 拦截 task 工具调用
                    # 使用 create_deep_agent 内置的 SummarizationMiddleware
                    HumanInTheLoopMiddleware(
                        interrupt_on={
                            "SandboxExecute": {
                                "allowed_decisions": ["approve", "reject"]
                            }
                        }
                    )
                ]
            )
            print(f"[DEBUG] langchain_service.py - DeepAgent热更新成功（保留checkpointer、更新工具、自动总结和subagents）")

            # 更新agent的deepagent实例
            agent_deepagent_data = {
                "deepagent": deepagent,
                "tools": tools,
                "llm": llm,
                "created_at": agent_config.get("created_at"),
                "school_id": school_id,
                "composite_backend": composite_backend,
                "subagents": subagents,
                "subagent_registry": subagent_registry,
                "task_pro_tool": task_pro_tool,
                "pre_task_pro_tool": pre_task_pro_tool
            }
            self.agent_deepagents[agent_id] = agent_deepagent_data

            # 更新agent信息
            self.agents[agent_id] = {
                "config": agent_config,
                "school_id": school_id,
                "created_at": agent_config.get("created_at"),
            }
            print(f"[DEBUG] langchain_service.py - 智能体已热更新，当前智能体数量: {len(self.agents)}")

            return {
                "success": True,
                "agent_id": agent_id,
                "school_id": school_id,
                "subagents_count": len(subagents),
                "message": f"DeepAgent hot updated successfully with {len(subagents)} subagents, conversation history preserved"
            }
        except Exception as e:
            print(f"[ERROR] langchain_service.py - 热更新带SubAgents的智能体失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "agent_id": agent_id,
                "error": str(e),
                "message": f"Failed to hot update DeepAgent with subagents: {str(e)}"
            }

    def _create_llm(self, agent_config: Dict) -> ChatOpenAI:
        """根据配置创建LLM实例（使用配置缓存）

        支持的配置项：
        - provider: 提供商类型（支持 ollama, aliyun, openai, anthropic, custom）
        - api_base: API基础URL
        - model: 模型名称
        - temperature: 温度参数
        - max_tokens: 最大token数
        - top_p: top_p采样参数
        - presence_penalty: 存在惩罚
        - thinking: 深度思考模式（用于控制是否提取thinking内容）
        - enable_search: 阿里云搜索功能开关
        - enable_thinking: 阿里云深度思考功能开关
        - system_prompt: 系统提示词
        """
        provider = agent_config.get("provider", "ollama")
        if provider not in ["ollama", "aliyun", "openai", "anthropic", "custom"]:
            raise ValueError(f"不支持的提供商: {provider}")

        api_base = agent_config.get("api_base", "http://localhost:11434")
        model_name = agent_config.get("model", "llama2")

        llm_params = {
            "base_url": f"{api_base}/v1" if provider == "ollama" else api_base,
            "model": model_name,
            "api_key": "ollama" if provider == "ollama" else agent_config.get("api_key"),
            "temperature": agent_config.get("temperature", 0.7),
            "max_tokens": agent_config.get("max_tokens", 2048),
            "top_p": agent_config.get("top_p", 0.9),
        }

        presence_penalty = agent_config.get("presence_penalty")
        if presence_penalty is not None:
            llm_params["presence_penalty"] = presence_penalty

        # 阿里云特有配置：enable_search 和 enable_thinking
        if provider == "aliyun":
            extra_body = {}
            if agent_config.get("enable_search"):
                extra_body["enable_search"] = True
                print(f"[DEBUG] langchain_service.py - 阿里云模型启用 enable_search")
            if agent_config.get("enable_thinking"):
                extra_body["enable_thinking"] = True
                print(f"[DEBUG] langchain_service.py - 阿里云模型启用 enable_thinking")
            if extra_body:
                llm_params["extra_body"] = extra_body

        # 生成配置的hash值作为缓存key
        # 注意：thinking参数不参与hash计算，因为它不影响LLM实例的创建
        import hashlib
        config_str = json.dumps(llm_params, sort_keys=True)
        config_hash = hashlib.md5(config_str.encode()).hexdigest()

        # 检查缓存中是否已存在相同配置的LLM实例
        if config_hash in self.llm_cache:
            print(f"[DEBUG] langchain_service.py - 使用缓存的LLM实例: {config_hash}")
            return self.llm_cache[config_hash]

        # 创建新的LLM实例并存入缓存
        llm = ChatOpenAI(**llm_params)
        self.llm_cache[config_hash] = llm
        print(f"[DEBUG] langchain_service.py - 创建并缓存新的LLM实例: {config_hash}, provider: {provider}")
        return llm

    async def _create_tools(self, school_id: Optional[str] = None) -> list:
        """创建智能体工具 - 根据school_id过滤工具（异步版本）

        Args:
            school_id: School ID，如果提供则只返回该school配置的工具

        Returns:
            工具列表（StructuredTool 对象，用于 Function Calling）
        """
        # 从 tools 模块获取所有工具
        all_tool_bases = get_all_tools()

        # 如果没有提供school_id，返回所有工具（向后兼容）
        if not school_id:
            tools = []
            for tool_base in all_tool_bases:
                tools.append(tool_base.structured_tool)
            print(f"[DEBUG] langchain_service.py - 未提供school_id，加载所有工具: {len(tools)}个工具")
            return tools

        # 获取school配置
        school = self._get_school_by_id(school_id)
        if not school:
            print(f"[WARNING] langchain_service.py - School {school_id} 不存在，返回空工具列表")
            return []

        # 获取school配置的工具列表
        school_tools_config = school.get("tools", [])
        enabled_tool_names = set()
        for tool_config in school_tools_config:
            if tool_config.get("enabled", True):
                enabled_tool_names.add(tool_config.get("tool_name"))

        # 过滤工具：只返回school配置的且启用的工具
        tools = []
        for tool_base in all_tool_bases:
            if tool_base.name in enabled_tool_names:
                tools.append(tool_base.structured_tool)

        # 获取school配置的MCP列表
        school_mcps_config = school.get("mcps", [])
        enabled_mcp_ids = []
        for mcp_config in school_mcps_config:
            if mcp_config.get("enabled", True):
                enabled_mcp_ids.append(mcp_config.get("mcp_id"))

        # 加载MCP工具（异步方式）
        from backend.models.mcp_config import MCPConfig
        for mcp_config_dict in school_mcps_config:
            if mcp_config_dict.get("enabled", True):
                mcp_id = mcp_config_dict.get("mcp_id")
                try:
                    # 创建MCP客户端
                    mcp_config = MCPConfig(**mcp_config_dict)
                    mcp_manager.create_mcp_client(mcp_config)

                    # 获取MCP工具并添加到工具列表（使用 await 直接调用异步方法）
                    try:
                        mcp_tools = await mcp_manager.get_mcp_tools(mcp_id)
                        tools.extend(mcp_tools)
                        print(f"[DEBUG] langchain_service.py - 成功加载 MCP {mcp_id} 的 {len(mcp_tools)} 个工具: {[t.name for t in mcp_tools]}")
                    except Exception as async_error:
                        print(f"[ERROR] langchain_service.py - 异步获取 MCP 工具失败: {async_error}")
                        import traceback
                        traceback.print_exc()
                except Exception as e:
                    print(f"[ERROR] langchain_service.py - 创建MCP客户端失败: {e}")
                    import traceback
                    traceback.print_exc()

        print(f"[DEBUG] langchain_service.py - School {school_id} 配置了 {len(enabled_tool_names)} 个工具，实际加载了 {len(tools)} 个工具: {[t.name for t in tools]}")
        print(f"[DEBUG] langchain_service.py - School {school_id} 配置了 {len(enabled_mcp_ids)} 个MCP")
        return tools

    # ==================== 执行智能体方法 ====================

    async def execute_agent(self, agent_id: str, message: str, history: Optional[list] = None, images: Optional[List[str]] = None, task_id: Optional[str] = None, conversation_id: Optional[str] = None) -> AsyncGenerator[Dict, None]:
        """执行智能体并流式返回结果（使用DeepAgent，支持Human-in-the-loop中断恢复）

        重构说明：
        - 采用 LangGraph 官方标准模式实现 HITL
        - 使用生成器模式支持多轮交互（中断 -> 等待决策 -> 恢复）
        - 保持相同的 thread_id 恢复执行
        - 流式输出在恢复后继续

        Args:
            agent_id: Agent ID
            message: 用户消息
            history: 聊天历史
            images: 图片列表
            task_id: 任务ID，用于取消任务
            conversation_id: 会话ID，用于checkpoint隔离

        Yields:
            流式响应数据
        """
        print(f"[DEBUG] langchain_service.py - 执行智能体: agent_id={agent_id}, task_id={task_id}, conversation_id={conversation_id}")
        print(f"[DEBUG] langchain_service.py - 当前智能体列表: {list(self.agents.keys())}")

        if agent_id not in self.agents:
            print(f"[ERROR] langchain_service.py - 智能体不存在: {agent_id}")
            yield {"type": "error", "error": f"Agent {agent_id} not found"}
            return

        agent_data = self.agents[agent_id]
        school_id = agent_data["school_id"]
        agent_config = agent_data["config"]

        # 获取agent的deepagent实例
        if agent_id not in self.agent_deepagents:
            print(f"[ERROR] langchain_service.py - Agent {agent_id} 的deepagent实例不存在")
            yield {"type": "error", "error": f"Agent {agent_id} deepagent instance not found"}
            return

        agent_deepagent = self.agent_deepagents[agent_id]
        deepagent = agent_deepagent["deepagent"]
        tools = agent_deepagent["tools"]
        llm = agent_deepagent["llm"]

        print(f"[DEBUG] langchain_service.py - 找到智能体: {agent_id}, 所属school: {school_id}, 可用工具: {[t.name for t in tools]}")

        # 使用conversation_id作为thread_id，如果没有提供则使用task_id
        thread_id = conversation_id or task_id
        if not thread_id:
            print(f"[WARNING] langchain_service.py - 未提供conversation_id或task_id，使用默认thread_id")
            thread_id = "default_thread"

        print(f"[DEBUG] langchain_service.py - 使用thread_id: {thread_id}")

        # 限制checkpoint数量（在执行前）
        self._limit_checkpoints(agent_id, thread_id, max_checkpoints=50)

        # 创建取消事件
        cancel_event = asyncio.Event()

        # 如果有task_id，注册取消事件到全局管理器
        if task_id:
            from backend.api.chat import task_manager
            # 存储取消事件，以便 /cancel 端点可以触发
            task_manager[task_id] = cancel_event

        # 设置 TaskProTool 的 cancel_event（如果存在）
        if agent_id in self.agent_deepagents:
            agent_data = self.agent_deepagents[agent_id]
            if "task_pro_tool" in agent_data:
                agent_data["task_pro_tool"].set_cancel_event(cancel_event)
                print(f"[DEBUG] langchain_service.py - 已设置 TaskProTool 的 cancel_event: {agent_id}")

        try:
            yield {"type": "thinking_start", "content": "正在分析请求..."}

            # 只传入当前用户消息，checkpoint会自动恢复历史
            user_content = self._build_multimodal_content(message, images)
            messages = [{"role": "user", "content": user_content}]

            print(f"[DEBUG] langchain_service.py - 使用thread_id: {thread_id}, checkpoint会自动恢复历史")

            # 使用DeepAgent的流式输出，传入config参数以使用checkpointer
            config = {"configurable": {"thread_id": thread_id}}

            # 创建线程间通信队列
            result_queue: asyncio.Queue = asyncio.Queue()

            # 获取主事件循环引用（用于线程安全地创建任务）
            main_loop = asyncio.get_event_loop()

            # 定义：在线程中执行 deepagent.stream()
            def _run_deepagent_stream(input_data):
                """在线程中执行 deepagent.stream()"""
                try:
                    print(f"[DEBUG] langchain_service.py - 开始流式执行，输入类型: {type(input_data)}")
                    for chunk in deepagent.stream(input_data, config=config):
                        # 检查取消事件（在线程中）
                        if cancel_event.is_set():
                            print(f"[DEBUG] langchain_service.py - 线程中检测到取消信号")
                            break
                        # 将chunk放入队列
                        import queue
                        try:
                            result_queue.put_nowait(chunk)
                        except queue.Full:
                            print(f"[WARNING] langchain_service.py - 结果队列已满，丢弃chunk")
                    # 流式输出完成，放入结束标记
                    try:
                        result_queue.put_nowait(None)
                    except queue.Full:
                        pass
                    print(f"[DEBUG] langchain_service.py - 流式执行完成")
                except Exception as e:
                    print(f"[ERROR] langchain_service.py - 线程中发生错误: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    # 将错误放入队列
                    try:
                        result_queue.put_nowait({"type": "error", "error": str(e)})
                    except queue.Full:
                        pass

            # 定义：等待用户决策并返回决策值
            async def _wait_for_user_decision(tool_name: str) -> str:
                """等待用户决策，返回 'approve' 或 'reject'"""
                # 创建中断事件并注册到全局管理器
                interrupt_event = asyncio.Event()
                interrupt_manager[thread_id] = {
                    "decision": None,
                    "event": interrupt_event
                }

                try:
                    # 等待用户决策（设置超时时间5分钟）
                    print(f"[DEBUG] langchain_service.py - 等待用户决策...")
                    await asyncio.wait_for(interrupt_event.wait(), timeout=300)

                    # 获取用户决策
                    decision = interrupt_manager[thread_id]["decision"]
                    print(f"[DEBUG] langchain_service.py - 收到用户决策: {decision}")
                    return decision

                except asyncio.TimeoutError:
                    # 超时，自动拒绝
                    print(f"[DEBUG] langchain_service.py - 用户决策超时，自动拒绝")
                    return "reject"

                finally:
                    # 清理中断管理器
                    if thread_id in interrupt_manager:
                        del interrupt_manager[thread_id]

            # 定义：处理单个 chunk 并 yield 结果
            # 注意：使用一个可变对象来传递中断状态，避免在生成器中使用 return
            async def _process_chunk(chunk: dict, interrupt_flag: dict):
                """处理单个chunk，如果发生中断则设置 interrupt_flag['interrupted'] = True"""
                print(f"[DEBUG] langchain_service.py - 处理chunk: {type(chunk)}, keys: {chunk.keys() if isinstance(chunk, dict) else 'N/A'}")

                # 处理不同类型的chunk
                if isinstance(chunk, dict):
                    # DeepAgent返回的格式: {'model': {'messages': [AIMessage(...)]}}
                    if 'model' in chunk and 'messages' in chunk['model']:
                        messages_list = chunk['model']['messages']
                        for msg in messages_list:
                            if hasattr(msg, 'content') and msg.content:
                                # 检查是否是AI回复（排除用户消息）
                                if hasattr(msg, 'type') and msg.type == 'ai':
                                    # 检查是否有工具调用
                                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                        for tool_call in msg.tool_calls:
                                            tool_name = tool_call.get('name', '')
                                            tool_args = tool_call.get('args', {})

                                            # 检测 load_skill 工具调用并注入 skill 内容
                                            if tool_name == 'load_skill':
                                                skill_context = self._detect_and_load_skill(tool_name, tool_args)
                                                if skill_context:
                                                    # 将 skill 内容注入到 graph 状态
                                                    success = self._inject_skill_to_graph_state(deepagent, thread_id, skill_context)
                                                    if success:
                                                        yield {"type": "thinking_content", "content": f"\n\n已加载 Skill: {skill_context['skill_id']} (披露级别: {skill_context['disclosure_level']})\n内容已注入到上下文"}
                                            
                                    # 检查 finish_reason 决定输出位置
                                    finish_reason = None
                                    if hasattr(msg, 'response_metadata') and msg.response_metadata:
                                        finish_reason = msg.response_metadata.get('finish_reason', '') if msg.response_metadata else None

                                    if finish_reason == 'tool_calls':
                                        # AI 决定调用工具，输出到深度思考框
                                        yield {"type": "thinking_content", "content": f"\n{msg.content}"}
                                    else:
                                        # AI 完成回复，输出到气泡中
                                        yield {"type": "content", "content": msg.content}

                    # 处理工具调用结果
                    elif 'tools' in chunk:
                        print(f"[DEBUG] langchain_service.py - 收到 tools chunk，keys: {chunk['tools'].keys()}")
                        # 检查是否有 todos 字段（write_todos 工具）
                        if 'todos' in chunk['tools']:
                            todos = chunk['tools']['todos']
                            print(f"[DEBUG] langchain_service.py - 检测到 todos 数据: {todos}, 类型: {type(todos)}")
                            if todos:
                                formatted_todos = self._format_todo_list(todos)
                                print(f"[DEBUG] langchain_service.py - 格式化后的 todos: {formatted_todos}")
                                yield {"type": "thinking_content", "content": f"\n\n    工具 write_todos 执行完成\n输出:\n{formatted_todos}"}

                        # 处理 messages
                        if 'messages' in chunk['tools']:
                            messages_list = chunk['tools']['messages']
                            for msg in messages_list:
                                if hasattr(msg, 'name') and hasattr(msg, 'content'):
                                    tool_name = msg.name
                                    tool_result = msg.content
                                    print(f"[DEBUG] langchain_service.py - 处理工具消息: {tool_name}, content: {tool_result[:100]}")
                                    # read_file 工具和 write_todos 工具不输出原始结果（write_todos 已在上面处理）
                                    if tool_name == 'read_file':
                                        yield {"type": "thinking_content", "content": f"\n\n    工具 {tool_name} 执行完成\n"}
                                    elif tool_name == 'write_todos':
                                        # write_todos 已在上面处理，跳过原始输出
                                        print(f"[DEBUG] langchain_service.py - 跳过 write_todos 的原始输出")
                                        pass
                                    elif tool_name == 'task_pro':
                                        # task_pro 工具现在直接返回最终结果字符串
                                        # LangGraph会自动将字符串包装成ToolMessage
                                        # 前端通过轮询数据库读取 SUB Agent 的执行过程
                                        yield {"type": "thinking_content", "content": f"\n\n    工具 {tool_name} 执行完成\n输出: {tool_result}"}
                                    else:
                                        yield {"type": "thinking_content", "content": f"\n\n    工具 {tool_name} 执行完成\n输出: {tool_result}"}

                    # 处理中间件节点流转
                    elif 'TodoListMiddleware.after_model' in chunk:
                        todo_list = chunk.get('TodoListMiddleware.after_model')
                        print(f"[DEBUG] langchain_service.py - TodoListMiddleware.after_model 值: {todo_list}, 类型: {type(todo_list)}")
                        if todo_list:
                            yield {"type": "thinking_content", "content": f"\n 任务清单已更新:\n{self._format_todo_list(todo_list)}"}

                    # 处理中断事件（HumanInTheLoopMiddleware）
                    elif '__interrupt__' in chunk:
                        interrupt_obj = chunk.get('__interrupt__')
                        print(f"[DEBUG] langchain_service.py - 收到中断事件: {interrupt_obj}, 类型: {type(interrupt_obj)}")

                        # interrupt_obj 是一个元组 (Interrupt(...),)，需要获取第一个元素
                        if isinstance(interrupt_obj, tuple) and len(interrupt_obj) > 0:
                            interrupt_obj = interrupt_obj[0]

                        if interrupt_obj and hasattr(interrupt_obj, 'value'):
                            # 解析中断对象
                            interrupt_value = interrupt_obj.value
                            action_requests = interrupt_value.get('action_requests', [])

                            if action_requests:
                                # 获取第一个 action_request
                                action_request = action_requests[0]
                                tool_name = action_request.get('name', '')
                                tool_args = action_request.get('args', {})

                                print(f"[DEBUG] langchain_service.py - 工具名称: {tool_name}, 工具参数: {tool_args}")

                                # 发送中断信息给前端
                                yield {
                                    "type": "interrupt",
                                    "tool_name": tool_name,
                                    "tool_args": tool_args,
                                    "thread_id": thread_id
                                }

                                # 设置中断标志
                                interrupt_flag['interrupted'] = True

                    # 处理错误
                    elif 'error' in chunk:
                        yield {"type": "error", "error": chunk['error']}

            # ===== 主执行流程 =====
            # 使用闭包变量来跟踪状态，避免在生成器中使用 return
            iteration_state = {'is_interrupted': False, 'is_cancelled': False}

            # 定义：处理一轮流式输出
            async def _handle_stream_iteration():
                """处理一轮流式输出，结果存储在 iteration_state 中"""
                iteration_state['is_interrupted'] = False
                iteration_state['is_cancelled'] = False

                while True:
                    # 检查取消事件
                    if cancel_event.is_set():
                        print(f"[DEBUG] langchain_service.py - 主线程检测到取消信号")
                        iteration_state['is_cancelled'] = True
                        return

                    # 从队列中获取chunk
                    try:
                        chunk = await asyncio.wait_for(result_queue.get(), timeout=0.1)
                    except asyncio.TimeoutError:
                        continue

                    # 检查结束标记
                    if chunk is None:
                        print(f"[DEBUG] langchain_service.py - 收到结束标记")
                        return

                    # 处理chunk（使用可变对象传递中断状态）
                    interrupt_flag = {'interrupted': False}
                    async for item in _process_chunk(chunk, interrupt_flag):
                        yield item

                    # 检查是否发生了中断
                    if interrupt_flag.get('interrupted', False):
                        iteration_state['is_interrupted'] = True
                        return

            # 第一次执行：使用初始输入
            print(f"[DEBUG] langchain_service.py - 开始第一次执行")
            stream_task = asyncio.create_task(asyncio.to_thread(_run_deepagent_stream, {"messages": messages}))

            # 处理流式输出
            async for item in _handle_stream_iteration():
                yield item

            # 如果发生中断，进入恢复循环
            while iteration_state.get('is_interrupted', False) and not cancel_event.is_set():
                print(f"[DEBUG] langchain_service.py - 进入中断恢复循环")

                # 等待用户决策
                decision = await _wait_for_user_decision("tool")

                # 根据决策发送反馈
                if decision == "reject":
                    yield {"type": "thinking_content", "content": f"\n\n用户拒绝了工具执行"}
                else:
                    yield {"type": "thinking_content", "content": f"\n\n用户同意执行工具"}

                # 清空队列（确保没有残留数据）
                while not result_queue.empty():
                    try:
                        result_queue.get_nowait()
                    except:
                        break

                # 使用 Command(resume=...) 恢复执行
                # HumanInTheLoopMiddleware 期望的格式是 {"decisions": [{"type": "approve"}]}
                from langgraph.types import Command
                
                if decision == "approve":
                    resume_value = {"decisions": [{"type": "approve"}]}
                elif decision == "reject":
                    resume_value = {"decisions": [{"type": "reject", "message": "用户拒绝了工具执行"}]}
                else:
                    resume_value = {"decisions": [{"type": "reject", "message": f"未知决策: {decision}"}]}
                
                print(f"[DEBUG] langchain_service.py - 使用 Command(resume={resume_value}) 恢复执行")

                # 启动新的流式任务（恢复执行）
                stream_task = asyncio.create_task(asyncio.to_thread(_run_deepagent_stream, Command(resume=resume_value)))

                # 继续处理恢复后的流式输出
                async for item in _handle_stream_iteration():
                    yield item

            # 等待流式任务完成（如果还没有完成）
            if not stream_task.done():
                stream_task.cancel()
                try:
                    await stream_task
                except asyncio.CancelledError:
                    pass

            # 如果没有取消，返回checkpoint信息
            if not cancel_event.is_set():
                checkpoint_info = self.get_latest_checkpoint_info(agent_id, thread_id)
                if checkpoint_info:
                    print(f"[DEBUG] langchain_service.py - 返回checkpoint信息: {checkpoint_info}")
                    yield {
                        "type": "checkpoint_info",
                        "thread_id": checkpoint_info["thread_id"],
                        "checkpoint_id": checkpoint_info["checkpoint_id"],
                        "parent_checkpoint_id": checkpoint_info["parent_checkpoint_id"]
                    }

                yield {"type": "thinking_end", "content": ""}
                yield {"type": "done"}
            else:
                yield {"type": "cancelled", "message": "Task was cancelled"}

        except asyncio.CancelledError:
            print(f"[DEBUG] langchain_service.py - 任务被取消: task_id={task_id}")
            yield {"type": "cancelled", "message": "Task was cancelled"}
            raise
        except Exception as e:
            import traceback
            print(f"[ERROR] langchain_service.py - 执行智能体失败: {str(e)}")
            traceback.print_exc()
            yield {"type": "error", "error": str(e)}
        finally:
            # 清理任务管理器
            if task_id and task_id in task_manager:
                del task_manager[task_id]

    # ==================== 删除智能体方法 ====================

    def delete_agent(self, agent_id: str) -> bool:
        """删除智能体
        
        Args:
            agent_id: Agent ID
            
        Returns:
            是否删除成功
        """
        if agent_id not in self.agents:
            return False
        
        # 删除agent的deepagent实例
        if agent_id in self.agent_deepagents:
            print(f"[DEBUG] langchain_service.py - 删除agent {agent_id} 的deepagent实例")
            del self.agent_deepagents[agent_id]
        
        # 删除agent的checkpointer
        if agent_id in self.agent_checkpointers:
            print(f"[DEBUG] langchain_service.py - 删除agent {agent_id} 的checkpointer")
            del self.agent_checkpointers[agent_id]
        
        # 删除agent的文件夹（包含checkpoint数据库）
        self._delete_agent_folder(agent_id)
        
        # 删除agent
        del self.agents[agent_id]
        
        return True

    async def update_agent_config(self, agent_id: str, new_config: Dict) -> bool:
        """更新agent配置，实时更新对应的agent实例

        Args:
            agent_id: Agent ID
            new_config: 新的agent配置

        Returns:
            是否更新成功
        """
        if agent_id not in self.agents:
            print(f"[ERROR] langchain_service.py - Agent {agent_id} 不存在，无法更新配置")
            return False

        print(f"[DEBUG] langchain_service.py - 更新agent {agent_id} 的配置")

        agent_data = self.agents[agent_id]
        school_id = agent_data["school_id"]

        # 删除旧的agent deepagent实例
        if agent_id in self.agent_deepagents:
            print(f"[DEBUG] langchain_service.py - 删除agent {agent_id} 的旧deepagent实例")
            del self.agent_deepagents[agent_id]

        # 更新agent配置
        agent_data["config"] = new_config

        # 获取agent的checkpointer（如果已存在则复用）
        checkpointer = self._get_agent_checkpointer(agent_id)
        if not checkpointer:
            print(f"[ERROR] langchain_service.py - 获取checkpointer失败")
            return False

        # 配置 Composite Backend（支持 /skills/ 和 /output/ 路由）
        skills_dir = get_skills_dir()
        output_dir = get_output_dir()
        print(f"[DEBUG] langchain_service.py - 配置 Composite Backend，skills 目录: {skills_dir}, output 目录: {output_dir}")

        # 创建 CompositeBackend 实例
        composite_backend = CompositeBackend(
            skills_dir=str(skills_dir),
            output_dir=str(output_dir),
            virtual_mode=True
        )
        print(f"[DEBUG] langchain_service.py - CompositeBackend 创建成功")

        # 获取system_prompt（不包含输出目录信息）
        system_prompt = new_config.get("system_prompt")

        # 获取school配置的 skills 列表
        school = self._get_school_by_id(school_id)
        school_skills_config = school.get("skills", []) if school else []
        enabled_skill_ids = []
        for skill_config in school_skills_config:
            if skill_config.get("enabled", True):
                enabled_skill_ids.append(skill_config.get("skill_id"))

        # 设置披露级别为 metadata（渐进式披露：启动时只加载元数据）
        self.skills_middleware.set_disclosure_level("metadata")

        # 格式化 skills 为提示词（只包含元数据）
        skills_prompt = self.skills_middleware.format_skills_for_prompt(enabled_skill_ids)

        # 将 skills 信息添加到 system_prompt
        if skills_prompt:
            if system_prompt:
                system_prompt = f"{system_prompt}\n\n{skills_prompt}"
            else:
                system_prompt = skills_prompt

        # 创建新的deepagent实例
        print(f"[DEBUG] langchain_service.py - 为agent {agent_id} 创建新的deepagent实例")
        llm = self._create_llm(new_config)
        tools = await self._create_tools(school_id)
        deepagent = create_deep_agent(
            model=llm,
            tools=tools,
            system_prompt=system_prompt,
            backend=composite_backend,
            checkpointer=checkpointer,
            middleware=[
                # 使用 create_deep_agent 内置的 SummarizationMiddleware
                HumanInTheLoopMiddleware(
                    interrupt_on={
                        "SandboxExecute": {
                            "allowed_decisions": ["approve", "reject"]
                        }
                    }
                )
            ]
        )

        agent_deepagent_data = {
            "deepagent": deepagent,
            "tools": tools,
            "llm": llm,
            "created_at": new_config.get("created_at"),
            "school_id": school_id,
            "composite_backend": composite_backend
        }
        self.agent_deepagents[agent_id] = agent_deepagent_data

        print(f"[DEBUG] langchain_service.py - Agent {agent_id} 的配置已更新，deepagent实例已重新创建（保留checkpointer）")
        return True

    async def move_agent_to_school(self, agent_id: str, new_school_id: str, agent_config: Dict) -> bool:
        """将agent移动到不同的school

        Args:
            agent_id: Agent ID
            new_school_id: 新的School ID
            agent_config: Agent配置（用于创建LLM）

        Returns:
            是否移动成功
        """
        if agent_id not in self.agents:
            print(f"[ERROR] langchain_service.py - Agent {agent_id} 不存在")
            return False

        agent_data = self.agents[agent_id]
        old_school_id = agent_data["school_id"]

        if old_school_id == new_school_id:
            print(f"[DEBUG] langchain_service.py - Agent {agent_id} 已经在school {new_school_id} 中，无需移动")
            return True

        print(f"[DEBUG] langchain_service.py - 将agent {agent_id} 从school {old_school_id} 移动到school {new_school_id}")

        # 更新agent的school_id
        agent_data["school_id"] = new_school_id

        # 删除旧的agent deepagent实例
        if agent_id in self.agent_deepagents:
            print(f"[DEBUG] langchain_service.py - 删除agent {agent_id} 的旧deepagent实例")
            del self.agent_deepagents[agent_id]

        # 获取agent的checkpointer（如果已存在则复用）
        checkpointer = self._get_agent_checkpointer(agent_id)
        if not checkpointer:
            print(f"[ERROR] langchain_service.py - 获取checkpointer失败")
            return False

        # 配置 Composite Backend（支持 /skills/ 和 /output/ 路由）
        skills_dir = get_skills_dir()
        output_dir = get_output_dir()
        print(f"[DEBUG] langchain_service.py - 配置 Composite Backend，skills 目录: {skills_dir}, output 目录: {output_dir}")

        # 创建 CompositeBackend 实例
        composite_backend = CompositeBackend(
            skills_dir=str(skills_dir),
            output_dir=str(output_dir),
            virtual_mode=True
        )
        print(f"[DEBUG] langchain_service.py - CompositeBackend 创建成功")

        # 获取system_prompt（不包含输出目录信息）
        system_prompt = agent_config.get("system_prompt")

        # 获取新school配置的 skills 列表
        new_school = self._get_school_by_id(new_school_id)
        school_skills_config = new_school.get("skills", []) if new_school else []
        enabled_skill_ids = []
        for skill_config in school_skills_config:
            if skill_config.get("enabled", True):
                enabled_skill_ids.append(skill_config.get("skill_id"))

        # 设置披露级别为 metadata（渐进式披露：启动时只加载元数据）
        self.skills_middleware.set_disclosure_level("metadata")

        # 格式化 skills 为提示词（只包含元数据）
        skills_prompt = self.skills_middleware.format_skills_for_prompt(enabled_skill_ids)

        # 将 skills 信息添加到 system_prompt
        if skills_prompt:
            if system_prompt:
                system_prompt = f"{system_prompt}\n\n{skills_prompt}"
            else:
                system_prompt = skills_prompt

        # 为agent创建新的deepagent实例（使用新school的工具配置）
        print(f"[DEBUG] langchain_service.py - 为agent {agent_id} 创建新的deepagent实例（school: {new_school_id}）")
        llm = self._create_llm(agent_config)
        tools = await self._create_tools(new_school_id)
        deepagent = create_deep_agent(
            model=llm,
            tools=tools,
            system_prompt=system_prompt,
            backend=composite_backend,
            checkpointer=checkpointer,
            middleware=[
                # 使用 create_deep_agent 内置的 SummarizationMiddleware
            ]
        )

        agent_deepagent_data = {
            "deepagent": deepagent,
            "tools": tools,
            "llm": llm,
            "created_at": agent_config.get("created_at"),
            "school_id": new_school_id,
            "composite_backend": composite_backend
        }
        self.agent_deepagents[agent_id] = agent_deepagent_data

        print(f"[DEBUG] langchain_service.py - Agent {agent_id} 已成功移动到school {new_school_id}，deepagent实例已更新（保留checkpointer）")
        return True

    def delete_conversation_checkpoints(self, agent_id: str, conversation_id: str) -> bool:
        """删除指定会话的所有checkpoint（公共方法）
        
        Args:
            agent_id: Agent ID
            conversation_id: 会话ID
            
        Returns:
            是否删除成功
        """
        print(f"[DEBUG] langchain_service.py - 删除会话checkpoint: agent_id={agent_id}, conversation_id={conversation_id}")
        return self._delete_conversation_checkpoints(agent_id, conversation_id)

    def get_agent_info(self, agent_id: str) -> Optional[Dict]:
        """获取智能体信息

        Args:
            agent_id: Agent ID

        Returns:
            智能体信息
        """
        if agent_id in self.agents:
            return {
                "agent_id": agent_id,
                "school_id": self.agents[agent_id]["school_id"],
                "config": self.agents[agent_id]["config"],
                "created_at": self.agents[agent_id]["created_at"]
            }
        return None

    def get_latest_checkpoint_info(self, agent_id: str, conversation_id: str) -> Optional[Dict]:
        """获取指定会话的最新checkpoint信息

        Args:
            agent_id: Agent ID
            conversation_id: 会话ID

        Returns:
            包含thread_id, checkpoint_id, parent_checkpoint_id的字典，如果失败返回None
        """
        try:
            db_path = self._get_agent_checkpoint_db_path(agent_id)
            if not os.path.exists(db_path):
                print(f"[DEBUG] langchain_service.py - 数据库不存在: {db_path}")
                return None

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 查询该thread_id的最新checkpoint
            cursor.execute("""
                SELECT thread_id, checkpoint_id, parent_checkpoint_id
                FROM checkpoints
                WHERE thread_id = ?
                ORDER BY checkpoint_id DESC
                LIMIT 1
            """, (conversation_id,))

            result = cursor.fetchone()
            conn.close()

            if result:
                thread_id, checkpoint_id, parent_checkpoint_id = result
                print(f"[DEBUG] langchain_service.py - 找到最新checkpoint: thread_id={thread_id}, checkpoint_id={checkpoint_id}, parent_checkpoint_id={parent_checkpoint_id}")
                return {
                    "thread_id": thread_id,
                    "checkpoint_id": checkpoint_id,
                    "parent_checkpoint_id": parent_checkpoint_id
                }
            else:
                print(f"[DEBUG] langchain_service.py - 未找到checkpoint: agent_id={agent_id}, conversation_id={conversation_id}")
                return None
        except Exception as e:
            print(f"[ERROR] langchain_service.py - 获取最新checkpoint信息失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def add_checkpoint_to_conversation(self, agent_id: str, source_checkpoint_id: str, target_thread_id: str) -> bool:
        """添加指定checkpoint的记忆到目标会话

        使用 LangGraph 官方 API 实现跨线程复制功能：
        - 查询源 checkpoint 的 thread_id
        - 使用 graph.get_state(source_config) 获取源状态
        - 使用 graph.update_state(target_config, values) 复制到目标 thread_id
        - LangGraph 自动创建新的 checkpoint 并维护正确的链式关系

        Args:
            agent_id: Agent ID
            source_checkpoint_id: 源checkpoint ID
            target_thread_id: 目标会话ID（thread_id）

        Returns:
            是否成功
        """
        try:
            # 1. 验证 agent 存在
            if agent_id not in self.agents:
                print(f"[ERROR] langchain_service.py - 智能体不存在: {agent_id}")
                return False

            # 2. 获取 agent 的 deepagent 实例
            if agent_id not in self.agent_deepagents:
                print(f"[ERROR] langchain_service.py - Agent {agent_id} 的deepagent实例不存在")
                return False

            agent_deepagent = self.agent_deepagents[agent_id]
            deepagent = agent_deepagent["deepagent"]

            # 3. 查询源 checkpoint 的 thread_id
            db_path = self._get_agent_checkpoint_db_path(agent_id)
            if not os.path.exists(db_path):
                print(f"[ERROR] langchain_service.py - 数据库不存在: {db_path}")
                return False

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT thread_id
                FROM checkpoints
                WHERE checkpoint_id = ?
            """, (source_checkpoint_id,))
            result = cursor.fetchone()
            conn.close()

            if not result:
                print(f"[ERROR] langchain_service.py - 源checkpoint不存在: {source_checkpoint_id}")
                return False

            source_thread_id = result[0]
            print(f"[DEBUG] langchain_service.py - 找到源checkpoint: source_thread_id={source_thread_id}, checkpoint_id={source_checkpoint_id}")

            # 4. 检查 deepagent 是否支持 get_state 和 update_state 方法
            # LangGraph 的 StateGraph 实例应该有这些方法
            if not hasattr(deepagent, 'get_state') or not hasattr(deepagent, 'update_state'):
                print(f"[ERROR] langchain_service.py - DeepAgent 实例不支持 get_state/update_state 方法")
                # 尝试访问 deepagent.graph 属性
                if hasattr(deepagent, 'graph'):
                    graph = deepagent.graph
                    if not hasattr(graph, 'get_state') or not hasattr(graph, 'update_state'):
                        print(f"[ERROR] langchain_service.py - DeepAgent.graph 也不支持 get_state/update_state 方法")
                        return False
                    print(f"[DEBUG] langchain_service.py - 使用 deepagent.graph")
                else:
                    return False
            else:
                graph = deepagent
                print(f"[DEBUG] langchain_service.py - 使用 deepagent 实例")

            # 5. 使用 LangGraph API 获取源状态（指定 checkpoint_id）
            source_config = {
                "configurable": {
                    "thread_id": source_thread_id,
                    "checkpoint_id": source_checkpoint_id
                }
            }
            try:
                source_state = graph.get_state(source_config)
                print(f"[DEBUG] langchain_service.py - 成功获取源状态: thread_id={source_thread_id}")
            except Exception as e:
                print(f"[ERROR] langchain_service.py - 获取源状态失败: {e}")
                import traceback
                traceback.print_exc()
                return False

            # 6. 使用 LangGraph API 更新目标 thread_id 的状态
            target_config = {"configurable": {"thread_id": target_thread_id}}
            try:
                # 获取状态值并更新到目标 thread
                state_values = source_state.values if hasattr(source_state, 'values') else source_state
                graph.update_state(target_config, state_values)
                print(f"[DEBUG] langchain_service.py - 成功复制状态到目标 thread: {target_thread_id}")
                print(f"[DEBUG] langchain_service.py - LangGraph 自动创建新的 checkpoint 并维护链式关系")
            except Exception as e:
                print(f"[ERROR] langchain_service.py - 更新目标状态失败: {e}")
                import traceback
                traceback.print_exc()
                return False

            print(f"[DEBUG] langchain_service.py - Checkpoint添加成功: {source_checkpoint_id} (thread: {source_thread_id}) -> {target_thread_id}")
            return True

        except Exception as e:
            print(f"[ERROR] langchain_service.py - 复制checkpoint失败: {e}")
            import traceback
            traceback.print_exc()
            return False


# 全局实例
langchain_service = LangChainAgentService()

# 全局中断决策管理器：存储中断状态和用户决策
interrupt_manager: Dict[str, Dict] = {}  # key: thread_id, value: {"decision": "approve"/"reject", "event": asyncio.Event}
