import argparse
import json
import os
import sys
import logging
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.crawler import Crawler
from src.extractor import ModuleExtractor

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('module_extractor.log')
    ]
)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract modules and submodules from documentation websites"
    )    
    parser.add_argument(
        "--urls", 
        nargs="+", 
        required=True,
        help="URLs of documentation websites to process"
    )    
    parser.add_argument(
        "--output", 
        type=str, 
        default="extracted_modules.json",
        help="Output file path for JSON results"
    )    
    parser.add_argument(
        "--max-pages", 
        type=int, 
        default=100,
        help="Maximum number of pages to crawl per URL"
    )    
    parser.add_argument(
        "--delay", 
        type=float, 
        default=0.5,
        help="Delay between requests in seconds"
    )    
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-3.5-turbo",
        choices=["gpt-3.5-turbo", "gpt-4"],
        help="OpenAI model to use (gpt-3.5-turbo is cheaper, gpt-4 may be more accurate)"
    )    
    parser.add_argument(
        "--save-structure", 
        action="store_true",
        help="Also save the site structure information to a separate file"
    )    
    parser.add_argument(
        "--save-raw-content", 
        action="store_true",
        help="Save the raw extracted content to a separate file"
    )    
    parser.add_argument(
        "--api-key", 
        type=str,
        help="OpenAI API key (if not set in environment variable)"
    )    
    return parser.parse_args()

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

def save_structure(site_structure, output_basename):
    structure_file = f"{os.path.splitext(output_basename)[0]}_structure.json"
    with open(structure_file, 'w', encoding='utf-8') as f:
        json.dump(site_structure, f, indent=2)
    logging.info(f"Site structure saved to {structure_file}")

def save_raw_content(content_data, output_basename):
    content_file = f"{os.path.splitext(output_basename)[0]}_content.json"
    with open(content_file, 'w', encoding='utf-8') as f:
        json.dump(content_data, f, indent=2)
    logging.info(f"Raw content saved to {content_file}")

def main():
    args = parse_args()
    # validating API key
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error("OpenAI API key not found. Please set OPENAI_API_KEY environment variable or use --api-key.")
        sys.exit(1)

    valid_urls, invalid_urls = validate_urls(args.urls)

    if invalid_urls:
        logging.error(f"Invalid URLs detected: {', '.join(invalid_urls)}")
        sys.exit(1)        
    if not valid_urls:
        logging.error("No valid URLs provided")
        sys.exit(1)

    try:
        max_depth = 1  
        crawler = Crawler(max_pages=args.max_pages, delay=args.delay, max_depth=max_depth)
        extractor = ModuleExtractor(api_key=api_key, model=args.model)
        logging.info(f"Crawling with max depth of {max_depth} (main page + direct links only)")
        logging.info(f"Using OpenAI model: {args.model}")
        
        all_results = {
            "content": {}, 
            "hierarchy": {}, 
            "titles": {}, 
            "depths": {}, 
            "metadata": {},
            "structure": {}
        }        
        for i, url in enumerate(valid_urls):
            logging.info(f"Crawling {url}... ({i+1}/{len(valid_urls)})")
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
            logging.info(f"Pages processed: {len(results['content'])}")
            logging.info(f"Links discovered: {sum(len(children) for children in results['hierarchy'].values())}")
            logging.info(f"Pages at depth 0 (main): {depth_counts.get(0, 0)}")
            logging.info(f"Pages at depth 1 (direct links): {depth_counts.get(1, 0)}")
            logging.info(f"Structure elements: {sum(structure_counts.values())} ({structure_counts})")
        if args.save_structure:
            save_structure(
                {
                    "hierarchy": all_results["hierarchy"], 
                    "titles": all_results["titles"],
                    "depths": all_results["depths"],
                    "structure": all_results["structure"],
                    "metadata": all_results["metadata"]
                }, 
                args.output
            )
        if args.save_raw_content:
            save_raw_content(
                {
                    "content": all_results["content"],
                    "titles": all_results["titles"]
                },
                args.output
            )
        logging.info(f"Analyzing content and extracting modules with {args.model}...")
        modules = extractor.extract_modules(all_results)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(modules, f, indent=2)            
        logging.info(f"Extraction completed! Results saved to {args.output}")      
        if modules:
            total_submodules = sum(len(m.get('Submodules', {})) for m in modules)
            logging.info(f"Extracted {len(modules)} modules with a total of {total_submodules} submodules.")
            for module in modules:
                submodule_count = len(module.get('Submodules', {}))
                logging.info(f"- {module['module']} ({submodule_count} submodules)")
        else:
            logging.warning("No modules extracted. The content might not contain enough structured information.")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()