"""
搜索工具
用于搜索信息（模拟）
"""
from typing import List
from pydantic import BaseModel, Field
from .tool_base import ToolBase


class SearchInput(BaseModel):
    """搜索工具输入参数"""
    query: str = Field(
        description="搜索关键词，例如：人工智能、机器学习"
    )


class SearchTool(ToolBase):
    """搜索工具（模拟）"""

    @property
    def name(self) -> str:
        return "Search"

    @property
    def description(self) -> str:
        return "用于搜索信息（模拟）。"

    @property
    def parameter_requirements(self) -> str:
        return """- 必须是有效的搜索关键词
- 不能为空字符串
- 关键词应该简洁明了"""

    @property
    def format_requirements(self) -> str:
        return """- 请直接提供搜索关键词，不要包含"搜索"、"使用"等动词
- 例如："人工智能"、"机器学习\""""

    @property
    def examples(self) -> List[str]:
        return [
            "输入：\"人工智能\" → 返回：\"搜索结果: 关于'人工智能'的信息（这是模拟的搜索结果）\"",
            "输入：\"机器学习\" → 返回：\"搜索结果: 关于'机器学习'的信息（这是模拟的搜索结果）\""
        ]

    @property
    def input_schema(self):
        """返回 Pydantic 模型作为输入 schema"""
        return SearchInput

    def execute(self, input: str) -> str:
        """执行搜索工具（模拟）"""
        return f"搜索结果: 关于'{input}'的信息（这是模拟的搜索结果）"
