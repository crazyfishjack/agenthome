"""
Skills Scanner
扫描 skills 目录，解析 SKILL.md 元数据
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from .skill_parser import SkillParser


class SkillScanner:
    """扫描 skills 目录，解析 SKILL.md 元数据"""

    def __init__(self, skills_base_path: str = "./skills/installed"):
        """
        初始化 SkillScanner

        Args:
            skills_base_path: skills 基础目录路径
        """
        self.skills_base_path = Path(skills_base_path).absolute()
        self._skills_cache: Optional[List[Dict[str, Any]]] = None

    def scan_skills(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        扫描 skills 目录，返回所有 skill 的元数据

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            skill 元数据列表
        """
        if not force_refresh and self._skills_cache is not None:
            print(f"[DEBUG] skill_scanner.py - 使用缓存的 skills 列表")
            return self._skills_cache

        if not self.skills_base_path.exists():
            print(f"[WARNING] skill_scanner.py - skills 目录不存在: {self.skills_base_path}")
            self._skills_cache = []
            return []

        skills = []

        # 遍历 skills 目录
        for skill_dir in self.skills_base_path.iterdir():
            if not skill_dir.is_dir():
                continue

            # 检查是否存在 SKILL.md 文件
            skill_md_path = skill_dir / "SKILL.md"
            if not skill_md_path.exists():
                print(f"[WARNING] skill_scanner.py - skill 目录缺少 SKILL.md: {skill_dir.name}")
                continue

            # 解析 SKILL.md
            skill_data = SkillParser.parse_skill_md(skill_md_path)
            if not skill_data:
                continue

            # 验证元数据
            if not SkillParser.validate_skill_metadata(skill_data["metadata"]):
                print(f"[WARNING] skill_scanner.py - skill 元数据无效: {skill_dir.name}")
                continue

            # 扫描 scripts/ 文件夹（只记录文件名，不加载内容）
            scripts_dir = skill_dir / "scripts"
            scripts_files = []
            if scripts_dir.exists() and scripts_dir.is_dir():
                for script_file in scripts_dir.glob("*.py"):
                    if script_file.name != "__init__.py":
                        scripts_files.append(script_file.name)
                print(f"[DEBUG] skill_scanner.py - 找到 {len(scripts_files)} 个脚本文件: {scripts_dir.name}")

            # 扫描 references/ 文件夹（只记录文件名，不加载内容）
            references_dir = skill_dir / "references"
            references_files = []
            if references_dir.exists() and references_dir.is_dir():
                for ref_file in references_dir.glob("*.md"):
                    references_files.append(ref_file.name)
                print(f"[DEBUG] skill_scanner.py - 找到 {len(references_files)} 个参考文档: {references_dir.name}")

            # 添加 scripts 和 references 信息到 skill_data
            skill_data["scripts"] = scripts_files
            skill_data["references"] = references_files

            # 添加到列表
            skills.append(skill_data)

        print(f"[DEBUG] skill_scanner.py - 扫描完成，找到 {len(skills)} 个 skills")
        self._skills_cache = skills
        return skills

    def get_skill_by_id(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """
        根据 skill_id 获取 skill 元数据

        Args:
            skill_id: skill ID（目录名称）

        Returns:
            skill 元数据，如果不存在返回 None
        """
        skills = self.scan_skills()
        for skill in skills:
            if skill["skill_id"] == skill_id:
                return skill
        return None

    def get_skill_names(self) -> List[str]:
        """
        获取所有 skill 的名称列表

        Returns:
            skill 名称列表
        """
        skills = self.scan_skills()
        return [skill["metadata"]["name"] for skill in skills]

    def get_skill_ids(self) -> List[str]:
        """
        获取所有 skill 的 ID 列表

        Returns:
            skill ID 列表
        """
        skills = self.scan_skills()
        return [skill["skill_id"] for skill in skills]

    def refresh_cache(self):
        """刷新缓存"""
        self._skills_cache = None
        print(f"[DEBUG] skill_scanner.py - 缓存已刷新")


# 全局实例
skill_scanner = SkillScanner()
