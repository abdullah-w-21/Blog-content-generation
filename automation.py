import os
import sys
import pandas as pd
from docx import Document
import re
from docx2python import docx2python
import markdown2
import json


LOG_FILENAME = "processing_log.txt"


def log_message(message):
    """Append a message to the log file."""
    with open(LOG_FILENAME, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def log_and_terminate(message):
    """Log an error message and terminate the script."""
    log_message("ERROR: " + message)
    sys.exit(1)


def read_csv_data(csv_file, cell_mapping, delimiter=",", header=0):
    """
    Reads data from a CSV file using the specified cell mapping.
    If the file cannot be opened, terminate.
    If any cell is empty, terminate.

    Args:
        csv_file (str): Path to the CSV file.
        cell_mapping (dict): Dictionary mapping data names to column names.
        delimiter (str, optional): Delimiter used in the CSV file (default ',').
        header (int or None, optional): Row number to use as header (default 0).

    Returns:
        dict: Dictionary containing the data extracted from the CSV file.
    """
    try:
        df = pd.read_csv(csv_file, delimiter=delimiter, header=header)
    except Exception as e:
        log_and_terminate(f"Failed to open CSV file '{csv_file}': {e}")

    data = {}
    for key, col_name in cell_mapping.items():
        val = df[col_name].iloc[0]  # Access the first row (index 0) of the column
        if pd.isna(val) or str(val).strip() == "":
            log_and_terminate(
                f"Cell for '{key}' in column '{col_name}' is empty. Cannot proceed."
            )
        data[key] = str(val).strip()

    log_message(f"Successfully read data from CSV file '{csv_file}'")
    return data


def find_nth_occurrence(content, substring, n):
    """
    Find the index of the nth occurrence of substring in content.
    Returns -1 if not found.
    """
    start = 0
    count = 0
    while True:
        index = content.find(substring, start)
        if index == -1:
            return -1
        count += 1
        if count == n:
            return index
        start = index + len(substring)


def replace_segment_in_html(
    html_content,
    search_start_marker,
    search_end_marker,
    replacement_text,
    start_occurrence=1,
    end_occurrence=1,
):
    """
    Finds the nth occurrence of search_start_marker and nth occurrence of search_end_marker in html_content
    and replaces everything from search_start_marker to search_end_marker (inclusive) with replacement_text.
    If occurrences are not found, terminate.
    """
    start_index = find_nth_occurrence(
        html_content, search_start_marker, start_occurrence
    )
    if start_index == -1:
        log_and_terminate(
            f"Search start marker '{search_start_marker}' (occurrence {start_occurrence}) not found in HTML."
        )

    end_index = find_nth_occurrence(
        html_content[start_index + len(search_start_marker) :],
        search_end_marker,
        end_occurrence,
    )
    if end_index == -1:
        log_and_terminate(
            f"Search end marker '{search_end_marker}' (occurrence {end_occurrence}) not found in HTML after start marker '{search_start_marker}'."
        )

    # Adjust end_index relative to the whole string
    end_index = start_index + len(search_start_marker) + end_index

    before = html_content[:start_index]
    after = html_content[end_index + len(search_end_marker) :]
    return before + replacement_text + after


def load_html_template(file_path):
    """Load the HTML template file. If fails, terminate."""
    if not os.path.isfile(file_path):
        log_and_terminate(f"HTML template file '{file_path}' does not exist.")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        log_message(f"Successfully loaded HTML template '{file_path}'.")
        return content
    except Exception as e:
        log_and_terminate(f"Failed to read HTML template '{file_path}': {e}")


def save_html_content(file_path, content):
    """Save the updated HTML content to a file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        log_message(f"Successfully saved updated HTML to '{file_path}'.")
    except Exception as e:
        log_and_terminate(f"Failed to write updated HTML to '{file_path}': {e}")


def update_html_content(html_content, data, replacements_config):
    """
    Given html_content, data dictionary, and replacements_config, perform all required replacements.

    Each entry in replacements_config should provide:
    - search_start_marker (string): marker that defines start of the section to remove
    - search_end_marker (string): marker that defines end of the section to remove
    - search_start_occurrence (int, optional): which occurrence of start marker
    - search_end_occurrence (int, optional): which occurrence of end marker
    - replacement_start (string, optional): text to put before cell content in the replacement
    - replacement_end (string, optional): text to put after cell content in the replacement

    If replacement_start/end are not provided, defaults to empty strings.
    """
    updated_content = html_content

    for key, config in replacements_config.items():
        cell_value = data.get(key, "")

        # Required keys for searching in HTML
        search_start_marker = config["search_start_marker"]
        search_end_marker = config["search_end_marker"]

        # Optional occurrence parameters
        start_occ = config.get("search_start_occurrence", 1)
        end_occ = config.get("search_end_occurrence", 1)

        # Optional replacement wrappers
        replacement_start = config.get("replacement_start", "")
        replacement_end = config.get("replacement_end", "")

        # Build the replacement text
        replacement_text = replacement_start + cell_value + replacement_end

        updated_content = replace_segment_in_html(
            updated_content,
            search_start_marker,
            search_end_marker,
            replacement_text,
            start_occurrence=start_occ,
            end_occurrence=end_occ,
        )

        log_message(
            f"Successfully replaced segment for '{key}' with '{replacement_text}'."
        )
    return updated_content


def process_html_template(
    html_file, excel_file, sheet_name, cell_mapping, replacements_config, in_place=True
):
    """
    Process a single HTML template and update based on Excel data.
    The script will terminate on any error.
    """
    data = read_excel_data(excel_file, sheet_name, cell_mapping)
    html_content = load_html_template(html_file)
    updated_content = update_html_content(html_content, data, replacements_config)

    if in_place:
        output_file = html_file
    else:
        base, ext = os.path.splitext(html_file)
        output_file = base + "-new" + ext

    save_html_content(output_file, updated_content)
    log_message("All operations completed successfully.")


def docx_to_html_with_docx2python(
    docx_path, entire_start="", entire_end="", p_start="<p>", p_end="</p>"
):
    """
    Converts a DOCX file into HTML with:
    - Detection and handling of nested bullet and numbered lists.
    - Optionally wraps entire content and paragraphs with specified tags.
    - No inline formatting (e.g., bold) is processed here.

    Args:
        docx_path (str): Path to the DOCX file.
        entire_start (str): HTML tag or string to wrap the entire content at the start.
        entire_end (str): HTML tag or string to wrap the entire content at the end.
        p_start (str): HTML tag to wrap each paragraph at the start.
        p_end (str): HTML tag to wrap each paragraph at the end.

    Returns:
        str: Generated HTML content.
    """
    doc_content = docx2python(docx_path)
    paragraphs = []

    # Extract non-empty paragraphs
    for section in doc_content.body:
        for page in section:
            for column in page:
                for paragraph in column:
                    if paragraph.strip():
                        paragraphs.append(paragraph)

    html_fragments = []
    if entire_start:
        html_fragments.append(entire_start)

    # This stack will track open lists. Each element is ("ul" or "ol").
    list_stack = []

    def close_all_lists():
        """Close all currently open lists."""
        while list_stack:
            tag = list_stack.pop()
            html_fragments.append(f"</{tag}>")

    def close_to_level(level):
        """
        Close lists until the nesting depth (len(list_stack)) equals 'level'.
        'level' here is the number of open lists desired.
        """
        while len(list_stack) > level:
            tag = list_stack.pop()
            html_fragments.append(f"</{tag}>")

    def open_list(list_type):
        """Open a new list of the given type (ul or ol)."""
        list_stack.append(list_type)
        html_fragments.append(f"<{list_type}>")

    # Function to detect and handle list paragraphs
    # We consider indent_level = number of leading tabs at line start.
    # For bullets: '--\t' at start (after indentation) indicates a bullet item.
    # For nested bullets: one extra leading tab per nesting level.
    # Numbered lists: a regex for leading digits, e.g., "1. " or "1) "
    for paragraph in paragraphs:
        # Count leading tabs
        indent_match = re.match(r"^(\t+)", paragraph)
        indent_level = len(indent_match.group(1)) if indent_match else 0

        # Line after removing leading tabs
        line_stripped = paragraph[indent_level:]

        # Detect bullet or number
        bullet_match = re.match(r"^--\t", line_stripped)
        number_match = re.match(r"^[0-9]+[\.\)]\s?", line_stripped)

        if bullet_match:
            current_type = "ul"
        elif number_match:
            current_type = "ol"
        else:
            current_type = None

        if current_type:
            # This is a list item
            # Desired depth: indent_level + 1 means if indent_level=0, we want 1 open list, if=1, we want 2, etc.
            desired_depth = indent_level + 1

            # Adjust the current list stack depth
            if len(list_stack) > desired_depth:
                # Close lists until we are at the correct depth
                close_to_level(desired_depth)
            elif len(list_stack) < desired_depth:
                # Need to open more lists
                while len(list_stack) < desired_depth:
                    open_list(current_type)
            else:
                # Same depth, check if the current top matches the current_type
                if list_stack[-1] != current_type:
                    # Close the mismatched list and open the correct one
                    close_to_level(desired_depth - 1)
                    open_list(current_type)

            # Remove the bullet or number marker from the content
            if bullet_match:
                # Remove the '--\t' marker
                item_content = re.sub(r"^--\t", "", line_stripped)
            else:
                # Remove the numbering marker (e.g. '1. ', '1) ')
                item_content = re.sub(r"^[0-9]+[\.\)]\s?", "", line_stripped)

            # Escape HTML special chars in content
            item_content = (
                item_content.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

            html_fragments.append(f"<li>{item_content}</li>")

        else:
            # Not a list item, close all lists and add a paragraph
            close_all_lists()
            paragraph_content = (
                paragraph.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            html_fragments.append(f"{p_start}{paragraph_content}{p_end}")

    # Close any remaining lists
    close_all_lists()

    if entire_end:
        html_fragments.append(entire_end)

    return "\n".join(html_fragments)


def replace_all_markers_in_html(html_content, markers):
    """
    Replace all occurrences of marker pairs in the HTML content with corresponding tags.

    Args:
        html_content (str): The HTML content where markers need to be replaced.
        markers (dict): Dictionary of markers in the format:
            {
                (start_marker, end_marker): (start_tag, end_tag),
                ...
            }

    Returns:
        str: Updated HTML content with all marker pairs replaced.
    """
    updated_html = html_content

    for (start_marker, end_marker), (start_tag, end_tag) in markers.items():
        while True:
            start_idx = updated_html.find(start_marker)
            if start_idx == -1:
                # No more start markers; move to the next marker pair
                break

            # Look for the next end marker after the start marker
            end_idx = updated_html.find(end_marker, start_idx + len(start_marker))
            if end_idx == -1:
                # No matching end marker; stop processing this pair
                log_message(
                    f"Unmatched start marker '{start_marker}' found without corresponding end marker '{end_marker}'."
                )
                break

            # Extract the content between start and end markers
            inner_content = updated_html[start_idx + len(start_marker) : end_idx]

            # Build the replacement with the tags
            replacement = f"{start_tag}{inner_content}{end_tag}"

            # Replace the segment (including start and end markers) with the replacement
            updated_html = (
                updated_html[:start_idx]
                + replacement
                + updated_html[end_idx + len(end_marker) :]
            )

    return updated_html


def process_preliminary_html(preliminary_html, markers):
    """
    Convert preliminary HTML into processed HTML by replacing markers with corresponding tags.

    Args:
        preliminary_html (str): The raw HTML generated from the DOCX file.
        markers (dict): Dictionary of markers in the format:
            {
                (start_marker, end_marker): (start_tag, end_tag),
                ...
            }

    Returns:
        str: Processed HTML with all markers replaced.
    """
    log_message("Starting to process preliminary HTML with markers...")
    processed_html = replace_all_markers_in_html(preliminary_html, markers)
    log_message("Successfully processed preliminary HTML.")
    return processed_html


def preprocess_bold_text(docx_path, output_path):
    """
    Preprocess a DOCX file to encapsulate bold text with <bold> and </bold> tags.

    Args:
        docx_path (str): Path to the input DOCX file.
        output_path (str): Path to save the modified DOCX file.

    Returns:
        None
    """
    doc = Document(docx_path)

    for paragraph in doc.paragraphs:
        new_runs = []
        for run in paragraph.runs:
            if run.bold:  # If the text is bold
                run.text = f"<bold>{run.text}</bold>"
                run.bold = False  # Remove the bold formatting
            new_runs.append(run.text)

        # Update paragraph text with modified runs
        paragraph.text = "".join(new_runs)

    # Save the modified document
    doc.save(output_path)
    print(f"Processed document saved to: {output_path}")


def markdown_to_html(markdown_text):
    """
    Converts Markdown text to HTML, handling headings, bullet points,
    numbered lists, bold text, and paragraphs (including multiple paragraphs
    and paragraphs ending at the end of lines or within a line).

    Args:
        markdown_text: The Markdown text to convert.

    Returns:
        The HTML representation of the Markdown text.
    """
    html_lines = []
    in_list = False
    in_ordered_list = False
    in_paragraph = False

    def close_paragraph():
        nonlocal in_paragraph
        if in_paragraph:
            html_lines.append("</p>")
            in_paragraph = False

    def close_list():
        nonlocal in_list, in_ordered_list
        if in_list:
            html_lines.append("</ul>")
            in_list = False
        if in_ordered_list:
            html_lines.append("</ol>")
            in_ordered_list = False

    for line in markdown_text.splitlines():
        line = line.strip()

        # Handle headings
        if line.startswith("#"):
            close_paragraph()
            close_list()
            match = re.match(r"(#+)\s*(H\d)?(:\s*)?(.*)", line)
            if match:
                level = len(match.group(1))
                text = match.group(4).strip()
                if 1 <= level <= 6:
                    html_lines.append(f"<h{level}>{text}</h{level}>")
            continue

        # Handle bullet points (unordered lists)
        if line.startswith("- "):
            close_paragraph()
            if not in_list:
                html_lines.append('<ul class="list" role="list">')
                in_list = True
            text = line[2:].strip()
            text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
            html_lines.append(f"  <li>{text}</li>")
            continue
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False

        # Handle numbered lists (ordered lists)
        if re.match(r"\d+\.\s", line):
            close_paragraph()
            if not in_ordered_list:
                html_lines.append('<ol class="list" role="list">')
                in_ordered_list = True
            text = line.split(". ", 1)[1].strip()
            text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
            html_lines.append(f"<li>{text}</li>")
            continue
        else:
            if in_ordered_list:
                html_lines.append("</ol>")
                in_ordered_list = False

        # Handle paragraphs (with line break detection within paragraphs)
        if not in_paragraph:
            html_lines.append("<p>")
            in_paragraph = True

        # Split the line by newline characters to handle paragraph breaks within lines
        sublines = line.split("\n")

        for subline in sublines:
            subline = subline.strip()
            if subline:
                # Apply bold formatting using regular expressions
                subline = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", subline)

                html_lines.append(subline)
                close_paragraph()  # Close the paragraph after each subline
                if (
                    subline != sublines[-1]
                ):  # Don't open a new paragraph if it's the last subline
                    html_lines.append("<p>")
                    in_paragraph = True

    # Close any open elements at the end
    close_paragraph()
    close_list()

    return "\n".join(html_lines)


def format_meta_tags(meta_tags_str):
    """
    Converts a JSON string of meta tags into HTML meta tag strings.

    Args:
      meta_tags_str: A JSON string containing meta tag information.
                     The JSON object should have a "raw_schema" key containing
                     the HTML code snippet with the meta tags.

    Returns:
      A string containing the formatted HTML meta tags with "```html"
      and "```" removed.
    """

    try:
        meta_tags_dict = json.loads(meta_tags_str)
        html_code = meta_tags_dict["raw_schema"]
        # Remove "```html" from the beginning and "```" from the end
        html_code = html_code.replace("```html\n", "").replace("```", "")
        return html_code
    except (json.JSONDecodeError, KeyError) as e:
        return f"Error: {e}"


def generate_filled_html(content, location):
    """
    Generates an HTML file filled with content from a CSV file for a specific location.

    Args:
        content (str): The name of the CSV file containing the content.
        location (str): The location (e.g., 'astoria', 'williamsburg') for which to generate the HTML.

    Returns:
        None
    """

    csv_file = content

    html_names = [
        "astoria",
        "williamsburg",
        "hicksville",
        "174th-street",
        "jackson-heights",
        "bartow-mall",
        "jamaica",
        "stuytown",
        "crown-heights",
        "mineola",
        "long-island-city",
    ]

    if location not in html_names:
        log_and_terminate(f"Invalid location: {location}")

    html_template_file = location + "-template.html"  # Construct the template file name
    saving_name = location + ".html"

    cell_mapping = {
        "TITLE": "TITLE",
        "META_DESC": "META_DESC",
        "FAQ_SCHEMA": "FAQ_SCHEMA",
        "CONTENT": "CONTENT",
        "H2": "H2",
    }

    # 1. Read data from the CSV file using a modified read_excel_data (now read_csv_data)
    data = read_csv_data(csv_file, cell_mapping)

    # 2. Load the HTML template
    template = load_html_template(html_template_file)

    # 3. Replace content in the template
    final_html = replace_segment_in_html(
        template, "<title>", "</title>", "<title>" + data["TITLE"] + "</title>"
    )
    final_html = replace_segment_in_html(
        final_html,
        "<meta",
        '"viewport"/>',
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>',
        start_occurrence=2,
    )
    final_html = replace_segment_in_html(
        final_html,
        "<meta",
        '"description"/>',
        '<meta name=description content="' + data["META_DESC"] + '"/>',
        start_occurrence=3,
    )
    data["FAQ_SCHEMA"] = format_meta_tags(data["FAQ_SCHEMA"])
    final_html = replace_segment_in_html(
        final_html, "<script type=", "</script>", data["FAQ_SCHEMA"]
    )
    data["CONTENT"] = markdown_to_html(data["CONTENT"])
    final_html = replace_segment_in_html(
        final_html,
        '<div class="frame-1000004889">',
        "</div>",
        '<section class="main-content">\n' + data["CONTENT"] + "\n</section>",
        end_occurrence=3,
    )
    final_html = replace_segment_in_html(
        final_html, "<h1>", "</h1>", "<h2>" + data["H2"] + "</h2>", start_occurrence=1
    )
    final_html = replace_segment_in_html(
        final_html, "<h1>", "</h1>", "<h2>" + data["H2"] + "</h2>", start_occurrence=1
    )

    # 4. Save the updated HTML
    save_html_content(saving_name, final_html)
    log_message(f"Successfully generated HTML for {location} from {csv_file}")


# Example Usage
# content_file_name = 'content.csv'
# location = 'astoria'
# generate_filled_html(content_file_name, location)
