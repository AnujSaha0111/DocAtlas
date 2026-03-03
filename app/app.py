import streamlit as st
import json
import os
from dotenv import load_dotenv
import sys
import logging
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler import Crawler
from src.extractor import ModuleExtractor

# Load environment variables
load_dotenv()

# Configure logging
logging.basic
    invalid_urls = []
    
    for url in urls:
        url = url.strip()
        if not url:
            continue
            
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            invalid_urls.append(url)
        else:
            valid_urls.append(url)
            
    return valier",
        options=["OpenAI", "Google Gemini", "Groq"],
        index=0
    )
    
    api_key = None
    model = None
    
    if provider == "OpenAI":
        # Check for OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            api_keyI key
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
        # Check for Groq API key
        api_key = os.
    # URL input
    st.subheader("Enter Documentation URLs")
    url_input = st.text_area(
        "Enter one or more URLs (one per line):", 
        placeholder="https://help.example.com/",
        height=100
    )
    
    # Advanced options
    with st.expander("Advanced Options"):
        max_pages = st.slider("Maximum pages to crawl (per URL)", 10, 300, 100)
        delay = st.slider("Delay between requests (seconds)", 0.1, 2.0, 0.5, 0.1)
        max_depth = 1  # Fixed to 1 level deep (main URL + direct links)
        st.info("Crawl depth is limited to 1 level deep from main URL (main page + directly linked pages only)")
    
    # Process button
    if st.button("Extract Modules", type="primary"):
        if not api_key:
            st.error(f"Please provide an API key for {provider}")
            st.stop()
            Ls detected: {', '.join(invalid_urls)}")
            st.stop()
            
        if not valid_urls:
            st.error("No valid URLs provided")
            st.stop()
        
        # Create progress indicators
        progress_container = st.empty()
        status_container = st.empty()
        crawl_info_container = st.empty()
        
        try:
            # Initialize crawler and extractor
            crawler = Crawler(max_pages=max_pages, delay=delay, max_depth=max_depth)
            
            # Map provider name to internal name
            provider_internal = "openai" if provider == "OpenAI" else "gemini"
            extractor =].update(results["hierarchy"])
                all_results["titles"].update(results["titles"])
                all_results["depths"].update(results["depths"])
                all_results["metadata"].update(results["metadata"])
                all_results["structure"].update(results["structure"])
                
                # Count pages by depth
                depth_counts = {}
                for url, depth in results["depths"].items():
                    depth_counts[depth] = depth_counts.get(depth, 0) + 1
                
                # Count structured elements
                structure_counts = {
                    "headings": 0,
                    "lists": 0,
                    "tables": 0,
                    "code_blocks": 0
                }
                
                for url, struct in results["structure"].items():
                    structure_counts["headings"] += len(struct.get("headings", []))
                    structure_counts["lists"] += len(struct.get("lists", []))
                    structur
            # Complete progress
            progress_bar.progress(1.0)
            status_container.success("Extraction completed!")
            progress_container.empty()
            crawl_info_container.empty()
            
            # Display results
            if modules:
                st.subheader("Extracted Modules")
                
                # Create tabs for different views
                tab1, tab2, tab3, tab4 = st.tabs(["Interactive View", "JSON Output", "Site Structure", "Content Structure"])
                
                with tab1:
                    for module in modules:
                        with st.expander(f"📁 {module['module']}"):
                            st.markdown(f"**Description:** {module['Description']}")
                            
                            if moon"
                    )
                    
                with tab3:
                    st.markdown("### Site Structure")
                    st.markdown("This shows the hierarchical relationship between pages that were crawled:")
                    
                    # Group by depth
                    pages_by_depth = {}
                    for url, depth in all_results["depths"].items():
                        if depth not in pages_by_depth:
                            pages_by_depth[depth] = []
                        pages_by_depth[depth].append(url)
                    
                    # Convert hierarchy to a more readable format with depth
                    structure_text = ""
                    
                    # Main pages (depth 0)
                    structure_text += "### Main URLs (Depth 0):\n"
                    for url in pages_by_depth.get(0, []):
                        title = all_results["titles"].get(url, url)
                        struture_text += f"  - {child_title}\n"
                    
                    st.text_area("Site Hierarchy", structure_text, height=300)
                
                with tab4:
                    st.markdown("### Document Structure")
                    st.markdown("This shows the structured elements extracted from the documentation:")
                    
                    # Sample headings
                    headings_sample = []
                    for url, structure in all_results["structure"].items():
                        for heading in structure.get("headings", [])[:5]:  # Limit to 5 headings per page
                            headinresults["titles"].get(url, url),
                                "headers": table["headers"],
                                "rows": len(table["rows"])
                            })
                    
                    if tables_info:
                        st.markdown("#### Sample Tables")
                        for table in tables_info[:5]:  # Limit to 5 tables
                            headers_str = ", ".join(table["headers"]) if table["headers"] else "No headers"
                            st.markdown(f"- **{table['page']}** - Headers: {headers_str} ({table['rows']} rows)")
                    
                    # Metadata
                    st.markdown("#### Document Metadata")
                    for url, metadata in list(all_results["metadata"].items())[:5]:  # Limit to 5 pages
                        with st.expander(f"Metadata for {all_results['titles'].get(url, url)}"):
                    
                st.warning("No modules extracted. The content might not contain enough structured information.")
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            logging.error(f"Error in extraction process: {e}", exc_info=True)

if __name__ == "__main__":
    main()
