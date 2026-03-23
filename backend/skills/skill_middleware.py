"""
Skills Middleware
实现渐进式披露的 AgentMiddleware
"""
from typing import Dict, Any, Optional, List
from langchain_core.messages import BaseMessage
from .skill_scanner import SkillScanner


class SkillsMiddleware:
    """
    Skills 中间件，实现渐进式披露机制

    渐进式披露分为三层：
    1. 元数据层：只提供 skill 的基本信息（名称、描述）
    2. 详情层：提供 skill 的完整文档内容
    3. 扩展层：提供 skill 的完整代码和资源
    """

    def __init__(self, skills_base_path: str = "./skills/installed"):
        """
        初始化 SkillsMiddleware

        Args:
            skills_base_path: skills 基础目录路径
        """
        self.skill_scanner = SkillScanner(skills_base_path)
        self._disclosure_level: str = "metadata"  # metadata, body, extended

    def set_disclosure_level(self, level: str):
        """
        设置披露级别

        Args:
            level: 披露级别（metadata, body, extended）
        """
        if level not in ["metadata", "body", "extended"]:
            raise ValueError(f"Invalid disclosure level: {level}")
        self._disclosure_level = level
        print(f"[DEBUG] skill_middleware.py - 披露级别设置为: {level}")

    def get_disclosure_level(self) -> str:
        """获取当前披露级别"""
        return self._disclosure_level

    def get_skills_metadata(self, skill_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        获取 skills 的元数据（第一层披露）

        Args:
            skill_ids: skill ID 列表，如果为 None 则返回所有 skills

        Returns:
            skill 元数据列表
        """
        all_skills = self.skill_scanner.scan_skills()

        if skill_ids:
            skills = [skill for skill in all_skills if skill["skill_id"] in skill_ids]
        else:
            skills = all_skills

        # 只返回元数据，不返回完整内容
        metadata_list = []
        for skill in skills:
            metadata = {
                "skill_id": skill["skill_id"],
                "name": skill["metadata"]["name"],
                "description": skill["metadata"]["description"],
                "version": skill["metadata"].get("version", "Unknown"),
                "author": skill["metadata"].get("author", "Unknown"),
                "tags": skill["metadata"].get("tags", []),
                "full_path": skill["full_path"]
            }
            metadata_list.append(metadata)

        return metadata_list

    def get_skill_details(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """
        获取 skill 的详情（第二层披露）

        Args:
            skill_id: skill ID

        Returns:
            skill 详情，如果不存在返回 None
        """
        skill = self.skill_scanner.get_skill_by_id(skill_id)
        if not skill:
            return None

        # 返回元数据和内容
        details = {
            "skill_id": skill["skill_id"],
            "metadata": skill["metadata"],
            "content": skill["content"],
            "full_path": skill["full_path"]
        }

        return details

    def get_skill_extended(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """
        获取 skill 的扩展信息（第三层披露）

        Args:
            skill_id: skill ID

        Returns:
            skill 扩展信息，如果不存在返回 None
        """
        skill = self.skill_scanner.get_skill_by_id(skill_id)
        if not skill:
            return None

        # 返回完整信息（包括文件列表等）
        from pathlib import Path

        skill_dir = Path(skill["full_path"])
        files = []

        # 列出 skill 目录下的所有文件
        for file_path in skill_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(skill_dir)
                files.append({
                    "path": str(relative_path),
                    "size": file_path.stat().st_size,
                    "is_md": file_path.suffix == ".md"
                })

        extended = {
            "skill_id": skill["skill_id"],
            "metadata": skill["metadata"],
            "content": skill["content"],
            "scripts": skill.get("scripts", []),
            "references": skill.get("references", []),
            "files": files,
            "full_path": skill["full_path"]
        }

        return extended

    def get_skills_for_agent(self, enabled_skill_ids: List[str]) -> List[Dict[str, Any]]:
        """
        获取 agent 可用的 skills（根据当前披露级别）

        Args:
            enabled_skill_ids: 启用的 skill ID 列表

        Returns:
            skills 列表
        """
        if self._disclosure_level == "metadata":
            return self.get_skills_metadata(enabled_skill_ids)
        elif self._disclosure_level == "body":
            skills = []
            for skill_id in enabled_skill_ids:
                details = self.get_skill_details(skill_id)
                if details:
                    skills.append(details)
            return skills
        elif self._disclosure_level == "extended":
            skills = []
            for skill_id in enabled_skill_ids:
                extended = self.get_skill_extended(skill_id)
                if extended:
                    skills.append(extended)
            return skills
        else:
            return []

    def format_skills_for_prompt(self, enabled_skill_ids: List[str]) -> str:
        """
        格式化 skills 为提示词文本

        Args:
            enabled_skill_ids: 启用的 skill ID 列表

        Returns:
            格式化的提示词文本
        """
        skills = self.get_skills_for_agent(enabled_skill_ids)

        if not skills:
            return "当前没有启用的 skills。"

        if self._disclosure_level == "metadata":
            # 元数据层：明确说明 Skills 的使用方式
            lines = [
                "## 可用的 Skills（注意：Skills 不是 Tools，使用方式不同）",
                "",
                "**重要说明**：",
                "Skills 是特殊的资源，需要通过特定的工具来使用：",
                "",
                "**使用 Skills 的正确方式**：",
                "如果你想了解某个 Skill 的功能，请使用 `load_skill` 工具加载 Skill 的详细信息"
                "**可用的 Skills 列表**：",
                ""
            ]
            for skill in skills:
                lines.append(f"### {skill['name']}")
                lines.append(f"- **描述**: {skill['description']}")
                lines.append(f"- **Skill ID**: `{skill['skill_id']}`")
                if skill['tags']:
                    lines.append(f"- **标签**: {', '.join(skill['tags'])}")
                lines.append("")
            return "\n".join(lines)

        elif self._disclosure_level == "body":
            # 详情层：显示完整文档
            lines = ["可用的 Skills（详情层）："]
            for skill in skills:
                lines.append(f"\n## {skill['metadata']['name']}")
                lines.append(f"**描述**: {skill['metadata']['description']}")
                lines.append(f"**版本**: {skill['metadata'].get('version', 'Unknown')}")
                lines.append(f"\n{skill['content']}")
            return "\n".join(lines)

        elif self._disclosure_level == "extended":
            # 扩展层：显示完整信息
            lines = ["可用的 Skills（扩展层）："]
            for skill in skills:
                lines.append(f"\n## {skill['metadata']['name']}")
                lines.append(f"**描述**: {skill['metadata']['description']}")
                lines.append(f"**版本**: {skill['metadata'].get('version', 'Unknown')}")
                lines.append(f"\n{skill['content']}")
                lines.append(f"\n**文件列表**:")
                for file_info in skill['files']:
                    lines.append(f"- {file_info['path']} ({file_info['size']} bytes)")
            return "\n".join(lines)

        return ""

    def load_skill_for_context(self, skill_id: str, disclosure_level: str = "body") -> Optional[Dict[str, Any]]:
        """
        加载 Skill 内容用于注入到 Agent 上下文（支持三级渐进式披露）

        Args:
            skill_id: Skill ID
            disclosure_level: 披露级别（metadata, body, extended）

        Returns:
            包含 Skill 内容的字典，如果 Skill 不存在返回 None
        """
        if disclosure_level not in ["metadata", "body", "extended"]:
            print(f"[ERROR] skill_middleware.py - 无效的披露级别: {disclosure_level}")
            return None

        print(f"[DEBUG] skill_middleware.py - 加载 Skill: {skill_id}, 披露级别: {disclosure_level}")

        if disclosure_level == "metadata":
            # 元数据层：只返回元数据
            skills = self.get_skills_metadata([skill_id])
            if not skills:
                return None
            return {
                "skill_id": skill_id,
                "disclosure_level": "metadata",
                "metadata": skills[0],
                "context_text": self._format_metadata_for_context(skills[0])
            }

        elif disclosure_level == "body":
            # 详情层：返回元数据和内容
            skill = self.get_skill_details(skill_id)
            if not skill:
                return None
            return {
                "skill_id": skill_id,
                "disclosure_level": "body",
                "metadata": skill["metadata"],
                "content": skill["content"],
                "context_text": self._format_body_for_context(skill)
            }

        elif disclosure_level == "extended":
            # 扩展层：返回完整信息
            skill = self.get_skill_extended(skill_id)
            if not skill:
                return None
            return {
                "skill_id": skill_id,
                "disclosure_level": "extended",
                "metadata": skill["metadata"],
                "content": skill["content"],
                "files": skill["files"],
                "context_text": self._format_extended_for_context(skill)
            }

        return None

    def _format_metadata_for_context(self, metadata: Dict[str, Any]) -> str:
        """格式化元数据为上下文文本"""
        lines = [
            f"## {metadata['name']}",
            f"**Skill ID**: {metadata['skill_id']}",
            f"**描述**: {metadata['description']}",
            f"**版本**: {metadata['version']}",
            f"**作者**: {metadata['author']}",
        ]
        if metadata['tags']:
            lines.append(f"**标签**: {', '.join(metadata['tags'])}")
        return "\n".join(lines)

    def _format_body_for_context(self, skill: Dict[str, Any]) -> str:
        """格式化详情为上下文文本"""
        metadata = skill["metadata"]
        content = skill["content"]
        lines = [
            f"## {metadata['name']}",
            f"**Skill ID**: {skill['skill_id']}",
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

    def _format_extended_for_context(self, skill: Dict[str, Any]) -> str:
        """格式化扩展信息为上下文文本"""
        metadata = skill["metadata"]
        content = skill["content"]
        files = skill["files"]
        lines = [
            f"## {metadata['name']}",
            f"**Skill ID**: {skill['skill_id']}",
            f"**描述**: {metadata['description']}",
            f"**版本**: {metadata.get('version', 'Unknown')}",
            f"**作者**: {metadata.get('author', 'Unknown')}",
        ]
        if metadata.get('tags'):
            lines.append(f"**标签**: {', '.join(metadata['tags'])}")
        lines.append("")
        lines.append("### Skill 内容")
        lines.append(content)
        lines.append("")
        lines.append("### 打包资源文件")
        for file_info in files:
            file_type = "📄" if file_info['is_md'] else "📦"
            lines.append(f"{file_type} {file_info['path']} ({file_info['size']} bytes)")
        return "\n".join(lines)

    def load_references_for_context(self, skill_id: str, reference_files: List[str] = None) -> str:
        """
        加载参考文档到上下文（按需加载）

        Args:
            skill_id: Skill ID
            reference_files: 要加载的参考文件列表，如果为 None 则加载所有

        Returns:
            格式化的参考文档内容（将被加载到上下文）
        """
        skill = self.skill_scanner.get_skill_by_id(skill_id)
        if not skill:
            return f"错误：未找到 Skill '{skill_id}'"

        from pathlib import Path

        skill_dir = Path(skill["full_path"])
        references_dir = skill_dir / "references"

        if not references_dir.exists() or not references_dir.is_dir():
            return f"Skill '{skill_id}' 没有 references 文件夹"

        # 确定要加载的文件列表
        available_refs = skill.get("references", [])
        if reference_files is None:
            # 加载所有参考文件
            files_to_load = available_refs
        else:
            # 加载指定的参考文件
            files_to_load = [f for f in reference_files if f in available_refs]

        if not files_to_load:
            return f"Skill '{skill_id}' 没有可加载的参考文档"

        # 加载并格式化参考文档
        lines = [
            f"## {skill['metadata']['name']} - 参考文档",
            f"**Skill ID**: {skill_id}",
            ""
        ]

        for ref_file in files_to_load:
            ref_path = references_dir / ref_file
            if ref_path.exists() and ref_path.is_file():
                try:
                    with open(ref_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    lines.append(f"### {ref_file}")
                    lines.append("")
                    lines.append(content)
                    lines.append("")
                    lines.append("---")
                    lines.append("")

                except Exception as e:
                    lines.append(f"### {ref_file}")
                    lines.append(f"错误：无法读取文件 - {str(e)}")
                    lines.append("")

        return "\n".join(lines)


# 全局实例
skills_middleware = SkillsMiddleware()
