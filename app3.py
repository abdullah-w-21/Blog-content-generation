__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import streamlit as st
import pandas as pd
from docx import Document
import json
import os
from crewai import Agent, Task, Crew, Process
from textwrap import dedent
from langchain_openai import ChatOpenAI
from datetime import datetime
import zipfile
import tempfile
import pandas as pd
from io import BytesIO, StringIO
import traceback
from datetime import datetime
import os
from automation import generate_filled_html


# Session state initialization
if 'page_type' not in st.session_state:
    st.session_state.page_type = None
if 'site_name' not in st.session_state:
    st.session_state.site_name = None
if 'template_text' not in st.session_state:
    st.session_state.template_text = None
if 'template_structure' not in st.session_state:
    st.session_state.template_structure = None
if 'primary_keyword' not in st.session_state:
    st.session_state.primary_keyword = None
if 'schema_template' not in st.session_state:
    st.session_state.schema_template = None
if 'service_name' not in st.session_state:
    st.session_state.service_name = None
if 'additional_keywords_list' not in st.session_state:
    st.session_state.additional_keywords_list = None
if 'generation_content' not in st.session_state:
    st.session_state.generation_content = None




def debug_print(message):
    """Print debug messages in Streamlit"""
    st.write(f"Debug: {message}")

def configure_openai():
    api_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        return True
    return False


def read_word_document(file):
    doc = Document(file)
    template_text = []
    template_structure = {'sections': []}

    current_section = None
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        style = paragraph.style.name

        if style.startswith('Heading'):
            if style.startswith('Heading 2'):
                current_section = {'heading': text, 'level': 2, 'subsections': [], 'content': []}
                template_structure['sections'].append(current_section)
            elif style.startswith('Heading 3') and current_section:
                current_section['subsections'].append({'heading': text, 'level': 3, 'content': []})
        elif current_section:
            if current_section['subsections']:
                current_section['subsections'][-1]['content'].append(text)
            else:
                current_section['content'].append(text)

        template_text.append(text)

    return '\n'.join(template_text), template_structure


class TemplateAnalyzer(Agent):
    def __init__(self):
        super().__init__(
            role='Template Analyzer',
            goal='Analyze content template structure and create detailed outline',
            backstory=dedent("""Expert in content analysis and structural pattern recognition."""),
            verbose=True,
            allow_delegation=False,
            llm=ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
        )


class ContentWriter(Agent):
    def __init__(self):
        super().__init__(
            role='Content Writer',
            goal='Write high-quality, SEO-optimized content',
            backstory=dedent("""Expert content writer with deep knowledge of SEO and EEAT framework."""),
            verbose=True,
            allow_delegation=False,
            llm=ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        )


class SEOSpecialist(Agent):
    def __init__(self):
        super().__init__(
            role='SEO Specialist',
            goal='Optimize content for search engines and create schema markup',
            backstory=dedent("""Expert in technical SEO, content optimization, and schema markup creation."""),
            verbose=True,
            allow_delegation=False,
            llm=ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        )


def format_content(content, format_type='markdown'):
    lines = content.split('\n')
    formatted = []

    for line in lines:
        line = line.strip()
        if format_type == 'markdown':
            if line.startswith('H2:'):
                formatted.append(f"## {line[3:].strip()}")
            elif line.startswith('H3:'):
                formatted.append(f"### {line[3:].strip()}")
            elif line:
                formatted.append(line)
        else:
            formatted.append(line)

    return '\n'.join(formatted)


def create_word_doc(content):
    doc = Document()
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('H2:'):
            doc.add_heading(line[3:].strip(), level=2)
        elif line.startswith('H3:'):
            doc.add_heading(line[3:].strip(), level=3)
        elif line:
            doc.add_paragraph(line)
    return doc


def generate_content(template_text, template_structure, primary_keyword, schema_template,
                     service_name=None, additional_keywords=None, progress_callbacks=None):
    try:
        template_analyzer = TemplateAnalyzer()
        writer = ContentWriter()
        seo_specialist = SEOSpecialist()

        # Template analysis task
        analysis_task = Task(
            description=f"""
            Analyze this content template and create a detailed outline:
            Template Structure: {json.dumps(template_structure)}
            Original Text: {template_text}

            Create a detailed analysis of:
            1. Content flow and exact structure
            2. Key sections and their purposes
            3. Content patterns and relationships
            4. Recommended approach for content creation
            5. The address details mentioned in the content remember it.
            6. Pay close attention to the use of headings (H1, H2, H3) and how they organize the information.
            7. The number of FAQ's
            8. FAQ's questions starts with Q: and Answer starts with A:
            """,
            expected_output="Detailed template analysis with structural insights and content recommendations",
            agent=template_analyzer
        )

        # Get template analysis
        template_analysis = template_analyzer.execute_task(analysis_task)

        # Writing task with template insights
        writing_task = Task(
            description=f"""
            Generate content using this template analysis:
            {template_analysis}

            Primary Keyword: {primary_keyword}
            Service Name: {service_name if service_name else 'Not specified'}
            Additional Keywords: {', '.join(additional_keywords) if additional_keywords else 'None'}

            Generate SEO Optimized high-quality, informative, and trustworthy content for Nao Medical, a leading healthcare provider in NYC with over 11 facilities. 
            Requirements:
            1. Follow provided template structure exactly and accurately (include the address if exists)
            2. Use H2: and H3: prefix for headings
            3. Word count: 1700-1800 so it ranks on google
            4. Follow EEAT framework
            5. Natural LSI keyword integration
            6. Prioritize user value and clarity
            7. FAQ's questions starts with (H3: Q:) and Answer starts with (A:)

            Output content using H2: and H3: prefixes for headings.
            Ensure that the output is perfect and the headings prefixes are mention (H1,H2,H3).
            """,
            expected_output="SEO-optimized content following template structure with proper heading hierarchy with (H1:,H2:,H3:) prefixes for headings. Output should only consist of the content along with their markdown.",
            agent=writer
        )

        content_result = writer.execute_task(writing_task)

        # SEO task with generated content
        seo_task = Task(
            description=f"""
            Using this content:
            {content_result}

            Create:
            1. SEO title (max 60 chars)
            2. Meta description (max 160 chars)
            3. FAQ Schema from content
            4. Adapt schema template: {schema_template}

            Primary keyword: {primary_keyword}

            Format:
            TITLE: [title]
            META: [description]
            SCHEMA:
            [complete meta tags and schema markup with FAQs schema]
            """,
            expected_output="SEO metadata including title, meta description, and complete meta tags and schema markup with FAQs schema",
            agent=seo_specialist
        )

        crew = Crew(
            agents=[template_analyzer, writer, seo_specialist],
            tasks=[analysis_task, writing_task, seo_task],
            verbose=True,
            process=Process.sequential
        )

        result = crew.kickoff()

        # Format outputs
        markdown_content = format_content(str(result.tasks_output[1]), 'markdown')
        word_content = format_content(str(result.tasks_output[1]), 'word')

        # Parse SEO output
        seo_output = str(result.tasks_output[2])
        title = meta_description = ""
        schema = {"meta_tags": [], "json_ld": []}

        current_section = None
        current_content = []

        for line in seo_output.split('\n'):
            line = line.strip()
            if line.startswith('TITLE:'):
                title = line[6:].strip()
            elif line.startswith('META:'):
                meta_description = line[5:].strip()
            elif line.startswith('SCHEMA:'):
                current_section = 'schema'
            elif current_section == 'schema':
                current_content.append(line)

        if current_content:
            try:
                schema = {"raw_schema": '\n'.join(current_content)}
            except:
                schema = {"error": "Schema processing failed"}

        return {
            'content': markdown_content,
            'word_content': word_content,
            'title': title,
            'meta_description': meta_description,
            'schema': schema,
            'template_analysis': str(result.tasks_output[0])
        }

    except Exception as e:
        if progress_callbacks and 'error' in progress_callbacks:
            progress_callbacks['error'](f"Error: {str(e)}")
        raise e


def parse_seo_output(seo_output):
    title = meta_description = ""
    schema = {"meta_tags": [], "json_ld": []}
    current_section = None
    current_content = []

    for line in seo_output.split('\n'):
        line = line.strip()
        if line.startswith('TITLE:'):
            title = line[6:].strip()
        elif line.startswith('META:'):
            meta_description = line[5:].strip()
        elif line.startswith('SCHEMA:'):
            current_section = 'schema'
        elif current_section == 'schema':
            current_content.append(line)

    if current_content:
        schema = {"raw_schema": '\n'.join(current_content)}

    return title, meta_description, schema


def regenerate_component(component_type, template_text, template_structure, primary_keyword,
                         schema_template, service_name=None, additional_keywords=None,
                         existing_content=None):
    if component_type == 'content':
        template_analyzer = TemplateAnalyzer()
        writer = ContentWriter()

        analysis_task = Task(
            description=f"""
            Analyze this content template and create a detailed outline:
            Template Structure: {json.dumps(template_structure)}
            Original Text: {template_text}

            Create a detailed analysis of:
            1. Content flow and exact structure
            2. Key sections and their purposes
            3. Content patterns and relationships
            4. Recommended approach for content creation
            5. The address details mentioned in the content remember it.
            6. Pay close attention to the use of headings (H1, H2, H3) and how they organize the information.
            7. The number of FAQ's
            8. FAQ's questions starts with Q: and Answer starts with A:
            """,
            expected_output="Detailed template analysis with structural insights and content recommendations",
            agent=template_analyzer
        )

        # Get template analysis
        template_analysis = template_analyzer.execute_task(analysis_task)

        # Writing task with template insights
        writing_task = Task(
           description=f"""
            Generate content using this template analysis:
            {template_analysis}

            Primary Keyword: {primary_keyword}
            Service Name: {service_name if service_name else 'Not specified'}
            Additional Keywords: {', '.join(additional_keywords) if additional_keywords else 'None'}

            Generate SEO Optimized high-quality, informative, and trustworthy content for Nao Medical, a leading healthcare provider in NYC with over 11 facilities. 
            Requirements:
            1. Follow provided template structure exactly and accurately (include the address if exists)
            2. Use H2: and H3: prefix for headings
            3. Word count: 1700-1800 so it ranks on google
            4. Follow EEAT framework
            5. Natural LSI keyword integration
            6. Prioritize user value and clarity
            7. FAQ's questions starts with (H3: Q:) and Answer starts with (A:)

            Output content using H2: and H3: prefixes for headings.
            Ensure that the output is perfect and the headings prefixes are mention (H1,H2,H3).
            """,
            expected_output="SEO-optimized content following template structure with proper heading hierarchy with (H1:,H2:,H3:) prefixes for headings. Output should only consist of the content along with their markdown.",
            agent=writer
        )

        content_result = writer.execute_task(writing_task)

        return {
            'content': format_content(str(content_result), 'markdown'),
            'word_content': format_content(str(content_result), 'word')
        }

    elif component_type == 'seo':
        seo_specialist = SEOSpecialist()
        seo_task = Task(
            description=f"""
                    Using this content:
                    {existing_content}

                    Create:
                    1. SEO title (max 60 chars)
                    2. Meta description (max 160 chars)
                    3. FAQ Schema from content
                    4. Adapt schema template: {schema_template}

                    Primary keyword: {primary_keyword}

                    Format:
                    TITLE: [title]
                    META: [description]
                    SCHEMA:
                    [complete meta tags and schema markup with FAQs schema]
                    """,
            expected_output="SEO metadata including title, meta description, and complete meta tags and schema markup with FAQs schema.",
            agent=seo_specialist
        )
        seo_result = seo_specialist.execute_task(seo_task)

        title, meta_description, schema = parse_seo_output(str(seo_result))
        return {
            'title': title,
            'meta_description': meta_description,
            'schema': schema
        }


def regenerate_callback(component_type):
    with st.spinner(f"Regenerating {component_type}..."):
        additional_keywords_list = ([k.strip() for k in st.session_state.additional_keywords.split('\n')
                                     if k.strip()] if st.session_state.additional_keywords else None)

        if component_type == 'content':
            result = regenerate_component('content',
                                          st.session_state.template_text,
                                          st.session_state.template_structure,
                                          st.session_state.primary_keyword,
                                          st.session_state.schema_template,
                                          st.session_state.service_name,
                                          additional_keywords_list)
            st.session_state.generation_content.update(result)
            # Update edited content as well
            st.session_state.edited_content = result.get('content', st.session_state.edited_content)
            st.rerun()  # Force rerun after update

        elif component_type == 'seo':
            result = regenerate_component('seo',
                                          st.session_state.template_text,
                                          st.session_state.template_structure,
                                          st.session_state.primary_keyword,
                                          st.session_state.schema_template,
                                          st.session_state.service_name,
                                          additional_keywords_list,
                                          st.session_state.generation_content['content'])
            st.session_state.generation_content.update(result)
            # Update edited SEO as well
            st.session_state.edited_seo.update({
                'title': result.get('title', st.session_state.edited_seo.get('title', '')),
                'meta_description': result.get('meta_description',
                                               st.session_state.edited_seo.get('meta_description', '')),
                'schema': result.get('schema', st.session_state.edited_seo.get('schema', {}))
            })
            st.rerun()  # Force rerun after update

        else:  # regenerate all
            result = generate_content(
                st.session_state.template_text,
                st.session_state.template_structure,
                st.session_state.primary_keyword,
                st.session_state.schema_template,
                st.session_state.service_name,
                additional_keywords_list)

            # Update both generation content and edited states
            st.session_state.generation_content = result
            st.session_state.edited_content = result['content']
            st.session_state.edited_seo = {
                'title': result['title'],
                'meta_description': result['meta_description'],
                'schema': result['schema']
            }
            st.rerun()  # Force rerun after update


def save_to_csv(data):
    df = pd.DataFrame([data])
    return df.to_csv(index=False).encode('utf-8')


def expand_content(selected_text, primary_keyword):
    """Function to expand selected content using GPT-4 directly"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

    prompt = f"""
    Expand and enhance this content while maintaining the same style and tone:
    {selected_text}

    Primary Keyword: {primary_keyword}

    Requirements:
    1. Maintain the same style and format
    2. Add more detailed information and examples
    3. Keep SEO optimization in mind
    4. Ensure natural flow with surrounding content
    5. Keep the same heading format if present (H1:, H2:, H3:)
    """

    response = llm.invoke(prompt)
    return response.content


def count_words(text):
    """Count words in text, excluding heading markers"""
    # Remove heading markers (H1:, H2:, H3:)
    cleaned_text = text.replace('H1:', '').replace('H2:', '').replace('H3:', '')
    return len(cleaned_text.split())


def main():
    # Initialize session states
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    if 'template_doc_content' not in st.session_state:
        st.session_state.template_doc_content = None
    if 'edited_content' not in st.session_state:
        st.session_state.edited_content = None
    if 'edited_seo' not in st.session_state:
        st.session_state.edited_seo = {}
    if 'generation_content' not in st.session_state:
        st.session_state.generation_content = None

    st.title("Content Generation App")

    with st.expander("ℹ️ About v2.0 Updates"):
        st.markdown("""
        ### 🆕 New Features in v2.0
        
        #### Content Management
        - **Original Content View**: Always visible generated content
        - **Content Editor**: Expandable editor for making changes
        - **Word Count**: Real-time word count tracking
        - **Content Expansion**: Ability to expand specific sections using AI
        
        #### Editor Features
        - 📝 Edit content while preserving original
        - 💾 Save changes independently
        - 🔄 Auto-sync with regenerated content
        - 📊 Real-time word count updates
        
        #### SEO Tools
        - 🎯 Enhanced SEO metadata editor
        - ✍️ Title character counter (60 char limit)
        - 📑 Meta description counter (160 char limit)
        - 🔧 JSON schema validation
        
        #### Regeneration Options
        - 🔄 Regenerate content only
        - 🎯 Regenerate SEO only
        - ⚡ Regenerate everything
        
        #### File Management
        - 📦 Download all files as ZIP
        - 📄 Individual file downloads
        - 💾 Auto-save of edited versions
        
        #### How to Use
        1. Generate initial content
        2. View generated content at the top
        3. Use the Content Editor expander to make changes
        4. Expand sections using AI assistance
        5. Edit SEO metadata in the SEO expander
        6. Download your preferred file format
        
        #### Tips
        - Use the content expander for major edits
        - Save changes before regenerating
        - Monitor word count for optimal SEO
        - Validate schema before saving
        """)

    if not configure_openai():
        st.warning("Please enter your OpenAI API key in the sidebar.")
        return

    # Initial form for content generation
    if not st.session_state.form_submitted:
        with st.form("content_form"):
            template_doc = st.file_uploader("Upload template Word document", type=['docx'])
            schema_template = st.text_area("Enter Schema Template", height=200)
            col1, col2 = st.columns(2)
            with col1:
                primary_keyword = st.text_input("Primary Keyword (required)")
                service_name = st.text_input("Service Name (optional)")
            with col2:
                additional_keywords = st.text_area("Additional Keywords (optional, one per line)")
            submitted = st.form_submit_button("Generate Content ✨")

            if submitted and template_doc and primary_keyword and schema_template:
                template_text, template_structure = read_word_document(template_doc)
                st.session_state.template_doc_content = template_doc.getvalue()
                st.session_state.template_text = template_text
                st.session_state.template_structure = template_structure
                st.session_state.primary_keyword = primary_keyword
                st.session_state.schema_template = schema_template
                st.session_state.service_name = service_name
                st.session_state.additional_keywords = additional_keywords
                st.session_state.form_submitted = True
                st.rerun()

    # Content generation and editing interface
    if st.session_state.form_submitted:
        if st.button("← Back to Form"):
            st.session_state.form_submitted = False
            st.session_state.generation_content = None
            st.session_state.edited_content = None
            st.session_state.edited_seo = {}
            st.rerun()

        progress_tab, output_tab = st.tabs(["Generation Progress", "Final Output"])

        with progress_tab:
            st.subheader("🔄 Generation Progress")
            status = st.empty()
            progress_bar = st.progress(0)

            if not st.session_state.generation_content:
                try:
                    status.text("Starting generation...")
                    progress_bar.progress(10)

                    additional_keywords_list = ([k.strip() for k in st.session_state.additional_keywords.split('\n')
                                                 if k.strip()] if st.session_state.additional_keywords else None)

                    result = generate_content(
                        st.session_state.template_text,
                        st.session_state.template_structure,
                        st.session_state.primary_keyword,
                        st.session_state.schema_template,
                        st.session_state.service_name,
                        additional_keywords_list
                    )

                    # Update both generation and edited content
                    st.session_state.generation_content = result
                    st.session_state.edited_content = result['content']
                    st.session_state.edited_seo = {
                        'title': result['title'],
                        'meta_description': result['meta_description'],
                        'schema': result['schema']
                    }
                    progress_bar.progress(100)
                    status.text("Generation complete!")

                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    return

        with output_tab:
            if st.session_state.generation_content:
                # Regeneration buttons
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.button("🔄 Regenerate Content", on_click=regenerate_callback, args=('content',),
                              key='btn_content')
                with col2:
                    st.button("🔄 Regenerate SEO", on_click=regenerate_callback, args=('seo',), key='btn_seo')
                with col3:
                    st.button("🔄 Regenerate All", on_click=regenerate_callback, args=('all',), key='btn_all')

                # Original Content View
                st.subheader("📄 Generated Content")
                st.markdown(st.session_state.generation_content['content'])

                # Content Editor in Expander
                with st.expander("📝 Content Editor"):
                    edited_content = st.text_area(
                        "Edit Generated Content",
                        value=st.session_state.edited_content,
                        height=500,
                        key="content_editor"
                    )

                    # Word Count Display
                    word_count = count_words(edited_content)
                    st.metric("Word Count", word_count)

                    # Save content changes
                    if st.button("Save Content Changes", key="save_content_btn"):
                        st.session_state.edited_content = edited_content
                        st.success("Content changes saved successfully!")

                # Content Expansion Feature
                with st.expander("✨ Expand Selected Content"):
                    selected_text = st.text_area(
                        "Paste the section you want to expand",
                        height=200,
                        key="expansion_input"
                    )
                    if st.button("Expand Content", key="expand_content_btn") and selected_text:
                        with st.spinner("Expanding content..."):
                            expanded_text = expand_content(
                                selected_text,
                                st.session_state.primary_keyword
                            )
                            st.text_area(
                                "Expanded Content (Copy and paste back to main editor)",
                                value=expanded_text,
                                height=300,
                                key="expanded_output"
                            )

                # SEO Metadata Editor
                with st.expander("📊 SEO Metadata Editor"):
                    edited_title = st.text_input(
                        "SEO Title",
                        value=st.session_state.edited_seo.get('title', ''),
                        max_chars=60,
                        help="Maximum 60 characters",
                        key="seo_title_input"
                    )
                    st.caption(f"Character count: {len(edited_title)}/60")

                    edited_meta = st.text_area(
                        "Meta Description",
                        value=st.session_state.edited_seo.get('meta_description', ''),
                        max_chars=160,
                        help="Maximum 160 characters",
                        key="seo_meta_input"
                    )
                    st.caption(f"Character count: {len(edited_meta)}/160")

                    edited_schema = st.text_area(
                        "Schema Markup",
                        value=json.dumps(st.session_state.edited_seo.get('schema', {}), indent=2),
                        height=300,
                        key="seo_schema_input"
                    )

                    if st.button("Save SEO Changes", key="save_seo_btn"):
                        try:
                            schema_dict = json.loads(edited_schema)
                            st.session_state.edited_seo = {
                                'title': edited_title,
                                'meta_description': edited_meta,
                                'schema': schema_dict
                            }
                            st.success("SEO changes saved successfully!")
                        except json.JSONDecodeError:
                            st.error("Invalid JSON in schema markup")

                # Save content changes
                if st.button("Save Content Changes"):
                    st.session_state.edited_content = edited_content
                    st.success("Content changes saved successfully!")

                # Template Analysis
                with st.expander("🔍 Template Analysis"):
                    st.write(st.session_state.generation_content['template_analysis'])

                # Download Section
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

                # Prepare files using edited content
                doc = create_word_doc(st.session_state.edited_content)
                word_buffer = BytesIO()
                doc.save(word_buffer)
                word_buffer.seek(0)

                csv_buffer = BytesIO()
                csv_buffer.write(save_to_csv({
                    'title': st.session_state.edited_seo['title'],
                    'meta_description': st.session_state.edited_seo['meta_description'],
                    'schema': json.dumps(st.session_state.edited_seo['schema'])
                }))
                csv_buffer.seek(0)

                # Create ZIP
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr(f'content_{timestamp}.docx', word_buffer.getvalue())
                    zf.writestr(f'content_{timestamp}.md',
                                st.session_state.edited_content.encode('utf-8'))
                    zf.writestr(f'metadata_{timestamp}.csv', csv_buffer.getvalue())
                zip_buffer.seek(0)

                # Download buttons
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.download_button(
                        "📦 Download All Files (ZIP)",
                        zip_buffer.getvalue(),
                        f"generated_content_{timestamp}.zip",
                        "application/zip",
                        use_container_width=True
                    )

                with col2:
                    with st.expander("Download Individual Files"):
                        st.download_button("📥 Download Word",
                                           word_buffer.getvalue(),
                                           f"content_{timestamp}.docx",
                                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                        st.download_button("📥 Download Markdown",
                                           st.session_state.edited_content,
                                           f"content_{timestamp}.md",
                                           "text/markdown")
                        st.download_button("📥 Download Metadata",
                                           csv_buffer.getvalue(),
                                           f"metadata_{timestamp}.csv",
                                           "text/csv")
                
            with st.expander("🌐 Generate HTML"):
                try:
                    page_type = st.selectbox(
                        "Select Page Type",
                        options=['service page'],
                        key="page_type_select"
                    )
                    
                    site_name = st.text_input(
                        "Enter Site Name",
                        key="site_name_input",
                        help="Make sure you have the corresponding template file (example: astoria-template.html) in your directory"
                    )
                    
                    # Check for template file before proceeding
                    if site_name:
                        template_file = f"{site_name.lower()}-template.html"
                        if not os.path.exists(template_file):
                            st.error(f"Template file '{template_file}' not found in the current directory. Please make sure the template file exists.")
                            st.info("Required template files should be named like: 'astoria-template.html', 'williamsburg-template.html', etc.")
                            debug_print(f"Looking for template file in: {os.getcwd()}")
                            debug_print(f"Files in current directory: {os.listdir()}")
                    
                    if st.button("Generate HTML", key="generate_html_btn"):
                        if page_type and site_name:
                            template_file = f"{site_name.lower()}-template.html"
                            if not os.path.exists(template_file):
                                st.error(f"Cannot proceed: Template file '{template_file}' not found.")
                                return
                                
                            try:
                                debug_print("Creating CSV data...")
                                csv_data = {
                                    'TITLE': [st.session_state.edited_seo.get('title', '')],
                                    'META_DESC': [st.session_state.edited_seo.get('meta_description', '')],
                                    'FAQ_SCHEMA': [json.dumps(st.session_state.edited_seo.get('schema', {}))],
                                    'CONTENT': [st.session_state.edited_content],
                                    'H2': [site_name]
                                }
                                
                                # Create a temporary CSV file
                                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as temp_csv:
                                    debug_print(f"Created temporary file: {temp_csv.name}")
                                    df = pd.DataFrame(csv_data)
                                    df.to_csv(temp_csv.name, index=False)
                                    debug_print(f"CSV Content Preview: {df.head()}")
                                
                                debug_print("Calling generate_filled_html...")
                                template_name = site_name.lower()
                                generate_filled_html(temp_csv.name, template_name)
                                
                                output_filename = f"{template_name}.html"
                                if os.path.exists(output_filename):
                                    with open(output_filename, 'r', encoding='utf-8') as f:
                                        html_content = f.read()
                                    
                                    st.download_button(
                                        "📥 Download Generated HTML",
                                        html_content,
                                        f"{template_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                                        "text/html"
                                    )
                                    
                                    # Clean up
                                    os.remove(output_filename)
                                    os.remove(temp_csv.name)
                                    st.success("HTML generated successfully!")
                                else:
                                    st.error(f"Output file {output_filename} was not created")
                                    
                            except Exception as e:
                                st.error(f"Error generating HTML: {str(e)}")
                                st.write(traceback.format_exc())
                            finally:
                                if 'temp_csv' in locals() and os.path.exists(temp_csv.name):
                                    os.remove(temp_csv.name)
                        else:
                            st.warning("Please select a page type and enter a site name.")
                except Exception as e:
                    st.error(f"Error in HTML generation section: {str(e)}")
                    st.write(traceback.format_exc())

if __name__ == "__main__":
    main()


