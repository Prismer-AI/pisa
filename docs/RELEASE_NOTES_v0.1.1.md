# PISA v0.1.1 - Documentation and Badge Updates

**Release Date**: November 25, 2024  
**PyPI**: https://pypi.org/project/pisa-python/0.1.1/

## 📦 Installation

```bash
pip install pisa-python
```

## 🔄 What's Changed

### Documentation Updates
- ✅ Added PyPI version badge to README
- ✅ Updated all package references from `pisa` to `pisa-python`
- ✅ Fixed PyPI project links in setup.cfg
- ✅ Updated PYPI_PUBLISH_GUIDE with correct package name
- ✅ Improved README badges display (removed non-working pepy badge)

### Package Information
- **Package Name**: `pisa-python` (changed from `pisa` due to name conflict)
- **Import Name**: `pisa` (unchanged - install as `pisa-python`, import as `pisa`)
- **Python**: >=3.11
- **License**: MIT

## 📚 Quick Start

```python
# Install
pip install pisa-python

# Verify installation
import pisa
print(pisa.__version__)  # 0.1.1
```

```bash
# Command line
pisa --version
pisa init my-agent
pisa run .prismer/agent.md -i "your task here"
```

## 🔗 Links

- **PyPI Package**: https://pypi.org/project/pisa-python/
- **Documentation**: https://github.com/Prismer-AI/pisa#readme
- **Issues**: https://github.com/Prismer-AI/pisa/issues
- **Discussions**: https://github.com/Prismer-AI/pisa/discussions

## 📝 Full Changelog

**v0.1.1**
- chore: release v0.1.1 with updated badges and links

**v0.1.0** (Initial Release)
- feat: initial PISA framework release
- Core framework with Plan-Execute loop
- Function, MCP, and Subagent capabilities
- CLI tools and rich observability
- Markdown-based agent definition
- Context management with Pyramid Context Engineering
- Experimental Temporal workflow integration

## 🙏 Acknowledgments

Built on the shoulders of giants:
- [OpenAI Agent SDK](https://openai.github.io/openai-agents-python/)
- [Temporal](https://temporal.io/)
- [Rich](https://github.com/Textualize/rich)

---

**⭐ If you find PISA useful, please star the repository!**

Made with ❤️ by [Prismer AI Lab](https://github.com/Prismer-AI)

