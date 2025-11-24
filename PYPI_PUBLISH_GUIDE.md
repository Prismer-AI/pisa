# PyPI 发布指南

## ✅ 准备工作（已完成）

- [x] 更新 `pyproject.toml` 配置
- [x] 添加 `MANIFEST.in` 文件
- [x] 构建分发包 (`dist/pisa-0.1.0-py3-none-any.whl` 和 `dist/pisa-0.1.0.tar.gz`)
- [x] 验证包质量 (`twine check` 通过)

## 📝 发布步骤

### 步骤 1: 创建 PyPI 账号（如果还没有）

访问 [PyPI](https://pypi.org/account/register/) 注册账号

### 步骤 2: 生成 API Token

1. 登录 PyPI 账号
2. 访问 [Account Settings - API tokens](https://pypi.org/manage/account/#api-tokens)
3. 点击 "Add API token"
4. Token name: `pisa-upload`
5. Scope: 选择 "Entire account" (首次发布) 或 "Project: pisa" (后续发布)
6. 创建后 **立即复制 token**（只显示一次！）

### 步骤 3: 配置 Twine 认证

**方法 A: 使用环境变量（推荐）**

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-AgEIcHl...你的token...
```

**方法 B: 使用 .pypirc 文件**

创建 `~/.pypirc` 文件：

```ini
[pypi]
username = __token__
password = pypi-AgEIcHl...你的token...
```

设置权限：
```bash
chmod 600 ~/.pypirc
```

### 步骤 4: 先上传到 TestPyPI（可选但推荐）

TestPyPI 是一个测试环境，可以在正式发布前验证：

```bash
# 上传到 TestPyPI
twine upload --repository testpypi dist/*

# 测试安装
pip install --index-url https://test.pypi.org/simple/ --no-deps pisa
```

TestPyPI 注册地址: https://test.pypi.org/account/register/
TestPyPI API Token: https://test.pypi.org/manage/account/#api-tokens

### 步骤 5: 正式发布到 PyPI

确认一切正常后，执行：

```bash
twine upload dist/*
```

输出示例：
```
Uploading distributions to https://upload.pypi.org/legacy/
Uploading pisa-0.1.0-py3-none-any.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 249.3/249.3 kB • 0:00:01
Uploading pisa-0.1.0.tar.gz
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.9/4.9 MB • 0:00:03

View at:
https://pypi.org/project/pisa/0.1.0/
```

### 步骤 6: 验证发布

1. 访问 https://pypi.org/project/pisa/
2. 检查项目信息是否正确
3. 测试安装：

```bash
# 在新的虚拟环境中测试
python -m venv test_env
source test_env/bin/activate
pip install pisa

# 验证安装
pisa --version
python -c "import pisa; print(pisa.__version__)"
```

## 🎯 快速发布命令（一键执行）

如果你已经配置好认证（使用环境变量或 .pypirc）：

```bash
# 进入项目目录
cd /Users/prismer/workspace/pisa/pisa

# 发布到 PyPI
twine upload dist/*
```

## 🔄 后续版本发布流程

1. **更新版本号**
   - 修改 `pyproject.toml` 中的 `version = "0.2.0"`
   - 更新 `CHANGELOG.rst`

2. **提交更改**
   ```bash
   git add pyproject.toml CHANGELOG.rst
   git commit -m "chore: bump version to 0.2.0"
   git tag v0.2.0
   git push origin main --tags
   ```

3. **重新构建**
   ```bash
   rm -rf dist/ build/
   python -m build
   twine check dist/*
   ```

4. **发布**
   ```bash
   twine upload dist/*
   ```

## ⚠️ 重要注意事项

1. **版本号不可重复**: 一旦发布某个版本，不能再次使用相同版本号
2. **Token 安全**: 
   - 不要将 token 提交到 Git
   - 不要分享给他人
   - 定期轮换 token
3. **README 重要性**: PyPI 会显示 README.md 作为项目主页
4. **分类标签**: classifiers 帮助用户发现你的项目
5. **依赖版本**: 确保 dependencies 中的版本约束合理

## 📋 检查清单

发布前确认：

- [ ] README.md 内容完整且准确
- [ ] LICENSE.txt 存在
- [ ] CHANGELOG.rst 已更新
- [ ] pyproject.toml 中的链接正确
- [ ] 版本号符合语义化版本规范
- [ ] 所有测试通过
- [ ] 文档链接可访问
- [ ] 已提交所有更改到 Git
- [ ] 已创建 Git tag

## 🎉 发布后的工作

1. **创建 GitHub Release**
   - 访问 https://github.com/Prismer-AI/pisa/releases/new
   - Tag: v0.1.0
   - Title: PISA v0.1.0 - Initial Alpha Release
   - Description: 复制 CHANGELOG.rst 中的内容

2. **宣传推广**
   - 在 Twitter 上分享
   - 在 Reddit r/Python 社区发布
   - 在相关技术论坛分享

3. **监控反馈**
   - 关注 GitHub Issues
   - 收集用户反馈
   - 准备下一个版本

## 🆘 常见问题

### 问题: "HTTPError: 403 Forbidden"

**解决**: 检查 API token 是否正确，是否有权限上传

### 问题: "File already exists"

**解决**: 该版本已存在，需要更新版本号

### 问题: "Invalid distribution"

**解决**: 运行 `twine check dist/*` 查看具体错误

### 问题: README 在 PyPI 显示不正确

**解决**: 确保 `long_description_content_type = "text/markdown"` 在 setup.cfg 中正确设置

## 📚 参考文档

- [PyPI 官方文档](https://pypi.org/help/)
- [Twine 文档](https://twine.readthedocs.io/)
- [Python Packaging 用户指南](https://packaging.python.org/)
- [语义化版本规范](https://semver.org/)

