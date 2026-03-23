"""
查询知识库信息脚本
用于返回所有分类，或返回指定分类的目录索引文件内容
"""

import sys
import json
import argparse
from pathlib import Path


def get_knowledge_base_path():
    """获取知识库根目录路径"""
    # 获取项目根目录（从scripts目录向上5级）
    project_root = Path(__file__).parent.parent.parent.parent.parent
    knowledge_base_path = project_root / "rag" / "rag_document_lib"
    return knowledge_base_path


def get_all_categories():
    """
    获取所有分类的基本信息
    返回：分类列表，每个分类包含名称、文档数量、更新时间
    """
    knowledge_base_path = get_knowledge_base_path()
    categories = []

    if not knowledge_base_path.exists():
        return {
            "success": False,
            "message": f"知识库目录不存在: {knowledge_base_path}",
            "categories": []
        }

    # 遍历知识库目录下的所有子目录
    for category_dir in knowledge_base_path.iterdir():
        if category_dir.is_dir():
            index_file = category_dir / "index.json"

            if index_file.exists():
                try:
                    with open(index_file, 'r', encoding='utf-8') as f:
                        index_data = json.load(f)

                    category_info = {
                        "category_name": index_data.get("category_name", category_dir.name),
                        "document_count": len(index_data.get("documents", [])),
                        "update_time": index_data.get("update_time", "")
                    }
                    categories.append(category_info)
                except json.JSONDecodeError as e:
                    # 如果index.json格式错误，跳过该分类
                    continue
                except Exception as e:
                    # 其他错误，跳过该分类
                    continue
            else:
                # 如果没有index.json文件，仍然列出该分类
                category_info = {
                    "category_name": category_dir.name,
                    "document_count": 0,
                    "update_time": "无索引文件"
                }
                categories.append(category_info)

    return {
        "success": True,
        "message": f"成功获取 {len(categories)} 个分类信息",
        "categories": categories
    }


def get_category_documents(category_name):
    """
    获取指定分类的目录索引文件内容
    参数：
        category_name: 分类名称
    返回：分类信息和文档列表
    """
    knowledge_base_path = get_knowledge_base_path()
    category_path = knowledge_base_path / category_name

    # 检查分类目录是否存在
    if not category_path.exists():
        return {
            "success": False,
            "message": f"分类目录不存在: {category_name}",
            "category": category_name,
            "documents": []
        }

    if not category_path.is_dir():
        return {
            "success": False,
            "message": f"分类路径不是目录: {category_name}",
            "category": category_name,
            "documents": []
        }

    # 检查index.json文件是否存在
    index_file = category_path / "index.json"
    if not index_file.exists():
        return {
            "success": False,
            "message": f"分类索引文件不存在: {category_name}/index.json",
            "category": category_name,
            "documents": []
        }

    # 读取index.json文件
    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "message": f"索引文件格式错误: {str(e)}",
            "category": category_name,
            "documents": []
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"读取索引文件失败: {str(e)}",
            "category": category_name,
            "documents": []
        }

    # 验证索引文件结构
    if "documents" not in index_data:
        return {
            "success": False,
            "message": "索引文件缺少documents字段",
            "category": category_name,
            "documents": []
        }

    # 提取文档信息（不包含doc_path，只返回基本信息）
    documents = []
    for doc in index_data.get("documents", []):
        doc_info = {
            "doc_name": doc.get("doc_name", ""),
            "doc_type": doc.get("doc_type", ""),
            "update_time": doc.get("update_time", ""),
            "summary": doc.get("summary", "")
        }
        documents.append(doc_info)

    return {
        "success": True,
        "message": f"成功获取分类 '{category_name}' 的 {len(documents)} 个文档信息",
        "category": index_data.get("category_name", category_name),
        "category_update_time": index_data.get("update_time", ""),
        "documents": documents
    }


def main():
    parser = argparse.ArgumentParser(
        description='查询知识库信息',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 查询所有分类
  python query_knowledge_base.py

  # 查询指定分类的文档列表
  python query_knowledge_base.py --category 金融分析
        """
    )
    parser.add_argument('--category', type=str, required=False,
                        help='分类名称（可选，不提供则返回所有分类）')

    args = parser.parse_args()
    category = args.category

    # 根据是否有category参数执行不同逻辑
    if category:
        # 查询指定分类
        result = get_category_documents(category)
    else:
        # 查询所有分类
        result = get_all_categories()

    # 输出JSON格式结果
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
