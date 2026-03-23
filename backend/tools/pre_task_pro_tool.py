"""
Pre Task Pro 工具 - 准备 Task Pro 执行

在调用 task_pro 之前使用，用于：
1. 生成 execution_id
2. 创建数据库记录
3. 通过特殊标记通知前端拉起窗口

必须与 task_pro 配合使用，先调用 pre_task_pro，再调用 task_pro。
"""

import json
import uuid
import time
from typing import List
from pydantic import BaseModel, Field

from backend.tools.tool_base import ToolBase
from backend.db.subagent_db import get_subagent_db


class PreTaskProInput(BaseModel):
    """Pre Task Pro 工具输入参数"""
    description: str = Field(
        description="任务的详细描述，包含所有必要的上下文和期望的输出格式"
    )
    subagent_type: str = Field(
        description="要使用的 SUB agent 类型，必须是可用 agent 类型之一"
    )
    show_thinking: bool = Field(
        default=True,
        description="是否显示 SUB agent 的思考过程"
    )


class PreTaskProTool(ToolBase):
    """
    Pre Task Pro 工具 - 准备 Task Pro 执行

    【第一步】在调用 task_pro 之前，必须先调用此工具！

    功能：
    1. 生成唯一的 execution_id
    2. 在数据库中创建执行记录
    3. 返回特殊标记，通知前端拉起窗口和按钮

    【重要】调用此工具后，必须立即调用 task_pro 工具！
    """

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "pre_task_pro"

    @property
    def description(self) -> str:
        return """【第一步】准备 Task Pro 执行，生成 execution_id 并拉起前端窗口。

【使用流程 - 必须严格遵守】
1. 调用 pre_task_pro 工具，传入任务参数
2. 获取返回的 execution_id
3. 【必须】紧接着调用 task_pro 工具，传入相同的参数和 execution_id

【示例】
用户要求："创建一个调研报告"
→ 调用 pre_task_pro(description="创建调研报告", subagent_type="researcher")
→ 获取返回的 execution_id
→ 【立即】调用 task_pro(description="创建调研报告", subagent_type="researcher", execution_id="返回的id")

⚠️ 重要提示：
- 必须先调用 pre_task_pro，再调用 task_pro
- 两次调用的参数必须完全相同（除了 execution_id）
- 调用 pre_task_pro 后，必须立即调用 task_pro，不要执行其他操作！
- 不要跳过 pre_task_pro 直接调用 task_pro！
"""

    @property
    def parameter_requirements(self) -> str:
        return """- description: 任务的详细描述，包含上下文和期望输出
- subagent_type: SUB agent 类型（如 general-purpose, researcher, code-reviewer 等）
- show_thinking: 是否显示思考过程（可选，默认 true）

注意：这些参数必须与后续 task_pro 调用的参数完全一致！"""

    @property
    def format_requirements(self) -> str:
        return """- description 应尽可能详细，包含所有必要上下文
- subagent_type 必须是可用的 agent 类型之一
- 返回的 execution_id 必须原样传递给 task_pro"""

    @property
    def examples(self) -> List[str]:
        return [
            'pre_task_pro(description="搜索 Python 异步编程资料", subagent_type="general-purpose")',
            'pre_task_pro(description="分析代码中的 bug", subagent_type="code-reviewer", show_thinking=True)',
            'pre_task_pro(description="调研 AI 行业现状", subagent_type="researcher")'
        ]

    @property
    def input_schema(self):
        return PreTaskProInput

    def execute(self, input_str: str) -> str:
        """同步执行 - 直接返回提示信息"""
        return "Pre Task Pro 工具需要参数执行，请使用结构化调用方式。"

    def _execute_with_schema(self, **kwargs) -> str:
        """
        使用 Pydantic schema 执行

        生成 execution_id，创建数据库记录，返回特殊标记供前端解析。

        Args:
            **kwargs: 工具参数，包含 description, subagent_type, show_thinking

        Returns:
            包含 execution_id 的特殊标记字符串
        """
        description = kwargs.get('description', '')
        subagent_type = kwargs.get('subagent_type', '')
        show_thinking = kwargs.get('show_thinking', True)

        # 拦截 general-purpose 子代理调用
        if subagent_type == 'general-purpose':
            return """名称为general-purpose 的子代理已被禁用，严禁使用该子代理
可以使用其他可用的子代理，或尝试自己执行"""

        # 生成 execution_id
        execution_id = f"taskpro_{uuid.uuid4().hex[:16]}_{int(time.time())}"

        # 创建数据库记录（pending 状态）
        db = get_subagent_db()
        db.create_execution(
            execution_id=execution_id,
            description=description,
            subagent_type=subagent_type,
            show_thinking=show_thinking
        )

        # 构建返回信息
        init_info = {
            "execution_id": execution_id,
            "subagent_type": subagent_type,
            "description": description
        }

        # 返回特殊标记，前端解析后会立即拉起窗口
        # 使用 [TASK_PRO_INIT]...[/TASK_PRO_INIT] 格式，与前端解析逻辑匹配
        result = f"""[TASK_PRO_INIT]{json.dumps(init_info)}[/TASK_PRO_INIT]

✅ 准备完成！execution_id: {execution_id}

⚠️ 现在必须立即调用 task_pro 工具！
⚠️ 使用相同的参数，并加上 execution_id="{execution_id}"

示例：
task_pro(
    description="{description}",
    subagent_type="{subagent_type}",
    show_thinking={show_thinking},
    execution_id="{execution_id}"
)
"""

        return result
