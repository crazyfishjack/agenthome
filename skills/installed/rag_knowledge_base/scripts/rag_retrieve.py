"""
RAG检索召回重排脚本
执行完整的召回+重排检索流程，支持滑动窗口召回
"""

import sys
import json
import argparse
import os
from pathlib import Path
from typing import List, Dict, Any
import httpx

# 尝试加载 .env 文件（从项目根目录）
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent.parent.parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    pass


def safe_json_print(data: dict):
    """
    安全地输出 JSON 数据，处理 Windows 下的编码问题
    """
    try:
        output = json.dumps(data, ensure_ascii=False, indent=2)
        print(output)
    except UnicodeEncodeError:
        # 如果 UTF-8 输出失败，使用 ASCII 转义
        output = json.dumps(data, ensure_ascii=True, indent=2)
        print(output)
    except Exception as e:
        # 最后的备选方案
        print(json.dumps({
            "success": False,
            "message": f"输出错误: {str(e)}",
            "query": data.get("query", ""),
            "recall_count": 0,
            "rerank_count": 0,
            "results": []
        }, ensure_ascii=True))


# 配置
EMBEDDING_API_KEY = os.environ.get("EMBEDDING_API_KEY", "")
EMBEDDING_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
EMBEDDING_MODEL = "text-embedding-v4"

RERANK_API_KEY = os.environ.get("RERANK_API_KEY", "")
RERANK_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
RERANK_MODEL = "qwen3-vl-rerank"

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
CHROMA_DB_PATH = PROJECT_ROOT / "rag" / "chroma_db"


class EmbeddingGenerator:
    """Embedding生成类"""

    @staticmethod
    def generate_embedding(text: str) -> List[float]:
        """
        生成单个文本的embedding向量
        """
        headers = {
            'Authorization': f'Bearer {EMBEDDING_API_KEY}',
            'Content-Type': 'application/json'
        }

        data = {
            'model': EMBEDDING_MODEL,
            'input': text,
            'encoding_format': 'float'
        }

        try:
            response = httpx.post(
                EMBEDDING_API_URL,
                headers=headers,
                json=data,
                timeout=30.0
            )
            response.raise_for_status()

            result = response.json()
            return result['data'][0]['embedding']

        except Exception as e:
            raise Exception(f"生成embedding失败: {e}")


class Reranker:
    """重排序类"""

    @staticmethod
    def rerank(query: str, documents: List[str], top_n: int = 3) -> List[Dict[str, Any]]:
        """
        使用Rerank模型对文档重新排序
        返回排序后的文档索引和分数
        """
        headers = {
            'Authorization': f'Bearer {RERANK_API_KEY}',
            'Content-Type': 'application/json'
        }

        data = {
            'model': RERANK_MODEL,
            'input': {
                'query': query,
                'documents': documents
            },
            'parameters': {
                'top_n': top_n
            }
        }

        try:
            response = httpx.post(
                RERANK_API_URL,
                headers=headers,
                json=data,
                timeout=30.0
            )
            response.raise_for_status()

            result = response.json()

            # 解析返回结果
            if 'output' in result and 'results' in result['output']:
                rerank_results = result['output']['results']
                # 转换为统一格式
                return [
                    {
                        'index': item['index'],
                        'relevance_score': item['relevance_score']
                    }
                    for item in rerank_results
                ]
            else:
                raise Exception(f"返回结果格式错误: {result}")

        except Exception as e:
            raise Exception(f"重排序失败: {e}")


class VectorDatabase:
    """向量数据库管理类"""

    def __init__(self, db_path: Path):
        try:
            import chromadb
        except ImportError:
            raise ImportError("需要安装 chromadb 库: pip install chromadb")

        self.client = chromadb.PersistentClient(path=str(db_path))
        self.collection = self.client.get_or_create_collection(
            name="rag_knowledge_base",
            metadata={"hnsw:space": "cosine"}
        )

    def query_by_documents(
        self,
        query_embedding: List[float],
        document_names: List[str],
        top_k: int = 20
    ) -> Dict[str, Any]:
        """
        在指定文档中检索
        """
        try:
            # 构建过滤条件：doc_name在document_names列表中
            # Chroma的where只支持简单的条件，不支持IN操作
            # 我们需要分别查询每个文档，然后合并结果

            all_results = {
                'ids': [],
                'distances': [],
                'metadatas': [],
                'documents': []
            }

            for doc_name in document_names:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    where={"doc_name": doc_name}
                )

                if results['ids'] and results['ids'][0]:
                    all_results['ids'].extend(results['ids'][0])
                    all_results['distances'].extend(results['distances'][0])
                    all_results['metadatas'].extend(results['metadatas'][0])
                    all_results['documents'].extend(results['documents'][0])

            # 按距离排序（距离越小越相似）
            if all_results['ids']:
                sorted_indices = sorted(
                    range(len(all_results['distances'])),
                    key=lambda i: all_results['distances'][i]
                )

                # 只返回top_k个结果
                top_indices = sorted_indices[:top_k]

                return {
                    'ids': [all_results['ids'][i] for i in top_indices],
                    'distances': [all_results['distances'][i] for i in top_indices],
                    'metadatas': [all_results['metadatas'][i] for i in top_indices],
                    'documents': [all_results['documents'][i] for i in top_indices]
                }

            return {
                'ids': [],
                'distances': [],
                'metadatas': [],
                'documents': []
            }

        except Exception as e:
            raise Exception(f"向量检索失败: {e}")

    def get_adjacent_chunks(
        self,
        category: str,
        doc_name: str,
        chunk_index: int
    ) -> Dict[str, str]:
        """
        获取指定chunk的相邻chunk（上一个和下一个）
        """
        try:
            # 查询该分类的所有chunk
            results = self.collection.get(
                where={"category": category}
            )

            previous_chunk = None
            next_chunk = None

            if results['metadatas']:
                # 先过滤出指定文档的chunk
                doc_chunks = [
                    (metadata, doc)
                    for metadata, doc in zip(results['metadatas'], results['documents'])
                    if metadata.get('doc_name') == doc_name
                ]

                # 按chunk_index排序
                sorted_chunks = sorted(
                    doc_chunks,
                    key=lambda x: x[0]['chunk_index']
                )

                for idx, (metadata, doc) in enumerate(sorted_chunks):
                    if metadata['chunk_index'] == chunk_index:
                        # 找到当前chunk，获取相邻chunk
                        if idx > 0:
                            previous_chunk = sorted_chunks[idx - 1][1]
                        if idx < len(sorted_chunks) - 1:
                            next_chunk = sorted_chunks[idx + 1][1]
                        break

            return {
                'previous': previous_chunk,
                'next': next_chunk
            }

        except Exception as e:
            raise Exception(f"获取相邻chunk失败: {e}")


def deduplicate_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    去重处理：如果返回的内容有重复信息，优先使用时间最新的chunk
    根据doc_update_time排序
    """
    if not results:
        return results

    # 按doc_update_time降序排序（最新的在前）
    sorted_results = sorted(
        results,
        key=lambda x: x.get('doc_update_time', ''),
        reverse=True
    )

    # 简单去重：如果chunk_content相似度很高，只保留第一个
    # 这里使用简单的字符串长度和开头字符来判断
    seen_contents = set()
    deduplicated = []

    for result in sorted_results:
        content = result.get('chunk_content', '')
        # 使用内容的前50个字符作为去重标识
        content_key = content[:50] if len(content) > 50 else content

        if content_key not in seen_contents:
            seen_contents.add(content_key)
            deduplicated.append(result)

    return deduplicated


def main():
    parser = argparse.ArgumentParser(description='RAG检索召回重排')
    parser.add_argument('--documents', type=str, required=True,
                        help='文档名称列表，多个文档用逗号分隔')
    parser.add_argument('--query', type=str, required=True,
                        help='检索查询文本')
    parser.add_argument('--recall_top_k', type=int, default=20,
                        help='召回返回的chunk数量（默认20）')
    parser.add_argument('--rerank_top_n', type=int, default=3,
                        help='重排返回的chunk数量（默认3）')

    args = parser.parse_args()

    # 支持中英文逗号分隔文档名称
    import re
    documents = [doc.strip() for doc in re.split(r'[,，]', args.documents) if doc.strip()]
    query = args.query
    recall_top_k = args.recall_top_k
    rerank_top_n = args.rerank_top_n

    try:
        # 1. 生成查询的embedding
        print(f"正在生成查询embedding...")
        query_embedding = EmbeddingGenerator.generate_embedding(query)

        # 2. 召回阶段：在指定文档中检索
        print(f"正在召回阶段，在 {len(documents)} 个文档中检索...")
        db = VectorDatabase(CHROMA_DB_PATH)
        recall_results = db.query_by_documents(
            query_embedding=query_embedding,
            document_names=documents,
            top_k=recall_top_k
        )

        if not recall_results['ids']:
            result = {
                "success": True,
                "message": "未找到相关内容",
                "query": query,
                "recall_count": 0,
                "rerank_count": 0,
                "results": []
            }
            safe_json_print(result)
            return

        print(f"召回阶段完成，返回 {len(recall_results['ids'])} 个chunk")

        # 3. 重排阶段：使用Rerank模型重新排序
        print(f"正在重排阶段...")
        recall_documents = recall_results['documents']
        rerank_results = Reranker.rerank(query, recall_documents, top_n=rerank_top_n)

        print(f"重排阶段完成，返回 {len(rerank_results)} 个chunk")

        # 4. 构建最终结果
        final_results = []
        for rerank_item in rerank_results:
            idx = rerank_item['index']
            rerank_score = rerank_item['relevance_score']

            metadata = recall_results['metadatas'][idx]
            chunk_content = recall_results['documents'][idx]
            recall_distance = recall_results['distances'][idx]
            recall_score = 1 - recall_distance  # 转换为相似度分数

            # 5. 滑动窗口：获取相邻chunk
            adjacent_chunks = db.get_adjacent_chunks(
                category=metadata['category'],
                doc_name=metadata['doc_name'],
                chunk_index=metadata['chunk_index']
            )

            result_item = {
                "chunk_id": metadata['chunk_id'],
                "category": metadata['category'],
                "doc_name": metadata['doc_name'],
                "doc_update_time": metadata['doc_update_time'],
                "chunk_content": chunk_content,
                "chunk_index": metadata['chunk_index'],
                "recall_score": round(recall_score, 3),
                "rerank_score": round(rerank_score, 3),
                "context_chunks": {
                    "previous": adjacent_chunks['previous'],
                    "current": chunk_content,
                    "next": adjacent_chunks['next']
                }
            }

            final_results.append(result_item)

        # 6. 去重处理
        final_results = deduplicate_results(final_results)

        # 返回结果
        result = {
            "success": True,
            "message": f"检索成功，返回 {len(final_results)} 个相关chunk",
            "query": query,
            "recall_count": len(recall_results['ids']),
            "rerank_count": len(final_results),
            "results": final_results
        }

        safe_json_print(result)

    except Exception as e:
        result = {
            "success": False,
            "message": f"检索失败: {str(e)}",
            "query": query,
            "recall_count": 0,
            "rerank_count": 0,
            "results": []
        }
        safe_json_print(result)


if __name__ == "__main__":
    main()
