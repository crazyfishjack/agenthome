"""
Skill Loader Tool
实现 Agent Skills 的渐进式披露机制
支持三级披露：metadata（元数据）、body（内容）、extended（扩展）
"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from backend.tools.tool_base import ToolBase


class LoadSkillInput(BaseModel):
    """load_skill 工具的输入参数"""
    skill_id: str = Field(..., description="Skill ID（skill 目录名称）")
    disclosure_level: str = Field(
        default="body",
        description="披露级别：metadata（仅元数据）、body（元数据+内容）、extended（元数据+内容+扩展）"
    )
    reference_files: Optional[List[str]] = Field(
        default=None,
        description="要加载的具体 reference 文件列表，如果为 None 则加载所有 references（仅在 extended 级别生效）"
    )


class SkillLoaderTool(ToolBase):
    """Skill 加载工具 - 实现渐进式披露机制"""

    def __init__(self):
        super().__init__()
        self._skills_middleware = None

    @property
    def name(self) -> str:
        """工具名称"""
        return "load_skill"

    @property
    def description(self) -> str:
        """工具描述"""
        return """需要使用技能时调用，加载指定 Skill 的内容，支持渐进式披露机制。

此工具允许 Agent 按需加载 Skill 的不同层级信息：
- metadata：仅加载 Skill 的元数据（名称、描述、版本等）
- body：加载 Skill 的元数据和 SKILL.md 主体内容
- extended：加载 Skill 的完整信息（包括打包资源文件列表和 references 参考文档）

使用场景：
- 当 Agent 需要了解某个 Skill 的功能时，使用 metadata 级别
- 当 Agent 需要使用某个 Skill 的详细说明时，使用 body 级别
- 当 Agent 需要查看 Skill 的完整资源时，使用 extended 级别
- 当 Agent 需要查看 Skill 的参考文档时，使用 extended 级别，并通过 reference_files 参数指定要加载的参考文件"""

    @property
    def parameter_requirements(self) -> str:
        """参数要求"""
        return """- skill_id: 必需，Skill ID（skill 目录名称）
- disclosure_level: 可选，披露级别（metadata/body/extended），默认为 body
- reference_files: 可选，要加载的具体 reference 文件列表，仅在 extended 级别生效，默认为 None（加载所有）"""

    @property
    def format_requirements(self) -> str:
        """格式要求"""
        return """参数以 JSON 格式传入，例如：
{
  "skill_id": "pdf",
  "disclosure_level": "body"
}

或加载指定 reference 文件：
{
  "skill_id": "pdf",
  "disclosure_level": "extended",
  "reference_files": ["reference1.md", "reference2.md"]
}"""

    @property
    def examples(self) -> List[str]:
        """使用示例"""
        return [
            'load_skill(skill_id="pdf", disclosure_level="metadata")',
            'load_skill(skill_id="pdf", disclosure_level="body")',
            'load_skill(skill_id="pdf", disclosure_level="extended")',
            'load_skill(skill_id="pdf", disclosure_level="extended", reference_files=["reference1.md", "reference2.md"])'
        ]

    @property
    def input_schema(self) -> Any:
        """输入参数的 Pydantic 模型"""
        return LoadSkillInput

    def execute(self, input: str) -> str:
        """执行工具 - 加载 Skill 内容

        Args:
            input: JSON 格式的输入参数

        Returns:
            Skill 内容（根据披露级别返回不同层级的信息）
        """
        try:
            # 解析输入参数
            import json
            params = json.loads(input)
            skill_id = params.get("skill_id")
            disclosure_level = params.get("disclosure_level", "body")
            reference_files = params.get("reference_files", None)

            # 验证参数
            if not skill_id:
                return "错误：skill_id 参数不能为空"

            if disclosure_level not in ["metadata", "body", "extended"]:
                return f"错误：disclosure_level 必须是 metadata、body 或 extended 之一，当前值：{disclosure_level}"

            # 延迟导入 SkillsMiddleware（避免循环依赖）
            if self._skills_middleware is None:
                from backend.skills.skill_middleware import skills_middleware
                self._skills_middleware = skills_middleware

            # 根据披露级别加载 Skill
            if disclosure_level == "metadata":
                result = self._load_metadata(skill_id)
            elif disclosure_level == "body":
                result = self._load_body(skill_id)
            elif disclosure_level == "extended":
                result = self._load_extended(skill_id, reference_files)
            else:
                result = f"错误：不支持的披露级别：{disclosure_level}"

            return result

        except json.JSONDecodeError as e:
            return f"错误：JSON 解析失败 - {str(e)}"
        except Exception as e:
            return f"错误：加载 Skill 失败 - {str(e)}"

    def _load_metadata(self, skill_id: str) -> str:
        """加载 Skill 元数据（第一层披露）

        Args:
            skill_id: Skill ID

        Returns:
            元数据信息
        """
        skills = self._skills_middleware.get_skills_metadata([skill_id])

        if not skills:
            return f"错误：未找到 Skill '{skill_id}'"

        skill = skills[0]

        # 格式化元数据
        lines = [
            f"## {skill['name']} (元数据层)",
            f"**Skill ID**: {skill['skill_id']}",
            f"**描述**: {skill['description']}",
            f"**版本**: {skill['version']}",
            f"**作者**: {skill['author']}",
        ]

        if skill['tags']:
            lines.append(f"**标签**: {', '.join(skill['tags'])}")

        return "\n".join(lines)

    def _load_body(self, skill_id: str) -> str:
        """加载 Skill 主体内容（第二层披露）

        Args:
            skill_id: Skill ID

        Returns:
            元数据 + SKILL.md 内容
        """
        skill = self._skills_middleware.get_skill_details(skill_id)

        if not skill:
            return f"错误：未找到 Skill '{skill_id}'"

        metadata = skill['metadata']
        content = skill['content']

        # 格式化元数据
        lines = [
            f"## {metadata['name']} (详情层)",
            f"**Skill ID**: {skill_id}",
            f"**描述**: {metadata['description']}",
            f"**版本**: {metadata.get('version', 'Unknown')}",
            f"**作者**: {metadata.get('author', 'Unknown')}",
        ]

        if metadata.get('tags'):
            lines.append(f"**标签**: {', '.join(metadata['tags'])}")

        lines.append("")
        lines.append("### Skill 内容")
        lines.append(content)

        return "\n".join(lines)

    def _load_extended(self, skill_id: str, reference_files: Optional[List[str]] = None) -> str:
        """加载 Skill 扩展信息（第三层披露）

        Args:
            skill_id: Skill ID
            reference_files: 要加载的具体 reference 文件列表，如果为 None 则加载所有

        Returns:
            元数据 + SKILL.md 内容 + 文件列表 + references 内容
        """
        skill = self._skills_middleware.get_skill_extended(skill_id)

        if not skill:
            return f"错误：未找到 Skill '{skill_id}'"

        metadata = skill['metadata']
        content = skill['content']
        files = skill['files']

        # 格式化元数据
        lines = [
            f"## {metadata['name']} (扩展层)",
            f"**Skill ID**: {skill_id}",
            f"**描述**: {metadata['description']}",
            f"**版本**: {metadata.get('version', 'Unknown')}",
            f"**作者**: {metadata.get('author', 'Unknown')}",
        ]

        if metadata.get('tags'):
            lines.append(f"**标签**: {', '.join(metadata['tags'])}")

        lines.append("")
        lines.append("### Skill 内容")
        lines.append(content)

        # 添加文件列表
        lines.append("")
        lines.append("### 打包资源文件")
        for file_info in files:
            file_type = "📄" if file_info['is_md'] else "📦"
            lines.append(f"{file_type} {file_info['path']} ({file_info['size']} bytes)")

        # 加载 references（按需加载）
        references_content = self._skills_middleware.load_references_for_context(skill_id, reference_files)
        if references_content and not references_content.startswith("错误") and not references_content.startswith("Skill"):
            lines.append("")
            lines.append(references_content)

        return "\n".join(lines)
