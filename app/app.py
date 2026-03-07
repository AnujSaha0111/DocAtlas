import streamlit as st
import json
import os
from dotenv import load_dotenv
import sys
import logging
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler import Crawler
from src.extractor import ModuleExtractor

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

st.set_page_config(
    page_title="DocAtlas",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

def validate_urls(urls):
    valid_urls = []
    invalid_urls = []
    
    for url in urls:
        url = url.strip()
        if not url:
            continue
            
        if not url.startswith(('http://', 'https://')):
            invalid_urls.append(url)
        else:
            valid_urls.append(url)
            
    return valid_urls, invalid_urls

def main():
    st.title("DocAtlas")
    st.markdown("""
    This application extracts structured module information from documentation-based websites.
    Enter one or more URLs to documentation pages and the AI will identify modules, submodules, and generate descriptions.
    """)
    
    provider = st.sidebar.selectbox(
        "Select AI Provider",
        options=["OpenAI", "Google Gemini", "Groq"],
        index=0
    )
    
    api_key = None
    model = None
    
    if provider == "OpenAI":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            api_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")
            if not api_key:
                st.warning("⚠️ OpenAI API key not found. Please set OPENAI_API_KEY env var or enter it here.")
        
        model = st.sidebar.selectbox(
            "OpenAI Model", 
            options=["gpt-3.5-turbo", "gpt-4"], 
            index=0
        )
        
    elif provider == "Google Gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")
            if not api_key:
                st.warning("⚠️ Gemini API key not found. Please set GEMINI_API_KEY env var or enter it here.")
        
        model = st.sidebar.selectbox(
            "Gemini Model", 
            options=["gemini-1.5-flash", "gemini-pro"], 
            index=0
        )
        
    elif provider == "Groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            api_key = st.sidebar.text_input("Enter Groq API Key", type="password")
            if not api_key:
                st.warning("⚠️ Groq API key not found. Please set GROQ_API_KEY env var or enter it here.")
        
        model = st.sidebar.selectbox(
            "Groq Model", 
            options=["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768"], 
            index=0
        )
    
    st.subheader("Enter Documentation URLs")
    url_input = st.text_area(
        "Enter one or more URLs (one per line):", 
        placeholder="https://help.example.com/",
        height=100
    )
    
    with st.expander("Advanced Options"):
        max_pages = st.slider("Maximum pages to crawl (per URL)", 10, 300, 100)
        delay = st.slider("Delay between requests (seconds)", 0.1, 2.0, 0.5, 0.1)
        max_depth = 1  
        st.info("Crawl depth is limited to 1 level deep from main URL (main page + directly linked pages only)")
    
    if st.button("Extract Modules", type="primary"):
        if not api_key:
            st.error(f"Please provide an API key for {provider}")
            st.stop()
            
        if not url_input:
            st.error("Please enter at least one URL")
            st.stop()
            
        urls = [url.strip() for url in url_input.split("\n") if url.strip()]
        valid_urls, invalid_urls = validate_urls(urls)
        
        if invalid_urls:
            st.error(f"Invalid URLs detected: {', '.join(invalid_urls)}")
            st.stop()
            
        if not valid_urls:
            st.error("No valid URLs provided")
            st.stop()
        
        progress_container = st.empty()
        status_container = st.empty()
        crawl_info_container = st.empty()
        
        try:
            crawler = Crawler(max_pages=max_pages, delay=delay, max_depth=max_depth)
            
            provider_internal = "openai" if provider == "OpenAI" else "gemini"
            extractor = ModuleExtractor(api_key=api_key, model=model, provider=provider_internal)
            
            status_container.info("Crawling websites... This may take a few minutes.")
            progress_bar = progress_container.progress(0)
            
            all_results = {"content": {}, "hierarchy": {}, "titles": {}, "depths": {}, "metadata": {}, "structure": {}}
            
            for i, url in enumerate(valid_urls):
                status_container.info(f"Crawling {url}...")
                results = crawler.crawl(url)
                
                all_results["content"].update(results["content"])
                all_results["hierarchy"].update(results["hierarchy"])
                all_results["titles"].update(results["titles"])
                all_results["depths"].update(results["depths"])
                all_results["metadata"].update(results["metadata"])
                all_results["structure"].update(results["structure"])
                
                depth_counts = {}
                for url, depth in results["depths"].items():
                    depth_counts[depth] = depth_counts.get(depth, 0) + 1
                
                structure_counts = {
                    "headings": 0,
                    "lists": 0,
                    "tables": 0,
                    "code_blocks": 0
                }
                
                for url, struct in results["structure"].items():
                    structure_counts["headings"] += len(struct.get("headings", []))
                    structure_counts["lists"] += len(struct.get("lists", []))
                    structure_counts["tables"] += len(struct.get("tables", []))
                    structure_counts["code_blocks"] += len(struct.get("code_blocks", []))
                
                crawl_info = f"""
                **Crawl Progress:**
                - Pages visited: {len(results['content'])}
                - Links discovered: {sum(len(children) for children in results['hierarchy'].values())}
                - Depth 0 (main pages): {depth_counts.get(0, 0)} pages
                - Depth 1 (direct links): {depth_counts.get(1, 0)} pages
                
                **Content Structure:**
                - Headings extracted: {structure_counts['headings']}
                - Lists extracted: {structure_counts['lists']}
                - Tables extracted: {structure_counts['tables']}
                - Code blocks extracted: {structure_counts['code_blocks']}
                """
                crawl_info_container.markdown(crawl_info)
                
                progress = (i + 1) / len(valid_urls) * 0.5  
                progress_bar.progress(progress)
            
            status_container.info(f"Analyzing content and extracting modules using {model}...")
            
            modules = extractor.extract_modules(all_results)
            
            progress_bar.progress(1.0)
            status_container.success("Extraction completed!")
            progress_container.empty()
            crawl_info_container.empty()
            
            if modules:
                st.subheader("Extracted Modules")
                
                tab1, tab2, tab3, tab4 = st.tabs(["Interactive View", "JSON Output", "Site Structure", "Content Structure"])
                
                with tab1:
                    for module in modules:
                        with st.expander(f"📁 {module['module']}"):
                            st.markdown(f"**Description:** {module['Description']}")
                            
                            if module['Submodules']:
                                st.markdown("**Submodules:**")
                                for submodule_name, submodule_desc in module['Submodules'].items():
                                    st.markdown(f"- **{submodule_name}:** {submodule_desc}")
                            else:
                                st.markdown("*No submodules identified*")
                
                with tab2:
                    st.json(modules)
                    
                    json_str = json.dumps(modules, indent=2)
                    st.download_button(
                        label="Download JSON",
                        data=json_str,
                        file_name="extracted_modules.json",
                        mime="application/json"
                    )
                    
                with tab3:
                    st.markdown("### Site Structure")
                    st.markdown("This shows the hierarchical relationship between pages that were crawled:")
                    
                    pages_by_depth = {}
                    for url, depth in all_results["depths"].items():
                        if depth not in pages_by_depth:
                            pages_by_depth[depth] = []
                        pages_by_depth[depth].append(url)
                    
                    structure_text = ""
                    
                    structure_text += "### Main URLs (Depth 0):\n"
                    for url in pages_by_depth.get(0, []):
                        title = all_results["titles"].get(url, url)
                        structure_text += f"- {title} [{url}]\n"
                    
                    structure_text += "\n### Direct Links (Depth 1):\n"
                    for parent_url in pages_by_depth.get(0, []):
                        parent_title = all_results["titles"].get(parent_url, parent_url)
                        child_urls = all_results["hierarchy"].get(parent_url, [])
                        if child_urls:
                            structure_text += f"- From {parent_title}:\n"
                            for child_url in child_urls:
                                child_title = all_results["titles"].get(child_url, child_url)
                                structure_text += f"  - {child_title}\n"
                    
                    st.text_area("Site Hierarchy", structure_text, height=300)
                
                with tab4:
                    st.markdown("### Document Structure")
                    st.markdown("This shows the structured elements extracted from the documentation:")
                    
                    headings_sample = []
                    for url, structure in all_results["structure"].items():
                        for heading in structure.get("headings", [])[:5]: 
                            headings_sample.append({
                                "page": all_results["titles"].get(url, url),
                                "level": heading["level"],
                                "text": heading["text"]
                            })
                    
                    if headings_sample:
                        st.markdown("#### Sample Headings")
                        for heading in headings_sample[:15]: 
                            st.markdown(f"- **{heading['page']}** - H{heading['level']}: {heading['text']}")
                    
                    tables_info = []
                    for url, structure in all_results["structure"].items():
                        for table in structure.get("tables", []):
                            tables_info.append({
                                "page": all_results["titles"].get(url, url),
                                "headers": table["headers"],
                                "rows": len(table["rows"])
                            })
                    
                    if tables_info:
                        st.markdown("#### Sample Tables")
                        for table in tables_info[:5]: 
                            headers_str = ", ".join(table["headers"]) if table["headers"] else "No headers"
                            st.markdown(f"- **{table['page']}** - Headers: {headers_str} ({table['rows']} rows)")
                    
                    st.markdown("#### Document Metadata")
                    for url, metadata in list(all_results["metadata"].items())[:5]:  # Limit to 5 pages
                        with st.expander(f"Metadata for {all_results['titles'].get(url, url)}"):
                            last_updated = metadata.get("last_updated", "Not available")
                            st.markdown(f"- **Last Updated:** {last_updated}")
                            
                            meta_tags = metadata.get("meta_tags", {})
                            if meta_tags:
                                st.markdown("**Meta Tags:**")
                                for name, content in list(meta_tags.items())[:10]:
                                    st.markdown(f"- {name}: {content}")
            else:
                st.warning("No modules extracted. The content might not contain enough structured information.")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            logging.error(f"Error in extraction process: {e}", exc_info=True)

if __name__ == "__main__":
    main()
