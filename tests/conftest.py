"""
Pytest Configuration and Fixtures

提供测试所需的通用 fixtures 和配置
"""

import pytest


def pytest_addoption(parser):
    """添加自定义命令行选项"""
    parser.addoption(
        "--real-llm",
        action="store_true",
        default=False,
        help="运行需要真实 LLM 调用的集成测试（会消耗 API quota）"
    )
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock


@pytest.fixture(scope="session")
def test_env():
    """测试环境配置"""
    return {
        "OPENAI_API_KEY": "test-api-key",
        "OPENAI_API_BASE_URL": "http://test-api.example.com/v1",
        "AGENT_DEFAULT_MODEL": "test-model",
        "EXASEARCH_API_KEY": "test-exa-key",
    }


@pytest.fixture(scope="session")
def project_root():
    """获取项目根目录"""
    return Path(__file__).parent.parent


@pytest.fixture
def mock_config(test_env, monkeypatch):
    """Mock 配置，避免依赖实际的 .env 文件"""
    from pisa.config import Config
    
    # 设置环境变量
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    
    # 重新加载配置
    Config._initialized = False
    Config.load()
    
    yield Config
    
    # 清理
    Config._initialized = False


@pytest.fixture
def mock_agent_sdk(monkeypatch):
    """Mock OpenAI Agent SDK"""
    # Mock Agent class
    mock_agent_class = Mock()
    mock_agent_instance = Mock()
    mock_agent_class.return_value = mock_agent_instance
    
    # Mock 相关函数
    mock_set_client = Mock()
    mock_set_api = Mock()
    mock_set_tracing = Mock()
    mock_async_openai = Mock()
    
    # 创建 mock 模块
    mock_agents_module = MagicMock()
    mock_agents_module.Agent = mock_agent_class
    mock_agents_module.set_default_openai_client = mock_set_client
    mock_agents_module.set_default_openai_api = mock_set_api
    mock_agents_module.set_tracing_disabled = mock_set_tracing
    
    mock_openai_module = MagicMock()
    mock_openai_module.AsyncOpenAI = mock_async_openai
    
    # Patch imports
    monkeypatch.setitem(__import__('sys').modules, 'agents', mock_agents_module)
    monkeypatch.setitem(__import__('sys').modules, 'openai', mock_openai_module)
    
    return {
        'Agent': mock_agent_class,
        'set_default_openai_client': mock_set_client,
        'set_default_openai_api': mock_set_api,
        'set_tracing_disabled': mock_set_tracing,
        'AsyncOpenAI': mock_async_openai,
    }


@pytest.fixture
def sample_agent_md(tmp_path):
    """创建示例 agent.md 文件"""
    agent_md = tmp_path / "agent.md"
    agent_md.write_text("""
# Agent Configuration

## Basic Info
- name: test_agent
- loop_type: react
- description: Test agent for unit tests

## Capabilities
- search_knowledge_base
- web_search

## System Prompt
You are a helpful test assistant.
""")
    return agent_md


@pytest.fixture
def sample_context_md(tmp_path):
    """创建示例 context.md 文件"""
    context_md = tmp_path / "context.md"
    context_md.write_text("""
# Context Configuration

## Settings
- max_tokens: 100000
- compression_enabled: true
- memory_enabled: false

## Initial Context
This is test context.
""")
    return context_md


@pytest.fixture
def temp_log_dir(tmp_path):
    """创建临时日志目录"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


# Pytest markers
def pytest_configure(config):
    """配置自定义 markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_api: mark test as requiring external API"
    )


# Test collection hooks
def pytest_collection_modifyitems(config, items):
    """修改测试收集行为"""
    # 默认跳过需要 API 的测试
    skip_api = pytest.mark.skip(reason="requires API credentials")
    for item in items:
        if "requires_api" in item.keywords:
            # 检查是否有 API 凭据
            if not os.getenv("OPENAI_API_KEY"):
                item.add_marker(skip_api)
