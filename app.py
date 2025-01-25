from dotenv import load_dotenv
import os
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from PyPDF2 import PdfReader
from docx import Document
import re

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Retrieve the API key
api_key = os.getenv("OPENAI_API_KEY")

# Initialize the OpenAI client with your API key
client = OpenAI(api_key=api_key)  

# Helper function to format and filter the summary
def process_summary(text):
    lines = text.splitlines()
    processed_lines = []
    current_point = None
    current_subpoints = []
    
    for line in lines:
        line = line.replace("**", "")    
        if not line:
            continue
        
        # Identify main points enclosed in '**'
        if line.startswith('- ') and line.endswith(':'):
            if current_point:
                processed_lines.append(f"<strong>{current_point}</strong>")
                processed_lines.extend([f"<li>{sub}</li>" for sub in current_subpoints])
                current_subpoints = []
            
            current_point = line.lstrip('- ').rstrip(':').strip()
        
        # Identify subpoints
        elif line.startswith(' ') and '-' in line:
            current_subpoints.append(line.lstrip('- ').strip())
    
    # Append last detected main point and its subpoints
    if current_point:
        processed_lines.append(f"<strong>{current_point}</strong>")
        processed_lines.extend([f"<li>{sub}</li>" for sub in current_subpoints])
        
    return "\n".join(processed_lines)

# Helper function to split text into chunks with overlap
def split_text_with_overlap(text, max_tokens=1500, overlap=50):
    words = text.split()
    start = 0
    while start < len(words):
        end = start + max_tokens
        chunk = ' '.join(words[start:end])
        yield chunk
        start = end - overlap  # Shift back by overlap to ensure continuity

# Helper function to call the OpenAI API for summarization with context
def openai_summarize_with_context(text, previous_summary=""):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", #gpt-3.5-turbo
            messages=[
                {"role": "system", "content": """
                Create a detailed and focused summary of a given regulatory document. The summary should include important metrics and key points, structured to allow the user to understand the main content without reading the original document.

                - Focus on identifying the most significant points and metrics in the regulatory document.
                - Organize the summary logically, covering each key aspect thoroughly.
                - Ensure the summary is comprehensive enough to provide a clear understanding of the original content.

                # Steps

                1. Read the given regulatory document thoroughly.
                2. Identify and extract the most important metrics and key points.
                3. Organize these points logically to form a coherent summary.
                4. Compose the summary in a clear and detailed manner, ensuring it is understandable without reference to the original text.

                # Output Format

                - A well-structured summary in bullet points with sub-points for each main point.
                - Should be 150-250 words for optimal detail and comprehensiveness.

                # Examples

                **Input:** "The regulatory document mandates a 20% reduction in emission levels by 2030, introduces a compliance framework with quarterly reporting and penalties for non-compliance..."

                **Output:** 
                - **Emission Reduction Goals:**
                  - 20% reduction by 2030
                  - Implementation strategies outlined
                  - Monitoring and reporting mechanisms established
                - **Compliance Framework:**
                  - Quarterly reporting requirements detailed
                  - Penalties for non-compliance specified
                  - Incentives for early compliance offered
                - **Additional Regulations:**
                  - New standards for industrial emissions
                  - Alignment with international guidelines
                  - Impact assessment procedures included (Real examples should be longer.)

                # Notes

                - Pay special attention to regulatory data, compliance metrics, and guidelines as they are crucial to understanding the document.
                - Ensure the summary is detailed to clearly convey the regulatory requirements and implications, maintaining clarity while thoroughly capturing the essence of the original content."""},
                {"role": "user", "content": f"{text}"}
                ],
            max_tokens=1500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

# Helper function to summarize the entire document using rolling context
def summarize_text_with_context(text):
    chunks = list(split_text_with_overlap(text, max_tokens=1500, overlap=50))
    full_summary = []
    previous_summary = ""

    for chunk in chunks:
        summary = openai_summarize_with_context(chunk, previous_summary)
        if summary:
            full_summary.append(summary)
            previous_summary = summary  # Pass this as context for the next chunk

    # Combine the summarized chunks into a single summary
    return "\n".join(full_summary)

# Function to get a title from the first chunk of the text
def openai_generate_title(text):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates concise and meaningful titles."},
                {"role": "user", "content": f"Generate a brief and meaningful title for the following text: {text}"}
            ],
            max_tokens=20  # Keep the title brief
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating title: {e}")
        return "Document Summary"  # Fallback title if generation fails

# Helper function to extract text from Word documents
def extract_text_from_word(docx_file):
    try:
        doc = Document(docx_file)
        return '\n'.join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
    except Exception as e:
        print(f"Error extracting text from Word document: {e}")
        return ""

# Helper function to filter out contents pages
def filter_contents_page(text):
    lines = text.splitlines()
    filtered_lines = []
    for line in lines:
        # Skip lines indicating contents, e.g., "Table of Contents", or lines with page numbers
        if re.search(r"Table of Contents|\.{5,}|\b\d+\b", line):
            continue
        filtered_lines.append(line)
    return '\n'.join(filtered_lines)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/summarize', methods=['POST'])
def summarize():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']

    # Check if the file is a valid PDF or Word document
    if file.filename == '' or not (file.filename.endswith('.pdf') or file.filename.endswith('.docx')):
        return jsonify({'error': 'Invalid file format'}), 400

    # Extract text from the file
    try:
        if file.filename.endswith('.pdf'):
            reader = PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        elif file.filename.endswith('.docx') or file.filename.endswith('.doc'):
            text = extract_text_from_word(file)

        # If the document has no extractable text, return an error
        if not text.strip():
            return jsonify({'error': 'The document has no readable text'}), 400

        # Filter out the contents page
        text = filter_contents_page(text)

    except Exception as e:
        print(f'Error extracting text: {e}')
        return jsonify({'error': f'Error processing document: {str(e)}'}), 500

    # Generate title using the first chunk of the text
    first_chunk = next(split_text_with_overlap(text, max_tokens=1500), "")
    generated_title = openai_generate_title(first_chunk)
    
    # Remove word 'summary' if present in the title
    if 'summary' in generated_title.lower():
        generated_title = re.sub(r'\b[Ss]ummary\b', '', generated_title).strip()

    # Summarize the extracted text using OpenAI API with rolling context
    try:
        structured_summary = summarize_text_with_context(text)
        if structured_summary:
            print(structured_summary)
        formatted_summary = process_summary(structured_summary)
    except Exception as e:
        return jsonify({'error': f'Error summarizing document: {str(e)}'}), 500

    # Return the structured summary as JSON
    return jsonify({'title': f"{generated_title} Summary", 'summary': formatted_summary})

# if __name__ == '__main__':
#     app.run(debug=True)
