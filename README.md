# DocAtlas

DocAtlas is a powerful tool designed to extract structured information from documentation websites. It automatically identifies modules, submodules, and generates detailed descriptions by analyzing the content and structure of documentation pages using AI language models.

## Features

- **Multi-Provider AI Support**: Choose between OpenAI, Google Gemini, and Groq for extraction.
- **Intelligent Web Crawling**: Navigates documentation websites while respecting site structure (depth 1 to avoid infinite loops).
- **Smart Content Extraction**: Identifies and extracts relevant content while preserving structure (headings, lists, tables).
- **Advanced Structure Recognition**: Extracts headings, tables, lists, and code blocks with their relationships.
- **Hierarchical Organization**: Maintains relationships between content sections.
- **Multiple Interfaces**: Access via an interactive Streamlit web app or a command-line interface (CLI).
- **Structured Output**: Generates clean JSON output for further processing.

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your preferred API keys in a `.env` file in the root directory(optional):
   ```env
   OPENAI_API_KEY=your_openai_key_here
   GEMINI_API_KEY=your_gemini_key_here
   GROQ_API_KEY=your_groq_key_here
   ```

## Usage

### Web Interface

Run the interactive Streamlit app:
```bash
streamlit run app/app.py
```
From the sidebar, you can select your AI provider (OpenAI, Gemini, or Groq), enter your API key if it's not in your `.env` file, and select the specific model you want to use.

### Command-Line Interface

Run the CLI tool directly:
```bash
python cli.py --urls https://docs.python.org/3/library/os.html --provider groq --model llama3-8b-8192 --output os_module.json
```

**Options:**
- `--urls`: One or more URLs to process (required). Note: Avoid massive index/changelog pages with hundreds of links.
- `--provider`: AI Provider to use (`openai`, `gemini`, or `groq`). Default: `openai`.
- `--model`: Model to use (e.g., `gpt-3.5-turbo`, `gemini-1.5-flash`, `llama3-8b-8192`).
- `--api-key`: API key for the selected provider (if not set in `.env`).
- `--output`: Output file path (default: `extracted_modules.json`).
- `--max-pages`: Maximum pages to crawl per URL (default: 100).
- `--delay`: Delay between requests in seconds (default: 0.5).
- `--save-structure`: Save site structure information to a separate file.
- `--save-raw-content`: Save raw extracted content to a separate file.

## Project Structure

- `app/`: Streamlit web application (`app.py`)
- `src/`: Core logic
  - `crawler.py`: Web crawler and structure extractor
  - `extractor.py`: AI-powered module extractor supporting multiple providers
- `cli.py`: Command-line interface orchestration script
- `requirements.txt`: Python dependencies
