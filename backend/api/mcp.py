"""
MCP API 接口
提供 MCP 的 CRUD 操作
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from datetime import datetime
import json
import os

from backend.models.mcp_config import (
    MCPConfig,
    MCPCreateRequest,
    MCPUpdateRequest,
    MCPListResponse,
    SchoolMCPUpdateRequest,
    MCPMode
)
from backend.services.mcp_manager import mcp_manager

router = APIRouter()

MCP_FILE = "./data/mcps.json"


def load_mcps() -> List[Dict]:
    """加载所有 MCP"""
    if not os.path.exists(MCP_FILE):
        return []
    with open(MCP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("mcps", [])


def save_mcps(mcps: List[Dict]):
    """保存所有 MCP"""
    os.makedirs(os.path.dirname(MCP_FILE), exist_ok=True)
    with open(MCP_FILE, "w", encoding="utf-8") as f:
        json.dump({"mcps": mcps}, f, ensure_ascii=False, indent=2)


def get_mcp_by_id(mcp_id: str) -> Optional[Dict]:
    """根据 ID 获取 MCP"""
    mcps = load_mcps()
    for mcp in mcps:
        if mcp["mcp_id"] == mcp_id:
            return mcp
    return None


@router.get("/mcps")
async def get_all_mcps():
    """获取所有 MCP"""
    mcps = load_mcps()
    return {"mcps": mcps}


@router.get("/mcps/{mcp_id}")
async def get_mcp(mcp_id: str):
    """获取指定 MCP"""
    mcp = get_mcp_by_id(mcp_id)
    if not mcp:
        raise HTTPException(status_code=404, detail="MCP not found")
    return mcp


@router.post("/mcps", response_model=MCPConfig)
async def create_mcp(request: MCPCreateRequest):
    """创建新的 MCP"""
    mcps = load_mcps()

    # 验证配置
    mode = request.mode
    config = request.config

    if mode == MCPMode.REMOTE:
        # Remote 模式：验证 url
        if "url" not in config:
            raise HTTPException(status_code=400, detail="Remote 模式需要提供 url")
        if "type" not in config:
            config["type"] = "streamable_http"
    elif mode == MCPMode.STDIO:
        # Stdio 模式：验证 command
        if "command" not in config:
            raise HTTPException(status_code=400, detail="Stdio 模式需要提供 command")
        if "args" not in config:
            config["args"] = []

    # 创建临时 MCP 配置用于测试
    temp_mcp_id = f"mcp_{datetime.now().timestamp()}"
    temp_mcp_config = {
        "mcp_id": temp_mcp_id,
        "name": request.name,
        "description": request.description,
        "mode": mode.value,
        "config": config,
        "enabled": True,
        "added_at": datetime.now().isoformat()
    }

    # 创建 MCP 客户端并测试连接
    mcp_config = MCPConfig(**temp_mcp_config)
    client = mcp_manager.create_mcp_client(mcp_config)
    
    if not client:
        raise HTTPException(status_code=400, detail="创建 MCP 客户端失败")

    # 测试连接和工具发现
    try:
        tools = await mcp_manager.get_mcp_tools(temp_mcp_id)
        if not tools:
            print(f"[WARNING] mcp.py - MCP {temp_mcp_id} 测试成功，但没有发现任何工具")
        else:
            print(f"[DEBUG] mcp.py - MCP {temp_mcp_id} 测试成功，发现 {len(tools)} 个工具: {[t.name for t in tools]}")
    except Exception as e:
        # 测试失败，清理客户端并拒绝保存
        await mcp_manager.remove_mcp_client(temp_mcp_id)
        raise HTTPException(status_code=400, detail=f"MCP 连接测试失败: {str(e)}")

    # 测试成功，保存配置
    new_mcp = {
        "mcp_id": temp_mcp_id,
        "name": request.name,
        "description": request.description,
        "mode": mode.value,
        "config": config,
        "enabled": True,
        "added_at": datetime.now().isoformat()
    }

    mcps.append(new_mcp)
    save_mcps(mcps)

    print(f"[DEBUG] mcp.py - MCP {temp_mcp_id} 创建成功并已测试")
    return new_mcp


@router.put("/mcps/{mcp_id}", response_model=MCPConfig)
async def update_mcp(mcp_id: str, request: MCPUpdateRequest):
    """更新 MCP"""
    mcps = load_mcps()
    for i, mcp in enumerate(mcps):
        if mcp["mcp_id"] == mcp_id:
            update_data = request.dict(exclude_unset=True)

            # 验证配置
            if "mode" in update_data or "config" in update_data:
                mode = update_data.get("mode", mcp["mode"])
                config = update_data.get("config", mcp["config"])

                if mode == MCPMode.REMOTE:
                    if "url" not in config:
                        raise HTTPException(status_code=400, detail="Remote 模式需要提供 url")
                    if "type" not in config:
                        config["type"] = "streamable_http"
                elif mode == MCPMode.STDIO:
                    if "command" not in config:
                        raise HTTPException(status_code=400, detail="Stdio 模式需要提供 command")
                    if "args" not in config:
                        config["args"] = []

            mcps[i].update(update_data)
            mcps[i]["updated_at"] = datetime.now().isoformat()
            save_mcps(mcps)

            # 重新创建 MCP 客户端
            await mcp_manager.remove_mcp_client(mcp_id)
            mcp_config = MCPConfig(**mcps[i])
            mcp_manager.create_mcp_client(mcp_config)

            return mcps[i]

    raise HTTPException(status_code=404, detail="MCP not found")


@router.delete("/mcps/{mcp_id}")
async def delete_mcp(mcp_id: str):
    """删除 MCP"""
    mcps = load_mcps()
    for i, mcp in enumerate(mcps):
        if mcp["mcp_id"] == mcp_id:
            # 移除 MCP 客户端
            await mcp_manager.remove_mcp_client(mcp_id)

            # 删除 MCP
            mcps.pop(i)
            save_mcps(mcps)

            # 从所有 school 中移除该 MCP
            schools = load_schools()
            schools_updated = False
            for school in schools:
                if "mcps" in school:
                    original_mcps = school["mcps"]
                    school["mcps"] = [m for m in school["mcps"] if m.get("mcp_id") != mcp_id]
                    if len(school["mcps"]) != len(original_mcps):
                        schools_updated = True
                        school["updated_at"] = datetime.now().isoformat()
                        print(f"[DEBUG] mcp.py - 从 school {school['id']} 中移除 MCP {mcp_id}")

            if schools_updated:
                save_schools(schools)
                print(f"[DEBUG] mcp.py - 已更新 schools.json")

            # 更新所有配置了该 MCP 的 agent 的 deepagent 实例
            try:
                from backend.services.langchain_service import langchain_service
                # 使用新的方法从所有 agent 中移除该 MCP（异步）
                await langchain_service.remove_mcp_from_all_agents(mcp_id)
            except Exception as e:
                print(f"[WARNING] mcp.py - 更新 agent deepagent 实例失败: {e}")
                import traceback
                traceback.print_exc()

            return {"message": "MCP deleted successfully"}

    raise HTTPException(status_code=404, detail="MCP not found")


@router.patch("/mcps/{mcp_id}/toggle")
async def toggle_mcp(mcp_id: str, enabled: bool):
    """启用/禁用 MCP"""
    mcps = load_mcps()
    for i, mcp in enumerate(mcps):
        if mcp["mcp_id"] == mcp_id:
            mcps[i]["enabled"] = enabled
            mcps[i]["updated_at"] = datetime.now().isoformat()
            save_mcps(mcps)
            return {"message": f"MCP {mcp_id} {'enabled' if enabled else 'disabled'} successfully"}

    raise HTTPException(status_code=404, detail="MCP not found")


@router.get("/mcps/{mcp_id}/tools")
async def get_mcp_tools(mcp_id: str):
    """获取 MCP 的工具列表"""
    mcp = get_mcp_by_id(mcp_id)
    if not mcp:
        raise HTTPException(status_code=404, detail="MCP not found")

    # 获取 MCP 工具（强制刷新缓存）
    tools = await mcp_manager.get_mcp_tools(mcp_id, force_refresh=True)

    return {"tools": [tool.name for tool in tools]}


@router.post("/mcps/test")
async def test_mcp(request: MCPCreateRequest):
    """测试 MCP 连接和工具发现（不保存配置）"""
    # 验证配置
    mode = request.mode
    config = request.config

    if mode == MCPMode.REMOTE:
        # Remote 模式：验证 url
        if "url" not in config:
            raise HTTPException(status_code=400, detail="Remote 模式需要提供 url")
        if "type" not in config:
            config["type"] = "streamable_http"
    elif mode == MCPMode.STDIO:
        # Stdio 模式：验证 command
        if "command" not in config:
            raise HTTPException(status_code=400, detail="Stdio 模式需要提供 command")
        if "args" not in config:
            config["args"] = []

    # 创建临时 MCP 配置用于测试
    temp_mcp_id = f"test_mcp_{datetime.now().timestamp()}"
    temp_mcp_config = {
        "mcp_id": temp_mcp_id,
        "name": request.name,
        "description": request.description,
        "mode": mode.value,
        "config": config,
        "enabled": True,
        "added_at": datetime.now().isoformat()
    }

    # 创建 MCP 客户端并测试连接
    mcp_config = MCPConfig(**temp_mcp_config)
    client = mcp_manager.create_mcp_client(mcp_config)
    
    if not client:
        raise HTTPException(status_code=400, detail="创建 MCP 客户端失败")

    # 测试连接和工具发现
    try:
        tools = await mcp_manager.get_mcp_tools(temp_mcp_id)
        tool_names = [tool.name for tool in tools]

        # 清理临时客户端
        await mcp_manager.remove_mcp_client(temp_mcp_id)

        return {
            "success": True,
            "message": f"MCP 连接测试成功，发现 {len(tools)} 个工具",
            "tools": tool_names,
            "tool_count": len(tools)
        }
    except Exception as e:
        # 测试失败，清理客户端
        await mcp_manager.remove_mcp_client(temp_mcp_id)
        raise HTTPException(status_code=400, detail=f"MCP 连接测试失败: {str(e)}")


# ==================== School MCP 接口 ====================

def load_schools() -> List[Dict]:
    """加载所有 School"""
    schools_file = "./data/schools.json"
    if not os.path.exists(schools_file):
        return []
    with open(schools_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("schools", [])


def save_schools(schools: List[Dict]):
    """保存所有 School"""
    schools_file = "./data/schools.json"
    os.makedirs(os.path.dirname(schools_file), exist_ok=True)
    with open(schools_file, "w", encoding="utf-8") as f:
        json.dump({"schools": schools}, f, ensure_ascii=False, indent=2)


def get_school_by_id(school_id: str) -> Optional[Dict]:
    """根据 ID 获取 School"""
    schools = load_schools()
    for school in schools:
        if school["id"] == school_id:
            return school
    return None


@router.get("/schools/{school_id}/mcps")
async def get_school_mcps(school_id: str):
    """获取 School 的 MCP 列表"""
    school = get_school_by_id(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return {"mcps": school.get("mcps", [])}


@router.post("/schools/{school_id}/mcps")
async def update_school_mcps(school_id: str, request: SchoolMCPUpdateRequest):
    """更新 School 的 MCP 列表"""
    schools = load_schools()
    school_found = False

    for school in schools:
        if school["id"] == school_id:
            school_found = True
            school["mcps"] = [mcp.dict() for mcp in request.mcps]
            school["updated_at"] = datetime.now().isoformat()
            save_schools(schools)

            # 更新该 school 的 deepagent 实例（如果存在）
            try:
                from backend.services.langchain_service import langchain_service
                await langchain_service._update_school_deepagent(school_id)
            except Exception as e:
                print(f"[WARNING] mcp.py - 更新 school {school_id} 的 deepagent 实例失败: {e}")

            return {"message": "School mcps updated successfully"}

    if not school_found:
        raise HTTPException(status_code=404, detail="School not found")


@router.patch("/schools/{school_id}/mcps/{mcp_id}")
async def toggle_school_mcp(school_id: str, mcp_id: str, enabled: bool):
    """启用/禁用 School 的 MCP"""
    schools = load_schools()
    school_found = False

    for school in schools:
        if school["id"] == school_id:
            school_found = True
            mcps = school.get("mcps", [])

            # 查找并更新 mcp 的 enabled 状态
            mcp_found = False
            for mcp in mcps:
                if mcp.get("mcp_id") == mcp_id:
                    mcp["enabled"] = enabled
                    mcp_found = True
                    break

            if not mcp_found:
                raise HTTPException(status_code=404, detail=f"MCP {mcp_id} not found in school")

            school["updated_at"] = datetime.now().isoformat()
            save_schools(schools)

            # 更新该 school 的 deepagent 实例（如果存在）
            try:
                from backend.services.langchain_service import langchain_service
                await langchain_service._update_school_deepagent(school_id)
            except Exception as e:
                print(f"[WARNING] mcp.py - 更新 school {school_id} 的 deepagent 实例失败: {e}")

            return {"message": f"MCP {mcp_id} updated successfully"}

    if not school_found:
        raise HTTPException(status_code=404, detail="School not found")
