"""
Tools 模块
包含所有可用的工具类
"""
from backend.tools.tool_base import ToolBase
from backend.tools.calculator_tool import CalculatorTool
from backend.tools.search_tool import SearchTool
from backend.tools.sandbox_tool import SandboxExecuteTool
from backend.tools.skill_loader_tool import SkillLoaderTool
from backend.tools.script_executor_tool import ScriptExecutorTool
from backend.tools.task_pro_tool import TaskProTool, create_task_pro_tool
from backend.tools.pre_task_pro_tool import PreTaskProTool

__all__ = [
    'ToolBase',
    'CalculatorTool',
    'SearchTool',
    'SandboxExecuteTool',
    'SkillLoaderTool',
    'ScriptExecutorTool',
    'TaskProTool',
    'create_task_pro_tool',
    'PreTaskProTool'
]

# 自动发现并注册所有工具
def get_all_tools():
    """获取所有已注册的工具（基础工具列表，供普通 Agent 使用）"""
    from backend.tools.calculator_tool import CalculatorTool
    from backend.tools.search_tool import SearchTool
    from backend.tools.sandbox_tool import SandboxExecuteTool
    from backend.tools.skill_loader_tool import SkillLoaderTool
    from backend.tools.script_executor_tool import ScriptExecutorTool
    return [
        CalculatorTool(),
        SearchTool(),
        SandboxExecuteTool(),
        SkillLoaderTool(),
        ScriptExecutorTool()
    ]

def get_tool_by_name(tool_name: str):
    """根据名称获取工具"""
    tools = get_all_tools()
    for tool in tools:
        if tool.name == tool_name:
            return tool
    return None
