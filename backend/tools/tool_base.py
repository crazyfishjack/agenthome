"""
工具基类
所有工具类都应该继承这个基类
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Any
from langchain_core.tools import Tool, StructuredTool


class ToolBase(ABC):
    """工具基类"""

    def __init__(self):
        self._tool: Optional[Tool] = None
        self._structured_tool: Optional[StructuredTool] = None

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass

    @property
    @abstractmethod
    def parameter_requirements(self) -> str:
        """参数要求"""
        pass

    @property
    @abstractmethod
    def format_requirements(self) -> str:
        """格式要求"""
        pass

    @property
    @abstractmethod
    def examples(self) -> List[str]:
        """使用示例"""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Any:
        """输入参数的 Pydantic 模型"""
        pass

    @abstractmethod
    def execute(self, input: str) -> str:
        """执行工具"""
        pass

    @property
    def tool(self) -> Tool:
        """获取 LangChain Tool 对象（向后兼容）"""
        if self._tool is None:
            full_description = self._build_full_description()
            self._tool = Tool(
                name=self.name,
                description=full_description,
                func=self.execute
            )
        return self._tool

    @property
    def structured_tool(self) -> StructuredTool:
        """获取 LangChain StructuredTool 对象（用于 Function Calling）"""
        if self._structured_tool is None:
            full_description = self._build_full_description()
            # 使用 StructuredTool.from_function 创建结构化工具
            self._structured_tool = StructuredTool.from_function(
                func=self._execute_with_schema,
                name=self.name,
                description=full_description,
                args_schema=self.input_schema
            )
        return self._structured_tool

    def _execute_with_schema(self, **kwargs) -> str:
        """使用 Pydantic 模型参数执行工具"""
        # 将 kwargs 转换为字符串输入
        # 根据不同的工具类型，提取相应的参数
        if hasattr(self.input_schema, '__fields__'):
            # 获取字段数量
            field_names = list(self.input_schema.__fields__.keys())
            field_count = len(field_names)

            if field_count == 1:
                # 单字段参数：提取第一个字段的值
                field_name = field_names[0]
                input_value = kwargs.get(field_name, "")
                return self.execute(input_value)
            else:
                # 多字段参数：将整个 kwargs 转换为 JSON 字符串
                import json
                return self.execute(json.dumps(kwargs))
        return self.execute(str(kwargs))

    def _build_full_description(self) -> str:
        """构建完整的工具描述"""
        return f"""{self.description}

参数要求：
{self.parameter_requirements}

格式要求：
{self.format_requirements}

示例：
{self._format_examples()}"""

    def _format_examples(self) -> str:
        """格式化示例"""
        return "\n".join([f"- {example}" for example in self.examples])

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "parameter_requirements": self.parameter_requirements,
            "format_requirements": self.format_requirements,
            "examples": self.examples
        }
