from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import json
import os

from backend.services.langchain_service import langchain_service
from backend.models.tool_config import ToolConfig
from backend.skills import SkillScanner

router = APIRouter()

SCHOOLS_FILE = "./data/schools.json"

# 创建全局的 SkillScanner 实例
skill_scanner = SkillScanner("./skills/installed")


class SchoolAgent(BaseModel):
    """School中的Agent信息"""
    agent_id: str
    agent_name: str
    added_at: str


class SchoolCreate(BaseModel):
    """创建School的请求"""
    name: str


class SchoolUpdate(BaseModel):
    """更新School的请求"""
    name: Optional[str] = None


class School(BaseModel):
    """School数据模型"""
    id: str
    name: str
    agents: List[SchoolAgent]
    tools: List[ToolConfig] = []
    skills: List[Dict] = []  # Skills 配置列表
    created_at: str
    updated_at: str


class AddAgentToSchoolRequest(BaseModel):
    """添加Agent到School的请求"""
    agent_id: str
    agent_name: str
    agent_config: Dict  # Agent的完整配置信息


def load_schools() -> List[Dict]:
    """加载所有School"""
    if not os.path.exists(SCHOOLS_FILE):
        return []
    with open(SCHOOLS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("schools", [])


def save_schools(schools: List[Dict]):
    """保存所有School"""
    os.makedirs(os.path.dirname(SCHOOLS_FILE), exist_ok=True)
    with open(SCHOOLS_FILE, "w", encoding="utf-8") as f:
        json.dump({"schools": schools}, f, ensure_ascii=False, indent=2)


def get_school_by_id(school_id: str) -> Optional[Dict]:
    """根据ID获取School"""
    schools = load_schools()
    for school in schools:
        if school["id"] == school_id:
            return school
    return None


@router.get("/schools")
async def get_all_schools():
    """获取所有School"""
    schools = load_schools()
    return {"schools": schools}


@router.get("/schools/{school_id}")
async def get_school(school_id: str):
    """获取指定School"""
    school = get_school_by_id(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school


@router.post("/schools", response_model=School)
async def create_school(request: SchoolCreate):
    """创建新的School"""
    schools = load_schools()

    new_school = {
        "id": f"school_{datetime.now().timestamp()}",
        "name": request.name,
        "agents": [],
        "tools": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    schools.append(new_school)
    save_schools(schools)
    return new_school


@router.put("/schools/{school_id}", response_model=School)
async def update_school(school_id: str, request: SchoolUpdate):
    """更新School"""
    schools = load_schools()
    for i, school in enumerate(schools):
        if school["id"] == school_id:
            update_data = request.dict(exclude_unset=True)
            schools[i].update(update_data)
            schools[i]["updated_at"] = datetime.now().isoformat()
            save_schools(schools)
            return schools[i]
    raise HTTPException(status_code=404, detail="School not found")


@router.delete("/schools/{school_id}")
async def delete_school(school_id: str):
    """删除School"""
    schools = load_schools()
    for i, school in enumerate(schools):
        if school["id"] == school_id:
            # 删除该school的所有agent
            for agent in school["agents"]:
                langchain_service.delete_agent(agent["agent_id"])
            
            # 清理该school的deepagent实例
            if school_id in langchain_service.school_deepagents:
                del langchain_service.school_deepagents[school_id]
                print(f"[DEBUG] schools.py - 清理school {school_id} 的deepagent实例")
            
            # 删除school
            schools.pop(i)
            save_schools(schools)
            return {"message": "School deleted successfully"}
    raise HTTPException(status_code=404, detail="School not found")


@router.post("/schools/{school_id}/agents")
async def add_agent_to_school(school_id: str, request: AddAgentToSchoolRequest):
    """添加Agent到School"""
    schools = load_schools()
    school_found = False
    old_school_id = None

    # 检查agent是否已经在其他school中
    for school in schools:
        for agent in school["agents"]:
            if agent["agent_id"] == request.agent_id:
                if school["id"] == school_id:
                    # agent已经在目标school中
                    raise HTTPException(
                        status_code=400,
                        detail=f"Agent {request.agent_id} already in school {school_id}"
                    )
                else:
                    # agent在另一个school中，需要先移除
                    old_school_id = school["id"]
                    print(f"[DEBUG] schools.py - Agent {request.agent_id} 从school {old_school_id} 移动到school {school_id}")
                    # 从旧school移除agent
                    school["agents"].remove(agent)
                    school["updated_at"] = datetime.now().isoformat()
                    break

    for school in schools:
        if school["id"] == school_id:
            school_found = True

            # 添加agent到新school
            school["agents"].append({
                "agent_id": request.agent_id,
                "agent_name": request.agent_name,
                "added_at": datetime.now().isoformat(),
                "agent_config": request.agent_config  # 保存agent的完整配置
            })
            school["updated_at"] = datetime.now().isoformat()
            save_schools(schools)

            # 创建或更新LangChain智能体
            try:
                # 如果agent从另一个school移动过来，使用move_agent_to_school
                if old_school_id:
                    await langchain_service.move_agent_to_school(
                        agent_id=request.agent_id,
                        new_school_id=school_id,
                        agent_config=request.agent_config
                    )
                else:
                    # 新创建的agent
                    agent_result = await langchain_service.create_agent(
                        agent_id=request.agent_id,
                        agent_config=request.agent_config,
                        school_id=school_id
                    )

                    if not agent_result["success"]:
                        # 如果创建智能体失败，回滚操作
                        for i, agent in enumerate(school["agents"]):
                            if agent["agent_id"] == request.agent_id:
                                school["agents"].pop(i)
                                break
                        save_schools(schools)

                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to create LangChain agent: {agent_result.get('error')}"
                        )

            except Exception as e:
                # 如果创建/移动智能体失败，回滚操作
                for i, agent in enumerate(school["agents"]):
                    if agent["agent_id"] == request.agent_id:
                        school["agents"].pop(i)
                        break
                save_schools(schools)

                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create/move LangChain agent: {str(e)}"
                )

            return {"message": "Agent added to school successfully"}

    if not school_found:
        raise HTTPException(status_code=404, detail="School not found")


@router.delete("/schools/{school_id}/agents/{agent_id}")
async def remove_agent_from_school(school_id: str, agent_id: str):
    """从School移除Agent"""
    schools = load_schools()
    school_found = False

    for school in schools:
        if school["id"] == school_id:
            school_found = True
            # 查找并移除agent
            for i, agent in enumerate(school["agents"]):
                if agent["agent_id"] == agent_id:
                    school["agents"].pop(i)
                    school["updated_at"] = datetime.now().isoformat()
                    save_schools(schools)

                    # 删除对应的LangChain智能体
                    langchain_service.delete_agent(agent_id)

                    return {"message": "Agent removed from school successfully"}

            raise HTTPException(
                status_code=404,
                detail=f"Agent {agent_id} not found in school"
            )

    if not school_found:
        raise HTTPException(status_code=404, detail="School not found")


@router.get("/schools/{school_id}/agents")
async def get_school_agents(school_id: str):
    """获取School中的所有Agent"""
    school = get_school_by_id(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return {"agents": school["agents"]}


@router.get("/agent/{agent_id}/school")
async def get_agent_school(agent_id: str):
    """获取Agent所在的School"""
    schools = load_schools()
    for school in schools:
        for agent in school["agents"]:
            if agent["agent_id"] == agent_id:
                return {
                    "school_id": school["id"],
                    "school_name": school["name"],
                    "agent": agent
                }
    return {"school_id": None, "school_name": None, "agent": None}


@router.get("/agent/{agent_id}/instantiation-status")
async def get_agent_instantiation_status(agent_id: str):
    """获取Agent的实例化状态"""
    is_instantiated = agent_id in langchain_service.agent_deepagents
    
    if is_instantiated:
        return {
            "agent_id": agent_id,
            "is_instantiated": True,
            "status": "instantiated"
        }
    else:
        return {
            "agent_id": agent_id,
            "is_instantiated": False,
            "status": "not_instantiated"
        }


@router.post("/agent/{agent_id}/instantiate")
async def instantiate_agent(agent_id: str):
    """实例化Agent（如果未实例化）"""
    schools = load_schools()
    agent_config = None
    school_id = None
    
    for school in schools:
        for agent in school["agents"]:
            if agent["agent_id"] == agent_id:
                agent_config = agent.get("agent_config")
                school_id = school["id"]
                break
        if agent_config:
            break
    
    if not agent_config or not school_id:
        raise HTTPException(
            status_code=404,
            detail=f"Agent {agent_id} not found in any school"
        )
    
    try:
        result = await langchain_service.create_agent(
            agent_id=agent_id,
            agent_config=agent_config,
            school_id=school_id
        )
        
        if result["success"]:
            return {
                "agent_id": agent_id,
                "is_instantiated": True,
                "status": "instantiated",
                "message": "Agent instantiated successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to instantiate agent: {result.get('error')}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to instantiate agent: {str(e)}"
        )


@router.get("/schools/{school_id}/tools")
async def get_school_tools(school_id: str):
    """获取School的Tool列表"""
    school = get_school_by_id(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return {"tools": school.get("tools", [])}


@router.post("/schools/{school_id}/tools")
async def update_school_tools(school_id: str, request: Dict):
    """更新School的Tool列表"""
    schools = load_schools()
    school_found = False

    for school in schools:
        if school["id"] == school_id:
            school_found = True
            school["tools"] = request.get("tools", [])
            school["updated_at"] = datetime.now().isoformat()
            save_schools(schools)

            # 更新该school的deepagent实例（如果存在）
            try:
                await langchain_service._update_school_deepagent(school_id)
            except Exception as e:
                print(f"[WARNING] schools.py - 更新school {school_id} 的deepagent实例失败: {e}")

            return {"message": "School tools updated successfully"}

    if not school_found:
        raise HTTPException(status_code=404, detail="School not found")


@router.get("/skills")
async def get_all_skills():
    """获取所有可用的 Skills"""
    try:
        skills = skill_scanner.scan_skills(force_refresh=True)
        # 只返回元数据
        skills_metadata = []
        for skill in skills:
            metadata = {
                "skill_id": skill["skill_id"],
                "name": skill["metadata"]["name"],
                "description": skill["metadata"]["description"],
                "version": skill["metadata"].get("version", "Unknown"),
                "author": skill["metadata"].get("author", "Unknown"),
                "tags": skill["metadata"].get("tags", [])
            }
            skills_metadata.append(metadata)
        return {"skills": skills_metadata}
    except Exception as e:
        print(f"[ERROR] schools.py - 获取 skills 失败: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get skills: {str(e)}")


@router.get("/schools/{school_id}/skills")
async def get_school_skills(school_id: str):
    """获取School的Skill列表"""
    school = get_school_by_id(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return {"skills": school.get("skills", [])}


@router.post("/schools/{school_id}/skills")
async def update_school_skills(school_id: str, request: Dict):
    """更新School的Skill列表"""
    schools = load_schools()
    school_found = False

    for school in schools:
        if school["id"] == school_id:
            school_found = True
            school["skills"] = request.get("skills", [])
            school["updated_at"] = datetime.now().isoformat()
            save_schools(schools)

            # 更新该school的deepagent实例（如果存在）
            try:
                await langchain_service._update_school_deepagent(school_id)
            except Exception as e:
                print(f"[WARNING] schools.py - 更新school {school_id} 的deepagent实例失败: {e}")

            return {"message": "School skills updated successfully"}

    if not school_found:
        raise HTTPException(status_code=404, detail="School not found")


@router.patch("/schools/{school_id}/skills/{skill_id}")
async def toggle_school_skill(school_id: str, skill_id: str, request: Dict):
    """启用/禁用School的Skill"""
    schools = load_schools()
    school_found = False

    for school in schools:
        if school["id"] == school_id:
            school_found = True
            skills = school.get("skills", [])

            # 查找并更新 skill 的 enabled 状态
            skill_found = False
            for skill in skills:
                if skill.get("skill_id") == skill_id:
                    skill["enabled"] = request.get("enabled", True)
                    skill_found = True
                    break

            if not skill_found:
                raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found in school")

            school["updated_at"] = datetime.now().isoformat()
            save_schools(schools)

            # 更新该school的deepagent实例（如果存在）
            try:
                await langchain_service._update_school_deepagent(school_id)
            except Exception as e:
                print(f"[WARNING] schools.py - 更新school {school_id} 的deepagent实例失败: {e}")

            return {"message": f"Skill {skill_id} updated successfully"}

    if not school_found:
        raise HTTPException(status_code=404, detail="School not found")
