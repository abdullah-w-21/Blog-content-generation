import streamlit as st
import pandas as pd
from docx import Document
import json
import os
os.environ["CHROMA_DB_IMPL"] = st.secrets["CHROMA_DB_IMPL"]
from crewai import Agent, Task, Crew, Process
from textwrap import dedent
from io import BytesIO
from langchain_openai import ChatOpenAI
from datetime import datetime
import zipfile

# Session state initialization
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
            1. Content flow and structure
            2. Key sections and their purposes
            3. Content patterns and relationships
            4. Recommended approach for content creation
            5. Pay close attention to the use of headings (H1, H2, H3) and how they organize the information.
            6. The number of FAQ's
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
            1. Follow provided template structure exactly
            2. Use H2: and H3: prefix for headings
            3. Word count: 1700-1800 so it ranks on google
            4. Follow EEAT framework
            5. Natural LSI keyword integration
            6. Prioritize user value and clarity

            Output content using H2: and H3: prefixes for headings.
            """,
            expected_output="SEO-optimized content following template structure with proper heading hierarchy with (H1:,H2:,H3:) prefixes for headings.",
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
            [complete schema markup with FAQs schema]
            """,
            expected_output="SEO metadata including title, meta description, and complete schema markup with FAQs schema",
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
                    1. Content flow and structure
                    2. Key sections and their purposes
                    3. Content patterns and relationships
                    4. Recommended approach for content creation
                    5. Pay close attention to the use of headings (H1, H2, H3) and how they organize the information.
                    6. The number of FAQ's
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
                    1. Follow provided template structure exactly
                    2. Use H2: and H3: prefix for headings
                    3. Word count: 1700-1800 so it ranks on google
                    4. Follow EEAT framework
                    5. Natural LSI keyword integration
                    6. Prioritize user value and clarity

                    Output content using H2: and H3: prefixes for headings. 
                    """,
            expected_output="SEO-optimized content following template structure with proper heading hierarchy with (H1:,H2:,H3:) prefixes for headings.",
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
                    [complete schema markup with FAQs schema]
                    """,
            expected_output="SEO metadata including title, meta description, and complete schema markup with FAQs schema",
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
            st.rerun()  # Force rerun after update

        else:
            st.session_state.generation_content = generate_content(
                st.session_state.template_text,
                st.session_state.template_structure,
                st.session_state.primary_keyword,
                st.session_state.schema_template,
                st.session_state.service_name,
                additional_keywords_list)
            st.rerun()  # Force rerun after update


def save_to_csv(data):
    df = pd.DataFrame([data])
    return df.to_csv(index=False).encode('utf-8')


def main():
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    if 'template_doc_content' not in st.session_state:
        st.session_state.template_doc_content = None

    st.title("Content Generation App")

    if not configure_openai():
        st.warning("Please enter your OpenAI API key in the sidebar.")
        return

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

    if st.session_state.form_submitted:
        if st.button("← Back to Form"):
            st.session_state.form_submitted = False
            st.session_state.generation_content = None
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

                    st.session_state.generation_content = result
                    progress_bar.progress(100)
                    status.text("Generation complete!")

                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    return

        with output_tab:
            if st.session_state.generation_content:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.button("🔄 Regenerate Content", on_click=regenerate_callback, args=('content',),
                              key='btn_content')
                with col2:
                    st.button("🔄 Regenerate SEO", on_click=regenerate_callback, args=('seo',), key='btn_seo')
                with col3:
                    st.button("🔄 Regenerate All", on_click=regenerate_callback, args=('all',), key='btn_all')

                st.subheader("📄 Generated Content")
                st.markdown(st.session_state.generation_content['content'])

                with st.expander("📊 SEO Metadata"):
                    st.write("Title:", st.session_state.generation_content['title'])
                    st.write("Meta Description:", st.session_state.generation_content['meta_description'])
                    st.write("Schema:", st.session_state.generation_content['schema'])

                with st.expander("🔍 Template Analysis"):
                    st.write(st.session_state.generation_content['template_analysis'])

                # Create download options
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

                # Prepare files
                doc = create_word_doc(st.session_state.generation_content['word_content'])
                word_buffer = BytesIO()
                doc.save(word_buffer)
                word_buffer.seek(0)

                csv_buffer = BytesIO()
                csv_buffer.write(save_to_csv({
                    'title': st.session_state.generation_content['title'],
                    'meta_description': st.session_state.generation_content['meta_description'],
                    'schema': json.dumps(st.session_state.generation_content['schema'])
                }))
                csv_buffer.seek(0)

                # Create ZIP
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr(f'content_{timestamp}.docx', word_buffer.getvalue())
                    zf.writestr(f'content_{timestamp}.md',
                                st.session_state.generation_content['content'].encode('utf-8'))
                    zf.writestr(f'metadata_{timestamp}.csv', csv_buffer.getvalue())
                zip_buffer.seek(0)

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
                        st.download_button("📥 Download Word", word_buffer.getvalue(),
                                           f"content_{timestamp}.docx",
                                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                        st.download_button("📥 Download Markdown",
                                           st.session_state.generation_content['content'],
                                           f"content_{timestamp}.md", "text/markdown")
                        st.download_button("📥 Download Metadata", csv_buffer.getvalue(),
                                           f"metadata_{timestamp}.csv", "text/csv")


if __name__ == "__main__":
    main()
