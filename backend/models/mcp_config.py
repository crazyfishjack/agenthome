"""
MCP 配置数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum


class MCPMode(str, Enum):
    """MCP 连接模式"""
    REMOTE = "remote"
    STDIO = "stdio"


class MCPRemoteConfig(BaseModel):
    """Remote 模式配置"""
    type: str = Field(default="streamable_http", description="连接类型")
    url: str = Field(..., description="MCP 服务器 URL")


class MCPStdioConfig(BaseModel):
    """Stdio 模式配置"""
    command: str = Field(..., description="执行命令")
    args: List[str] = Field(default_factory=list, description="命令参数")


class MCPConfig(BaseModel):
    """MCP 配置"""
    mcp_id: str = Field(..., description="MCP ID")
    name: str = Field(..., description="MCP 名称")
    description: Optional[str] = Field(None, description="MCP 描述")
    mode: MCPMode = Field(..., description="MCP 连接模式")
    config: Dict[str, Any] = Field(..., description="MCP 配置（根据模式不同而不同）")
    enabled: bool = Field(default=True, description="是否启用")
    added_at: str = Field(..., description="添加时间")

    class Config:
        json_schema_extra = {
            "example": {
                "mcp_id": "mcp_123",
                "name": "My MCP Server",
                "description": "示例 MCP 服务器",
                "mode": "remote",
                "config": {
                    "type": "streamable_http",
                    "url": "http://localhost:3000/mcp"
                },
                "enabled": True,
                "added_at": "2026-03-05T00:00:00"
            }
        }


class MCPCreateRequest(BaseModel):
    """创建 MCP 请求"""
    name: str = Field(..., description="MCP 名称")
    description: Optional[str] = Field(None, description="MCP 描述")
    mode: MCPMode = Field(..., description="MCP 连接模式")
    config: Dict[str, Any] = Field(..., description="MCP 配置")


class MCPUpdateRequest(BaseModel):
    """更新 MCP 请求"""
    name: Optional[str] = Field(None, description="MCP 名称")
    description: Optional[str] = Field(None, description="MCP 描述")
    mode: Optional[MCPMode] = Field(None, description="MCP 连接模式")
    config: Optional[Dict[str, Any]] = Field(None, description="MCP 配置")
    enabled: Optional[bool] = Field(None, description="是否启用")


class MCPListResponse(BaseModel):
    """MCP 列表响应"""
    mcps: List[MCPConfig] = Field(..., description="MCP 列表")
    total: int = Field(..., description="MCP 总数")


class SchoolMCPUpdateRequest(BaseModel):
    """School MCP 更新请求"""
    mcps: List[MCPConfig] = Field(..., description="MCP 列表")
