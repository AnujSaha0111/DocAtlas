import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin, urlparse
import logging
import re
import time
from collections import defaultdict
import json
import html2text
import asyncio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Crawler:
    def __init__(self, max_pages=100, delay=0.5, max_depth=1):
        self.visited_urls = set()
        self.queue = []
        self.content_map = {}
        self.max_pages = max_pages
        self.delay = delay 
        self.max_depth = max_depth
        
        self.url_hierarchy = defaultdict(list)
        self.url_titles = {}
        self.url_depths = {}  
        self.url_metadata = {} 
        self.url_structure = {} 
                self.h2t = html2text.HTML2Text()
        self.h2t.body_width = 0 
        self.h2t.ignore_links = False
        self.h2t.ignore_images = True
        self.h2t.ignore_tables = False
        self.h2t.unicode_snob = True
        self.h2t.bypass_tables = False
        self.h2t.mark_code = True
        
    def is_valid_url(self, url, base_url):
        """Check if URL is valid and belongs to the same domain"""
        if not url:
            return False
            
        base_domain = urlparse(base_url).netloc
        url_domain = urlparse(url).netloc
        
        skip_extensions = ['.pdf', '.jpg', '.png', '.gif', '.jpeg', '.svg', '.mp4', '.zip', '.css', '.js']
        if any(url.lower().endswith(ext) for oup)
            self.url_structure[url] = doc_structure
            
            enhanced_text = self.generate_structured_text(main_content or soup)
            try:
                import trafilatura
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        asyncio.set_event_loop(asyncio.new_event_loop())
                except RuntimeError:
                    asyncio.set_event_loop(asyncio.new_event_loop())
                    
                downloaded = trafilatura.fetch_url(url)
                if downloaded:
                    traf_text = trafilatura.extract(downloaded, include_links=True, include_formatting=True)
                    if traf_text and len(traf_text) > len(enhanced_text) * 0.7:
                        return traf_text
            except Exception:
                pass
                
            return enhanced_text
            
        except Exception as e:
            logging.error(f"Error extracting content from {url}: {e}")
            return ""
    
    def extract_metadata(self, soup, url):
        metadata = {
            "url": url,
            "timestamp": time.time(),
            "meta_tags": {}
        }
        
        # Extract meta tags
        for meta in soup.find_all('meta'):
            if meta.get('name') and meta.get('content'):
                metadata["meta_tags"][meta['name']] = meta['content']
            elif meta.get('property') and meta.get('content'):
                metadata["meta_tags"][meta['property']] = meta['content']
        
        # Try to find last updated date
        date_patterns = [
            r'Last updated:?\s*([A-Za-z]+ \d+,? \d{4})',
            r'Updated:?\s*([A-Za-z]+ \d+,? \d{4})',
            r'Published:?\s*([A-Za-z]+ \d+,? \d{4})'
        ]
        
        text = soup.get_text()
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                metadata["last_updated"] = match.group(1)
                break
        
        return metadata
    
    def identify_main_content(self, soup):
        """
        Identify the main content area of the page using common selectors
        Returns the main content element, or None if no suitable element is found
        """
        # Common selectors for main content, in order of preference
        content_selectors = [
            'main', 'article', '[role="main"]',
            '.main-content', '.content-main', '.article-content', '.documentation',
            '#main-content', '#content', '#main', '#docs', '#documentation',
            '.container', '.content', '.page-content'
        ]
        
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                # Select the largest content block by text length if multiple elements match
                if len(elements) > 1:
                    return max(elements, key=lambda e: len(e.get_text()))
                return elements[0]
        
        # If no main content found by selectors, try some heuristics
        # Find largest <div> with significant content
        candidates = soup.find_all('div', recursive=True)
        if candidates:
            filtered = [div for div in candidates if len(div.get_text().strip()) > 200]
            if filtered:
                return max(filtered, key=lambda e: len(e.get_text()))
        
        return None
    
    def extract_document_structure(self, element):
        """
        Extract structured information about the document's organization
        ].append({
                    "level": i,
                    "text": heading.get_text().strip(),
                    "id": heading.get('id', '')
                })
        
        # Extract lists
        for list_ele
            'article', 'doc', 'help', 'guide', 'faq', 'tutorial', 'support',
            'manual', 'reference', 'category', 'section', 'topic', 'content'
        ]
        
        def get_url_priority(url):
            # Give higher priority to URLs with documentation-related patterns
            url_lower = url.lower()
            if any(pattern in url_lower for pattern in documentation_patterns):
                return 0  # Highest priority
            
            # Paths with fewer segments are likely higher-level pages
            path_depth = url.count('/')
            return path_depth
        
        # Sort URLs by priority (lower number = higher priority)
        return sorted(url_list, key=get_url_priority)
    
    def crawl(self, start_url):
        """Crawl the website starting from the given URL"""
        self.visited_urls = set()
        self.queue = [(start_url, 0)]  # (url, depth) pairs
        self.content_map = {}
        self.url_hierarchy = defaultdict(list)
        self.url_titles = {}
        self.url_depths = {start_url: 0}  # Start URL has depth 0
        self.url_metadata = {}
        self.url_structure = {}
        
        while self.queue and len(self.visited_urls) < self.max_pages:
            # Get next URL and its depth (breadth-first traversal is better for documentation sites)
            current_url, current_depth = self.queue.pop(0)
            
            if current_url in self.visited_urls:
                continue
                
            logging.info(f"Celf.visited_urls)} URLs.")
        logging.info(f"Found content on {len(self.content_map)} pages.")
        
        # Return both content and structure information
        result = {
            "content": self.content_map,
            "hierarchy": dict(self.url_hierarchy),
            "titles": self.url_titles,
            "depths": self.url_depths,
            "metadata": self.url_metadata,
            "structure": self.url_structure
        }
        
        return result

    def crawl_multiple(self, urls):
        """Crawl multiple starting URLs and combine results"""
        all_results = {
            "content": {},
            "hierarchy": {},
            "titles": {},
            "depths": {},
            "metadata": {},
            "structure": {}
        }
        
        for url in urls:
            result = self.crawl(url)
            all_results["content"].update(result["content"])
            all_results["hierarchy"].update(result["hierarchy"])
            all_results["titles"].update(result["titles"])
            all_results["depths"].update(result["depths"])
            all_results["metadata"].update(result["metadata"])
            all_results["structure"].update(result["structure"])
            
        return all_results
