from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, AsyncGenerator
from datetime import datetime
import json
import os
import asyncio
import uuid

from backend.services.langchain_service import langchain_service
from deepagents import CompiledSubAgent

# 任务管理器引用（从chat.py导入）
from backend.api.chat import task_manager

router = APIRouter()

TEAMS_FILE = "./data/teams.json"
SCHOOLS_FILE = "./data/schools.json"


class TeamChatRequest(BaseModel):
    """Team聊天请求"""
    message: str
    images: Optional[List[str]] = None
    history: Optional[List[Dict]] = None
    conversation_id: Optional[str] = None


class SubAgentConfig(BaseModel):
    """Sub Agent配置"""
    agent_id: str
    agent_name: str
    custom_name: str
    description: str
    agent_config: Dict


class TeamCreate(BaseModel):
    """创建Team的请求"""
    name: str
    main_agent_id: str
    main_agent_name: str
    main_agent_config: Dict
    sub_agents: List[SubAgentConfig]
    enable_search: Optional[bool] = False
    enable_thinking: Optional[bool] = False


class TeamUpdate(BaseModel):
    """更新Team的请求"""
    name: str
    main_agent_id: str
    main_agent_name: str
    main_agent_config: Dict
    sub_agents: List[SubAgentConfig]
    enable_search: Optional[bool] = False
    enable_thinking: Optional[bool] = False


class Team(BaseModel):
    """Team数据模型"""
    id: str
    name: str
    main_agent_id: str
    main_agent_name: str
    main_agent_config: Dict
    sub_agents: List[SubAgentConfig]
    enable_search: Optional[bool] = False
    enable_thinking: Optional[bool] = False
    status: str = "not_instantiated"  # creating, success, failed, not_instantiated
    created_at: str
    updated_at: str


def load_teams() -> List[Dict]:
    """加载所有Team"""
    if not os.path.exists(TEAMS_FILE):
        return []
    with open(TEAMS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("teams", [])


def save_teams(teams: List[Dict]):
    """保存所有Team"""
    os.makedirs(os.path.dirname(TEAMS_FILE), exist_ok=True)
    with open(TEAMS_FILE, "w", encoding="utf-8") as f:
        json.dump({"teams": teams}, f, ensure_ascii=False, indent=2)


def load_schools() -> List[Dict]:
    """加载所有School"""
    if not os.path.exists(SCHOOLS_FILE):
        return []
    with open(SCHOOLS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("schools", [])


def get_school_by_agent_id(agent_id: str) -> Optional[Dict]:
    """根据Agent ID获取其所属的School
    
    Args:
        agent_id: Agent ID
        
    Returns:
        School字典，如果未找到返回None
    """
    schools = load_schools()
    for school in schools:
        for agent in school.get("agents", []):
            if agent.get("agent_id") == agent_id:
                return school
    return None


def get_team_by_id(team_id: str) -> Optional[Dict]:
    """根据ID获取Team"""
    teams = load_teams()
    for team in teams:
        if team["id"] == team_id:
            return team
    return None


@router.get("/teams")
async def get_all_teams():
    """获取所有Team"""
    teams = load_teams()
    return {"teams": teams}


@router.get("/teams/{team_id}")
async def get_team(team_id: str):
    """获取指定Team"""
    team = get_team_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.post("/teams", response_model=Team)
async def create_team(request: TeamCreate):
    """创建新的Team
    
    流程：
    1. 获取主Agent的school信息
    2. 为每个Sub Agent获取各自的school信息
    3. 根据各自的school配置加载工具/技能/MCP
    """
    teams = load_teams()

    # 检查Sub Agent数量限制
    if len(request.sub_agents) > 10:
        raise HTTPException(status_code=400, detail="Sub Agent数量不能超过10个")

    # 获取主Agent的school信息
    main_agent_school = get_school_by_agent_id(request.main_agent_id)
    if not main_agent_school:
        raise HTTPException(
            status_code=400,
            detail=f"主Agent {request.main_agent_id} 未加入任何school，无法创建Team"
        )
    main_agent_school_id = main_agent_school["id"]
    print(f"[DEBUG] teams.py - 主Agent {request.main_agent_id} 所属school: {main_agent_school_id}")

    # 检查Sub Agent是否已加入school
    for sa in request.sub_agents:
        sub_agent_school = get_school_by_agent_id(sa.agent_id)
        if not sub_agent_school:
            raise HTTPException(
                status_code=400,
                detail=f"Sub Agent {sa.agent_id} 未加入任何school，无法添加到Team"
            )
        print(f"[DEBUG] teams.py - Sub Agent {sa.agent_id} 所属school: {sub_agent_school['id']}")

    team_id = f"team_{datetime.now().timestamp()}"

    new_team = {
        "id": team_id,
        "name": request.name,
        "main_agent_id": request.main_agent_id,
        "main_agent_name": request.main_agent_name,
        "main_agent_config": request.main_agent_config,
        "sub_agents": [sa.dict() for sa in request.sub_agents],
        "enable_search": request.enable_search,
        "enable_thinking": request.enable_thinking,
        "status": "creating",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    teams.append(new_team)
    save_teams(teams)

    # 异步创建Team的DeepAgent实例
    try:
        # 1. 首先创建所有SUB agent的CompiledSubAgent实例
        compiled_subagents = []
        for sa in request.sub_agents:
            try:
                # 获取Sub Agent的school信息
                sub_agent_school = get_school_by_agent_id(sa.agent_id)
                sub_agent_school_id = sub_agent_school["id"] if sub_agent_school else None
                
                if not sub_agent_school_id:
                    print(f"[WARNING] teams.py - Sub Agent {sa.agent_id} 没有school信息，跳过")
                    continue

                # 读取SUB agent配置
                sub_agent_config = sa.agent_config.copy()

                # 如果是阿里云模型，添加enable_search和enable_thinking配置
                # 使用Team级别的配置，确保Sub Agent和主Agent保持一致
                if sub_agent_config.get("provider") == "aliyun":
                    if request.enable_search:
                        sub_agent_config["enable_search"] = True
                    if request.enable_thinking:
                        sub_agent_config["enable_thinking"] = True

                # 创建SUB agent的LLM实例
                sub_llm = langchain_service._create_llm(sub_agent_config)
                print(f"[DEBUG] teams.py - SUB agent {sa.agent_id} LLM创建成功")

                # 创建SUB agent的工具（使用各自的school_id）
                sub_tools = await langchain_service._create_tools(sub_agent_school_id)
                print(f"[DEBUG] teams.py - SUB agent {sa.agent_id} 工具创建成功: {len(sub_tools)}个工具")

                # 创建SUB agent的CompositeBackend
                from backend.services.langchain_service import get_skills_dir, get_output_dir
                from backend.services.composite_backend import CompositeBackend
                sub_composite_backend = CompositeBackend(
                    skills_dir=str(get_skills_dir()),
                    output_dir=str(get_output_dir()),
                    virtual_mode=True
                )
                print(f"[DEBUG] teams.py - SUB agent {sa.agent_id} CompositeBackend创建成功")

                # 创建SUB agent的deepagent（带内存checkpoint，支持Human-in-the-loop）
                from deepagents import create_deep_agent
                from langchain.agents.middleware import SummarizationMiddleware, HumanInTheLoopMiddleware
                from langgraph.checkpoint.memory import MemorySaver

                # 获取Sub Agent所在school的skills配置
                sub_school_skills_config = sub_agent_school.get("skills", []) if sub_agent_school else []
                sub_enabled_skill_ids = []
                for skill_config in sub_school_skills_config:
                    if skill_config.get("enabled", True):
                        sub_enabled_skill_ids.append(skill_config.get("skill_id"))

                # 设置披露级别为metadata
                langchain_service.skills_middleware.set_disclosure_level("metadata")
                sub_skills_prompt = langchain_service.skills_middleware.format_skills_for_prompt(sub_enabled_skill_ids)

                # 构建system_prompt
                sub_system_prompt = sub_agent_config.get("system_prompt", "")
                if sub_skills_prompt:
                    if sub_system_prompt:
                        sub_system_prompt = f"{sub_system_prompt}\n\n{sub_skills_prompt}"
                    else:
                        sub_system_prompt = sub_skills_prompt

                # 创建内存checkpoint（支持Human-in-the-loop）
                sub_checkpointer = MemorySaver()

                sub_deepagent = create_deep_agent(
                    model=sub_llm,
                    tools=sub_tools,
                    system_prompt=sub_system_prompt,
                    backend=sub_composite_backend,
                    checkpointer=sub_checkpointer,  # 添加checkpoint支持中断恢复
                    middleware=[
                        SummarizationMiddleware(
                            model=sub_llm,
                            max_tokens_before_summary=6000,
                            messages_to_keep=20
                        ),
                        HumanInTheLoopMiddleware(
                            interrupt_on={
                                "SandboxExecute": {
                                    "allowed_decisions": ["approve", "reject"]
                                }
                            }
                        )
                    ]
                )
                print(f"[DEBUG] teams.py - SUB agent {sa.agent_id} DeepAgent创建成功（带checkpoint）")

                # 使用CompiledSubAgent包装，使用custom_name作为名称
                compiled_sub = CompiledSubAgent(
                    name=sa.custom_name,
                    description=sa.description,
                    runnable=sub_deepagent
                )
                compiled_subagents.append(compiled_sub)
                print(f"[DEBUG] teams.py - SUB agent {sa.agent_id} (custom_name: {sa.custom_name}) CompiledSubAgent创建成功")

            except Exception as sub_e:
                print(f"[ERROR] teams.py - 创建SUB agent {sa.agent_id} 失败: {str(sub_e)}")
                import traceback
                traceback.print_exc()
                # 继续创建其他SUB agent，不中断主流程

        # 2. 为主Agent创建DeepAgent实例（带checkpoint和subagents参数）
        main_agent_config = request.main_agent_config.copy()

        # 如果是阿里云模型，添加enable_search和enable_thinking配置
        if main_agent_config.get("provider") == "aliyun":
            if request.enable_search:
                main_agent_config["enable_search"] = True
            if request.enable_thinking:
                main_agent_config["enable_thinking"] = True

        # 创建主Agent的DeepAgent实例，传入subagents参数和主agent的school_id
        agent_result = await langchain_service.create_agent_with_subagents(
            agent_id=team_id,
            agent_config=main_agent_config,
            school_id=main_agent_school_id,  # 使用主Agent的school_id
            subagents=compiled_subagents
        )

        if agent_result["success"]:
            # 更新Team状态为success
            new_team["status"] = "success"
            teams = load_teams()
            for i, t in enumerate(teams):
                if t["id"] == team_id:
                    teams[i] = new_team
                    break
            save_teams(teams)
        else:
            # 更新Team状态为failed
            new_team["status"] = "failed"
            teams = load_teams()
            for i, t in enumerate(teams):
                if t["id"] == team_id:
                    teams[i] = new_team
                    break
            save_teams(teams)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create Team DeepAgent: {agent_result.get('error')}"
            )

    except Exception as e:
        # 更新Team状态为failed
        new_team["status"] = "failed"
        teams = load_teams()
        for i, t in enumerate(teams):
            if t["id"] == team_id:
                teams[i] = new_team
                break
        save_teams(teams)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Team: {str(e)}"
        )

    return new_team


@router.put("/teams/{team_id}", response_model=Team)
async def update_team(team_id: str, request: TeamUpdate):
    """更新Team（热更新，保留对话历史）
    
    流程：
    1. 获取主Agent和所有Sub Agent的最新school信息
    2. 根据最新的school配置更新工具/技能/MCP
    3. 保留原有的checkpoint（对话历史）
    """
    teams = load_teams()
    team_found = False

    for i, team in enumerate(teams):
        if team["id"] == team_id:
            team_found = True

            # 检查Sub Agent数量限制
            if len(request.sub_agents) > 10:
                raise HTTPException(status_code=400, detail="Sub Agent数量不能超过10个")

            # 获取主Agent的school信息
            main_agent_school = get_school_by_agent_id(request.main_agent_id)
            if not main_agent_school:
                raise HTTPException(
                    status_code=400,
                    detail=f"主Agent {request.main_agent_id} 未加入任何school，无法更新Team"
                )
            main_agent_school_id = main_agent_school["id"]
            print(f"[DEBUG] teams.py - 更新Team: 主Agent {request.main_agent_id} 所属school: {main_agent_school_id}")

            # 热更新：保留checkpointer，只更新工具和配置
            # 使用热更新方法而不是删除重建
            try:
                # 1. 首先处理所有SUB agent
                compiled_subagents = []
                for sa in request.sub_agents:
                    try:
                        # 获取Sub Agent的school信息
                        sub_agent_school = get_school_by_agent_id(sa.agent_id)
                        sub_agent_school_id = sub_agent_school["id"] if sub_agent_school else None
                        
                        if not sub_agent_school_id:
                            print(f"[WARNING] teams.py - Sub Agent {sa.agent_id} 没有school信息，跳过")
                            continue

                        # 读取SUB agent配置
                        sub_agent_config = sa.agent_config.copy()

                        # 如果是阿里云模型，添加enable_search和enable_thinking配置
                        # 使用Team级别的配置，确保Sub Agent和主Agent保持一致
                        if sub_agent_config.get("provider") == "aliyun":
                            if request.enable_search:
                                sub_agent_config["enable_search"] = True
                            if request.enable_thinking:
                                sub_agent_config["enable_thinking"] = True

                        # 创建SUB agent的LLM实例
                        sub_llm = langchain_service._create_llm(sub_agent_config)
                        print(f"[DEBUG] teams.py - SUB agent {sa.agent_id} LLM创建成功")

                        # 创建SUB agent的工具（使用各自的school_id）
                        sub_tools = await langchain_service._create_tools(sub_agent_school_id)
                        print(f"[DEBUG] teams.py - SUB agent {sa.agent_id} 工具创建成功: {len(sub_tools)}个工具")

                        # 创建SUB agent的CompositeBackend
                        from backend.services.langchain_service import get_skills_dir, get_output_dir
                        from backend.services.composite_backend import CompositeBackend
                        sub_composite_backend = CompositeBackend(
                            skills_dir=str(get_skills_dir()),
                            output_dir=str(get_output_dir()),
                            virtual_mode=True
                        )
                        print(f"[DEBUG] teams.py - SUB agent {sa.agent_id} CompositeBackend创建成功")

                        # 创建SUB agent的deepagent（不带checkpoint）
                        from deepagents import create_deep_agent
                        from langchain.agents.middleware import SummarizationMiddleware, HumanInTheLoopMiddleware

                        # 获取Sub Agent所在school的skills配置
                        sub_school_skills_config = sub_agent_school.get("skills", []) if sub_agent_school else []
                        sub_enabled_skill_ids = []
                        for skill_config in sub_school_skills_config:
                            if skill_config.get("enabled", True):
                                sub_enabled_skill_ids.append(skill_config.get("skill_id"))

                        # 设置披露级别为metadata
                        langchain_service.skills_middleware.set_disclosure_level("metadata")
                        sub_skills_prompt = langchain_service.skills_middleware.format_skills_for_prompt(sub_enabled_skill_ids)

                        # 构建system_prompt
                        sub_system_prompt = sub_agent_config.get("system_prompt", "")
                        if sub_skills_prompt:
                            if sub_system_prompt:
                                sub_system_prompt = f"{sub_system_prompt}\n\n{sub_skills_prompt}"
                            else:
                                sub_system_prompt = sub_skills_prompt

                        # 创建内存checkpoint（支持Human-in-the-loop）
                        sub_checkpointer = MemorySaver()

                        sub_deepagent = create_deep_agent(
                            model=sub_llm,
                            tools=sub_tools,
                            system_prompt=sub_system_prompt,
                            backend=sub_composite_backend,
                            checkpointer=sub_checkpointer,  # 添加checkpoint支持中断恢复
                            middleware=[
                                SummarizationMiddleware(
                                    model=sub_llm,
                                    max_tokens_before_summary=6000,
                                    messages_to_keep=20
                                ),
                                HumanInTheLoopMiddleware(
                                    interrupt_on={
                                        "SandboxExecute": {
                                            "allowed_decisions": ["approve", "reject"]
                                        }
                                    }
                                )
                            ]
                        )
                        print(f"[DEBUG] teams.py - SUB agent {sa.agent_id} DeepAgent创建成功（带checkpoint）")

                        # 使用CompiledSubAgent包装，使用custom_name作为名称
                        compiled_sub = CompiledSubAgent(
                            name=sa.custom_name,
                            description=sa.description,
                            runnable=sub_deepagent
                        )
                        compiled_subagents.append(compiled_sub)
                        print(f"[DEBUG] teams.py - SUB agent {sa.agent_id} (custom_name: {sa.custom_name}) CompiledSubAgent创建成功")

                    except Exception as sub_e:
                        print(f"[ERROR] teams.py - 创建SUB agent {sa.agent_id} 失败: {str(sub_e)}")
                        import traceback
                        traceback.print_exc()

                # 2. 为主Agent热更新DeepAgent实例（保留checkpointer）
                main_agent_config = request.main_agent_config.copy()

                # 如果是阿里云模型，添加enable_search和enable_thinking配置
                if main_agent_config.get("provider") == "aliyun":
                    if request.enable_search:
                        main_agent_config["enable_search"] = True
                    if request.enable_thinking:
                        main_agent_config["enable_thinking"] = True

                # 使用热更新方法，保留对话历史
                agent_result = await langchain_service.hot_update_agent_with_subagents(
                    agent_id=team_id,
                    agent_config=main_agent_config,
                    school_id=main_agent_school_id,
                    subagents=compiled_subagents
                )

                if agent_result["success"]:
                    # 更新Team数据
                    teams[i].update({
                        "name": request.name,
                        "main_agent_id": request.main_agent_id,
                        "main_agent_name": request.main_agent_name,
                        "main_agent_config": request.main_agent_config,
                        "sub_agents": [sa.dict() for sa in request.sub_agents],
                        "enable_search": request.enable_search,
                        "enable_thinking": request.enable_thinking,
                        "status": "success",
                        "updated_at": datetime.now().isoformat()
                    })
                    save_teams(teams)
                else:
                    teams[i]["status"] = "failed"
                    save_teams(teams)
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to update Team DeepAgent: {agent_result.get('error')}"
                    )

            except Exception as e:
                teams[i]["status"] = "failed"
                save_teams(teams)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to update Team: {str(e)}"
                )

            return teams[i]

    if not team_found:
        raise HTTPException(status_code=404, detail="Team not found")


@router.delete("/teams/{team_id}")
async def delete_team(team_id: str):
    """删除Team"""
    teams = load_teams()
    for i, team in enumerate(teams):
        if team["id"] == team_id:
            # 删除对应的DeepAgent实例
            langchain_service.delete_agent(team_id)

            # 删除Team
            teams.pop(i)
            save_teams(teams)
            return {"message": "Team deleted successfully"}

    raise HTTPException(status_code=404, detail="Team not found")


@router.get("/teams/{team_id}/instantiation-status")
async def get_team_instantiation_status(team_id: str):
    """获取Team的实例化状态"""
    team = get_team_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    is_instantiated = team_id in langchain_service.agent_deepagents

    return {
        "team_id": team_id,
        "is_instantiated": is_instantiated,
        "status": team.get("status", "not_instantiated")
    }


@router.post("/teams/{team_id}/instantiate")
async def instantiate_team(team_id: str):
    """实例化Team（如果未实例化）
    
    流程：
    1. 获取主Agent的school信息
    2. 为每个Sub Agent获取各自的school信息
    3. 根据各自的school配置加载工具/技能/MCP
    """
    team = get_team_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # 如果已经实例化，直接返回
    if team_id in langchain_service.agent_deepagents:
        return {
            "team_id": team_id,
            "is_instantiated": True,
            "status": "instantiated",
            "message": "Team already instantiated"
        }

    # 获取主Agent的school信息
    main_agent_id = team["main_agent_id"]
    main_agent_school = get_school_by_agent_id(main_agent_id)
    if not main_agent_school:
        raise HTTPException(
            status_code=400,
            detail=f"主Agent {main_agent_id} 未加入任何school，无法实例化Team"
        )
    main_agent_school_id = main_agent_school["id"]
    print(f"[DEBUG] teams.py - 实例化Team: 主Agent {main_agent_id} 所属school: {main_agent_school_id}")

    try:
        # 1. 首先创建所有SUB agent的CompiledSubAgent实例
        compiled_subagents = []
        for sa in team.get("sub_agents", []):
            try:
                # 获取Sub Agent的school信息
                sub_agent_school = get_school_by_agent_id(sa["agent_id"])
                sub_agent_school_id = sub_agent_school["id"] if sub_agent_school else None
                
                if not sub_agent_school_id:
                    print(f"[WARNING] teams.py - Sub Agent {sa['agent_id']} 没有school信息，跳过")
                    continue

                # 读取SUB agent配置
                sub_agent_config = sa.get("agent_config", {}).copy()

                # 如果是阿里云模型，添加enable_search和enable_thinking配置
                # 使用Team级别的配置，确保Sub Agent和主Agent保持一致
                if sub_agent_config.get("provider") == "aliyun":
                    if team.get("enable_search"):
                        sub_agent_config["enable_search"] = True
                    if team.get("enable_thinking"):
                        sub_agent_config["enable_thinking"] = True

                # 创建SUB agent的LLM实例
                sub_llm = langchain_service._create_llm(sub_agent_config)
                print(f"[DEBUG] teams.py - SUB agent {sa['agent_id']} LLM创建成功")

                # 创建SUB agent的工具（使用各自的school_id）
                sub_tools = await langchain_service._create_tools(sub_agent_school_id)
                print(f"[DEBUG] teams.py - SUB agent {sa['agent_id']} 工具创建成功: {len(sub_tools)}个工具")

                # 创建SUB agent的CompositeBackend
                from backend.services.langchain_service import get_skills_dir, get_output_dir
                from backend.services.composite_backend import CompositeBackend
                sub_composite_backend = CompositeBackend(
                    skills_dir=str(get_skills_dir()),
                    output_dir=str(get_output_dir()),
                    virtual_mode=True
                )
                print(f"[DEBUG] teams.py - SUB agent {sa['agent_id']} CompositeBackend创建成功")

                # 创建SUB agent的deepagent（带内存checkpoint，支持Human-in-the-loop）
                from deepagents import create_deep_agent
                from langchain.agents.middleware import SummarizationMiddleware, HumanInTheLoopMiddleware
                from langgraph.checkpoint.memory import MemorySaver

                # 获取Sub Agent所在school的skills配置
                sub_school_skills_config = sub_agent_school.get("skills", []) if sub_agent_school else []
                sub_enabled_skill_ids = []
                for skill_config in sub_school_skills_config:
                    if skill_config.get("enabled", True):
                        sub_enabled_skill_ids.append(skill_config.get("skill_id"))

                # 设置披露级别为metadata
                langchain_service.skills_middleware.set_disclosure_level("metadata")
                sub_skills_prompt = langchain_service.skills_middleware.format_skills_for_prompt(sub_enabled_skill_ids)

                # 构建system_prompt
                sub_system_prompt = sub_agent_config.get("system_prompt", "")
                if sub_skills_prompt:
                    if sub_system_prompt:
                        sub_system_prompt = f"{sub_system_prompt}\n\n{sub_skills_prompt}"
                    else:
                        sub_system_prompt = sub_skills_prompt

                # 创建内存checkpoint（支持Human-in-the-loop）
                sub_checkpointer = MemorySaver()

                sub_deepagent = create_deep_agent(
                    model=sub_llm,
                    tools=sub_tools,
                    system_prompt=sub_system_prompt,
                    backend=sub_composite_backend,
                    checkpointer=sub_checkpointer,  # 添加checkpoint支持中断恢复
                    middleware=[
                        SummarizationMiddleware(
                            model=sub_llm,
                            max_tokens_before_summary=6000,
                            messages_to_keep=20
                        ),
                        HumanInTheLoopMiddleware(
                            interrupt_on={
                                "SandboxExecute": {
                                    "allowed_decisions": ["approve", "reject"]
                                }
                            }
                        )
                    ]
                )
                print(f"[DEBUG] teams.py - SUB agent {sa['agent_id']} DeepAgent创建成功（带checkpoint）")

                # 使用CompiledSubAgent包装，使用custom_name作为名称
                custom_name = sa.get("custom_name", sa["agent_id"])
                compiled_sub = CompiledSubAgent(
                    name=custom_name,
                    description=sa.get("description", ""),
                    runnable=sub_deepagent
                )
                compiled_subagents.append(compiled_sub)
                print(f"[DEBUG] teams.py - SUB agent {sa['agent_id']} (custom_name: {custom_name}) CompiledSubAgent创建成功")

            except Exception as sub_e:
                print(f"[ERROR] teams.py - 创建SUB agent {sa['agent_id']} 失败: {str(sub_e)}")
                import traceback
                traceback.print_exc()

        # 2. 为主Agent创建DeepAgent实例
        main_agent_config = team["main_agent_config"].copy()

        # 如果是阿里云模型，添加enable_search和enable_thinking配置
        if main_agent_config.get("provider") == "aliyun":
            if team.get("enable_search"):
                main_agent_config["enable_search"] = True
            if team.get("enable_thinking"):
                main_agent_config["enable_thinking"] = True

        # 创建主Agent的DeepAgent实例，传入subagents参数和主agent的school_id
        agent_result = await langchain_service.create_agent_with_subagents(
            agent_id=team_id,
            agent_config=main_agent_config,
            school_id=main_agent_school_id,
            subagents=compiled_subagents
        )

        if agent_result["success"]:
            # 更新Team状态
            team["status"] = "success"
            teams = load_teams()
            for i, t in enumerate(teams):
                if t["id"] == team_id:
                    teams[i] = team
                    break
            save_teams(teams)

            return {
                "team_id": team_id,
                "is_instantiated": True,
                "status": "instantiated",
                "message": "Team instantiated successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to instantiate team: {agent_result.get('error')}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to instantiate team: {str(e)}"
        )


async def team_stream_generator(
    team_id: str,
    message: str,
    images: Optional[List[str]] = None,
    history: Optional[List[dict]] = None,
    conversation_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Team流式生成响应的生成器"""
    try:
        print(f"[DEBUG] teams.py - team_stream_generator 开始: team_id={team_id}")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 将任务ID添加到任务管理器
        task_manager[task_id] = False
        
        # 发送任务ID事件
        task_event = f"data: {json.dumps({'type': 'task_id', 'task_id': task_id})}\n\n"
        yield task_event
        
        # 使用 langchain_service 执行 Team（Team也是作为agent存储的）
        async for chunk in langchain_service.execute_agent(
            agent_id=team_id,
            message=message,
            history=history,
            images=images,
            task_id=task_id,
            conversation_id=conversation_id
        ):
            # 将每个chunk作为SSE事件发送
            chunk_event = f"data: {json.dumps(chunk)}\n\n"
            yield chunk_event
            
    except asyncio.CancelledError:
        # 任务被取消
        print(f"[DEBUG] teams.py - Team任务被取消")
        cancel_event = f"data: {json.dumps({'type': 'cancelled', 'message': 'Task was cancelled'})}\n\n"
        yield cancel_event
        raise
    except Exception as e:
        # 发送错误事件
        print(f"[ERROR] teams.py - team_stream_generator 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        error_event = f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        yield error_event


@router.post("/teams/{team_id}/chat")
async def chat_with_team(team_id: str, request: TeamChatRequest):
    """与Team进行流式聊天
    
    Args:
        team_id: Team ID
        request: 聊天请求
        
    Returns:
        流式响应
    """
    print(f"[DEBUG] teams.py - 收到Team聊天请求: team_id={team_id}, message={request.message}")
    
    # 检查Team是否存在
    team = get_team_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # 检查Team是否已实例化
    if team_id not in langchain_service.agent_deepagents:
        raise HTTPException(
            status_code=400, 
            detail="Team not instantiated. Please instantiate the team first."
        )
    
    # 准备历史消息
    history = None
    if request.history:
        history = [
            {
                "role": msg.get("role"),
                "content": msg.get("content"),
                "images": msg.get("images")
            }
            for msg in request.history
        ]
    
    # 返回流式响应
    return StreamingResponse(
        team_stream_generator(
            team_id=team_id,
            message=request.message,
            images=request.images,
            history=history,
            conversation_id=request.conversation_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/agents/with-school")
async def get_agents_with_school():
    """获取所有已加入school的agent列表
    
    仅返回已加入school的agent，用于agent team页面的agent列表显示
    """
    schools = load_schools()
    agents_with_school = []
    
    for school in schools:
        school_id = school["id"]
        school_name = school["name"]
        for agent in school.get("agents", []):
            agents_with_school.append({
                "agent_id": agent.get("agent_id"),
                "agent_name": agent.get("agent_name"),
                "school_id": school_id,
                "school_name": school_name,
                "added_at": agent.get("added_at"),
                "agent_config": agent.get("agent_config", {})
            })
    
    return {"agents": agents_with_school}


@router.get("/agent/{agent_id}/school-info")
async def get_agent_school_info(agent_id: str):
    """获取Agent的school信息（包括工具、技能、MCP配置）
    
    Args:
        agent_id: Agent ID
        
    Returns:
        Agent的school信息，包括tools、skills、mcps配置
    """
    school = get_school_by_agent_id(agent_id)
    if not school:
        raise HTTPException(
            status_code=404,
            detail=f"Agent {agent_id} not found in any school"
        )
    
    return {
        "agent_id": agent_id,
        "school_id": school["id"],
        "school_name": school["name"],
        "tools": school.get("tools", []),
        "skills": school.get("skills", []),
        "mcps": school.get("mcps", [])
    }
