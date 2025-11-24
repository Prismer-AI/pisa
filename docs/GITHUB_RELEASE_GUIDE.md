# GitHub Release 创建指南

## 📋 v0.1.1 Release 步骤

### 方法 1: 通过 GitHub Web UI（推荐）

1. **访问 Releases 页面**
   - 打开：https://github.com/Prismer-AI/pisa/releases/new

2. **选择 Tag**
   - 在 "Choose a tag" 下拉框中选择：`v0.1.1`
   - 或者手动输入：`v0.1.1`（如果没看到）

3. **填写 Release 标题**
   ```
   PISA v0.1.1 - Documentation and Badge Updates
   ```

4. **填写 Release 描述**
   
   复制 `RELEASE_NOTES_v0.1.1.md` 的内容，或使用以下简化版：

   ```markdown
   ## 📦 Installation
   
   ```bash
   pip install pisa-python
   ```
   
   ## 🔄 What's Changed
   
   - ✅ Added PyPI version badge to README
   - ✅ Updated all package references to `pisa-python`
   - ✅ Fixed PyPI project links
   - ✅ Improved documentation
   
   ## 🔗 Links
   
   - **PyPI**: https://pypi.org/project/pisa-python/0.1.1/
   - **Documentation**: https://github.com/Prismer-AI/pisa#readme
   
   **Full Changelog**: https://github.com/Prismer-AI/pisa/compare/v0.1.0...v0.1.1
   ```

5. **设置为 Pre-release**（可选）
   - 由于这是 Alpha 版本，可以勾选 "Set as a pre-release"

6. **点击 "Publish release"**

---

### 方法 2: 通过 GitHub CLI（gh）

如果你安装了 GitHub CLI：

```bash
cd /Users/prismer/workspace/pisa/pisa

# 使用准备好的 release notes
gh release create v0.1.1 \
  --title "PISA v0.1.1 - Documentation and Badge Updates" \
  --notes-file RELEASE_NOTES_v0.1.1.md \
  --prerelease

# 或者使用自动生成的 notes
gh release create v0.1.1 \
  --title "PISA v0.1.1 - Documentation and Badge Updates" \
  --generate-notes \
  --prerelease
```

---

## 📋 v0.1.0 Release 步骤（补充创建）

如果你也想为 v0.1.0 创建 Release：

1. **访问**：https://github.com/Prismer-AI/pisa/releases/new

2. **标题**：`PISA v0.1.0 - Initial Alpha Release`

3. **描述**：
   ```markdown
   ## 🎉 Initial Alpha Release
   
   First public release of PISA - Planning, Intelligent, Self-Adaptive Agent Framework
   
   ## 📦 Installation
   
   ```bash
   pip install pisa-python
   ```
   
   ## ✨ Features
   
   - ✅ Core framework with Plan-Execute loop
   - ✅ Function, MCP, and Subagent capabilities
   - ✅ CLI tools (init, run, validate, list-capabilities)
   - ✅ Markdown-based agent definition
   - ✅ Context management with Pyramid Context Engineering
   - ✅ Rich console output and observability
   - 🚧 Experimental Temporal workflow integration
   
   ## 🔗 Links
   
   - **PyPI**: https://pypi.org/project/pisa-python/0.1.0/
   - **Documentation**: https://github.com/Prismer-AI/pisa#readme
   
   ## ⚠️ Alpha Notice
   
   This is an alpha release. APIs may change in future versions.
   ```

4. **勾选** "Set as a pre-release"

5. **点击** "Publish release"

---

## 📊 Release 后的工作

### 1. 验证 Release
- 访问：https://github.com/Prismer-AI/pisa/releases
- 确认 Release 信息正确显示
- 检查 "Latest release" 标记

### 2. 分享 Release
- 复制 Release URL：`https://github.com/Prismer-AI/pisa/releases/tag/v0.1.1`
- 在社交媒体分享：
  ```
  🎉 PISA v0.1.1 released! 
  
  Build production-ready AI agents with markdown-defined workflows 🤖
  
  📦 pip install pisa-python
  📖 https://github.com/Prismer-AI/pisa
  
  #Python #AI #Agents #OpenAI #Temporal
  ```

### 3. 更新项目 README
- 在 README 中添加 "Latest Release" badge（可选）：
  ```markdown
  [![Latest Release](https://img.shields.io/github/v/release/Prismer-AI/pisa)](https://github.com/Prismer-AI/pisa/releases/latest)
  ```

### 4. 监控反馈
- 关注 GitHub Issues
- 查看 Release 下载统计
- 收集用户反馈

---

## 🔄 后续版本发布流程

每次发布新版本时：

1. **更新版本号**
   - `pyproject.toml`: 修改 `version`
   - `CHANGELOG.rst`: 添加新版本说明

2. **构建和发布到 PyPI**
   ```bash
   rm -rf dist/ build/
   python -m build
   twine check dist/*
   twine upload dist/*
   ```

3. **Git 操作**
   ```bash
   git add -A
   git commit -m "chore: release v0.x.x"
   git tag v0.x.x
   git push origin main --tags
   ```

4. **创建 GitHub Release**
   - 使用上述方法创建 Release
   - 包含 changelog 和安装说明

---

## 💡 提示

- 使用语义化版本号：`MAJOR.MINOR.PATCH`
- Alpha/Beta 版本标记为 pre-release
- 提供清晰的 changelog
- 链接到 PyPI 包页面
- 包含安装和快速开始说明

