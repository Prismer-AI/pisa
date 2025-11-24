# Copyright 2025 prismer
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     https://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Unified Search Capability

统一的搜索接口，支持多种搜索引擎：
- web: 通用网络搜索（使用 Serper API）
- exa: 研究论文和内容搜索（使用 Exa API）
- arxiv: arXiv 学术论文搜索
- pubmed: PubMed 医学文献搜索
- nature: Nature 期刊搜索
- science: Science 期刊搜索
"""

import os
from typing import Dict, Any, List, Optional, Literal
import httpx
from datetime import datetime

from pisa.capability import capability


# ============================================================
# 搜索引擎实现
# ============================================================

async def _search_web(
    query: str,
    num_results: int = 10,
    location: str = "United States",
    tbs: str = "qdr:w",
    country: str = "us",
    language: str = "en"
) -> Dict[str, Any]:
    """使用 Serper API 进行网络搜索"""
    api_key = os.getenv("SERPER_API_KEY") or os.getenv("SEARCH_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "SERPER_API_KEY or SEARCH_API_KEY not found in environment",
            "results": []
        }

    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "q": query,
        "location": location,
        "tbs": tbs,
        "num": num_results,
        "gl": country,
        "hl": language
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            results = []
            if "organic" in data:
                for item in data["organic"][:num_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "position": item.get("position", 0),
                        "source": "web"
                    })

            return {
                "success": True,
                "engine": "web",
                "query": query,
                "num_results": len(results),
                "results": results
            }

    except Exception as e:
        return {
            "success": False,
            "engine": "web",
            "error": str(e),
            "results": []
        }


async def _search_arxiv(
    query: str,
    num_results: int = 10,
    sort_by: str = "relevance"
) -> Dict[str, Any]:
    """使用 arXiv API 搜索学术论文"""
    try:
        import arxiv
        
        # 构建搜索客户端
        client = arxiv.Client()
        
        # 设置排序方式
        sort_order = arxiv.SortCriterion.Relevance
        if sort_by == "date":
            sort_order = arxiv.SortCriterion.SubmittedDate
        elif sort_by == "updated":
            sort_order = arxiv.SortCriterion.LastUpdatedDate
        
        # 创建搜索
        search = arxiv.Search(
            query=query,
            max_results=num_results,
            sort_by=sort_order
        )
        
        # 执行搜索
        results = []
        for paper in client.results(search):
            results.append({
                "title": paper.title,
                "url": paper.entry_id,
                "snippet": paper.summary[:300] + "..." if len(paper.summary) > 300 else paper.summary,
                "authors": [author.name for author in paper.authors],
                "published": paper.published.strftime("%Y-%m-%d"),
                "updated": paper.updated.strftime("%Y-%m-%d") if paper.updated else None,
                "categories": paper.categories,
                "pdf_url": paper.pdf_url,
                "source": "arxiv"
            })
        
        return {
            "success": True,
            "engine": "arxiv",
            "query": query,
            "num_results": len(results),
            "results": results
        }
        
    except ImportError:
        return {
            "success": False,
            "engine": "arxiv",
            "error": "arxiv package not installed. Install with: pip install arxiv",
            "results": []
        }
    except Exception as e:
        return {
            "success": False,
            "engine": "arxiv",
            "error": str(e),
            "results": []
        }


async def _search_pubmed(
    query: str,
    num_results: int = 10
) -> Dict[str, Any]:
    """使用 PubMed API 搜索医学文献"""
    try:
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 第一步：搜索获取 ID 列表
            search_url = f"{base_url}/esearch.fcgi"
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": num_results,
                "retmode": "json",
                "sort": "relevance"
            }
            
            search_response = await client.get(search_url, params=search_params)
            search_response.raise_for_status()
            search_data = search_response.json()
            
            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            
            if not id_list:
                return {
                    "success": True,
                    "engine": "pubmed",
                    "query": query,
                    "num_results": 0,
                    "results": []
                }
            
            # 第二步：获取详细信息
            fetch_url = f"{base_url}/esummary.fcgi"
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json"
            }
            
            fetch_response = await client.get(fetch_url, params=fetch_params)
            fetch_response.raise_for_status()
            fetch_data = fetch_response.json()
            
            results = []
            for pmid in id_list:
                if pmid in fetch_data.get("result", {}):
                    article = fetch_data["result"][pmid]
                    results.append({
                        "title": article.get("title", ""),
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        "snippet": article.get("title", ""),  # PubMed summary needs separate call
                        "authors": [author.get("name", "") for author in article.get("authors", [])],
                        "journal": article.get("source", ""),
                        "published": article.get("pubdate", ""),
                        "pmid": pmid,
                        "source": "pubmed"
                    })
            
            return {
                "success": True,
                "engine": "pubmed",
                "query": query,
                "num_results": len(results),
                "results": results
            }
            
    except Exception as e:
        return {
            "success": False,
            "engine": "pubmed",
            "error": str(e),
            "results": []
        }


async def _search_nature(
    query: str,
    num_results: int = 10
) -> Dict[str, Any]:
    """搜索 Nature 期刊"""
    try:
        search_url = "https://www.nature.com/search"
        params = {
            "q": query,
            "order": "relevance"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(search_url, params=params, headers=headers)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            articles = soup.find_all('article', limit=num_results)
            
            for article in articles:
                title_elem = article.find('h3') or article.find('h2')
                link_elem = article.find('a', href=True)
                snippet_elem = article.find('p')
                
                if title_elem and link_elem:
                    url = link_elem['href']
                    if not url.startswith('http'):
                        url = f"https://www.nature.com{url}"
                    
                    results.append({
                        "title": title_elem.get_text(strip=True),
                        "url": url,
                        "snippet": snippet_elem.get_text(strip=True) if snippet_elem else "",
                        "source": "nature"
                    })
            
            return {
                "success": True,
                "engine": "nature",
                "query": query,
                "num_results": len(results),
                "results": results
            }
            
    except ImportError:
        return {
            "success": False,
            "engine": "nature",
            "error": "beautifulsoup4 package not installed. Install with: pip install beautifulsoup4",
            "results": []
        }
    except Exception as e:
        return {
            "success": False,
            "engine": "nature",
            "error": str(e),
            "results": []
        }


async def _search_science(
    query: str,
    num_results: int = 10
) -> Dict[str, Any]:
    """搜索 Science 期刊"""
    try:
        search_url = "https://www.science.org/action/doSearch"
        params = {
            "AllField": query,
            "pageSize": num_results,
            "sortBy": "relevancy"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(search_url, params=params, headers=headers)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            articles = soup.find_all('div', class_='card-header', limit=num_results)
            
            for article in articles:
                title_elem = article.find('h3') or article.find('h2')
                link_elem = article.find('a', href=True)
                
                if title_elem and link_elem:
                    url = link_elem['href']
                    if not url.startswith('http'):
                        url = f"https://www.science.org{url}"
                    
                    # Find snippet in the card body
                    card_body = article.find_next_sibling('div', class_='card-body')
                    snippet = ""
                    if card_body:
                        snippet_elem = card_body.find('p')
                        if snippet_elem:
                            snippet = snippet_elem.get_text(strip=True)
                    
                    results.append({
                        "title": title_elem.get_text(strip=True),
                        "url": url,
                        "snippet": snippet,
                        "source": "science"
                    })
            
            return {
                "success": True,
                "engine": "science",
                "query": query,
                "num_results": len(results),
                "results": results
            }
            
    except ImportError:
        return {
            "success": False,
            "engine": "science",
            "error": "beautifulsoup4 package not installed. Install with: pip install beautifulsoup4",
            "results": []
        }
    except Exception as e:
        return {
            "success": False,
            "engine": "science",
            "error": str(e),
            "results": []
        }


async def _search_exa(
    query: str,
    num_results: int = 10,
    category: str = "research paper",
    max_characters: int = 5000,
    livecrawl: str = "never",
    user_location: str = "US"
) -> Dict[str, Any]:
    """使用 Exa API 进行研究和内容搜索"""
    api_key = os.getenv("EXA_API_KEY") or os.getenv("EXASEARCH_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "EXA_API_KEY not found in environment",
            "results": []
        }

    try:
        from exa_py import Exa

        # 初始化 Exa 客户端
        exa = Exa(api_key=api_key)

        # 执行搜索和内容获取
        result = exa.search_and_contents(
            query=query,
            category=category,
            context={
                "max_characters": max_characters
            },
            livecrawl=livecrawl,
            num_results=num_results,
            text=True,
            type="auto",
            user_location=user_location
        )

        # 处理结果
        results = []
        for item in result.results:
            results.append({
                "title": getattr(item, "title", ""),
                "url": getattr(item, "url", ""),
                "snippet": getattr(item, "text", "")[:500] + "..." if getattr(item, "text", "") and len(getattr(item, "text", "")) > 500 else getattr(item, "text", ""),
                "full_text": getattr(item, "text", ""),
                "author": getattr(item, "author", ""),
                "published_date": getattr(item, "published_date", ""),
                "score": getattr(item, "score", 0.0),
                "source": "exa"
            })

        return {
            "success": True,
            "engine": "exa",
            "query": query,
            "num_results": len(results),
            "results": results
        }

    except ImportError:
        return {
            "success": False,
            "engine": "exa",
            "error": "exa_py package not installed. Install with: pip install exa_py",
            "results": []
        }
    except Exception as e:
        return {
            "success": False,
            "engine": "exa",
            "error": str(e),
            "results": []
        }


# ============================================================
# 统一搜索接口
# ============================================================

@capability(
    name="search",
    description="Unified search interface supporting multiple engines: web (general), exa (research), arxiv (academic papers), pubmed (medical), nature (journal), science (journal)",
    capability_type="function",
    tags=["search", "web", "academic", "research"],
    auto_register=True
)
async def search(
    query: str,
    engine: Literal["web", "exa", "arxiv", "pubmed", "nature", "science"] = "web",
    num_results: int = 10,
    **kwargs
) -> Dict[str, Any]:
    """
    Unified search interface for multiple search engines.

    Args:
        query: Search query string
        engine: Search engine to use
            - "web": General web search using Serper API (requires SERPER_API_KEY)
            - "exa": Research and content search using Exa API (requires EXA_API_KEY)
            - "arxiv": Academic papers from arXiv
            - "pubmed": Medical literature from PubMed
            - "nature": Articles from Nature journal
            - "science": Articles from Science journal
        num_results: Maximum number of results to return (default: 10)
        **kwargs: Additional engine-specific parameters
            - For web: location (str), tbs (str), country (str), language (str)
            - For exa: category (str), max_characters (int), livecrawl (str), user_location (str)
            - For arxiv: sort_by (str: "relevance", "date", "updated")

    Returns:
        Dictionary containing:
        - success: Whether the search succeeded
        - engine: The engine used
        - query: The search query
        - num_results: Number of results returned
        - results: List of search results, each with:
            - title: Result title
            - url: Result URL
            - snippet: Brief description/abstract
            - source: Search engine name
            - (engine-specific fields)
        - error: Error message if success is False

    Examples:
        >>> # Web search with location and time filter
        >>> await search("apple inc", engine="web", location="United States", tbs="qdr:w")

        >>> # Research paper search with Exa
        >>> await search("XQGAN", engine="exa", category="research paper", max_characters=5000)

        >>> # Academic paper search
        >>> await search("transformer architecture", engine="arxiv", sort_by="date")

        >>> # Medical literature search
        >>> await search("COVID-19 treatment", engine="pubmed")

        >>> # Journal article search
        >>> await search("climate change", engine="nature")
    """
    # 参数验证
    num_results = max(1, min(num_results, 100))  # 限制在 1-100
    
    # 根据引擎分发搜索
    if engine == "web":
        location = kwargs.get("location", "United States")
        tbs = kwargs.get("tbs", "qdr:w")
        country = kwargs.get("country", "us")
        language = kwargs.get("language", "en")
        return await _search_web(query, num_results, location, tbs, country, language)

    elif engine == "exa":
        category = kwargs.get("category", "research paper")
        max_characters = kwargs.get("max_characters", 5000)
        livecrawl = kwargs.get("livecrawl", "never")
        user_location = kwargs.get("user_location", "US")
        return await _search_exa(query, num_results, category, max_characters, livecrawl, user_location)

    elif engine == "arxiv":
        sort_by = kwargs.get("sort_by", "relevance")
        return await _search_arxiv(query, num_results, sort_by)

    elif engine == "pubmed":
        return await _search_pubmed(query, num_results)

    elif engine == "nature":
        return await _search_nature(query, num_results)

    elif engine == "science":
        return await _search_science(query, num_results)

    else:
        return {
            "success": False,
            "error": f"Unknown engine: {engine}. Supported engines: web, exa, arxiv, pubmed, nature, science",
            "results": []
        }


# ============================================================
# 辅助函数：多引擎并行搜索
# ============================================================

@capability(
    name="search_multi",
    description="Search across multiple engines in parallel and aggregate results",
    capability_type="function",
    tags=["search", "multi-engine", "parallel"],
    auto_register=True
)
async def search_multi(
    query: str,
    engines: List[str] = ["web", "arxiv"],
    num_results_per_engine: int = 5
) -> Dict[str, Any]:
    """
    Search across multiple engines in parallel.
    
    Args:
        query: Search query string
        engines: List of engines to search (default: ["web", "arxiv"])
        num_results_per_engine: Results per engine (default: 5)
    
    Returns:
        Dictionary with aggregated results from all engines
    """
    import asyncio
    
    # 创建所有搜索任务
    tasks = []
    for engine in engines:
        if engine in ["web", "exa", "arxiv", "pubmed", "nature", "science"]:
            tasks.append(search(query, engine=engine, num_results=num_results_per_engine))
    
    # 并行执行所有搜索
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 聚合结果
    aggregated = {
        "success": True,
        "query": query,
        "engines": engines,
        "total_results": 0,
        "results_by_engine": {},
        "all_results": []
    }
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            continue
        
        if result.get("success"):
            engine = result["engine"]
            aggregated["results_by_engine"][engine] = result
            aggregated["all_results"].extend(result["results"])
            aggregated["total_results"] += result["num_results"]
    
    return aggregated
