from typing import Dict, Optional, List, AsyncGenerator
import httpx
import base64
import json


class ModelProvider:
    def __init__(self):
        self.current_model = None
        self.api_key = None
        self.api_base = None
        self.provider = None
        self.temperature = 0.7
        self.max_tokens = 2048
        self.thinking = False
        self.top_p = 0.9
        self.top_k = 40
        self.repeat_penalty = 1.1
        self.presence_penalty = 0
        self.system_prompt = None

    def set_config(self, config: Dict):
        """设置模型配置"""
        self.provider = config.get("provider")
        self.api_key = config.get("api_key")
        self.api_base = config.get("api_base")
        self.current_model = config.get("model")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2048)
        self.thinking = config.get("thinking", False)
        self.top_p = config.get("top_p", 0.9)
        self.top_k = config.get("top_k", 40)
        self.repeat_penalty = config.get("repeat_penalty", 1.1)
        self.presence_penalty = config.get("presence_penalty", 0)
        self.system_prompt = config.get("system_prompt")

    async def generate_response(
        self,
        messages: List[Dict],
        images: Optional[List[str]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, str]:
        """生成响应（非流式），返回包含content和thinking的字典"""
        print(f"[DEBUG] model_provider.py - generate_response: images={images is not None}")
        if images:
            print(f"[DEBUG] model_provider.py - 图片数量: {len(images)}")

        model = model or self.current_model
        temperature = temperature or self.temperature
        max_tokens = max_tokens or self.max_tokens

        if self.provider == "openai":
            return await self._call_openai(messages, images, model, temperature, max_tokens)
        elif self.provider == "anthropic":
            return await self._call_anthropic(messages, images, model, temperature, max_tokens)
        elif self.provider == "ollama":
            return await self._call_ollama(messages, images, model, temperature, max_tokens)
        elif self.provider == "aliyun":
            return await self._call_aliyun(messages, images, model, temperature, max_tokens)
        elif self.provider == "custom":
            return await self._call_custom(messages, images, model, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def stream_response_with_thinking(
        self,
        messages: List[Dict],
        images: Optional[List[str]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[Dict[str, str], None]:
        """流式生成响应，实时解析 thinking 标签，返回结构化数据

        返回格式：
        - {"type": "thinking_start", "content": ""}
        - {"type": "thinking_content", "content": "思考内容"}
        - {"type": "thinking_end", "content": ""}
        - {"type": "content", "content": "回复内容"}
        - {"type": "done", "content": ""}
        """
        print(f"[DEBUG] model_provider.py - stream_response_with_thinking: images={images is not None}")
        if images:
            print(f"[DEBUG] model_provider.py - 图片数量: {len(images)}")

        model = model or self.current_model
        temperature = temperature or self.temperature
        max_tokens = max_tokens or self.max_tokens

        if self.provider == "openai":
            async for chunk in self._stream_openai_with_thinking(messages, images, model, temperature, max_tokens):
                yield chunk
        elif self.provider == "anthropic":
            async for chunk in self._stream_anthropic_with_thinking(messages, images, model, temperature, max_tokens):
                yield chunk
        elif self.provider == "ollama":
            async for chunk in self._stream_ollama_with_thinking(messages, images, model, temperature, max_tokens):
                yield chunk
        elif self.provider == "aliyun":
            async for chunk in self._stream_aliyun_with_thinking(messages, images, model, temperature, max_tokens):
                yield chunk
        elif self.provider == "custom":
            async for chunk in self._stream_custom_with_thinking(messages, images, model, temperature, max_tokens):
                yield chunk
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def _call_openai(
        self,
        messages: List[Dict],
        images: Optional[List[str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, str]:
        """调用OpenAI API，返回包含content和thinking的字典"""
        try:
            # 如果有图片，需要将图片添加到最后一条用户消息中
            api_messages = self._prepare_messages_with_images(messages, images)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # 构建payload，包含所有支持的参数
            payload = {
                "model": model,
                "messages": api_messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            # 添加可选参数（只传递非None和非默认值的参数）
            if self.top_p is not None:
                payload["top_p"] = self.top_p

            if self.presence_penalty is not None:
                payload["presence_penalty"] = self.presence_penalty

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                message = result["choices"][0].get("message", {})
                content = message.get("content", "")

                # 根据thinking配置决定是否提取thinking内容
                thinking = None
                if self.thinking:
                    # 如果启用了thinking，提取thinking内容
                    thinking = message.get("reasoning_content") or message.get("thinking")
                else:
                    # 如果未启用thinking，不提取thinking内容
                    thinking = None

                return {"content": content or "", "thinking": thinking}
        except Exception as e:
            raise Exception(f"OpenAI API调用失败: {str(e)}")

    async def _call_anthropic(
        self,
        messages: List[Dict],
        images: Optional[List[str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, str]:
        """调用Anthropic API，返回包含content和thinking的字典"""
        try:
            # Anthropic API格式略有不同
            api_messages = self._prepare_messages_with_images(messages, images, anthropic=True)

            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }

            # 构建payload，包含所有支持的参数
            payload = {
                "model": model,
                "messages": api_messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            # 添加可选参数（只传递非None和非默认值的参数）
            if self.top_p is not None:
                payload["top_p"] = self.top_p

            if self.presence_penalty is not None:
                payload["presence_penalty"] = self.presence_penalty

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.api_base}/v1/messages",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                content = result["content"][0]["text"]

                # 根据thinking配置决定是否提取thinking内容
                thinking = None
                if self.thinking:
                    # 如果启用了thinking，提取thinking内容
                    thinking = result.get("reasoning_content") or result.get("thinking")
                else:
                    # 如果未启用thinking，不提取thinking内容
                    thinking = None

                return {"content": content or "", "thinking": thinking}
        except Exception as e:
            raise Exception(f"Anthropic API调用失败: {str(e)}")

    async def _call_ollama(
        self,
        messages: List[Dict],
        images: Optional[List[str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, str]:
        """调用Ollama API（本地模型），返回包含content和thinking的字典"""
        try:
            print(f"[DEBUG] _call_ollama - 开始调用Ollama API")
            print(f"[DEBUG] _call_ollama - images={images is not None}")
            if images:
                print(f"[DEBUG] _call_ollama - 图片数量: {len(images)}")
                for i, img in enumerate(images):
                    print(f"[DEBUG] _call_ollama - 图片{i}长度: {len(img)}")
                    print(f"[DEBUG] _call_ollama - 图片{i}前50字符: {img[:50]}")

            # Ollama API支持图片，但格式不同
            # 对于多模态模型，使用 /v1/chat/completions 端点
            # images字段需要在payload的顶层，而不是在消息内部

            # 检查是否使用兼容OpenAI格式的端点
            use_openai_format = "-vl" in model.lower() or "vision" in model.lower()

            if use_openai_format:
                # 多模态模型使用OpenAI兼容格式
                api_messages = self._prepare_messages_with_images(messages, images)

                # 构建payload，包含所有支持的参数
                payload = {
                    "model": model,
                    "messages": api_messages,
                    "stream": False,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }

                # 添加可选参数（只传递非None和非默认值的参数）
                if self.top_p is not None:
                    payload["top_p"] = self.top_p

                if self.presence_penalty is not None:
                    payload["presence_penalty"] = self.presence_penalty

                endpoint = f"{self.api_base}/v1/chat/completions"
            else:
                # 普通模型使用Ollama原生格式
                api_messages = self._prepare_messages_with_images(messages, images, ollama=True)

                # 构建payload，包含所有支持的参数
                payload = {
                    "model": model,
                    "messages": api_messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }

                # 添加所有Ollama支持的参数到options中
                if self.top_p is not None:
                    payload["options"]["top_p"] = self.top_p

                if self.top_k is not None:
                    payload["options"]["top_k"] = self.top_k

                if self.repeat_penalty is not None:
                    payload["options"]["repeat_penalty"] = self.repeat_penalty

                if self.presence_penalty is not None:
                    payload["options"]["presence_penalty"] = self.presence_penalty

                # 如果有图片，将images字段添加到payload顶层
                # 注意：Ollama API的images字段需要完整的data URI格式，包括前缀
                if images:
                    print(f"[DEBUG] _call_ollama - 使用完整data URI格式，数量: {len(images)}")
                    payload["images"] = images
                    print(f"[DEBUG] _call_ollama - payload中images字段已添加")

                endpoint = f"{self.api_base}/api/chat"

            print(f"[DEBUG] _call_ollama - 准备发送请求到: {endpoint}")
            print(f"[DEBUG] _call_ollama - payload keys: {list(payload.keys())}")
            print(f"[DEBUG] _call_ollama - 完整payload: {payload}")

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    endpoint,
                    json=payload
                )
                print(f"[DEBUG] _call_ollama - 收到响应，状态码: {response.status_code}")
                response.raise_for_status()
                result = response.json()
                print(f"[DEBUG] _call_ollama - 原始响应内容: {result}")

                # 处理不同格式的响应
                content = None
                thinking = None

                if "choices" in result:
                    # OpenAI兼容格式
                    message = result["choices"][0].get("message", {})
                    content = message.get("content", "")
                    # 优先使用Ollama原生的thinking字段
                    thinking = message.get("thinking")
                    print(f"[DEBUG] _call_ollama - OpenAI格式 - content: {content[:100] if content else 'None'}")
                    print(f"[DEBUG] _call_ollama - OpenAI格式 - thinking: {thinking[:100] if thinking else 'None'}")
                elif "message" in result:
                    # Ollama原生格式
                    message = result.get("message", {})
                    content = message.get("content", "")
                    # 优先使用Ollama原生的thinking字段
                    thinking = message.get("thinking")
                    print(f"[DEBUG] _call_ollama - Ollama原生格式 - content: {content[:100] if content else 'None'}")
                    print(f"[DEBUG] _call_ollama - Ollama原生格式 - thinking: {thinking[:100] if thinking else 'None'}")
                else:
                    raise Exception(f"Unexpected response format: {result}")

                # 根据thinking配置决定是否提取thinking内容
                if self.thinking:
                    # 如果启用了thinking，提取thinking内容
                    if not thinking and content:
                        if "<thinking>" in content:
                            # 提取 <thinking> 标签中的内容
                            import re
                            pattern = r"<thinking>(.*?)</thinking>"
                            matches = re.findall(pattern, content, re.DOTALL)
                            if matches:
                                thinking = "".join(matches)
                                print(f"[DEBUG] _call_ollama - 从content解析出thinking: {thinking[:100] if thinking else 'None'}")
                                # 从content中移除 <thinking> 标签
                                content = re.sub(r"<thinking>.*?</thinking>", "", content, flags=re.DOTALL).strip()
                                print(f"[DEBUG] _call_ollama - 移除thinking后的content: {content[:100] if content else 'None'}")
                else:
                    # 如果未启用thinking，不提取thinking内容，直接返回content
                    thinking = None
                    if content:
                        # 移除content中的thinking标签
                        thinking_pattern = r"<thinking>[\s\S]*?</thinking>"
                        import re
                        content = re.sub(thinking_pattern, '', content, flags=re.DOTALL).strip()

                print(f"[DEBUG] _call_ollama - 最终提取content: {content[:100] if content else 'None'}")
                print(f"[DEBUG] _call_ollama - 最终提取thinking: {thinking[:100] if thinking else 'None'}")

                return {"content": content or "", "thinking": thinking}
        except httpx.HTTPStatusError as e:
            # 提供更详细的错误信息
            error_detail = e.response.text
            raise Exception(f"Ollama API调用失败 (HTTP {e.response.status_code}): {error_detail}")
        except Exception as e:
            raise Exception(f"Ollama API调用失败: {str(e)}")

    async def _call_custom(
        self,
        messages: List[Dict],
        images: Optional[List[str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, str]:
        """调用自定义API（兼容OpenAI格式），返回包含content和thinking的字典"""
        try:
            api_messages = self._prepare_messages_with_images(messages, images)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # 构建payload，包含所有支持的参数
            payload = {
                "model": model,
                "messages": api_messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            # 添加可选参数（只传递非None和非默认值的参数）
            if self.top_p is not None:
                payload["top_p"] = self.top_p

            if self.presence_penalty is not None:
                payload["presence_penalty"] = self.presence_penalty

            # 注意：自定义API可能支持top_k和repeat_penalty参数
            # 取决于具体的API实现，这里我们传递这些参数
            if self.top_k is not None:
                payload["top_k"] = self.top_k

            if self.repeat_penalty is not None:
                payload["repeat_penalty"] = self.repeat_penalty

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                message = result["choices"][0].get("message", {})
                content = message.get("content", "")

                # 根据thinking配置决定是否提取thinking内容
                thinking = None
                if self.thinking:
                    # 如果启用了thinking，提取thinking内容
                    thinking = message.get("reasoning_content") or message.get("thinking")
                else:
                    # 如果未启用thinking，不提取thinking内容
                    thinking = None

                return {"content": content or "", "thinking": thinking}
        except Exception as e:
            raise Exception(f"自定义API调用失败: {str(e)}")

    async def _call_aliyun(
        self,
        messages: List[Dict],
        images: Optional[List[str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, str]:
        """调用阿里云通义千问API（兼容OpenAI格式），返回包含content和thinking的字典"""
        try:
            api_messages = self._prepare_messages_with_images(messages, images)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # 构建payload，包含所有支持的参数
            payload = {
                "model": model,
                "messages": api_messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            # 添加可选参数（只传递非None和非默认值的参数）
            if self.top_p is not None:
                payload["top_p"] = self.top_p

            if self.presence_penalty is not None:
                payload["presence_penalty"] = self.presence_penalty

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                message = result["choices"][0].get("message", {})
                content = message.get("content", "")

                # 根据thinking配置决定是否提取thinking内容
                thinking = None
                if self.thinking:
                    # 如果启用了thinking，提取thinking内容
                    thinking = message.get("reasoning_content") or message.get("thinking")
                else:
                    # 如果未启用thinking，不提取thinking内容
                    thinking = None

                return {"content": content or "", "thinking": thinking}
        except Exception as e:
            raise Exception(f"阿里云API调用失败: {str(e)}")

    def _prepare_messages_with_images(
        self,
        messages: List[Dict],
        images: Optional[List[str]],
        anthropic: bool = False,
        ollama: bool = False
    ) -> List[Dict]:
        """准备包含图片的消息"""
        if not images or len(images) == 0:
            return messages

        # 对于Ollama，images字段在payload顶层，不需要在消息内部处理
        if ollama:
            return messages

        # 找到最后一条用户消息，添加图片
        api_messages = []
        for msg in messages:
            if msg["role"] == "user":
                # 检查是否是最后一条用户消息
                is_last_user = True
                for m in messages[messages.index(msg)+1:]:
                    if m["role"] == "user":
                        is_last_user = False
                        break

                if is_last_user:
                    # 添加所有图片到这条消息
                    if anthropic:
                        # Anthropic格式
                        content = [{"type": "text", "text": msg["content"]}]
                        for image in images:
                            content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": self._extract_base64(image)
                                }
                            })
                        api_messages.append({
                            "role": "user",
                            "content": content
                        })
                    else:
                        # OpenAI/自定义API格式
                        content = [{"type": "text", "text": msg["content"]}]
                        for image in images:
                            content.append({
                                "type": "image_url",
                                "image_url": {"url": image}
                            })
                        api_messages.append({
                            "role": "user",
                            "content": content
                        })
                else:
                    api_messages.append(msg)
            else:
                api_messages.append(msg)

        return api_messages

    def _extract_base64(self, data_uri: str) -> str:
        """从data URI中提取base64数据"""
        if data_uri.startswith("data:"):
            # 移除data:image/xxx;base64,前缀
            return data_uri.split(",", 1)[1]
        return data_uri

    # 流式API方法
    async def _stream_openai_with_thinking(
        self,
        messages: List[Dict],
        images: Optional[List[str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[Dict[str, str], None]:
        """流式调用OpenAI API，使用Ollama官方推荐的reasoning_content字段"""
        try:
            api_messages = self._prepare_messages_with_images(messages, images)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # 构建payload，包含所有支持的参数
            payload = {
                "model": model,
                "messages": api_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }

            # 添加可选参数（只传递非None和非默认值的参数）
            if self.top_p is not None:
                payload["top_p"] = self.top_p

            if self.presence_penalty is not None:
                payload["presence_penalty"] = self.presence_penalty

            # 状态变量
            in_thinking = False
            thinking_started = False

            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get("delta", {})

                                    # 根据thinking配置决定是否处理thinking字段
                                    reasoning_content = None
                                    if self.thinking:
                                        # 如果启用了thinking，提取thinking内容
                                        reasoning_content = delta.get("reasoning_content") or delta.get("thinking")
                                    content = delta.get("content", "")

                                    # 根据thinking配置决定是否处理reasoning_content
                                    if self.thinking:
                                        # 处理reasoning_content
                                        if reasoning_content:
                                            if not in_thinking:
                                                in_thinking = True
                                                thinking_started = True
                                                yield {"type": "thinking_start", "content": ""}
                                            yield {"type": "thinking_content", "content": reasoning_content}
                                        else:
                                            # 如果之前在thinking模式，现在结束了
                                            if in_thinking:
                                                in_thinking = False
                                                yield {"type": "thinking_end", "content": ""}

                                        # 处理普通content
                                        if content:
                                            yield {"type": "content", "content": content}
                                    else:
                                        # 未启用thinking，只输出content，忽略reasoning_content
                                        if content:
                                            yield {"type": "content", "content": content}
                            except json.JSONDecodeError:
                                pass

            # 确保thinking_end已发送
            if in_thinking:
                yield {"type": "thinking_end", "content": ""}

            yield {"type": "done", "content": ""}
        except Exception as e:
            raise Exception(f"OpenAI流式API调用失败: {str(e)}")

    async def _stream_anthropic_with_thinking(
        self,
        messages: List[Dict],
        images: Optional[List[str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[Dict[str, str], None]:
        """流式调用Anthropic API，使用Ollama官方推荐的reasoning_content字段"""
        try:
            api_messages = self._prepare_messages_with_images(messages, images, anthropic=True)

            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }

            # 构建payload，包含所有支持的参数
            payload = {
                "model": model,
                "messages": api_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True
            }

            # 添加可选参数（只传递非None和非默认值的参数）
            if self.top_p is not None:
                payload["top_p"] = self.top_p

            if self.presence_penalty is not None:
                payload["presence_penalty"] = self.presence_penalty

            # 状态变量
            in_thinking = False
            thinking_started = False

            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.api_base}/v1/messages",
                    headers=headers,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            try:
                                chunk = json.loads(data)
                                if chunk.get("type") == "content_block_delta":
                                    delta = chunk.get("delta", {})

                                    # 根据thinking配置决定是否处理thinking字段
                                    reasoning_content = None
                                    if self.thinking:
                                        # 如果启用了thinking，提取thinking内容
                                        reasoning_content = delta.get("reasoning_content") or delta.get("thinking")
                                    text = delta.get("text", "")

                                    # 根据thinking配置决定是否处理reasoning_content
                                    if self.thinking:
                                        # 处理reasoning_content
                                        if reasoning_content:
                                            if not in_thinking:
                                                in_thinking = True
                                                thinking_started = True
                                                yield {"type": "thinking_start", "content": ""}
                                            yield {"type": "thinking_content", "content": reasoning_content}
                                        else:
                                            # 如果之前在thinking模式，现在结束了
                                            if in_thinking:
                                                in_thinking = False
                                                yield {"type": "thinking_end", "content": ""}

                                        # 处理普通text
                                        if text:
                                            yield {"type": "content", "content": text}
                                    else:
                                        # 未启用thinking，只输出text，忽略reasoning_content
                                        if text:
                                            yield {"type": "content", "content": text}
                            except json.JSONDecodeError:
                                pass

            # 确保thinking_end已发送
            if in_thinking:
                yield {"type": "thinking_end", "content": ""}

            yield {"type": "done", "content": ""}
        except Exception as e:
            raise Exception(f"Anthropic流式API调用失败: {str(e)}")

    async def _stream_ollama_with_thinking(
        self,
        messages: List[Dict],
        images: Optional[List[str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[Dict[str, str], None]:
        """流式调用Ollama API，优先使用原生的thinking字段，同时支持解析 <thinking> 标签

        返回格式：
        - {"type": "thinking_start", "content": ""}
        - {"type": "thinking_content", "content": "思考内容"}
        - {"type": "thinking_end", "content": ""}
        - {"type": "content", "content": "回复内容"}
        - {"type": "done", "content": ""}
        """
        try:
            print(f"[DEBUG] _stream_ollama_with_thinking - 开始调用Ollama流式API")
            print(f"[DEBUG] _stream_ollama_with_thinking - thinking配置: {self.thinking}")

            use_openai_format = "-vl" in model.lower() or "vision" in model.lower()

            if use_openai_format:
                api_messages = self._prepare_messages_with_images(messages, images)
                # 构建payload，包含所有支持的参数
                payload = {
                    "model": model,
                    "messages": api_messages,
                    "stream": True,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }

                # 添加可选参数（只传递非None和非默认值的参数）
                if self.top_p is not None:
                    payload["top_p"] = self.top_p

                if self.presence_penalty is not None:
                    payload["presence_penalty"] = self.presence_penalty

                endpoint = f"{self.api_base}/v1/chat/completions"
            else:
                api_messages = self._prepare_messages_with_images(messages, images, ollama=True)
                # 构建payload，包含所有支持的参数
                payload = {
                    "model": model,
                    "messages": api_messages,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }

                # 添加所有Ollama支持的参数到options中
                if self.top_p is not None:
                    payload["options"]["top_p"] = self.top_p

                if self.top_k is not None:
                    payload["options"]["top_k"] = self.top_k

                if self.repeat_penalty is not None:
                    payload["options"]["repeat_penalty"] = self.repeat_penalty

                if self.presence_penalty is not None:
                    payload["options"]["presence_penalty"] = self.presence_penalty

                if images:
                    payload["images"] = images
                endpoint = f"{self.api_base}/api/chat"

            print(f"[DEBUG] _stream_ollama_with_thinking - 准备发送流式请求到: {endpoint}")
            print(f"[DEBUG] _stream_ollama_with_thinking - payload: {json.dumps(payload, ensure_ascii=False)}")

            # 状态变量 - 用于流式解析 thinking
            in_thinking = False
            thinking_started = False
            chunk_count = 0

            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    endpoint,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    print(f"[DEBUG] _stream_ollama_with_thinking - 开始接收流式响应")

                    async for line in response.aiter_lines():
                        if not line or not line.strip():
                            continue

                        chunk_count += 1
                        if chunk_count % 10 == 0:
                            print(f"[DEBUG] _stream_ollama_with_thinking - 已处理 {chunk_count} 个数据块")

                        try:
                            chunk = json.loads(line)
                            print(f"[DEBUG] _stream_ollama_with_thinking - 原始chunk: {chunk}")

                            # 获取content和thinking字段
                            if use_openai_format:
                                # OpenAI兼容格式
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    thinking = delta.get("thinking")
                                else:
                                    content = ""
                                    thinking = None
                            else:
                                # Ollama原生格式
                                if "message" in chunk:
                                    content = chunk["message"].get("content", "")
                                    # 优先使用Ollama原生的thinking字段
                                    thinking = chunk["message"].get("thinking")
                                else:
                                    content = ""
                                    thinking = None

                            print(f"[DEBUG] _stream_ollama_with_thinking - content: {content[:100] if content else 'None'}")
                            print(f"[DEBUG] _stream_ollama_with_thinking - thinking: {thinking[:100] if thinking else 'None'}")
                            print(f"[DEBUG] _stream_ollama_with_thinking - self.thinking配置: {self.thinking}")

                            # 根据thinking配置决定是否处理thinking字段
                            if self.thinking:
                                # 处理thinking字段（Ollama原生支持）
                                if thinking:
                                    if not in_thinking:
                                        in_thinking = True
                                        thinking_started = True
                                        print(f"[DEBUG] _stream_ollama_with_thinking - 发送thinking_start")
                                        yield {"type": "thinking_start", "content": ""}
                                    print(f"[DEBUG] _stream_ollama_with_thinking - 发送thinking_content: {thinking[:100]}")
                                    yield {"type": "thinking_content", "content": thinking}
                                else:
                                    # 如果之前在thinking模式，现在结束了
                                    if in_thinking:
                                        in_thinking = False
                                        print(f"[DEBUG] _stream_ollama_with_thinking - 发送thinking_end")
                                        yield {"type": "thinking_end", "content": ""}

                                # 处理普通content
                                if content:
                                    print(f"[DEBUG] _stream_ollama_with_thinking - 发送content: {content[:100]}")
                                    yield {"type": "content", "content": content}
                            else:
                                # 未启用thinking，只输出content，忽略thinking字段
                                if content:
                                    print(f"[DEBUG] _stream_ollama_with_thinking - 发送content: {content[:100]}")
                                    yield {"type": "content", "content": content}

                            # 检查是否完成
                            if chunk.get("done"):
                                print(f"[DEBUG] _stream_ollama_with_thinking - 收到done信号")
                                break

                        except json.JSONDecodeError as e:
                            print(f"[ERROR] _stream_ollama_with_thinking - JSON解析失败: {e}, line: {line[:200]}")
                            pass

            print(f"[DEBUG] _stream_ollama_with_thinking - 流式响应结束，共处理 {chunk_count} 个数据块")

            # 确保thinking_end已发送
            if in_thinking:
                print(f"[DEBUG] _stream_ollama_with_thinking - 发送thinking_end（确保）")
                yield {"type": "thinking_end", "content": ""}

            print(f"[DEBUG] _stream_ollama_with_thinking - 发送done事件")
            yield {"type": "done", "content": ""}

        except Exception as e:
            print(f"[ERROR] _stream_ollama_with_thinking - 流式API调用失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Ollama流式API调用失败: {str(e)}")

    async def _stream_custom_with_thinking(
        self,
        messages: List[Dict],
        images: Optional[List[str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[Dict[str, str], None]:
        """流式调用自定义API（兼容OpenAI格式），使用Ollama官方推荐的reasoning_content字段"""
        try:
            api_messages = self._prepare_messages_with_images(messages, images)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # 构建payload，包含所有支持的参数
            payload = {
                "model": model,
                "messages": api_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }

            # 添加可选参数（只传递非None和非默认值的参数）
            if self.top_p is not None:
                payload["top_p"] = self.top_p

            if self.presence_penalty is not None:
                payload["presence_penalty"] = self.presence_penalty

            # 注意：自定义API可能支持top_k和repeat_penalty参数
            # 取决于具体的API实现，这里我们传递这些参数
            if self.top_k is not None:
                payload["top_k"] = self.top_k

            if self.repeat_penalty is not None:
                payload["repeat_penalty"] = self.repeat_penalty

            # 状态变量
            in_thinking = False
            thinking_started = False

            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get("delta", {})

                                    # 根据thinking配置决定是否处理thinking字段
                                    reasoning_content = None
                                    if self.thinking:
                                        # 如果启用了thinking，提取thinking内容
                                        reasoning_content = delta.get("reasoning_content") or delta.get("thinking")
                                    content = delta.get("content", "")

                                    # 根据thinking配置决定是否处理reasoning_content
                                    if self.thinking:
                                        # 处理reasoning_content
                                        if reasoning_content:
                                            if not in_thinking:
                                                in_thinking = True
                                                thinking_started = True
                                                yield {"type": "thinking_start", "content": ""}
                                            yield {"type": "thinking_content", "content": reasoning_content}
                                        else:
                                            # 如果之前在thinking模式，现在结束了
                                            if in_thinking:
                                                in_thinking = False
                                                yield {"type": "thinking_end", "content": ""}

                                        # 处理普通content
                                        if content:
                                            yield {"type": "content", "content": content}
                                    else:
                                        # 未启用thinking，只输出content，忽略reasoning_content
                                        if content:
                                            yield {"type": "content", "content": content}
                            except json.JSONDecodeError:
                                pass

            # 确保thinking_end已发送
            if in_thinking:
                yield {"type": "thinking_end", "content": ""}

            yield {"type": "done", "content": ""}
        except Exception as e:
            raise Exception(f"自定义流式API调用失败: {str(e)}")

    async def _stream_aliyun_with_thinking(
        self,
        messages: List[Dict],
        images: Optional[List[str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[Dict[str, str], None]:
        """流式调用阿里云通义千问API（兼容OpenAI格式），使用Ollama官方推荐的reasoning_content字段"""
        try:
            api_messages = self._prepare_messages_with_images(messages, images)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # 构建payload，包含所有支持的参数
            payload = {
                "model": model,
                "messages": api_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }

            # 添加可选参数（只传递非None和非默认值的参数）
            if self.top_p is not None:
                payload["top_p"] = self.top_p

            if self.presence_penalty is not None:
                payload["presence_penalty"] = self.presence_penalty

            # 状态变量
            in_thinking = False
            thinking_started = False

            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get("delta", {})

                                    # 根据thinking配置决定是否处理thinking字段
                                    reasoning_content = None
                                    if self.thinking:
                                        # 如果启用了thinking，提取thinking内容
                                        reasoning_content = delta.get("reasoning_content") or delta.get("thinking")
                                    content = delta.get("content", "")

                                    # 根据thinking配置决定是否处理reasoning_content
                                    if self.thinking:
                                        # 处理reasoning_content
                                        if reasoning_content:
                                            if not in_thinking:
                                                in_thinking = True
                                                thinking_started = True
                                                yield {"type": "thinking_start", "content": ""}
                                            yield {"type": "thinking_content", "content": reasoning_content}
                                        else:
                                            # 如果之前在thinking模式，现在结束了
                                            if in_thinking:
                                                in_thinking = False
                                                yield {"type": "thinking_end", "content": ""}

                                        # 处理普通content
                                        if content:
                                            yield {"type": "content", "content": content}
                                    else:
                                        # 未启用thinking，只输出content，忽略reasoning_content
                                        if content:
                                            yield {"type": "content", "content": content}
                            except json.JSONDecodeError:
                                pass

            # 确保thinking_end已发送
            if in_thinking:
                yield {"type": "thinking_end", "content": ""}

            yield {"type": "done", "content": ""}
        except Exception as e:
            raise Exception(f"阿里云流式API调用失败: {str(e)}")


model_provider = ModelProvider()
