"""
Unified Search Capability

统一的搜索接口，支持多种搜索引擎：
- web: 网络搜索（Serper API）
- arxiv: arXiv 学术论文
- pubmed: PubMed 医学文献
- nature: Nature 期刊
- science: Science 期刊
- exa: Exa 神经搜索

Note: Capabilities are auto-discovered by the registry.
This __init__.py file should not import them to avoid duplicate registration.
"""

__version__ = "3.0.0"
