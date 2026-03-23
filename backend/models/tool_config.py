"""
Tool 配置数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class ToolConfig(BaseModel):
    """Tool 配置"""
    tool_name: str = Field(..., description="工具名称")
    tool_description: str = Field(..., description="工具描述")
    parameter_requirements: str = Field(..., description="参数要求")
    format_requirements: str = Field(..., description="格式要求")
    examples: List[str] = Field(default_factory=list, description="使用示例")
    enabled: bool = Field(default=True, description="是否启用")

    class Config:
        json_schema_extra = {
            "example": {
                "tool_name": "Calculator",
                "tool_description": "用于执行数学计算。",
                "parameter_requirements": "- 必须是有效的数学表达式\n- 不能包含任何非法字符\n- 表达式应该简洁明了",
                "format_requirements": "- 请直接提供数学表达式，不要包含\"计算\"、\"使用\"等动词\n- 例如：\"7+0\"、\"3*4\"、\"10/2\"",
                "examples": [
                    "输入：\"7+0\" → 返回：\"计算结果: 7\"",
                    "输入：\"3*4\" → 返回：\"计算结果: 12\""
                ],
                "enabled": True
            }
        }


class ToolListResponse(BaseModel):
    """Tool 列表响应"""
    tools: List[ToolConfig] = Field(..., description="工具列表")
    total: int = Field(..., description="工具总数")


class SchoolToolUpdateRequest(BaseModel):
    """School 工具更新请求"""
    tools: List[ToolConfig] = Field(..., description="工具列表")


class SchoolToolResponse(BaseModel):
    """School 工具响应"""
    school_id: str = Field(..., description="School ID")
    school_name: str = Field(..., description="School 名称")
    tools: List[ToolConfig] = Field(..., description="工具列表")
