"""
Crawl Tool

Crawl Tool is a tool for crawling the internet for information using crawl4ai.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any

try:
    from crawl4ai import AsyncWebCrawler
    try:
        from crawl4ai.async_configs import BrowserConfig
        HAS_BROWSER_CONFIG = True
    except ImportError:
        HAS_BROWSER_CONFIG = False
    HAS_CRAWL4AI = True
except ImportError:
    HAS_CRAWL4AI = False
    HAS_BROWSER_CONFIG = False

# Optional CapSolver integration for advanced CAPTCHA solving
try:
    from capsolver import CapSolver
    HAS_CAPSOLVER = True
except ImportError:
    HAS_CAPSOLVER = False


_logger = logging.getLogger(__name__)

# Import capability decorator
try:
    from pisa.capability import capability
    HAS_CAPABILITY = True
except ImportError:
    HAS_CAPABILITY = False
    _logger.warning("pisa.capability not available, @capability decorator will not work")


@capability(capability_type="function", name="crawl_tool")
class CrawlTool():
    """
    Crawl Tool using crawl4ai
    
    A powerful web crawling tool that can extract content from web pages,
    supporting JavaScript-rendered pages, markdown conversion, and more.
    """
    
    def __init__(self):
        if not HAS_CRAWL4AI:
            _logger.warning(
                "crawl4ai is not installed. Please install it with: pip install crawl4ai"
            )
        
        # Default configuration for bypassing Cloudflare and anti-bot protection
        # These will be used when bypass_cloudflare=True
        self.default_crawler_config = {
            "headless": True,  # Run in headless mode
            "verbose": False,  # Reduce logging noise
            "browser_type": "chromium",  # Use Chromium for better compatibility
        }

    async def _crawl_single_url(
        self,
        url: str,
        output_format: str = "markdown",
        wait_for: Optional[str] = None,
        screenshot: bool = False,
        bypass_cloudflare: bool = True,
        wait_time: Optional[float] = None,
        capsolver_api_key: Optional[str] = None,
        use_persistent_context: bool = False,
        user_data_dir: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Crawl a single URL (internal method)
        
        Args:
            url: The URL to crawl
            output_format: Output format - "markdown", "html", "text", or "json"
            wait_for: Optional CSS selector to wait for before extracting content
            screenshot: Whether to take a screenshot
            bypass_cloudflare: Whether to enable Cloudflare bypass features (default: True)
            wait_time: Optional wait time in seconds after page load (useful for Cloudflare)
            **kwargs: Additional parameters for crawl4ai
        
        Returns:
            Dictionary containing the crawled content and metadata
        """
        try:
            # Ensure URL has protocol
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            
            # Prepare crawler configuration for Cloudflare bypass
            # crawl4ai's AsyncWebCrawler accepts: config (BrowserConfig), crawler_strategy, etc.
            crawler_kwargs: Dict[str, Any] = {}
            
            if bypass_cloudflare:
                # Configure browser to bypass Cloudflare detection
                # Use BrowserConfig if available, otherwise use basic parameters
                if HAS_BROWSER_CONFIG:
                    try:
                        # Enhanced browser arguments to better mimic real browser
                        extra_args = [
                            "--disable-blink-features=AutomationControlled",  # Hide automation
                            "--disable-dev-shm-usage",
                            "--no-sandbox",
                            "--disable-setuid-sandbox",
                            "--disable-web-security",  # Disable web security for better compatibility
                            "--disable-features=IsolateOrigins,site-per-process",  # Disable site isolation
                            "--disable-site-isolation-trials",
                            "--disable-infobars",  # Hide automation info bars
                            "--window-size=1920,1080",  # Set realistic window size
                        ]
                        
                        # Create BrowserConfig with enhanced stealth settings for Cloudflare bypass
                        # Reference: https://www.capsolver.com/blog/Partners/crawl4ai-capsolver/
                        browser_config = BrowserConfig(
                            headless=True,
                            verbose=False,
                            enable_stealth=True,  # Enable stealth mode to bypass detection
                            extra_args=extra_args,
                            # Set realistic user agent (Chrome on macOS)
                            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            # Use persistent context to maintain session state (helps with Cloudflare)
                            use_persistent_context=use_persistent_context,
                            user_data_dir=user_data_dir,
                            # Set realistic viewport
                            viewport_width=1920,
                            viewport_height=1080,
                            # Enable JavaScript (required for Cloudflare challenges)
                            java_script_enabled=True,
                            # Ignore HTTPS errors (some sites have certificate issues)
                            ignore_https_errors=True,
                        )
                        crawler_kwargs["config"] = browser_config
                    except Exception as e:
                        _logger.debug(f"Could not create BrowserConfig: {e}, using basic config")
                        # Fallback to basic parameters
                        crawler_kwargs.update({
                            "headless": True,
                            "verbose": False,
                        })
                else:
                    # Fallback: use basic parameters if BrowserConfig is not available
                    crawler_kwargs.update({
                        "headless": True,
                        "verbose": False,
                    })
            else:
                # Basic configuration without Cloudflare bypass
                crawler_kwargs.update({
                    "headless": True,
                    "verbose": False,
                })
            
            # Merge with any custom config from kwargs (avoid conflicts)
            if "crawler_config" in kwargs:
                custom_config = kwargs.pop("crawler_config")
                # Only update if it doesn't conflict with existing keys
                for key, value in custom_config.items():
                    if key not in crawler_kwargs:
                        crawler_kwargs[key] = value
            
            # Prepare crawl4ai parameters for arun()
            crawl_params: Dict[str, Any] = {
                "url": url,
            }
            
            # Add optional parameters
            if wait_for:
                crawl_params["wait_for"] = wait_for
            
            if screenshot:
                crawl_params["screenshot"] = True
            
            # Add wait_time if specified (useful for Cloudflare challenges)
            # crawl4ai uses 'delay_before_return_html' or 'page_delay' parameter
            # For Cloudflare-protected sites, longer wait times are recommended (10-15 seconds)
            if wait_time:
                # Use the most common parameter name
                crawl_params["delay_before_return_html"] = wait_time
                # Also try page_delay as alternative
                if "page_delay" not in crawl_params:
                    crawl_params["page_delay"] = wait_time
            
            # CapSolver integration for advanced CAPTCHA solving (optional)
            # Reference: https://www.capsolver.com/blog/Partners/crawl4ai-capsolver/
            if capsolver_api_key and HAS_CAPSOLVER:
                try:
                    capsolver = CapSolver(api_key=capsolver_api_key)
                    # Note: CapSolver integration requires additional setup
                    # For Cloudflare Turnstile, we would need to:
                    # 1. Detect the CAPTCHA on the page
                    # 2. Call CapSolver API to get the token
                    # 3. Inject the token using js_code parameter
                    # This is a simplified version - full implementation would require
                    # detecting the CAPTCHA type and site key from the page
                    _logger.info("CapSolver API key provided, but full integration requires detecting CAPTCHA type and site key")
                except Exception as e:
                    _logger.warning(f"CapSolver initialization failed: {e}")
            
            # Add any additional kwargs to crawl_params
            crawl_params.update(kwargs)
            
            # Perform crawling with configured crawler
            # Create crawler with anti-bot configuration
            # For Cloudflare-protected sites, we may need multiple attempts
            max_retries = 2 if bypass_cloudflare else 1
            last_error = None
            result = None
            
            for attempt in range(max_retries):
                try:
                    async with AsyncWebCrawler(**crawler_kwargs) as crawler:
                        result = await crawler.arun(**crawl_params)
                        if result and result.markdown:
                            # Check if we got blocked by Cloudflare
                            content_lower = result.markdown.lower()
                            if any(indicator in content_lower for indicator in [
                                "checking your browser", "just a moment", "please wait",
                                "cloudflare", "ddos protection", "access denied",
                                "正在验证", "请稍候", "验证中"
                            ]):
                                if attempt < max_retries - 1:
                                    _logger.warning(f"Cloudflare challenge detected, retrying (attempt {attempt + 1}/{max_retries})...")
                                    # Increase wait time for retry
                                    if wait_time:
                                        crawl_params["delay_before_return_html"] = wait_time * (attempt + 2)
                                    await asyncio.sleep(5)  # Wait before retry
                                    continue
                                else:
                                    _logger.warning("Cloudflare challenge detected but max retries reached")
                            else:
                                # Success - we got actual content
                                break
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    
                    # Check if it's a network/connection error that shouldn't be retried
                    is_connection_error = any(indicator in error_str for indicator in [
                        "err_connection_closed",
                        "err_connection_refused",
                        "err_connection_reset",
                        "err_connection_timed_out",
                        "err_name_not_resolved",
                        "net::err_connection",
                        "connection closed",
                        "connection refused",
                        "connection reset",
                        "connection timed out",
                        "name not resolved",
                    ])
                    
                    if is_connection_error:
                        # Network errors are usually not retryable (server down, DNS issues, etc.)
                        _logger.warning(f"Network/connection error for {url}: {e}")
                        # Don't retry connection errors, just log and continue
                        break
                    elif attempt < max_retries - 1:
                        _logger.warning(f"Crawl attempt {attempt + 1} failed: {e}, retrying...")
                        await asyncio.sleep(3)  # Wait before retry
                    else:
                        _logger.error(f"All crawl attempts failed: {e}")
            
            if not result:
                if last_error:
                    return {
                        "url": url,
                        "success": False,
                        "error": f"Failed to crawl URL after {max_retries} attempts: {str(last_error)}",
                        "content": None,
                        "content_length": 0,
                        "metadata": {}
                    }
                else:
                    return {
                        "url": url,
                        "success": False,
                        "error": "Failed to crawl URL - no result returned",
                        "content": None,
                        "content_length": 0,
                        "metadata": {}
                    }
            
            # Extract content based on output format
            content = None
            if output_format == "markdown":
                content = result.markdown or result.cleaned_html or result.html
            elif output_format == "html":
                content = result.html or result.cleaned_html
            elif output_format == "text":
                content = result.text or result.markdown
            elif output_format == "json":
                # Return structured data
                return {
                    "url": url,
                    "success": result.success if hasattr(result, 'success') else True,
                    "markdown": result.markdown,
                    "html": result.html,
                    "cleaned_html": result.cleaned_html if hasattr(result, 'cleaned_html') else None,
                    "text": result.text if hasattr(result, 'text') else None,
                    "metadata": {
                        "title": result.metadata.get("title") if hasattr(result, 'metadata') and result.metadata else None,
                        "description": result.metadata.get("description") if hasattr(result, 'metadata') and result.metadata else None,
                        "links": result.links if hasattr(result, 'links') else [],
                        "images": result.images if hasattr(result, 'images') else [],
                    } if hasattr(result, 'metadata') else {},
                    "screenshot": result.screenshot if screenshot and hasattr(result, 'screenshot') else None,
                }
            
            # Return content in requested format
            return {
                "url": url,
                "output_format": output_format,
                "success": result.success if hasattr(result, 'success') else True,
                "content": content,
                "content_length": len(content) if content else 0,
                "metadata": {
                    "title": result.metadata.get("title") if hasattr(result, 'metadata') and result.metadata else None,
                    "description": result.metadata.get("description") if hasattr(result, 'metadata') and result.metadata else None,
                    "links_count": len(result.links) if hasattr(result, 'links') else 0,
                    "images_count": len(result.images) if hasattr(result, 'images') else 0,
                } if hasattr(result, 'metadata') else {},
            }
                
        except Exception as e:
            error_str = str(e).lower()
            
            # Categorize errors for better error messages
            if any(indicator in error_str for indicator in [
                "err_connection_closed",
                "err_connection_refused",
                "err_connection_reset",
                "err_connection_timed_out",
                "net::err_connection",
            ]):
                error_type = "Network connection error"
                error_msg = f"Connection failed: {str(e)}"
            elif "timeout" in error_str:
                error_type = "Timeout error"
                error_msg = f"Request timed out: {str(e)}"
            elif "cloudflare" in error_str or "ddos" in error_str or "access denied" in error_str:
                error_type = "Cloudflare/Access denied"
                error_msg = f"Blocked by Cloudflare or access denied: {str(e)}"
            else:
                error_type = "Unknown error"
                error_msg = str(e)
            
            _logger.error(f"Error crawling {url} ({error_type}): {e}", exc_info=False)
            return {
                "url": url,
                "success": False,
                "error": error_msg,
                "error_type": error_type,
                "content": None,
                "content_length": 0,
                "metadata": {}
            }

    async def run(
        self,
        url: str | list[str],
        output_format: str = "markdown",
        wait_for: Optional[str] = None,
        screenshot: bool = False,
        max_concurrent: Optional[int] = None,
        bypass_cloudflare: bool = True,
        wait_time: Optional[float] = None,
        capsolver_api_key: Optional[str] = None,
        use_persistent_context: bool = False,
        user_data_dir: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Run the crawl tool - supports single URL or multiple URLs with concurrent processing
        
        Args:
            url: Single URL string or list of URLs to crawl
            output_format: Output format - "markdown", "html", "text", or "json" (default: "markdown")
            wait_for: Optional CSS selector to wait for before extracting content (applies to all URLs)
            screenshot: Whether to take a screenshot (default: False)
            max_concurrent: Maximum number of concurrent crawls (default: None, no limit)
            bypass_cloudflare: Whether to enable Cloudflare bypass features (default: True)
            wait_time: Optional wait time in seconds after page load (useful for Cloudflare challenges, default: None)
            **kwargs: Additional parameters for crawl4ai (e.g., word_count_threshold, extraction_strategy)
        
        Returns:
            JSON string containing the crawled content and metadata.
            For single URL: returns single result object.
            For multiple URLs: returns object with "results" array and summary statistics.
        """
        if not HAS_CRAWL4AI:
            return json.dumps({
                "error": "crawl4ai is not installed. Please install it with: pip install crawl4ai",
                "url": url,
                "content": None
            }, indent=2, ensure_ascii=False)
        
        try:
            # Normalize input: convert single URL to list
            is_single_url = isinstance(url, str)
            urls = [url] if is_single_url else url
            
            # Validate URLs
            if not urls:
                return json.dumps({
                    "error": "No URLs provided",
                    "url": url,
                    "content": None
                }, indent=2, ensure_ascii=False)
            
            # Validate each URL
            validated_urls = []
            for u in urls:
                if not u or not isinstance(u, str):
                    _logger.warning(f"Invalid URL skipped: {u}")
                    continue
                validated_urls.append(u)
            
            if not validated_urls:
                return json.dumps({
                    "error": "No valid URLs provided",
                    "url": url,
                    "content": None
                }, indent=2, ensure_ascii=False)
            
            # Validate output format
            valid_formats = ["markdown", "html", "text", "json"]
            if output_format not in valid_formats:
                _logger.warning(f"Invalid output_format '{output_format}', using 'markdown'")
                output_format = "markdown"
            
            # Create tasks for concurrent crawling
            tasks = [
                self._crawl_single_url(
                    url=u,
                    output_format=output_format,
                    wait_for=wait_for,
                    screenshot=screenshot,
                    bypass_cloudflare=bypass_cloudflare,
                    wait_time=wait_time,
                    **kwargs
                )
                for u in validated_urls
            ]
            
            # Execute tasks with optional concurrency limit
            if max_concurrent and max_concurrent > 0:
                # Use semaphore to limit concurrent requests
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def bounded_crawl(task):
                    async with semaphore:
                        return await task
                
                results = await asyncio.gather(
                    *[bounded_crawl(task) for task in tasks],
                    return_exceptions=True
                )
            else:
                # No limit, execute all concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle exceptions
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_str = str(result).lower()
                    error_type = "Unknown error"
                    
                    # Categorize errors for better error messages
                    if any(indicator in error_str for indicator in [
                        "err_connection_closed",
                        "err_connection_refused",
                        "err_connection_reset",
                        "err_connection_timed_out",
                        "net::err_connection",
                    ]):
                        error_type = "Network connection error"
                    elif "timeout" in error_str:
                        error_type = "Timeout error"
                    elif "cloudflare" in error_str or "ddos" in error_str:
                        error_type = "Cloudflare/Access denied"
                    
                    url = validated_urls[i] if i < len(validated_urls) else "unknown"
                    _logger.warning(f"Exception crawling {url} ({error_type}): {result}")
                    processed_results.append({
                        "url": url,
                        "success": False,
                        "error": str(result),
                        "error_type": error_type,
                        "content": None,
                        "content_length": 0,
                        "metadata": {}
                    })
                else:
                    processed_results.append(result)
            
            # Calculate summary statistics
            total_urls = len(validated_urls)
            successful = sum(1 for r in processed_results if r.get("success", False))
            failed = total_urls - successful
            total_content_length = sum(r.get("content_length", 0) for r in processed_results)
            
            # Return results
            if is_single_url:
                # Single URL: return the result directly
                return json.dumps(processed_results[0], indent=2, ensure_ascii=False)
            else:
                # Multiple URLs: return array with summary
                return json.dumps({
                    "total_urls": total_urls,
                    "successful": successful,
                    "failed": failed,
                    "total_content_length": total_content_length,
                    "results": processed_results
                }, indent=2, ensure_ascii=False)
                
        except Exception as e:
            _logger.error(f"Error in CrawlTool: {e}", exc_info=True)
            return json.dumps({
                "error": str(e),
                "url": url,
                "content": None
            }, indent=2, ensure_ascii=False)
            
            
            
async def main():
    """
    Main function to test the crawl tool - demonstrates both single and concurrent crawling
    """
    crawl_tool = CrawlTool()
    
    # # Example 1: Single URL (backward compatible)
    # print("=" * 60)
    # print("Example 1: Single URL")
    # print("=" * 60)
    # result = await crawl_tool.run(
    #     url="https://www.promptingguide.ai/guides/context-engineering-guide",
    #     output_format="markdown"
    # )
    # result_dict = json.loads(result)
    # content = result_dict["content"]
    # print(f"✓ Success: {result_dict.get('success')}")
    # print(f"✓ Content length: {result_dict.get('content_length', 0)} characters")
    # print(f"✓ Title: {result_dict.get('metadata', {}).get('title', 'N/A')}")
    
    # # Save single result (only if content is not None)
    # if content:
    #     with open("data/input/crawl_result.md", "w") as f:
    #         f.write(content)
    # else:
    #     print("⚠ Warning: No content to save (crawl may have failed)")
    
    # Example 2: Multiple URLs (concurrent processing)
    print("\n" + "=" * 60)
    print("Example 2: Multiple URLs (Concurrent)")
    print("=" * 60)
    urls = [
        # "https://www.promptingguide.ai/guides/context-engineering-guide",
        # "https://www.nature.com/",
        # "https://openai.github.io/openai-agents-python/examples/",
        # "https://www.alphaxiv.org/",
        # "https://www.science.org/",
        # "https://openreview.net/",
        # "https://www.thelancet.com/latest-research",
        # # "https://scholar.google.com",
        # "https://arxiv.org",
        # "https://pubmed.ncbi.nlm.nih.gov/trending/?filter=dates.2025%2F11%2F1-2025%2F11%2F11&sort=date",
        # "https://ieeexplore.ieee.org",
        # "https://dl.acm.org",
        # "https://link.springer.com",
        # "https://www.nature.com",
        # "https://www.science.org",
        # "https://www.jstor.org",
        # "https://www.scopus.com",
        # "https://www.webofscience.com",
        # "https://www.researchgate.net",
        # "https://www.semanticscholar.org",
        # "https://papers.ssrn.com",
        # "https://www.plos.org",
        # "https://doaj.org",
        # "https://core.ac.uk",
        # "https://pubchem.ncbi.nlm.nih.gov",
        # "https://www.nih.gov",
        # "https://www.crossref.org",
        # "https://repec.org",
        # "https://ui.adsabs.harvard.edu",  # NASA Astrophysics Data System (ADS)
        # "https://www.biorxiv.org",
        # "https://www.medrxiv.org",
        # "https://www.openaire.eu"
        "https://www.linkedin.com/in/zoeysun120/",
        "https://karpathy.ai/"
    ]
    
    result_multi = await crawl_tool.run(
        url=urls,
        output_format="markdown",
        max_concurrent=12,  # Limit to 8 concurrent requests
        bypass_cloudflare=True,  # Enable Cloudflare bypass
        wait_time=20,  # Wait 15 seconds for Cloudflare challenges to complete
        # Optional: Uncomment and set your CapSolver API key for advanced CAPTCHA solving
        # capsolver_api_key="YOUR_CAPSOLVER_API_KEY",
        # use_persistent_context=True,  # Use persistent browser context to maintain session
        # user_data_dir="/tmp/crawl4ai_profile",  # Directory for browser profile
    )
    result_multi_dict = json.loads(result_multi)
    for i, result in enumerate(result_multi_dict.get('results', [])):
        content = result.get("content")
        if content:
            with open(f"data/input/crawl_result_{i}.md", "w") as f:
                f.write(content)
        else:
            _logger.warning(f"No content for URL {i}: {result.get('url', 'unknown')}")
    print(f"✓ Total URLs: {result_multi_dict.get('total_urls')}")
    print(f"✓ Successful: {result_multi_dict.get('successful')}")
    print(f"✓ Failed: {result_multi_dict.get('failed')}")
    print(f"✓ Total content length: {result_multi_dict.get('total_content_length')} characters")
    
    # Print results for each URL
    for i, res in enumerate(result_multi_dict.get('results', []), 1):
        print(f"\n  URL {i}: {res.get('url')}")
        print(f"    Success: {res.get('success')}")
        print(f"    Content length: {res.get('content_length', 0)} characters")
        if not res.get('success'):
            print(f"    Error: {res.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())