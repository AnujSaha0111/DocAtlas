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
        if not url:
            return False
            
        base_domain = urlparse(base_url).netloc
        url_domain = urlparse(url).netloc
        
        skip_extensions = ['.pdf', '.jpg', '.png', '.gif', '.jpeg', '.svg', '.mp4', '.zip', '.css', '.js']
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            return False
            
        skip_patterns = ['/cdn-cgi/', '/wp-content/', '/wp-includes/', '/static/', '/assets/']
        if any(pattern in url for pattern in skip_patterns):
            return False
            
        return url_domain == base_domain or url_domain.endswith('.' + base_domain)
    
    def extract_clean_text(self, url):
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title = soup.title.string if soup.title else "Untitled"
            self.url_titles[url] = title.strip()
            
            metadata = self.extract_metadata(soup, url)
            self.url_metadata[url] = metadata
            
            main_content = self.identify_main_content(soup)
            
            doc_structure = self.extract_document_structure(main_content or soup)
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
        
        for meta in soup.find_all('meta'):
            if meta.get('name') and meta.get('content'):
                metadata["meta_tags"][meta['name']] = meta['content']
            elif meta.get('property') and meta.get('content'):
                metadata["meta_tags"][meta['property']] = meta['content']
        
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
        content_selectors = [
            'main', 'article', '[role="main"]',
            '.main-content', '.content-main', '.article-content', '.documentation',
            '#main-content', '#content', '#main', '#docs', '#documentation',
            '.container', '.content', '.page-content'
        ]
        
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                if len(elements) > 1:
                    return max(elements, key=lambda e: len(e.get_text()))
                return elements[0]
        
        candidates = soup.find_all('div', recursive=True)
        if candidates:
            filtered = [div for div in candidates if len(div.get_text().strip()) > 200]
            if filtered:
                return max(filtered, key=lambda e: len(e.get_text()))
        
        return None
    
    def extract_document_structure(self, element):
        structure = {
            "headings": [],
            "lists": [],
            "tables": [],
            "code_blocks": []
        }
        
        if not element:
            return structure
        
        for i in range(1, 7):
            for heading in element.find_all(f'h{i}'):
                structure["headings"].append({
                    "level": i,
                    "text": heading.get_text().strip(),
                    "id": heading.get('id', '')
                })
        
        for list_elem in element.find_all(['ul', 'ol']):
            items = []
            for li in list_elem.find_all('li', recursive=False):
                nested_lists = []
                for nested in li.find_all(['ul', 'ol'], recursive=False):
                    nested_items = [item.get_text().strip() for item in nested.find_all('li')]
                    nested_lists.append({
                        "type": nested.name,
                        "items": nested_items
                    })
                
                list_text = li.get_text().strip()
                for nested in li.find_all(['ul', 'ol'], recursive=False):
                    nested_text = nested.get_text().strip()
                    list_text = list_text.replace(nested_text, '')
                
                items.append({
                    "text": list_text.strip(),
                    "nested_lists": nested_lists
                })
            
            structure["lists"].append({
                "type": list_elem.name,  
                "items": items
            })
        
        for table in element.find_all('table'):
            rows = []
            
            headers = []
            for th in table.find_all('th'):
                headers.append(th.get_text().strip())
            
            for tr in table.find_all('tr'):
                row = [td.get_text().strip() for td in tr.find_all(['td'])]
                if row: 
                    rows.append(row)
            
            structure["tables"].append({
                "headers": headers,
                "rows": rows
            })
        
        for code in element.find_all(['pre', 'code']):
            if code.name == 'code' and code.parent.name == 'pre':
                continue
                
            structure["code_blocks"].append({
                "type": code.name,
                "text": code.get_text(),
                "language": code.get('class', [''])[0] if code.get('class') else ''
            })
        
        return structure
    
    def generate_structured_text(self, element):
        if not element:
            return ""
            
        for unwanted in element.find_all(["script", "style", "nav", "footer", "header", "aside"]):
            unwanted.extract()
        
        html = str(element)
        markdown_text = self.h2t.handle(html)
        
        for i in range(6, 0, -1): 
            markdown_text = re.sub(r'<h{0}>(.*?)</h{0}>'.format(i), r'{"#" * i} \1', markdown_text)
        
        markdown_text = re.sub(r'```\n', '```\n', markdown_text)
        
        return markdown_text
    
    def get_links(self, url, current_depth):
        try:
            if current_depth >= self.max_depth:
                logging.info(f"Reached maximum depth ({self.max_depth}) at {url}, not extracting further links")
                return []
                
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            links = []
            
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                
                if not href or href.startswith('javascript:') or href == '#':
                    continue
                    
                full_url = urljoin(url, href)
                
                full_url = re.sub(r'#.*$', '', full_url)
                
                if self.is_valid_url(full_url, url) and full_url not in self.visited_urls:
                    links.append(full_url)
                    
                    self.url_hierarchy[url].append(full_url)
                    
                    self.url_depths[full_url] = current_depth + 1
                    
                    link_text = a_tag.get_text(strip=True)
                    if link_text and full_url not in self.url_titles:
                        self.url_titles[full_url] = link_text
                    
            return links
        except Exception as e:
            logging.error(f"Error extracting links from {url}: {e}")
            return []
    
    def prioritize_urls(self, url_list):
        documentation_patterns = [
            'article', 'doc', 'help', 'guide', 'faq', 'tutorial', 'support',
            'manual', 'reference', 'category', 'section', 'topic', 'content'
        ]
        
        def get_url_priority(url):
            url_lower = url.lower()
            if any(pattern in url_lower for pattern in documentation_patterns):
                return 0  
            
            path_depth = url.count('/')
            return path_depth
        
        return sorted(url_list, key=get_url_priority)
    
    def crawl(self, start_url):
        self.visited_urls = set()
        self.queue = [(start_url, 0)]  
        self.content_map = {}
        self.url_hierarchy = defaultdict(list)
        self.url_titles = {}
        self.url_depths = {start_url: 0} 
        self.url_metadata = {}
        self.url_structure = {}
        
        while self.queue and len(self.visited_urls) < self.max_pages:
            current_url, current_depth = self.queue.pop(0)
            
            if current_url in self.visited_urls:
                continue
                
            logging.info(f"Crawling: {current_url} (depth {current_depth})")
            self.visited_urls.add(current_url)
            
            time.sleep(self.delay)
            
            content = self.extract_clean_text(current_url)
            if content.strip():
                self.content_map[current_url] = content
                
            links = self.get_links(current_url, current_depth)
            
            if current_depth < self.max_depth:
                prioritized_links = self.prioritize_urls(links)
                
                for link in prioritized_links:
                    if link not in self.visited_urls and link not in [u for u, _ in self.queue]:
                        self.queue.append((link, current_depth + 1))
            
        logging.info(f"Crawling completed. Processed {len(self.visited_urls)} URLs.")
        logging.info(f"Found content on {len(self.content_map)} pages.")
        
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
