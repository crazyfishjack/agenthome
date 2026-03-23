"""
Script Executor Tool
执行 Skill 文件夹中的脚本
"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from backend.tools.tool_base import ToolBase
import subprocess
import sys
import os
from pathlib import Path


class ExecuteScriptInput(BaseModel):
    """execute_script 工具的输入参数"""
    skill_id: str = Field(..., description="Skill ID（skill 目录名称）")
    script_name: str = Field(..., description="脚本名称（例如：aggregate_benchmark, package_skill）")
    args: list = Field(default=[], description="脚本参数列表（例如：['<workspace>/iteration-N', '--skill-name', '<name>']）")
    working_dir: str = Field(default="", description="工作目录（可选，默认为 skill 目录）")


class ScriptExecutorTool(ToolBase):
    """脚本执行工具 - 执行 Skill 文件夹中的脚本"""

    def __init__(self):
        super().__init__()
        self._skills_middleware = None

    @property
    def name(self) -> str:
        """工具名称"""
        return "execute_script"

    @property
    def description(self) -> str:
        """工具描述"""
        return """执行 Skill 文件夹中的脚本。

支持以下功能：
1. 执行指定的 Python 脚本
2. 传递参数给脚本
3. 返回执行结果

使用场景：
- 当 Agent 需要执行 skill 的脚本时
- 当需要批量执行多个脚本时
- 当需要传递参数给脚本时

脚本执行方式：
- 使用 `python -m` 方式执行（符合 skill-creator 的标准做法）
- 参数通过命令行传递
- 工作目录默认为 skill 目录，可自定义
- 超时控制：60 秒

示例：
- execute_script(skill_id="skill-creator", script_name="aggregate_benchmark", args=["<workspace>/iteration-N", "--skill-name", "<name>"])
- execute_script(skill_id="skill-creator", script_name="package_skill", args=["<path/to/skill-folder>"])
- execute_script(skill_id="skill-creator", script_name="run_eval", args=["--eval-set", "<path-to-trigger-eval.json>", "--model", "<model-id>"])"""

    @property
    def parameter_requirements(self) -> str:
        """参数要求"""
        return """- skill_id: 必需，Skill ID（skill 目录名称）
- script_name: 必需，脚本名称（例如：aggregate_benchmark, package_skill）
- args: 可选，脚本参数列表（例如：['<workspace>/iteration-N', '--skill-name', '<name>']）
- working_dir: 可选，工作目录（默认为 skill 目录）"""

    @property
    def format_requirements(self) -> str:
        """格式要求"""
        return """参数以 JSON 格式传入，例如：
{
  "skill_id": "skill-creator",
  "script_name": "aggregate_benchmark",
  "args": ["<workspace>/iteration-N", "--skill-name", "<name>"],
  "working_dir": ""
}"""

    @property
    def examples(self) -> List[str]:
        """使用示例"""
        return [
            'execute_script(skill_id="skill-creator", script_name="aggregate_benchmark", args=["<workspace>/iteration-N", "--skill-name", "<name>"])',
            'execute_script(skill_id="skill-creator", script_name="package_skill", args=["<path/to/skill-folder>"])',
            'execute_script(skill_id="skill-creator", script_name="run_eval", args=["--eval-set", "<path-to-trigger-eval.json>", "--model", "<model-id>"])'
        ]

    @property
    def input_schema(self) -> Any:
        """输入参数的 Pydantic 模型"""
        return ExecuteScriptInput

    def execute(self, input: str) -> str:
        """执行工具 - 执行脚本

        Args:
            input: JSON 格式的输入参数

        Returns:
            执行结果（stdout + stderr）
        """
        try:
            # 解析输入参数
            import json
            params = json.loads(input)
            skill_id = params.get("skill_id")
            script_name = params.get("script_name")
            args = params.get("args", [])
            working_dir = params.get("working_dir", "")

            # 验证参数
            if not skill_id:
                return "错误：skill_id 参数不能为空"

            if not script_name:
                return "错误：script_name 参数不能为空"

            # 延迟导入 SkillsMiddleware（避免循环依赖）
            if self._skills_middleware is None:
                from backend.skills.skill_middleware import skills_middleware
                self._skills_middleware = skills_middleware

            # 获取 skill 信息
            skill = self._skills_middleware.skill_scanner.get_skill_by_id(skill_id)
            if not skill:
                return f"错误：未找到 Skill '{skill_id}'"

            # 检查脚本是否存在（支持带 .py 和不带 .py 的脚本名）
            scripts = skill.get("scripts", [])
            
            # 标准化脚本名：移除 .py 后缀（如果存在）
            normalized_script_name = script_name[:-3] if script_name.endswith('.py') else script_name
            
            # 查找匹配的脚本（支持两种格式）
            matched_script = None
            for script in scripts:
                # 标准化存储的脚本名
                normalized_stored_script = script[:-3] if script.endswith('.py') else script
                if normalized_script_name == normalized_stored_script:
                    matched_script = script
                    break
            
            if not matched_script:
                return f"错误：Skill '{skill_id}' 中没有脚本 '{script_name}'。可用的脚本：{', '.join(scripts)}"
            
            # 使用存储的脚本名（带 .py 后缀）进行后续操作
            script_name = matched_script

            # 确定工作目录
            skill_dir = Path(skill["full_path"])
            if working_dir:
                work_dir = Path(working_dir).absolute()
            else:
                work_dir = skill_dir

            if not work_dir.exists():
                return f"错误：工作目录不存在：{work_dir}"

            # 构建 python -m 命令
            # 使用 python -m scripts.script_name 方式执行
            # 注意：模块名不能包含 .py 后缀
            module_name = script_name[:-3] if script_name.endswith('.py') else script_name
            cmd = [sys.executable, "-m", f"scripts.{module_name}"] + args

            # 设置环境变量
            env = os.environ.copy()
            # 添加 skill 目录到 PYTHONPATH
            env["PYTHONPATH"] = str(skill_dir) + os.pathsep + env.get("PYTHONPATH", "")

            print(f"[DEBUG] script_executor_tool.py - 执行命令: {' '.join(cmd)}")
            print(f"[DEBUG] script_executor_tool.py - 工作目录: {work_dir}")
            print(f"[DEBUG] script_executor_tool.py - PYTHONPATH: {env['PYTHONPATH']}")

            # 执行脚本
            result = subprocess.run(
                cmd,
                cwd=str(work_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=60  # 60 秒超时
            )

            # 构建输出
            output_lines = [
                f"## 脚本执行结果",
                f"**Skill ID**: {skill_id}",
                f"**脚本名称**: {script_name}",
                f"**命令**: {' '.join(cmd)}",
                f"**工作目录**: {work_dir}",
                f"**退出码**: {result.returncode}",
                ""
            ]

            if result.stdout:
                output_lines.append("### 标准输出 (stdout)")
                output_lines.append("```")
                output_lines.append(result.stdout)
                output_lines.append("```")
                output_lines.append("")

            if result.stderr:
                output_lines.append("### 标准错误 (stderr)")
                output_lines.append("```")
                output_lines.append(result.stderr)
                output_lines.append("```")
                output_lines.append("")

            if result.returncode == 0:
                output_lines.append("✅ 脚本执行成功")
            else:
                output_lines.append("❌ 脚本执行失败")

            return "\n".join(output_lines)

        except json.JSONDecodeError as e:
            return f"错误：JSON 解析失败 - {str(e)}"
        except subprocess.TimeoutExpired:
            return "错误：脚本执行超时（60秒）"
        except FileNotFoundError as e:
            return f"错误：找不到文件 - {str(e)}"
        except Exception as e:
            return f"错误：脚本执行失败 - {str(e)}"
