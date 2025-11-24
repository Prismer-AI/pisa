"""
统一配置管理模块

使用 dotenv 从 .env 文件读取配置，提供统一的配置访问接口。
集成 OpenAI Agent SDK 配置。
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# 延迟导入 OpenAI Agent SDK，仅在需要时导入
_HAS_AGENTS = False
_Agent = None
_set_default_openai_client = None
_set_default_openai_api = None
_set_tracing_disabled = None
_AsyncOpenAI = None

try:
    from agents import Agent, set_default_openai_client, set_default_openai_api, set_tracing_disabled
    from openai import AsyncOpenAI
    _HAS_AGENTS = True
    _Agent = Agent
    _set_default_openai_client = set_default_openai_client
    _set_default_openai_api = set_default_openai_api
    _set_tracing_disabled = set_tracing_disabled
    _AsyncOpenAI = AsyncOpenAI
except ImportError:
    pass


class Config:
    """统一配置类，从 .env 文件读取配置"""

    # 项目根目录
    _project_root: Optional[Path] = None

    # OpenAI 配置
    openai_api_key: Optional[str] = None
    openai_api_base_url: Optional[str] = None
    agent_default_model: Optional[str] = None
    openai_api_trace_key: Optional[str] = None

    # Exa Search 配置
    exasearch_api_key: Optional[str] = None

    # OpenAI Agent SDK 客户端
    _openai_client: Optional[any] = None
    _agent_sdk_configured: bool = False

    _initialized: bool = False

    @classmethod
    def _get_project_root(cls) -> Path:
        """获取项目根目录"""
        if cls._project_root is None:
            # 从当前文件位置向上查找，直到找到包含 .env 文件的目录
            current = Path(__file__).resolve()
            while current.parent != current:
                if (current / ".env").exists():
                    cls._project_root = current
                    break
                current = current.parent
            else:
                # 如果找不到，使用当前工作目录
                cls._project_root = Path.cwd()
        return cls._project_root

    @classmethod
    def load(cls, env_file: Optional[str] = None) -> None:
        """
        加载环境变量配置

        Args:
            env_file: .env 文件路径，如果为 None 则自动查找项目根目录下的 .env 文件
        """
        if cls._initialized:
            return

        if env_file is None:
            env_file = str(cls._get_project_root() / ".env")

        # 加载 .env 文件
        load_dotenv(dotenv_path=env_file, override=False)

        # 读取 OpenAI 配置
        cls.openai_api_key = os.getenv("OPENAI_API_KEY")
        cls.openai_api_base_url = os.getenv("OPENAI_API_BASE_URL")
        cls.agent_default_model = os.getenv("AGENT_DEFAULT_MODEL")
        cls.openai_api_trace_key = os.getenv("OPENAI_API_TRACE_KEY")

        # 读取 Exa Search 配置
        cls.exasearch_api_key = os.getenv("EXASEARCH_API_KEY")

        cls._initialized = True

    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取配置值

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            配置值，如果不存在则返回默认值
        """
        if not cls._initialized:
            cls.load()
        return os.getenv(key, default)

    @classmethod
    def reload(cls, env_file: Optional[str] = None) -> None:
        """
        重新加载配置

        Args:
            env_file: .env 文件路径，如果为 None 则自动查找项目根目录下的 .env 文件
        """
        cls._initialized = False
        cls.load(env_file)

    @classmethod
    def validate(cls) -> bool:
        """
        验证必需的配置项是否存在

        Returns:
            如果所有必需配置都存在则返回 True，否则返回 False
        """
        if not cls._initialized:
            cls.load()

        required_configs = [
            ("OPENAI_API_KEY", cls.openai_api_key),
            ("OPENAI_API_BASE_URL", cls.openai_api_base_url),
            ("AGENT_DEFAULT_MODEL", cls.agent_default_model),
        ]

        missing = [name for name, value in required_configs if not value]
        if missing:
            raise ValueError(f"缺少必需的配置项: {', '.join(missing)}")

        return True

    @classmethod
    def __str__(cls) -> str:
        """返回配置类的字符串表示"""
        if not cls._initialized:
            cls.load()

        config_items = {
            "openai_api_key": cls.openai_api_key[:10] + "..." if cls.openai_api_key else None,
            "openai_api_base_url": cls.openai_api_base_url,
            "agent_default_model": cls.agent_default_model,
            "exasearch_api_key": cls.exasearch_api_key[:10] + "..." if cls.exasearch_api_key else None,
        }
        return f"Config({config_items})"

    @classmethod
    def __repr__(cls) -> str:
        """返回配置类的字符串表示"""
        return cls.__str__()

    # ==================== OpenAI Agent SDK 配置 ====================

    @classmethod
    def has_agent_sdk(cls) -> bool:
        """
        检查是否安装了 OpenAI Agent SDK

        Returns:
            是否安装了 Agent SDK
        """
        return _HAS_AGENTS

    @classmethod
    def setup_agent_sdk(
        cls,
        disable_tracing: bool = True,
        use_chat_completions: bool = True,
        force: bool = False
    ) -> bool:
        """
        配置 OpenAI Agent SDK

        根据 .env 配置自动设置 OpenAI Agent SDK 的全局客户端

        Args:
            disable_tracing: 是否禁用追踪（默认 True）
            use_chat_completions: 是否使用 chat_completions API（默认 True）
            force: 强制重新配置（默认 False）

        Returns:
            是否配置成功

        Raises:
            ImportError: 如果未安装 OpenAI Agent SDK
            ValueError: 如果缺少必需的配置

        Example:
            ```python
            from pisa.config import Config

            # 加载配置并设置 Agent SDK
            Config.load()
            Config.setup_agent_sdk()

            # 现在可以使用 Agent
            from agents import Agent, Runner

            agent = Agent(
                name="Assistant",
                instructions="You are helpful",
                model=Config.agent_default_model
            )
            ```
        """
        if not cls._initialized:
            cls.load()

        if cls._agent_sdk_configured and not force:
            return True

        if not _HAS_AGENTS:
            raise ImportError(
                "OpenAI Agent SDK not installed. "
                "Install with: pip install openai-agents"
            )

        # 验证配置
        if not cls.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in .env")
        if not cls.openai_api_base_url:
            raise ValueError("OPENAI_API_BASE_URL not found in .env")

        # 创建 OpenAI 客户端
        cls._openai_client = _AsyncOpenAI(
            base_url=cls.openai_api_base_url,
            api_key=cls.openai_api_key
        )

        # 设置全局客户端
        _set_default_openai_client(cls._openai_client)

        # 设置 API 类型
        if use_chat_completions:
            _set_default_openai_api("chat_completions")

        # 禁用追踪
        if disable_tracing:
            _set_tracing_disabled(True)

        cls._agent_sdk_configured = True
        return True

    @classmethod
    def get_openai_client(cls):
        """
        获取配置的 OpenAI 客户端

        Returns:
            AsyncOpenAI 客户端实例

        Raises:
            RuntimeError: 如果 Agent SDK 未配置
        """
        if not cls._agent_sdk_configured:
            cls.setup_agent_sdk()

        return cls._openai_client

    @classmethod
    def create_agent(
        cls,
        name: str,
        instructions: str,
        model: Optional[str] = None,
        **kwargs
    ):
        """
        创建 OpenAI Agent

        便捷方法，自动使用配置的模型和客户端

        Args:
            name: Agent 名称
            instructions: Agent 指令
            model: 模型名称（默认使用 AGENT_DEFAULT_MODEL）
            **kwargs: 其他 Agent 参数

        Returns:
            Agent 实例

        Raises:
            ImportError: 如果未安装 Agent SDK
            RuntimeError: 如果 Agent SDK 未配置

        Example:
            ```python
            from pisa.config import Config

            Config.setup_agent_sdk()
            agent = Config.create_agent(
                name="Assistant",
                instructions="You are helpful"
            )
            ```
        """
        if not _HAS_AGENTS:
            raise ImportError(
                "OpenAI Agent SDK not installed. "
                "Install with: pip install openai-agents"
            )

        if not cls._agent_sdk_configured:
            cls.setup_agent_sdk()

        # 使用默认模型（如果未指定）
        if model is None:
            model = cls.agent_default_model

        return _Agent(
            name=name,
            instructions=instructions,
            model=model,
            **kwargs
        )

    @classmethod
    def get_agent_sdk_status(cls) -> dict:
        """
        获取 Agent SDK 配置状态

        Returns:
            状态字典，包含配置信息

        Example:
            ```python
            status = Config.get_agent_sdk_status()
            print(status)
            # {
            #     'installed': True,
            #     'configured': True,
            #     'model': 'openai/gpt-oss-120b',
            #     'base_url': 'http://...'
            # }
            ```
        """
        return {
            'installed': _HAS_AGENTS,
            'configured': cls._agent_sdk_configured,
            'model': cls.agent_default_model,
            'base_url': cls.openai_api_base_url,
            'has_api_key': bool(cls.openai_api_key),
        }


# 自动加载配置
Config.load()

