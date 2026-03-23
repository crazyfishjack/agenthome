"""
计算器工具
用于执行数学计算
"""
from typing import List
from pydantic import BaseModel, Field
from .tool_base import ToolBase


class CalculatorInput(BaseModel):
    """计算器工具输入参数"""
    expression: str = Field(
        description="数学表达式，例如：7+0、3*4、10/2"
    )


class CalculatorTool(ToolBase):
    """计算器工具"""

    @property
    def name(self) -> str:
        return "Calculator"

    @property
    def description(self) -> str:
        return "用于执行数学计算。"

    @property
    def parameter_requirements(self) -> str:
        return """- 必须是有效的数学表达式
- 不能包含任何非法字符
- 表达式应该简洁明了"""

    @property
    def format_requirements(self) -> str:
        return """- 请直接提供数学表达式，不要包含"计算"、"使用"等动词
- 例如："7+0"、"3*4"、"10/2\""""

    @property
    def examples(self) -> List[str]:
        return [
            "输入：\"7+0\" → 返回：\"计算结果: 7\"",
            "输入：\"3*4\" → 返回：\"计算结果: 12\"",
            "输入：\"10/2\" → 返回：\"计算结果: 5\""
        ]

    @property
    def input_schema(self):
        """返回 Pydantic 模型作为输入 schema"""
        return CalculatorInput

    def execute(self, input: str) -> str:
        """执行计算器工具"""
        try:
            result = eval(input, {"__builtins__": {}}, {})
            return f"计算结果: {result}"
        except Exception as e:
            return f"计算错误: {str(e)}"
