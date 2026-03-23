from typing import List, Dict, Optional, AsyncGenerator
from datetime import datetime
import asyncio
from backend.core.model_provider import model_provider


class ChatEngine:
    def __init__(self):
        self.active_sessions: Dict[str, List[Dict]] = {}
    
    async def send_message(
        self,
        model_config: Dict,
        message: str,
        images: Optional[List[str]] = None,
        history: Optional[List[Dict]] = None
    ) -> Dict:
        """发送消息并获取响应"""
        print(f"[DEBUG] chat_engine.py - 收到消息: message={message}, images={images is not None}")
        if images:
            print(f"[DEBUG] chat_engine.py - 图片数量: {len(images)}")
        
        # 设置模型配置
        model_provider.set_config(model_config)
        
        # 准备消息历史
        messages = []

        # 添加system prompt（如果有）
        system_prompt = model_config.get("system_prompt")
        if system_prompt and system_prompt.strip():
            messages.append({
                "role": "system",
                "content": system_prompt.strip()
            })
        
        if history:
            # 将历史消息转换为API格式
            for msg in history:
                messages.append({
                    "role": msg.get("role"),
                    "content": msg.get("content", "")
                })
        
        # 添加当前消息
        messages.append({
            "role": "user",
            "content": message
        })
        
        # 调用模型生成响应
        try:
            result = await model_provider.generate_response(
                messages=messages,
                images=images
            )
            
            # result现在是字典，包含content和thinking
            content = result.get("content", "")
            thinking = result.get("thinking")
            
            print(f"[DEBUG] chat_engine.py - 收到content: {content[:100] if content else 'None'}")
            print(f"[DEBUG] chat_engine.py - 收到thinking: {thinking[:100] if thinking else 'None'}")
            
            response = {
                "id": f"msg_{datetime.now().timestamp()}",
                "role": "assistant",
                "content": content,
                "thinking": thinking,
                "timestamp": datetime.now().isoformat()
            }
            
            return response
        except Exception as e:
            # 返回错误信息
            response = {
                "id": f"msg_{datetime.now().timestamp()}",
                "role": "assistant",
                "content": f"抱歉，生成响应时出错: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            return response
    
    async def stream_message(
        self,
        model_config: Dict,
        message: str,
        images: Optional[List[str]] = None,
        history: Optional[List[Dict]] = None,
        task_id: Optional[str] = None
    ) -> AsyncGenerator[Dict, None]:
        """流式发送消息并获取响应（真正的流式输出）"""
        print(f"[DEBUG] chat_engine.py - stream_message 开始")
        print(f"[DEBUG] chat_engine.py - task_id: {task_id}")
        print(f"[DEBUG] chat_engine.py - message: {message[:100]}")
        print(f"[DEBUG] chat_engine.py - images: {images is not None}")
        
        # 设置模型配置
        model_provider.set_config(model_config)
        
        # 准备消息历史
        messages = []

        # 添加system prompt（如果有）
        system_prompt = model_config.get("system_prompt")
        if system_prompt and system_prompt.strip():
            messages.append({
                "role": "system",
                "content": system_prompt.strip()
            })
        
        if history:
            for msg in history:
                messages.append({
                    "role": msg.get("role"),
                    "content": msg.get("content", "")
                })
        
        # 添加当前消息
        messages.append({
            "role": "user",
            "content": message
        })
        
        print(f"[DEBUG] chat_engine.py - 准备调用 model_provider.stream_response_with_thinking")
        
        # 调用模型生成响应（真正的流式输出）
        try:
            chunk_count = 0
            # 直接转发流式数据，不做任何延迟处理
            async for chunk in model_provider.stream_response_with_thinking(
                messages=messages,
                images=images
            ):
                chunk_count += 1
                if chunk_count % 5 == 0:
                    print(f"[DEBUG] chat_engine.py - 已转发 {chunk_count} 个chunk")
                print(f"[DEBUG] chat_engine.py - 收到chunk: {chunk}")
                # 检查是否被取消
                if task_id:
                    from backend.api.chat import task_manager
                    if task_manager.get(task_id, False):
                        print(f"[DEBUG] chat_engine.py - 检测到取消标志")
                        raise asyncio.CancelledError()
                # 直接转发流式数据
                yield chunk
            print(f"[DEBUG] chat_engine.py - stream_message 完成，共转发 {chunk_count} 个chunk")
        except asyncio.CancelledError:
            print(f"[DEBUG] chat_engine.py - 任务被取消: task_id={task_id}")
            yield {"type": "cancelled", "message": "Task was cancelled"}
            raise
        except Exception as e:
            print(f"[ERROR] chat_engine.py - stream_message 发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            yield {"type": "error", "error": str(e)}
    
    def create_session(self, session_id: str) -> str:
        """创建会话"""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = []
        return session_id
    
    def add_message_to_session(self, session_id: str, message: Dict):
        """添加消息到会话"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id].append(message)
    
    def get_session_messages(self, session_id: str) -> List[Dict]:
        """获取会话消息"""
        return self.active_sessions.get(session_id, [])


chat_engine = ChatEngine()
