"""
Tools API 接口
提供工具扫描、配置和管理功能
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict
import os
import importlib.util
import sys

from backend.models.tool_config import ToolConfig, ToolListResponse
from backend.tools import get_all_tools, get_tool_by_name

router = APIRouter()


@router.get("/scan", response_model=ToolListResponse)
async def scan_tools():
    """
    扫描 tools 文件夹，返回所有可用的工具列表
    """
    try:
        tools = get_all_tools()
        tool_configs = []

        for tool in tools:
            tool_dict = tool.to_dict()
            tool_configs.append(ToolConfig(
                tool_name=tool_dict["name"],
                tool_description=tool_dict["description"],
                parameter_requirements=tool_dict["parameter_requirements"],
                format_requirements=tool_dict["format_requirements"],
                examples=tool_dict["examples"],
                enabled=True
            ))

        return ToolListResponse(
            tools=tool_configs,
            total=len(tool_configs)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan tools: {str(e)}")


@router.get("/config/{tool_name}", response_model=ToolConfig)
async def get_tool_config(tool_name: str):
    """
    获取指定工具的配置信息
    """
    try:
        tool = get_tool_by_name(tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

        tool_dict = tool.to_dict()
        return ToolConfig(
            tool_name=tool_dict["name"],
            tool_description=tool_dict["description"],
            parameter_requirements=tool_dict["parameter_requirements"],
            format_requirements=tool_dict["format_requirements"],
            examples=tool_dict["examples"],
            enabled=True
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tool config: {str(e)}")


@router.post("/reload")
async def reload_tools():
    """
    重新加载工具模块
    """
    try:
        # 重新导入 tools 模块
        if 'backend.tools' in sys.modules:
            del sys.modules['backend.tools']
        if 'backend.tools.tool_base' in sys.modules:
            del sys.modules['backend.tools.tool_base']
        if 'backend.tools.calculator_tool' in sys.modules:
            del sys.modules['backend.tools.calculator_tool']
        if 'backend.tools.search_tool' in sys.modules:
            del sys.modules['backend.tools.search_tool']

        # 重新导入
        import backend.tools

        return {"message": "Tools reloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload tools: {str(e)}")
