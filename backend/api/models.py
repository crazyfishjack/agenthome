from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import json
import os
import httpx

router = APIRouter()

CONFIG_FILE = "./data/model_configs.json"


class TestResult(BaseModel):
    success: bool
    message: str
    timestamp: str
    latency: Optional[float] = None


class OllamaSearchResult(BaseModel):
    found: bool
    api_base: Optional[str] = None
    models: List[str] = []
    message: str


class ModelConfigCreate(BaseModel):
    name: str
    provider: str
    type: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model: str
    temperature: float = 0.7
    max_tokens: int = 2048
    thinking: Optional[bool] = False
    top_p: Optional[float] = 0.9
    top_k: Optional[int] = 40
    repeat_penalty: Optional[float] = 1.1
    presence_penalty: Optional[float] = 0
    system_prompt: Optional[str] = None


class ModelConfigUpdate(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    thinking: Optional[bool] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    repeat_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    system_prompt: Optional[str] = None


class ModelConfig(BaseModel):
    id: str
    name: str
    provider: str
    type: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model: str
    temperature: float
    max_tokens: int
    thinking: Optional[bool] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    repeat_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    system_prompt: Optional[str] = None
    is_tested: Optional[bool] = None
    test_result: Optional[TestResult] = None
    created_at: str
    updated_at: str


class Provider(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    type: str
    default_api_base: Optional[str] = None
    requires_api_key: bool


PROVIDERS = [
    {
        "id": "openai",
        "name": "OpenAI",
        "description": "OpenAI官方API，支持GPT系列模型",
        "icon": "🤖",
        "type": "api",
        "default_api_base": "https://api.openai.com/v1",
        "requires_api_key": True
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "description": "Anthropic Claude系列模型",
        "icon": "🧠",
        "type": "api",
        "default_api_base": "https://api.anthropic.com",
        "requires_api_key": True
    },
    {
        "id": "ollama",
        "name": "Ollama",
        "description": "本地部署的开源大模型",
        "icon": "🦙",
        "type": "local",
        "default_api_base": "http://localhost:11434",
        "requires_api_key": False
    },
    {
        "id": "aliyun",
        "name": "阿里云",
        "description": "阿里云通义千问系列模型",
        "icon": "☁️",
        "type": "api",
        "default_api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "requires_api_key": True
    },
    {
        "id": "custom",
        "name": "自定义API",
        "description": "自定义兼容OpenAI格式的API",
        "icon": "⚙️",
        "type": "api",
        "requires_api_key": True
    }
]


def load_configs() -> List[Dict]:
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


def save_configs(configs: List[Dict]):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"configs": configs}, f, ensure_ascii=False, indent=2)


@router.get("/providers")
async def get_providers():
    return PROVIDERS


@router.post("/ollama/search")
async def search_ollama():
    """
    自动搜索本地运行的Ollama服务
    尝试常见的Ollama端口和地址
    """
    # 常见的Ollama地址列表
    ollama_addresses = [
        "http://localhost:11434",
        "http://127.0.0.1:11434",
        "http://localhost:11434/v1",
        "http://127.0.0.1:11434/v1",
    ]
    
    for api_base in ollama_addresses:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # 尝试获取模型列表
                response = await client.get(f"{api_base}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = []
                    if "models" in data:
                        models = [model["name"] for model in data["models"]]
                    
                    return OllamaSearchResult(
                        found=True,
                        api_base=api_base,
                        models=models,
                        message=f"成功找到Ollama服务，地址：{api_base}"
                    )
        except Exception:
            continue
    
    return OllamaSearchResult(
        found=False,
        api_base=None,
        models=[],
        message="未找到本地运行的Ollama服务，请确保Ollama已启动"
    )


@router.get("/ollama/models")
async def get_ollama_models():
    """获取Ollama本地模型列表（详细信息）"""
    try:
        configs = load_configs()
        ollama_configs = [c for c in configs if c.get("provider") == "ollama"]
        
        if not ollama_configs:
            return {"models": [], "error": "No Ollama configuration found"}
        
        api_base = ollama_configs[0].get("api_base", "http://localhost:11434")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{api_base}/api/tags")
            response.raise_for_status()
            result = response.json()
            return {"models": result.get("models", [])}
    except Exception as e:
        return {"models": [], "error": str(e)}


@router.get("/providers/{provider}/models")
async def get_provider_models(provider: str):
    provider_models = {
        "openai": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview", "gpt-4o"],
        "anthropic": ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"],
        "ollama": ["llama2", "llama3", "mistral", "codellama", "phi3"],
        "aliyun": ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-max-longcontext"],
        "custom": []
    }
    return provider_models.get(provider, [])


@router.get("/config")
async def get_model_configs():
    return load_configs()


@router.get("/config/{config_id}")
async def get_model_config(config_id: str):
    configs = load_configs()
    for config in configs:
        if config["id"] == config_id:
            return config
    raise HTTPException(status_code=404, detail="Model config not found")


@router.post("/config", response_model=ModelConfig)
async def create_model_config(config: ModelConfigCreate):
    configs = load_configs()
    new_config = {
        "id": f"config_{datetime.now().timestamp()}",
        **config.dict(),
        "is_tested": False,
        "test_result": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    configs.append(new_config)
    save_configs(configs)
    return new_config


@router.put("/config/{config_id}", response_model=ModelConfig)
async def update_model_config(config_id: str, config: ModelConfigUpdate):
    configs = load_configs()
    for i, existing_config in enumerate(configs):
        if existing_config["id"] == config_id:
            update_data = config.dict(exclude_unset=True)
            configs[i].update(update_data)
            configs[i]["updated_at"] = datetime.now().isoformat()
            save_configs(configs)
            
            # 实时更新使用该配置的所有agent实例和model_provider
            try:
                from backend.services.langchain_service import langchain_service
                from backend.core.model_provider import model_provider
                from backend.api.schools import load_schools
                
                # 更新 model_provider 的配置（ChatEngine 路径）
                updated_config = configs[i].copy()
                model_provider.set_config(updated_config)
                print(f"[DEBUG] models.py - 已更新 model_provider 的配置: {config_id}")
                
                schools = load_schools()
                updated_agents = []
                
                # 查找所有使用该config_id的agent
                for school in schools:
                    for agent in school.get("agents", []):
                        if agent.get("agent_id") == config_id:
                            # 更新agent的配置（LangChain 路径）
                            await langchain_service.update_agent_config(config_id, updated_config)
                            updated_agents.append(config_id)
                            break
                
                if updated_agents:
                    print(f"[DEBUG] models.py - 已更新 {len(updated_agents)} 个agent的配置: {updated_agents}")
            except Exception as e:
                print(f"[WARNING] models.py - 更新配置失败: {e}")
            
            return configs[i]
    raise HTTPException(status_code=404, detail="Model config not found")


@router.delete("/config/{config_id}")
async def delete_model_config(config_id: str):
    configs = load_configs()
    for i, config in enumerate(configs):
        if config["id"] == config_id:
            configs.pop(i)
            save_configs(configs)
            return {"message": "Model config deleted successfully"}
    raise HTTPException(status_code=404, detail="Model config not found")


@router.post("/config/{config_id}/test")
async def test_model_connection(config_id: str):
    configs = load_configs()
    target_config = None
    for config in configs:
        if config["id"] == config_id:
            target_config = config
            break
    
    if not target_config:
        raise HTTPException(status_code=404, detail="Model config not found")
    
    import time
    start_time = time.time()
    
    try:
        if target_config["provider"] == "openai":
            result = await test_openai_connection(target_config)
        elif target_config["provider"] == "anthropic":
            result = await test_anthropic_connection(target_config)
        elif target_config["provider"] == "ollama":
            result = await test_ollama_connection(target_config)
        elif target_config["provider"] == "aliyun":
            result = await test_aliyun_connection(target_config)
        else:
            result = await test_custom_connection(target_config)
        
        latency = time.time() - start_time
        
        test_result = TestResult(
            success=result["success"],
            message=result["message"],
            timestamp=datetime.now().isoformat(),
            latency=latency if result["success"] else None
        )
        
        for i, config in enumerate(configs):
            if config["id"] == config_id:
                configs[i]["is_tested"] = True
                configs[i]["test_result"] = test_result.dict()
                configs[i]["updated_at"] = datetime.now().isoformat()
                break
        
        save_configs(configs)
        return test_result
        
    except Exception as e:
        test_result = TestResult(
            success=False,
            message=f"Connection failed: {str(e)}",
            timestamp=datetime.now().isoformat()
        )
        return test_result


async def test_openai_connection(config: Dict) -> Dict:
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config['api_base']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config['api_key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": config['model'],
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 10
                },
                timeout=10.0
            )
            if response.status_code == 200:
                return {"success": True, "message": "Connection successful"}
            else:
                return {"success": False, "message": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


async def test_anthropic_connection(config: Dict) -> Dict:
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config['api_base']}/v1/messages",
                headers={
                    "x-api-key": config['api_key'],
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": config['model'],
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "test"}]
                },
                timeout=10.0
            )
            if response.status_code == 200:
                return {"success": True, "message": "Connection successful"}
            else:
                return {"success": False, "message": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


async def test_ollama_connection(config: Dict) -> Dict:
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config['api_base']}/api/tags",
                timeout=10.0
            )
            if response.status_code == 200:
                return {"success": True, "message": "Connection successful"}
            else:
                return {"success": False, "message": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


async def test_custom_connection(config: Dict) -> Dict:
    return await test_openai_connection(config)


async def test_aliyun_connection(config: Dict) -> Dict:
    """测试阿里云通义千问连接"""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config['api_base']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config['api_key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": config['model'],
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 10
                },
                timeout=10.0
            )
            if response.status_code == 200:
                return {"success": True, "message": "Connection successful"}
            else:
                return {"success": False, "message": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}
