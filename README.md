# Blog-content-generation

# Content Generation App
A Streamlit application for generating SEO-optimized content using AI agents.

## Features
- Content generation with template-based structure
- SEO metadata and schema generation
- Downloadable outputs (Word, Markdown, CSV)
- Regeneration capabilities for content and SEO
- Template analysis and structure preservation

## Installation
```bash
pip install streamlit pandas python-docx crewai langchain-openai
```

## Configuration
1. Get OpenAI API key
2. Add key in sidebar when running app

## Usage
1. Upload Word template document
2. Enter schema template
3. Input primary keyword and optional fields
4. Click "Generate Content"
5. Use regeneration buttons to refine outputs

## File Structure
```
content_generation/
├── app.py          # Main application
├── requirements.txt # Dependencies
└── README.md       # Documentation
```

## Required API Keys
- OpenAI API key for content generation

## Dependencies
- streamlit
- pandas
- python-docx
- crewai
- langchain-openai
