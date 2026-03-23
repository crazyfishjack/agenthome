"""
SkillsMP Parser
解析标准 SkillsMP 格式的 SKILL.md 文件（YAML Front Matter）
"""
import re
from typing import Optional, Dict, Any
from pathlib import Path


class SkillParser:
    """解析 SkillsMP 格式的 SKILL.md 文件"""

    @staticmethod
    def parse_skill_md(skill_path: Path) -> Optional[Dict[str, Any]]:
        """
        解析 SKILL.md 文件，提取元数据和内容

        Args:
            skill_path: SKILL.md 文件的路径

        Returns:
            包含元数据和内容的字典，如果解析失败返回 None
        """
        if not skill_path.exists():
            print(f"[WARNING] skill_parser.py - SKILL.md 文件不存在: {skill_path}")
            return None

        try:
            with open(skill_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析 YAML Front Matter
            front_matter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)

            if not front_matter_match:
                print(f"[WARNING] skill_parser.py - SKILL.md 文件格式不正确（缺少 YAML Front Matter）: {skill_path}")
                return None

            yaml_content = front_matter_match.group(1)
            markdown_content = front_matter_match.group(2)

            # 解析 YAML 元数据
            try:
                import yaml
                metadata = yaml.safe_load(yaml_content) if yaml_content.strip() else {}
            except ImportError:
                print(f"[ERROR] skill_parser.py - 未安装 pyyaml 库，无法解析 YAML Front Matter")
                return None
            except Exception as e:
                print(f"[ERROR] skill_parser.py - 解析 YAML Front Matter 失败: {e}")
                return None

            # 提取 skill 目录名称作为 skill_id
            skill_id = skill_path.parent.name

            # 构建返回数据
            result = {
                "skill_id": skill_id,
                "metadata": metadata,
                "content": markdown_content,
                "full_path": str(skill_path.parent.absolute())
            }

            print(f"[DEBUG] skill_parser.py - 成功解析 SKILL.md: {skill_id}")
            return result

        except Exception as e:
            print(f"[ERROR] skill_parser.py - 读取 SKILL.md 文件失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def get_skill_metadata(skill_path: Path) -> Optional[Dict[str, Any]]:
        """
        只获取 SKILL.md 的元数据（不包含内容）

        Args:
            skill_path: SKILL.md 文件的路径

        Returns:
            元数据字典，如果解析失败返回 None
        """
        result = SkillParser.parse_skill_md(skill_path)
        if result:
            return result["metadata"]
        return None

    @staticmethod
    def validate_skill_metadata(metadata: Dict[str, Any]) -> bool:
        """
        验证 skill 元数据是否符合 SkillsMP 标准

        Args:
            metadata: 元数据字典

        Returns:
            是否有效
        """
        # 检查必需字段
        required_fields = ["name", "description"]
        for field in required_fields:
            if field not in metadata:
                print(f"[WARNING] skill_parser.py - 元数据缺少必需字段: {field}")
                return False

        # 检查字段类型
        if not isinstance(metadata["name"], str) or not metadata["name"].strip():
            print(f"[WARNING] skill_parser.py - name 字段必须是非空字符串")
            return False

        if not isinstance(metadata["description"], str) or not metadata["description"].strip():
            print(f"[WARNING] skill_parser.py - description 字段必须是非空字符串")
            return False

        # version 字段是可选的，但如果存在则验证格式
        version = metadata.get("version")
        if version is not None:
            if not isinstance(version, str) or not version.strip():
                print(f"[WARNING] skill_parser.py - version 字段必须是非空字符串")
                return False

        return True
