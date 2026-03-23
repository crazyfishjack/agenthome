"""
沙箱执行工具
用于在安全的沙箱环境中执行 Python 文件和系统命令
"""
from typing import List, Optional
from pydantic import BaseModel, Field
import subprocess
import os
import json
import signal
from pathlib import Path
from .tool_base import ToolBase


class SandboxExecuteInput(BaseModel):
    """沙箱执行工具输入参数"""
    command: str = Field(
        description="要执行的命令或 Python 文件路径。可以是：\n"
                   "- Python 文件路径（如：python test.py）\n"
                   "- 系统命令（如：ls -la、cat data.txt）"
    )
    timeout: Optional[int] = Field(
        default=30,
        description="执行超时时间（秒），默认30秒"
    )


class SandboxExecuteTool(ToolBase):
    """沙箱执行工具 - 在安全环境中执行命令和 Python 文件"""

    # 危险命令黑名单（绝对禁止）
    FORBIDDEN_COMMANDS = {
        # 系统破坏性命令
        'rm -rf /', 'rm -rf /*', 'rm -rf .', 'rm -rf ~',
        'format', 'fdisk', 'mkfs', 'mkswap',
        'dd', 'dd if=', 'dd of=', 'shred', 'wipe',

        # 系统控制命令
        'shutdown', 'reboot', 'halt', 'poweroff',
        'init 0', 'init 6', 'systemctl poweroff', 'systemctl reboot',

        # 权限提升命令
        'su', 'sudo', 'sudo -i', 'sudo su',
        'passwd', 'chown', 'chmod 777', 'chmod +s',

        # 网络相关危险命令
        'iptables', 'ip6tables', 'nftables',
        'netstat', 'ss', 'nmap', 'nc -l', 'netcat -l',
        'tcpdump', 'wireshark', 'tshark',

        # 网络下载命令（防止下载恶意脚本）
        'curl', 'wget', 'fetch', 'aria2c',

        # 远程连接命令
        'nc', 'telnet', 'ssh', 'ftp', 'sftp', 'scp',

        # 代码执行命令
        'eval', 'exec', 'system', 'popen', 'passthru',
        'shell_exec', 'proc_open', 'pcntl_exec',

        # 数据库相关危险操作
        'mysqladmin', 'pg_dump', 'mongodump', 'mysqldump',
        'drop database', 'drop table', 'truncate table',

        # 文件系统操作
        'mount', 'umount', 'mkfs.', 'fsck',
        'ln -s /', 'ln -s /etc/', 'ln -s /root/',

        # 进程控制
        'killall', 'pkill', 'kill -9', 'kill -15',
        'killall -9', 'pkill -9',

        # 其他危险命令
        'chroot', 'pivot_root', 'nsenter', 'unshare',
        'crontab', 'at ', 'batch',
        'history -c', 'history -w',
        'setuid', 'setgid',
    }

    # 默认超时时间（秒）
    DEFAULT_TIMEOUT = 30

    # 最大超时时间（秒）
    MAX_TIMEOUT = 300

    # 最大命令长度（字符数）
    MAX_COMMAND_LENGTH = 1000

    @property
    def SANDBOX_DIR(self) -> str:
        """动态获取沙箱工作目录（从 langchain_service 获取当前的 output_dir）"""
        try:
            from backend.services.langchain_service import get_output_dir
            output_dir = get_output_dir()
            return str(output_dir.absolute())
        except Exception as e:
            # 如果获取失败，使用默认值
            print(f"[WARNING] sandbox_tool.py - 获取 output_dir 失败，使用默认值: {e}")
            return str((Path(__file__).parent.parent.parent / "output").absolute())

    @property
    def name(self) -> str:
        return "SandboxExecute"

    @property
    def description(self) -> str:
        return "在安全的沙箱环境中执行 Python 文件和系统命令。采用黑名单安全策略，禁止危险命令和操作。"

    @property
    def parameter_requirements(self) -> str:
        return """- 必须提供要执行的命令或 Python 文件路径
- 可选提供超时时间（秒），默认30秒，最大300秒
- 命令长度不能超过1000个字符
- 禁止执行危险命令（如 rm -rf /、format、sudo 等）
- 禁止使用管道、重定向、命令链和命令替换
- 禁止访问敏感系统路径（/etc/、/sys/、/proc/、/dev/）
- 允许执行任意 .py 文件
- 允许使用常用开发工具命令"""

    @property
    def format_requirements(self) -> str:
        return """支持两种输入格式：

1. 简单命令格式（推荐）：
   - "python test.py"
   - "ls -la"
   - "cat data.txt"

2. JSON 格式（用于指定超时）：
   {
     "command": "python test.py",
     "timeout": 60
   }"""

    @property
    def examples(self) -> List[str]:
        return [
            '输入："python test.py" → 执行当前 output 目录下的 test.py 文件',
            '输入："ls -la" → 列出当前 output 目录下的所有文件',
            '输入："cat data.txt" → 查看 data.txt 文件内容',
            '输入：\'{"command": "python script.py", "timeout": 60}\' → 使用60秒超时执行 Python 文件',
            '输入："npm install" → 在当前 output 目录中安装 npm 依赖',
            '输入："git status" → 查看 git 状态',
            '输入："make build" → 执行构建命令',
            '安全限制示例：禁止 "rm -rf /"、禁止 "cat /etc/passwd"、禁止 "ls | grep test"'
        ]

    @property
    def input_schema(self):
        """返回 Pydantic 模型作为输入 schema"""
        return SandboxExecuteInput

    def execute(self, input: str) -> str:
        """执行沙箱命令

        Args:
            input: 输入参数，可以是简单命令字符串或 JSON 格式

        Returns:
            执行结果或错误信息
        """
        try:
            # 解析输入参数
            command, timeout = self._parse_input(input)

            # 安全检查
            self._security_check(command)

            # 执行命令
            result = self._execute_command(command, timeout)

            return result

        except ValueError as e:
            return f"参数错误: {str(e)}"
        except PermissionError as e:
            return f"权限错误: {str(e)}"
        except subprocess.TimeoutExpired:
            return f"执行超时（超过 {timeout} 秒）"
        except Exception as e:
            return f"执行失败: {str(e)}"

    def _parse_input(self, input: str) -> tuple[str, int]:
        """解析输入参数

        Args:
            input: 输入字符串

        Returns:
            (command, timeout) 元组

        Raises:
            ValueError: 输入格式错误
        """
        input = input.strip()

        # 尝试解析为 JSON
        if input.startswith('{'):
            try:
                data = json.loads(input)
                command = data.get('command', '').strip()
                timeout = data.get('timeout', self.DEFAULT_TIMEOUT)

                if not command:
                    raise ValueError("JSON 格式中必须提供 'command' 字段")

                # 验证超时时间
                timeout = int(timeout)
                if timeout <= 0:
                    raise ValueError("超时时间必须大于0")
                if timeout > self.MAX_TIMEOUT:
                    raise ValueError(f"超时时间不能超过 {self.MAX_TIMEOUT} 秒")

                return command, timeout

            except json.JSONDecodeError as e:
                raise ValueError(f"JSON 解析失败: {str(e)}")

        # 简单命令格式
        else:
            command = input
            timeout = self.DEFAULT_TIMEOUT
            return command, timeout

    def _security_check(self, command: str) -> None:
        """安全检查 - 采用黑名单 + 基础安全规则策略

        Args:
            command: 要执行的命令

        Raises:
            PermissionError: 命令不安全或被禁止
        """
        command_lower = command.lower().strip()
        command_stripped = command.strip()

        # 1. 检查命令长度
        if len(command_stripped) > self.MAX_COMMAND_LENGTH:
            raise PermissionError(
                f"命令长度超过限制（最多 {self.MAX_COMMAND_LENGTH} 个字符，当前 {len(command_stripped)} 个字符）"
            )

        # 2. 检查命令是否为空
        if not command_stripped:
            raise PermissionError("命令不能为空")

        # 3. 检查危险命令黑名单
        for forbidden in self.FORBIDDEN_COMMANDS:
            if forbidden in command_lower:
                raise PermissionError(f"禁止执行危险命令: {forbidden}")

        # 4. 禁止管道和重定向操作
        if '|' in command_stripped:
            raise PermissionError("禁止使用管道操作符 (|)")
        if '>' in command_stripped:
            raise PermissionError("禁止使用输出重定向 (>)")
        if '<' in command_stripped:
            raise PermissionError("禁止使用输入重定向 (<)")
        if '>>' in command_stripped:
            raise PermissionError("禁止使用追加重定向 (>>)")
        if '2>' in command_stripped or '2>>' in command_stripped:
            raise PermissionError("禁止使用错误输出重定向")

        # 5. 禁止命令链
        if '&&' in command_stripped:
            raise PermissionError("禁止使用命令链 (&&)")
        if ';' in command_stripped:
            raise PermissionError("禁止使用命令分隔符 (;)")
        if '||' in command_stripped:
            raise PermissionError("禁止使用逻辑或操作符 (||)")
        if '&' in command_stripped and not command_stripped.endswith('&'):
            # 允许命令末尾的 &（后台运行），但禁止中间的 &
            raise PermissionError("禁止使用后台执行操作符 (&)")

        # 6. 禁止反引号和命令替换
        if '`' in command_stripped:
            raise PermissionError("禁止使用反引号命令替换 (`)")
        if '$(' in command_stripped:
            raise PermissionError("禁止使用 $() 命令替换")
        if '${' in command_stripped:
            raise PermissionError("禁止使用 ${} 变量替换")

        # 7. 检查敏感系统路径
        sensitive_paths = ['/etc/', '/sys/', '/proc/', '/dev/']
        for path in sensitive_paths:
            if path in command_stripped:
                raise PermissionError(f"禁止访问敏感系统路径: {path}")

        # 8. 特殊处理：允许 Python 执行任意 .py 文件
        parts = command_stripped.split()
        cmd_name = parts[0].lower()

        if cmd_name in ['python', 'python3', 'py']:
            # Python 命令允许执行任意 .py 文件
            if not any(arg.endswith('.py') for arg in parts[1:]):
                raise PermissionError("Python 命令必须指定 .py 文件")
            # 额外检查：确保 Python 文件参数不包含危险路径
            for arg in parts[1:]:
                if arg.endswith('.py'):
                    # 检查文件路径是否包含敏感路径
                    for path in sensitive_paths:
                        if path in arg:
                            raise PermissionError(f"禁止访问敏感系统路径中的 Python 文件: {path}")
            return  # Python 命令通过检查

        # 9. 允许其他常用开发工具命令
        # 不再使用白名单，只要不违反上述安全规则即可执行
        # 这允许使用 git、npm、make、docker 等常用开发工具
        pass

    def _execute_command(self, command: str, timeout: int) -> str:
        """执行命令

        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）

        Returns:
            执行结果

        Raises:
            subprocess.TimeoutExpired: 执行超时
            Exception: 执行失败
        """
        # 确保沙箱目录存在
        os.makedirs(self.SANDBOX_DIR, exist_ok=True)

        # 根据操作系统选择合适的 shell
        shell = True
        if os.name == 'nt':  # Windows
            # Windows 使用 cmd.exe
            shell_cmd = ['cmd', '/c', command]
        else:  # Unix/Linux/Mac
            shell_cmd = ['sh', '-c', command]

        try:
            # 执行命令
            process = subprocess.Popen(
                shell_cmd,
                cwd=self.SANDBOX_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False  # 我们已经手动处理了 shell
            )

            # 等待命令完成或超时
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                # 超时，终止进程
                process.kill()
                process.wait()
                raise

            # 处理执行结果
            if process.returncode == 0:
                # 成功
                if stdout:
                    return f"执行成功:\n{stdout}"
                else:
                    return "执行成功（无输出）"
            else:
                # 失败
                error_msg = stderr if stderr else stdout
                if error_msg:
                    return f"执行失败（退出码 {process.returncode}）:\n{error_msg}"
                else:
                    return f"执行失败（退出码 {process.returncode}，无错误信息）"

        except subprocess.TimeoutExpired:
            raise
        except FileNotFoundError as e:
            raise Exception(f"命令或文件不存在: {str(e)}")
        except Exception as e:
            raise Exception(f"执行命令时发生错误: {str(e)}")

    def _get_sandbox_info(self) -> str:
        """获取沙箱信息

        Returns:
            沙箱信息字符串
        """
        info = [
            f"沙箱工作目录: {self.SANDBOX_DIR}",
            f"安全策略: 黑名单 + 基础安全规则",
            f"禁止的命令数量: {len(self.FORBIDDEN_COMMANDS)}",
            f"默认超时: {self.DEFAULT_TIMEOUT} 秒",
            f"最大超时: {self.MAX_TIMEOUT} 秒",
            f"最大命令长度: {self.MAX_COMMAND_LENGTH} 个字符",
            f"安全限制: 禁止管道、重定向、命令链、命令替换和敏感路径访问"
        ]
        return '\n'.join(info)
