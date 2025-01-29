# Content Generation Application Documentation

## Table of Contents
1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [Application Structure](#application-structure)
5. [Key Features](#key-features)
6. [Component Documentation](#component-documentation)
7. [User Guide](#user-guide)
8. [Technical Details](#technical-details)
9. [Troubleshooting](#troubleshooting)

## Overview

The Content Generation Application is a Streamlit-based tool that leverages AI to generate, optimize, and manage content. It uses OpenAI's GPT models and implements a crew-based approach with specialized agents for different aspects of content creation.

### Core Capabilities
- Content template analysis and generation
- SEO optimization
- Schema markup generation
- Content editing and expansion
- Multiple export formats
- HTML generation with templates

## System Requirements

### Software Dependencies
```text
- Python 3.9+
- Streamlit
- OpenAI API access
- python-docx
- pandas
- crewai
- langchain_openai
- pysqlite3
```

### API Requirements
- OpenAI API key with access to GPT-4 models

## Installation

1. Install required packages:
```bash
pip install streamlit python-docx pandas crewai langchain_openai pysqlite3
```

2. Configure environment:
- Set up OpenAI API key
- Prepare HTML templates for content generation
- Ensure write permissions in the application directory

## Application Structure

### Main Components

1. **AuthManager Class**
   - Handles authentication with Google APIs
   - Manages token refresh and storage

2. **Agent Classes**
   - `TemplateAnalyzer`: Analyzes content templates
   - `ContentWriter`: Generates optimized content
   - `SEOSpecialist`: Handles SEO and schema markup

3. **Utility Functions**
   - `format_content()`: Content formatting
   - `create_word_doc()`: Document creation
   - `generate_content()`: Main content generation
   - `expand_content()`: AI-powered content expansion

### State Management
The application uses Streamlit's session state to manage:
- Page type and site name
- Template content and structure
- Keywords and service information
- Generated and edited content
- SEO metadata

## Key Features

### Content Generation
- Template-based content creation
- AI-powered writing with SEO optimization
- Content structure analysis
- Word count tracking
- Content expansion capabilities

### SEO Tools
- Title and meta description optimization
- Schema markup generation
- Character count validation
- JSON schema validation

### Export Options
- Word document (.docx)
- Markdown (.md)
- CSV metadata
- HTML generation
- ZIP package with all files

### Editor Features
- Real-time content editing
- Word count tracking
- Content expansion tool
- SEO metadata editor

## Component Documentation

### Content Generation Process

1. **Template Analysis**
```python
class TemplateAnalyzer(Agent):
    def __init__(self):
        super().__init__(
            role='Template Analyzer',
            goal='Analyze content template structure and create detailed outline',
            backstory="""Expert in content analysis and structural pattern recognition."""
        )
```

2. **Content Writing**
```python
class ContentWriter(Agent):
    def __init__(self):
        super().__init__(
            role='Content Writer',
            goal='Write high-quality, SEO-optimized content',
            backstory="""Expert content writer with deep knowledge of SEO and EEAT framework."""
        )
```

3. **SEO Optimization**
```python
class SEOSpecialist(Agent):
    def __init__(self):
        super().__init__(
            role='SEO Specialist',
            goal='Optimize content for search engines and create schema markup',
            backstory="""Expert in technical SEO, content optimization, and schema markup creation."""
        )
```

### Content Processing Functions

#### generate_content()
```python
def generate_content(template_text, template_structure, primary_keyword, schema_template,
                     service_name=None, additional_keywords=None):
    """
    Generates complete content package including:
    - Optimized content
    - SEO metadata
    - Schema markup
    - Template analysis
    """
```

#### regenerate_component()
```python
def regenerate_component(component_type, template_text, template_structure, primary_keyword,
                         schema_template, service_name=None, additional_keywords=None,
                         existing_content=None):
    """
    Regenerates specific components (content or SEO) while preserving others
    """
```

## User Guide

### Getting Started

1. Launch the application:
```bash
streamlit run app.py
```

2. Enter OpenAI API key in the sidebar

3. Upload required files:
   - Word template document
   - Schema template
   - Primary keyword
   - Additional keywords (optional)

### Content Generation

1. **Initial Generation**
   - Upload template and fill required fields
   - Click "Generate Content"
   - Monitor progress in "Generation Progress" tab

2. **Content Editing**
   - Use the Content Editor expander
   - Make changes to generated content
   - Track word count
   - Save changes before regeneration

3. **SEO Optimization**
   - Edit title (60 char limit)
   - Edit meta description (160 char limit)
   - Modify schema markup
   - Validate JSON before saving

### Export Options

1. **Download Options**
   - Complete ZIP package
   - Individual file downloads
   - Generated HTML
   - Metadata CSV

### HTML Generation

1. Select page type and site name
2. Enter H2 heading
3. Generate and download HTML file

## Technical Details

### State Management
The application uses Streamlit's session state for persistent data:
```python
st.session_state.form_submitted
st.session_state.template_doc_content
st.session_state.edited_content
st.session_state.edited_seo
st.session_state.generation_content
```

### File Handling
- Temporary file management
- Multiple format support
- Secure file operations

### Error Handling
- Input validation
- Process monitoring
- Error recovery
- User feedback

## Troubleshooting

### Common Issues

1. **API Key Issues**
   - Verify API key validity
   - Check API quota
   - Ensure proper environment setup

2. **Template Problems**
   - Verify template file format
   - Check file permissions
   - Validate template structure

3. **Generation Errors**
   - Check API responses
   - Verify input data
   - Monitor error logs

### Error Messages

Common error messages and solutions:
1. "No template files found"
   - Check template directory
   - Verify file naming
   - Check file permissions

2. "Invalid JSON in schema markup"
   - Validate JSON structure
   - Check for syntax errors
   - Use a JSON validator

3. "Error generating HTML"
   - Verify template availability
   - Check file permissions
   - Validate input data

### Support

For technical support:
1. Check error logs
2. Verify configuration
3. Review documentation
4. Contact system administrator
