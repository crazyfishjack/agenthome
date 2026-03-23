"""
Composite Backend
支持多目录路由的 Backend 实现
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
from deepagents.backends import FilesystemBackend
from deepagents.backends.protocol import FileDownloadResponse, EditResult, WriteResult, FileUploadResponse


class CompositeBackend:
    """
    复合 Backend，支持多目录路由

    路由规则：
    - /skills/* -> skills 目录
    - /conversation_history/* -> data/conversation_history 目录
    - /output/* -> output 目录
    - 其他路径 -> output 目录（默认）
    """

    def __init__(
        self,
        skills_dir: str,
        output_dir: str,
        conversation_history_dir: Optional[str] = None,
        virtual_mode: bool = True
    ):
        """
        初始化 CompositeBackend

        Args:
            skills_dir: skills 目录路径
            output_dir: output 目录路径
            conversation_history_dir: 对话历史记录目录路径，默认为 None（使用 output_dir/conversation_history）
            virtual_mode: 是否使用虚拟模式
        """
        self.skills_dir = Path(skills_dir).absolute()
        self.output_dir = Path(output_dir).absolute()
        
        # 设置对话历史记录目录
        if conversation_history_dir:
            self.conversation_history_dir = Path(conversation_history_dir).absolute()
        else:
            # 默认使用项目根目录下的 data/conversation_history
            # 从 output_dir 推断项目根目录（output 目录在项目根目录下）
            project_root = self.output_dir.parent  # output -> project_root
            self.conversation_history_dir = project_root / "data" / "conversation_history"
        
        self.virtual_mode = virtual_mode

        # 创建三个 FilesystemBackend 实例
        self.skills_backend = FilesystemBackend(
            root_dir=str(self.skills_dir),
            virtual_mode=virtual_mode
        )
        self.output_backend = FilesystemBackend(
            root_dir=str(self.output_dir),
            virtual_mode=virtual_mode
        )
        self.conversation_history_backend = FilesystemBackend(
            root_dir=str(self.conversation_history_dir),
            virtual_mode=virtual_mode
        )

        print(f"[DEBUG] composite_backend.py - CompositeBackend 初始化完成")
        print(f"[DEBUG] composite_backend.py - skills_dir: {self.skills_dir}")
        print(f"[DEBUG] composite_backend.py - output_dir: {self.output_dir}")
        print(f"[DEBUG] composite_backend.py - conversation_history_dir: {self.conversation_history_dir}")

    def _route_path(self, path: str) -> FilesystemBackend:
        """
        根据路径路由到相应的 Backend

        Args:
            path: 文件路径

        Returns:
            对应的 FilesystemBackend 实例
        """
        # 规范化路径
        normalized_path = path.replace("\\", "/")

        # 路由规则
        if normalized_path.startswith("/skills/") or normalized_path.startswith("skills/"):
            print(f"[DEBUG] composite_backend.py - 路由到 skills_backend: {path}")
            return self.skills_backend
        elif normalized_path.startswith("/conversation_history/") or normalized_path.startswith("conversation_history/"):
            print(f"[DEBUG] composite_backend.py - 路由到 conversation_history_backend: {path}")
            return self.conversation_history_backend
        else:
            print(f"[DEBUG] composite_backend.py - 路由到 output_backend: {path}")
            return self.output_backend

    def read(self, path: str, offset: int = 0, limit: int = 2000) -> str:
        """
        读取文件内容

        Args:
            path: 文件路径
            offset: 从哪一行开始读取（0索引），默认为0
            limit: 最多读取多少行，默认为2000

        Returns:
            文件内容
        """
        backend = self._route_path(path)
        return backend.read(path, offset=offset, limit=limit)

    def write(self, path: str, content: str) -> WriteResult:
        """
        写入文件内容

        Args:
            path: 文件路径
            content: 文件内容

        Returns:
            WriteResult 对象
        """
        backend = self._route_path(path)
        return backend.write(path, content)

    def ls_info(self, path: str = ""):
        """
        列出目录中的文件

        Args:
            path: 目录路径

        Returns:
            FileInfo 对象列表
        """
        backend = self._route_path(path)
        return backend.ls_info(path)

    def glob_info(self, pattern: str, path: str = "/"):
        """
        查找匹配的文件

        Args:
            pattern: 文件匹配模式
            path: 搜索路径，默认为根目录

        Returns:
            FileInfo 对象列表
        """
        backend = self._route_path(path)
        return backend.glob_info(pattern, path=path)

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult:
        """
        编辑文件内容（替换指定字符串）

        Args:
            file_path: 文件路径
            old_string: 要替换的旧字符串
            new_string: 替换后的新字符串
            replace_all: 是否替换所有匹配项，默认为 False（只替换第一个匹配项）

        Returns:
            EditResult 对象，包含替换次数等信息
        """
        backend = self._route_path(file_path)
        return backend.edit(file_path, old_string, new_string, replace_all=replace_all)

    def grep_raw(self, pattern: str, path: str = None, glob: str = None):
        """
        在文件中搜索文本模式

        Args:
            pattern: 要搜索的文本模式（字面量字符串，不是正则表达式）
            path: 要搜索的目录或文件路径，默认为当前目录
            glob: 可选的 glob 模式来过滤要搜索的文件

        Returns:
            GrepMatch 对象列表，包含 path、line 和 text 字段
        """
        # 如果没有指定路径，默认搜索当前目录
        if path is None:
            path = "/"

        # 根据路径路由到相应的 backend
        backend = self._route_path(path)

        print(f"[DEBUG] composite_backend.py - grep_raw 调用: pattern={pattern}, path={path}, glob={glob}")

        # 调用对应 backend 的 grep_raw 方法
        result = backend.grep_raw(pattern, path, glob)

        print(f"[DEBUG] composite_backend.py - grep_raw 结果: 找到 {len(result) if isinstance(result, list) else 0} 个匹配项")

        return result

    # ==================== SummarizationMiddleware 需要的方法 ====================

    def download_files(self, paths: List[str]) -> List[FileDownloadResponse]:
        """
        下载文件内容（SummarizationMiddleware 需要）

        Args:
            paths: 文件路径列表

        Returns:
            FileDownloadResponse 对象列表
        """
        results = []
        for path in paths:
            backend = self._route_path(path)
            try:
                # 使用 read 获取内容，然后构造 FileDownloadResponse
                content = backend.read(path)
                results.append(FileDownloadResponse(
                    path=path,
                    content=content.encode('utf-8') if content else b'',
                    error=None
                ))
            except Exception as e:
                # 文件不存在或其他错误
                error_type = self._get_error_type(e)
                results.append(FileDownloadResponse(
                    path=path,
                    content=None,
                    error=error_type
                ))
        return results

    async def adownload_files(self, paths: List[str]) -> List[FileDownloadResponse]:
        """异步版本"""
        results = []
        for path in paths:
            backend = self._route_path(path)
            try:
                content = await backend.aread(path)
                results.append(FileDownloadResponse(
                    path=path,
                    content=content.encode('utf-8') if content else b'',
                    error=None
                ))
            except Exception as e:
                error_type = self._get_error_type(e)
                results.append(FileDownloadResponse(
                    path=path,
                    content=None,
                    error=error_type
                ))
        return results

    def upload_files(self, files: List[tuple[str, bytes]]) -> List[FileUploadResponse]:
        """
        上传文件（SummarizationMiddleware 可能需要）

        Args:
            files: 文件列表，每个元素是 (path, content) 元组

        Returns:
            FileUploadResponse 对象列表
        """
        results = []
        for file_path, content in files:
            backend = self._route_path(file_path)
            try:
                # 将 bytes 转换为 str 写入
                content_str = content.decode('utf-8') if content else ''
                backend.write(file_path, content_str)
                results.append(FileUploadResponse(
                    path=file_path,
                    error=None
                ))
            except Exception as e:
                results.append(FileUploadResponse(
                    path=file_path,
                    error=str(e)
                ))
        return results

    async def aupload_files(self, files: List[tuple[str, bytes]]) -> List[FileUploadResponse]:
        """异步版本"""
        results = []
        for file_path, content in files:
            backend = self._route_path(file_path)
            try:
                content_str = content.decode('utf-8') if content else ''
                await backend.awrite(file_path, content_str)
                results.append(FileUploadResponse(
                    path=file_path,
                    error=None
                ))
            except Exception as e:
                results.append(FileUploadResponse(
                    path=file_path,
                    error=str(e)
                ))
        return results

    def _get_error_type(self, error: Exception) -> Optional[str]:
        """根据异常类型返回错误类型字符串"""
        error_msg = str(error).lower()
        if "not found" in error_msg or "no such file" in error_msg:
            return "file_not_found"
        elif "permission" in error_msg:
            return "permission_denied"
        elif "is a directory" in error_msg:
            return "is_directory"
        elif "invalid" in error_msg:
            return "invalid_path"
        return None

    # ==================== 异步方法 ====================

    async def aread(self, path: str, offset: int = 0, limit: int = 2000) -> str:
        """
        异步读取文件内容

        Args:
            path: 文件路径
            offset: 从哪一行开始读取（0索引），默认为0
            limit: 最多读取多少行，默认为2000

        Returns:
            文件内容
        """
        backend = self._route_path(path)
        return await backend.aread(path, offset=offset, limit=limit)

    async def awrite(self, path: str, content: str) -> WriteResult:
        """
        异步写入文件内容

        Args:
            path: 文件路径
            content: 文件内容

        Returns:
            WriteResult 对象
        """
        backend = self._route_path(path)
        return await backend.awrite(path, content)

    async def als_info(self, path: str = ""):
        """
        异步列出目录中的文件

        Args:
            path: 目录路径

        Returns:
            FileInfo 对象列表
        """
        backend = self._route_path(path)
        return await backend.als_info(path)

    async def aglob_info(self, pattern: str, path: str = "/"):
        """
        异步查找匹配的文件

        Args:
            pattern: 文件匹配模式
            path: 搜索路径，默认为根目录

        Returns:
            FileInfo 对象列表
        """
        backend = self._route_path(path)
        return await backend.aglob_info(pattern, path=path)

    async def aedit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult:
        """
        异步编辑文件内容（替换指定字符串）

        Args:
            file_path: 文件路径
            old_string: 要替换的旧字符串
            new_string: 替换后的新字符串
            replace_all: 是否替换所有匹配项，默认为 False（只替换第一个匹配项）

        Returns:
            EditResult 对象，包含替换次数等信息
        """
        backend = self._route_path(file_path)
        return await backend.aedit(file_path, old_string, new_string, replace_all=replace_all)

    async def agrep_raw(self, pattern: str, path: str = None, glob: str = None):
        """
        异步在文件中搜索文本模式

        Args:
            pattern: 要搜索的文本模式（字面量字符串，不是正则表达式）
            path: 要搜索的目录或文件路径，默认为当前目录
            glob: 可选的 glob 模式来过滤要搜索的文件

        Returns:
            GrepMatch 对象列表，包含 path、line 和 text 字段
        """
        # 如果没有指定路径，默认搜索当前目录
        if path is None:
            path = "/"

        # 根据路径路由到相应的 backend
        backend = self._route_path(path)

        print(f"[DEBUG] composite_backend.py - agrep_raw 调用: pattern={pattern}, path={path}, glob={glob}")

        # 调用对应 backend 的 agrep_raw 方法
        result = await backend.agrep_raw(pattern, path, glob)

        print(f"[DEBUG] composite_backend.py - agrep_raw 结果: 找到 {len(result) if isinstance(result, list) else 0} 个匹配项")

        return result

    def update_output_dir(self, new_output_dir: str):
        """
        更新 output 目录路径

        Args:
            new_output_dir: 新的 output 目录路径
        """
        print(f"[DEBUG] composite_backend.py - 开始更新 output_dir")
        print(f"[DEBUG] composite_backend.py - 旧 output_dir: {self.output_dir}")
        print(f"[DEBUG] composite_backend.py - 新 output_dir: {new_output_dir}")

        # 更新 output_dir
        self.output_dir = Path(new_output_dir).absolute()

        # 重新初始化 output_backend（使用新的 output_dir）
        self.output_backend = FilesystemBackend(
            root_dir=str(self.output_dir),
            virtual_mode=self.virtual_mode
        )

        # skills_backend 和 conversation_history_backend 保持不变
        print(f"[DEBUG] composite_backend.py - output_dir 已更新为: {self.output_dir}")
        print(f"[DEBUG] composite_backend.py - skills_dir 保持不变: {self.skills_dir}")
        print(f"[DEBUG] composite_backend.py - conversation_history_dir 保持不变: {self.conversation_history_dir}")
        print(f"[DEBUG] composite_backend.py - output_backend 已重新初始化")
