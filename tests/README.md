# PISA 测试套件

## 目录结构

```
tests/
├── unit/                  # 单元测试
│   ├── test_config.py
│   ├── test_logger.py
│   └── test_observability.py
├── integration/           # 集成测试
│   └── test_agent_sdk_integration.py
├── e2e/                   # 端到端测试
├── conftest.py           # Pytest 配置和 fixtures
└── README.md             # 本文件
```

## 运行测试

**注意**: 所有测试都使用 `uv run pytest` 来执行，以确保在正确的环境中运行。

### 运行所有测试

```bash
uv run pytest
```

### 运行特定类型的测试

```bash
# 只运行单元测试
uv run pytest tests/unit/

# 只运行集成测试
uv run pytest tests/integration/

# 只运行端到端测试
uv run pytest tests/e2e/

# 运行特定测试文件
uv run pytest tests/unit/test_capability.py
```

### 使用 markers 过滤测试

```bash
# 只运行单元测试标记的测试
uv run pytest -m unit

# 只运行集成测试标记的测试
uv run pytest -m integration

# 跳过需要 API 的测试
uv run pytest -m "not requires_api"

# 跳过慢速测试
uv run pytest -m "not slow"
```

### 查看覆盖率

```bash
# 运行测试并生成覆盖率报告
uv run pytest --cov=pisa --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

### 详细输出

```bash
# 显示详细输出
uv run pytest -v

# 显示打印输出
uv run pytest -s

# 组合使用
uv run pytest -v -s

# 简洁输出
uv run pytest -q
```

## 测试 Markers

- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.e2e` - 端到端测试
- `@pytest.mark.slow` - 慢速测试
- `@pytest.mark.requires_api` - 需要 API 凭据的测试

## Fixtures

### 配置相关

- `test_env` - 测试环境变量
- `project_root` - 项目根目录
- `mock_config` - Mock 配置对象
- `mock_agent_sdk` - Mock Agent SDK

### 文件相关

- `sample_agent_md` - 示例 agent.md 文件
- `sample_context_md` - 示例 context.md 文件
- `temp_log_dir` - 临时日志目录

## 编写测试

### 单元测试示例

```python
import pytest
from pisa.config import Config


class TestMyModule:
    """测试我的模块"""
    
    def test_basic_functionality(self):
        """测试基础功能"""
        # Arrange
        input_data = "test"
        
        # Act
        result = my_function(input_data)
        
        # Assert
        assert result == expected_output
    
    def test_with_fixture(self, mock_config):
        """使用 fixture 的测试"""
        # 使用 mock_config fixture
        value = Config.get("SOME_KEY")
        assert value is not None
```

### 集成测试示例

```python
import pytest
from pisa.config import Config


@pytest.mark.integration
@pytest.mark.requires_api
class TestIntegration:
    """集成测试"""
    
    def test_full_flow(self):
        """测试完整流程"""
        # 设置
        Config.setup_agent_sdk()
        
        # 执行
        agent = Config.create_agent(
            name="Test",
            instructions="Test"
        )
        
        # 验证
        assert agent is not None
```

### 异步测试示例

```python
import pytest


@pytest.mark.asyncio
async def test_async_function():
    """测试异步函数"""
    result = await my_async_function()
    assert result is not None
```

## 环境配置

### 测试环境变量

创建 `.env.test` 文件用于测试：

```bash
# .env.test
OPENAI_API_KEY=test-api-key
OPENAI_API_BASE_URL=http://test-api.example.com/v1
AGENT_DEFAULT_MODEL=test-model
```

### CI/CD 配置

在 GitHub Actions 中配置：

```yaml
- name: Run tests
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: |
    pytest --cov=pisa
```

## 最佳实践

1. **测试命名**：使用清晰的名称，如 `test_function_name_scenario`
2. **Arrange-Act-Assert**：遵循 AAA 模式组织测试
3. **使用 Fixtures**：避免重复代码，使用 fixtures 提供测试数据
4. **隔离测试**：每个测试应该独立，不依赖其他测试
5. **Mock 外部依赖**：使用 mock 避免依赖外部服务
6. **添加标记**：使用 markers 组织测试
7. **测试边界情况**：不仅测试正常情况，也要测试边界和异常情况

## 故障排除

### 导入错误

如果遇到导入错误，确保：

1. 在项目根目录运行测试
2. 安装了所有依赖：`pip install -e .[testing]`
3. PYTHONPATH 正确设置

### API 测试失败

如果 API 测试失败：

1. 检查 `.env` 文件中的 API 凭据
2. 使用 `-m "not requires_api"` 跳过 API 测试
3. 检查网络连接

### 慢速测试

如果测试运行太慢：

1. 使用 `-m "not slow"` 跳过慢速测试
2. 只运行特定的测试文件
3. 使用 `pytest -x` 在第一个失败时停止

## 持续集成

测试应该在每次提交时自动运行。配置 GitHub Actions：

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e .[testing]
      - name: Run tests
        run: |
          pytest --cov=pisa --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## 贡献

添加新测试时：

1. 选择合适的目录（unit/integration/e2e）
2. 使用合适的 markers
3. 添加必要的 fixtures
4. 确保测试通过：`pytest tests/unit/test_your_module.py`
5. 检查覆盖率：`pytest --cov=pisa`

