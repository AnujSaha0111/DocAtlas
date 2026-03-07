import os
import json
import logging
from openai import OpenAI
try:
    import google.genai as genai  # new package
except ImportError:
    import google.generativeai as genai  # fallback to old package
from groq import Groq
import time
from urllib.parse import urlparse
import re
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ModuleExtractor:
    def __init__(self, api_key=None, model="gpt-3.5-turbo", provider="openai"):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        
        if self.provider == "openai":
            self.api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OpenAI API key is required. Set it using the OPENAI_API_KEY environment variable.")
            self.client = OpenAI(api_key=self.api_key)
            logging.info(f"Using OpenAI model: {self.model}")
            
        elif self.provider == "gemini":
            self.api_key = self.api_key or os.getenv("GEMINI_API_KEY")
            if not self.api_key:
                raise ValueError("Gemini API key is required. Set it using the GEMINI_API_KEY environment variable.")
            try:
                self.client = genai.Client(api_key=self.api_key)
                self._gemini_new_api = True
            except AttributeError:
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(self.model)
                self._gemini_new_api = False
            logging.info(f"Using Google Gemini model: {self.model}")
            
        elif self.provider == "groq":
            self.api_key = self.api_key or os.getenv("GROQ_API_KEY")
            if not self.api_key:
                raise ValueError("Groq API key is required. Set it using the GROQ_API_KEY environment variable.")
            self.client = Groq(api_key=self.api_key)
            logging.info(f"Using Groq model: {self.model}")
            
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _chunk_text(self, text, max_tokens=6000):
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_tokens = len(word) / 0.75
            
            if current_length + word_tokens > max_tokens and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_tokens
            else:
                current_chunk.append(word)
                current_length += word_tokens
                
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks
    
    def _identify_potential_modules(self, hierarchy, titles, structure):
        potential_modules = {}
        
        entry_points = set(hierarchy.keys())
        all_children = set()
        for children in hierarchy.values():
            all_children.update(children)
        
        root_urls = entry_points - all_children
        
        url_depth = {}
        for root in root_urls:
            url_depth[root] = 0
            self._calculate_depth(root, hierarchy, url_depth, depth=0)
        
        urls_by_depth = {}
        for url, depth in url_depth.items():
            if depth not in urls_by_depth:
                urls_by_depth[depth] = []
            urls_by_depth[depth].append(url)
        
        if 1 in urls_by_depth:
            for url in urls_by_depth[1]:
                if url in titles:
                    potential_modules[url] = {
                        "title": titles[url],
                        "child_urls": hierarchy.get(url, []),
                        "source": "hierarchy"
                    }
        
        if not potential_modules and 0 in urls_by_depth:
            for url in urls_by_depth[0]:
                if url in titles:
                    potential_modules[url] = {
                        "title": titles[url],
                        "child_urls": hierarchy.get(url, []),
                        "source": "hierarchy"
                    }
        
        for url, page_structure in structure.items():
            if "headings" in page_structure and page_structure["headings"]:
                headings_by_level = defaultdict(list)
                for heading in page_structure["headings"]:
                    headings_by_level[heading["level"]].append(heading)
                
                for level in range(1, 4):  # Check h1, h2, h3
                    level_headings = headings_by_level[level]
                    if len(level_headings) >= 2:  # Need at least 2 headings to form modules
                        for heading in level_headings:
                            module_id = f"{url}#{heading['id']}" if heading['id'] else f"{url}#{heading['text']}"
                            potential_modules[module_id] = {
                                "title": heading["text"],
                                "url": url,
                                "heading_level": level,
                                "source": "heading"
                            }
                        break
        
        return potential_modules
    
    def _calculate_depth(self, url, hierarchy, url_depth, depth):
        for child in hierarchy.get(url, []):
            if child not in url_depth or depth + 1 < url_depth[child]:
                url_depth[child] = depth + 1
                self._calculate_depth(child, hierarchy, url_depth, depth + 1)
    
    def _group_urls_by_module(self, potential_modules, content_map, structure):
        modules_content = {}
        
        for module_id, module_info in potential_modules.items():
            module_title = module_info["title"]
            source_type = module_info.get("source", "unknown")
            
            if source_type == "hierarchy":
                module_url = module_id
                
                module_content = content_map.get(module_url, "")
                
                child_contents = {}
                for child_url in module_info["child_urls"]:
                    if child_url in content_map:
                        child_contents[child_url] = content_map[child_url]
                
                module_structured_data = {}
                if module_url in structure:
                    module_structured_data = self._extract_structured_content_summary(structure[module_url])
                
                child_structured_data = {}
                for child_url in module_info["child_urls"]:
                    if child_url in structure:
                        child_structured_data[child_url] = self._extract_structured_content_summary(structure[child_url])
                
                modules_content[module_title] = {
                    "main_content": module_content,
                    "child_contents": child_contents,
                    "module_structure": module_structured_data,
                    "child_structures": child_structured_data,
                    "source_type": source_type
                }
            
            elif source_type == "heading":
                module_url = module_info["url"]
                heading_text = module_title
                heading_level = module_info["heading_level"]
                
                section_content = self._extract_section_content(
                    content_map.get(module_url, ""),
                    heading_text,
                    heading_level
                )
                
                subheadings = self._extract_subheadings(
                    structure.get(module_url, {}).get("headings", []),
                    heading_text,
                    heading_level
                )
                
                modules_content[module_title] = {
                    "main_content": section_content,
                    "subheadings": subheadings,
                    "source_type": source_type,
                    "url": module_url
                }
        
        return modules_content
    
    def _extract_structured_content_summary(self, page_structure):
        """Create a summary of structured content elements from a page"""
        summary = {}
        
        heading_counts = defaultdict(int)
        headings_sample = []
        if "headings" in page_structure:
            for heading in page_structure["headings"]:
                level = heading["level"]
                heading_counts[level] += 1
                if heading_counts[level] <= 3:
                    headings_sample.append(f"H{level}: {heading['text']}")
        
        summary["heading_counts"] = dict(heading_counts)
        summary["headings_sample"] = headings_sample
        
        if "lists" in page_structure:
            list_count = len(page_structure["lists"])
            summary["list_count"] = list_count
            
            if list_count > 0:
                list_samples = []
                for i, list_obj in enumerate(page_structure["lists"]):
                    if i >= 2:  # Limit to 2 lists
                        break
                    list_type = list_obj["type"]
                    items = [item["text"] for item in list_obj["items"][:3]]  # Up to 3 items
                    list_samples.append({
                        "type": list_type,
                        "items": items
                    })
                summary["list_samples"] = list_samples
        
        if "tables" in page_structure:
            table_count = len(page_structure["tables"])
            summary["table_count"] = table_count
            
            if table_count > 0:
                table_samples = []
                for i, table in enumerate(page_structure["tables"]):
                    if i >= 2:  
                        break
                    headers = table["headers"]
                    table_samples.append({
                        "headers": headers,
                        "row_count": len(table["rows"])
                    })
                summary["table_samples"] = table_samples
        
        if "code_blocks" in page_structure:
            code_count = len(page_structure["code_blocks"])
            summary["code_block_count"] = code_count
        
        return summary
    
    def _extract_section_content(self, content, heading_text, heading_level):
        if not content:
            return ""
            
        heading_patterns = [
            r'#{%d} %s\s*\n' % (heading_level, re.escape(heading_text)),  # Markdown
            r'<h%d[^>]*>%s</h%d>' % (heading_level, re.escape(heading_text), heading_level)  # HTML
        ]
        
        start_pos = -1
        for pattern in heading_patterns:
            match = re.search(pattern, content)
            if match:
                start_pos = match.end()
                break
        
        if start_pos == -1:
            pattern = re.escape(heading_text)
            match = re.search(pattern, content)
            if match:
                start_pos = match.end()
            else:
                return "" 
        
        next_heading_pattern = r'#{1,%d} |<h[1-%d][^>]*>' % (heading_level, heading_level)
        end_match = re.search(next_heading_pattern, content[start_pos:])
        
        if end_match:
            end_pos = start_pos + end_match.start()
            section_content = content[start_pos:end_pos].strip()
        else:
            section_content = content[start_pos:].strip()
            
        return section_content
    
    def _extract_subheadings(self, headings, parent_heading, parent_level):
        subheadings = []
        
        parent_index = -1
        for i, heading in enumerate(headings):
            if heading["level"] == parent_level and heading["text"] == parent_heading:
                parent_index = i
                break
        
        if parent_index == -1:
            return subheadings
            
        i = parent_index + 1
        while i < len(headings):
            heading = headings[i]
            if heading["level"] <= parent_level:
                break
            elif heading["level"] == parent_level + 1:
                subheadings.append(heading["text"])
            i += 1
            
        return subheadings
    
    def extract_modules(self, crawl_results):
        content_map = crawl_results["content"]
        hierarchy = crawl_results["hierarchy"]
        titles = crawl_results["titles"]
        structure = crawl_results["structure"]
        
        potential_modules = self._identify_potential_modules(hierarchy, titles, structure)
        
        if not potential_modules:
            logging.info("No clear modules identified from site structure. Processing all content together.")
            return self._extract_from_unstructured_content(content_map)
        
        modules_content = self._group_urls_by_module(potential_modules, content_map, structure)
        
        all_modules = []
        
        for module_title, module_data in modules_content.items():
            logging.info(f"Processing module: {module_title}")
            
            source_type = module_data.get("source_type", "unknown")
            
            if source_type == "hierarchy":
                module_content = self._format_hierarchy_module(module_title, module_data)
            elif source_type == "heading":
                module_content = self._format_heading_module(module_title, module_data)
            else:
                module_content = f"MODULE: {module_title}\n\n"
                module_content += f"CONTENT:\n{module_data.get('main_content', '')}"
            
            content_chunks = self._chunk_text(module_content)
            
            module_results = []
            for i, chunk in enumerate(content_chunks):
                try:
                    chunk_result = self._extract_module_with_submodules(
                        module_title, 
                        chunk, 
                        source_type,
                        module_data
                    )
                    module_results.append(chunk_result)
                    
                    if i < len(content_chunks) - 1:
                        time.sleep(1)
                        
                except Exception as e:
                    logging.error(f"Error processing chunk for module {module_title}: {e}")
            
            if module_results:
                merged_module = self._merge_module_results(module_results)
                all_modules.append(merged_module)
            
        return all_modules
    
    def _format_hierarchy_module(self, module_title, module_data):
        module_content = f"MODULE: {module_title}\n\n"
        
        module_content += f"MAIN CONTENT:\n{module_data['main_content']}\n\n"
        
        if module_data.get("module_structure"):
            structure_info = module_data["module_structure"]
            
            if "headings_sample" in structure_info and structure_info["headings_sample"]:
                module_content += "HEADINGS IN MAIN CONTENT:\n"
                for heading in structure_info["headings_sample"]:
                    module_content += f"- {heading}\n"
                module_content += "\n"
        
        if module_data["child_contents"]:
            module_content += "SUBMODULE CONTENTS:\n\n"
            for url, content in module_data["child_contents"].items():
                title = url.split("/")[-1].replace("-", " ").title()
                if url in module_data["child_structures"]:
                    structure_info = module_data["child_structures"][url]
                    
                    if "headings_sample" in structure_info and structure_info["headings_sample"]:
                        title_candidates = [h.split(": ", 1)[1] for h in structure_info["headings_sample"] 
                                           if h.startswith("H1:") or h.startswith("H2:")]
                        if title_candidates:
                            title = title_candidates[0]
                
                module_content += f"--- SUBMODULE: {title} ---\n{content}\n\n"
        
        return module_content
    
    def _format_heading_module(self, module_title, module_data):
        module_content = f"MODULE: {module_title}\n\n"
        
        module_content += f"CONTENT:\n{module_data['main_content']}\n\n"
        
        if module_data.get("subheadings"):
            module_content += "SUBHEADINGS:\n"
            for subheading in module_data["subheadings"]:
                module_content += f"- {subheading}\n"
            module_content += "\n"
            
        if module_data.get("url"):
            module_content += f"SOURCE: {module_data['url']}\n\n"
            
        return module_content
    
    def _extract_page_title_from_url(self, url):
        path = urlparse(url).path
        segments = [s for s in path.split('/') if s]
        
        if segments:
            last_segment = segments[-1]
            title = last_segment.replace('-', ' ').replace('_', ' ').title()
            return title
        
        return "Untitled Page"
    
    def _extract_from_unstructured_content(self, content_map):
        all_content = "\n\n".join([
            f"URL: {url}\nCONTENT:\n{content}"
            for url, content in content_map.items()
        ])
        
        content_chunks = self._chunk_text(all_content)
        logging.info(f"Processing unstructured content in {len(content_chunks)} chunks")
        
        all_modules = []
        
        for i, chunk in enumerate(content_chunks):
            try:
                logging.info(f"Processing chunk {i+1}/{len(content_chunks)}")
                
                modules = self._extract_from_chunk(chunk)
                all_modules.extend(modules)
                
                if i < len(content_chunks) - 1:
                    time.sleep(1)
                    
            except Exception as e:
                logging.error(f"Error processing chunk {i+1}: {e}")
        
        merged_modules = self._merge_modules(all_modules)
        return merged_modules
    
    def _extract_module_with_submodules(self, module_title, content, source_type, module_data=None):
        if source_type == "hierarchy":
            prompt = self._create_hierarchy_module_prompt(module_title, content, module_data)
        elif source_type == "heading":
            prompt = self._create_heading_module_prompt(module_title, content, module_data)
        else:
            prompt = f"""
            Analyze the following documentation content for the module '{module_title}'.
            Extract details about this module and identify its submodules.
            
            Guidelines:
            1. Focus on the specific functionality of this module
            2. Identify submodules (specific features or capabilities within this module)
            3. Generate detailed descriptions for the module and each submodule
            4. Use only information from the provided content
            
            CONTENT:
            {content}
            
            Output the module in the following JSON format:
            {{
              "module": "{module_title}",
              "Description": "Detailed description of the module",
              "Submodules": {{
                "Submodule 1": "Detailed description of submodule 1",
                "Submodule 2": "Detailed description of submodule 2"
              }}
            }}
            """
        
        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert AI assistant that extracts structured information from documentation."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=4000
                )
                result_text = response.choices[0].message.content.strip()
                
            elif self.provider == "gemini":
                full_prompt = "You are an expert AI assistant that extracts structured information from documentation.\n\n" + prompt
                response = self.client.generate_content(full_prompt)
                result_text = response.text.strip()
                
            elif self.provider == "groq":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert AI assistant that extracts structured information from documentation."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=4000
                )
                result_text = response.choices[0].message.content.strip()
            
            json_start = result_text.find('{') 
            json_end = result_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = result_text[json_start:json_end]
                module = json.loads(json_str)
                return module
            else:
                logging.error("Could not extract JSON from response")
                return {
                    "module": module_title,
                    "Description": "No description available",
                    "Submodules": {}
                }
                
        except json.JSONDecodeError as e:
            logging.error(f"JSON decoding error: {e}")
            logging.error(f"Response text: {result_text}")
            return {
                "module": module_title,
                "Description": "No description available",
                "Submodules": {}
            }
        except Exception as e:
            logging.error(f"Error parsing response: {e}")
            return {
                "module": module_title,
                "Description": "No description available",
                "Submodules": {}
            }
    
    def _create_hierarchy_module_prompt(self, module_title, content, module_data):
        submodule_hint = ""
        
        if module_data:
            if module_data.get("child_structures"):
                submodule_candidates = []
                for url, structure in module_data["child_structures"].items():
                    if "headings_sample" in structure and structure["headings_sample"]:
                        heading = structure["headings_sample"][0].split(": ", 1)[1] if ": " in structure["headings_sample"][0] else structure["headings_sample"][0]
                        submodule_candidates.append(heading)
                    else:
                        name = self._extract_page_title_from_url(url)
                        submodule_candidates.append(name)
                        
                if submodule_candidates:
                    submodule_hint = "Potential submodules based on structure:\n"
                    for candidate in submodule_candidates:
                        submodule_hint += f"- {candidate}\n"
        
        prompt = f"""
        Analyze the following documentation content for the module '{module_title}'.
        This module was identified from the website's hierarchy structure.
        
        Guidelines:
        1. Focus on the specific functionality of this module
        2. Identify submodules (specific features or capabilities within this module)
        3. Generate detailed descriptions for the module and each submodule
        4. Use only information from the provided content
        
        {submodule_hint}
        
        CONTENT:
        {content}
        
        Output the module in the following JSON format:
        {{
          "module": "{module_title}",
          "Description": "Detailed description of the module",
          "Submodules": {{
            "Submodule 1": "Detailed description of submodule 1",
            "Submodule 2": "Detailed description of submodule 2"
          }}
        }}
        """
        
        return prompt
    
    def _create_heading_module_prompt(self, module_title, content, module_data):
        submodule_hint = ""
        
        if module_data and module_data.get("subheadings"):
            submodule_hint = "Potential submodules based on subheadings:\n"
            for subheading in module_data["subheadings"]:
                submodule_hint += f"- {subheading}\n"
        
        prompt = f"""
        Analyze the following documentation content for the module '{module_title}'.
        This module was identified from a heading in the documentation.
        
        Guidelines:
        1. Focus on the specific functionality described in this section
        2. Identify submodules (specific features or capabilities within this module)
        3. Generate detailed descriptions for the module and each submodule
        4. Use only information from the provided content
        
        {submodule_hint}
        
        CONTENT:
        {content}
        
        Output the module in the following JSON format:
        {{
          "module": "{module_title}",
          "Description": "Detailed description of the module",
          "Submodules": {{
            "Submodule 1": "Detailed description of submodule 1",
            "Submodule 2": "Detailed description of submodule 2"
          }}
        }}
        """
        
        return prompt
    
    def _extract_from_chunk(self, content):
        """Extract modules from a single content chunk"""
        prompt = f"""
        Analyze the following help documentation content and identify key modules and submodules.
        Each module should represent a major feature or category, and submodules should represent specific functionalities within that module.
        
        Guidelines:
        1. Identify main features/categories as modules
        2. Group related functionalities as submodules under each module
        3. Generate detailed descriptions for each
        4. Use only information from the provided content
        
        CONTENT:
        {content}
        
        Output a list of modules in the following JSON format:
        [
          {{
            "module": "Module Name",
            "Description": "Detailed description of the module",
            "Submodules": {{
              "Submodule 1": "Detailed description of submodule 1",
              "Submodule 2": "Detailed description of submodule 2"
            }}
          }}
        ]
        """
        
        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert AI assistant that extracts structured information from documentation."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=4000
                )
                result_text = response.choices[0].message.content.strip()
                
            elif self.provider == "gemini":
                full_prompt = "You are an expert AI assistant that extracts structured information from documentation.\n\n" + prompt
                response = self.client.generate_content(full_prompt)
                result_text = response.text.strip()
                
            elif self.provider == "groq":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert AI assistant that extracts structured information from documentation."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=4000
                )
                result_text = response.choices[0].message.content.strip()
            
            json_start = result_text.find('[')
            json_end = result_text.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = result_text[json_start:json_end]
                modules = json.loads(json_str)
                return modules
            else:
                logging.error("Could not extract JSON from response")
                return []
                
        except json.JSONDecodeError as e:
            logging.error(f"JSON decoding error: {e}")
            logging.error(f"Response text: {result_text}")
            return []
        except Exception as e:
            logging.error(f"Error parsing response: {e}")
            return []
    
    def _merge_module_results(self, module_results):
        if not module_results:
            return None
            
        merged = module_results[0].copy()
        
        for result in module_results[1:]:
            if len(result.get("Description", "")) > len(merged.get("Description", "")):
                merged["Description"] = result["Description"]
                
            for subname, subdesc in result.get("Submodules", {}).items():
                if subname not in merged.get("Submodules", {}):
                    if "Submodules" not in merged:
                        merged["Submodules"] = {}
                    merged["Submodules"][subname] = subdesc
                elif len(subdesc) > len(merged["Submodules"][subname]):
                    merged["Submodules"][subname] = subdesc
                    
        return merged
    
    def _merge_modules(self, all_modules):
        module_dict = {}
        
        for module_item in all_modules:
            module_name = module_item["module"]
            
            if module_name not in module_dict:
                module_dict[module_name] = module_item
            else:
                existing_module = module_dict[module_name]
                
                if len(module_item["Description"]) > len(existing_module["Description"]):
                    existing_module["Description"] = module_item["Description"]
                
                for submodule_name, submodule_desc in module_item["Submodules"].items():
                    if submodule_name not in existing_module["Submodules"]:
                        existing_module["Submodules"][submodule_name] = submodule_desc
                    elif len(submodule_desc) > len(existing_module["Submodules"][submodule_name]):
                        existing_module["Submodules"][submodule_name] = submodule_desc
        
        return list(module_dict.values())
