from dotenv import load_dotenv
import os
from openai import OpenAI
from flask import Flask, request, jsonify, render_template
from PyPDF2 import PdfReader
import re

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Retrieve the API key
api_key = os.getenv("OPENAI_API_KEY")

# Initialize the OpenAI client with your API key
client = OpenAI(api_key=api_key)  # Replace with your actual API key

# Helper function to format and filter the summary
def process_summary(text):
    lines = text.splitlines()  # Split the text into individual lines
    processed_lines = []
    current_point = None
    current_subpoints = []
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Handle main points (lines ending with ':')
        if line.endswith(':'):
            if current_point:  # If there was a previous main point, process its sub-points
                if current_subpoints:
                    processed_lines.append(f"<strong>{current_point}</strong>")
                    processed_lines.extend([f"<li>{sub}</li>" for sub in current_subpoints])
                current_subpoints = []
            
            # Clean the main point
            clean_point = re.sub(r"^\d+\.\s*", "", line).strip(":")
            current_point = clean_point
        
        # Handle sub-points (lines starting with '-')
        elif line.startswith('-'):
            clean_subpoint = re.sub(r"^\d+\.\s*", "", line).lstrip("-").strip()
            current_subpoints.append(clean_subpoint)
    
    # Add the last point and its sub-points
    if current_point and current_subpoints:
        processed_lines.append(f"<strong>{current_point}</strong>")
        processed_lines.extend([f"<li>{sub}</li>" for sub in current_subpoints])
    
    # Return the processed HTML-formatted summary
    return "\n".join(processed_lines)

# Helper function to split text into chunks with overlap
def split_text_with_overlap(text, max_tokens=1500, overlap=100):
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
            model="gpt-3.5-turbo",  # You can also use 'gpt-4' if available
            messages=[
                {"role": "system", "content": "You are a concise and detail-focused summarizer."},
                {"role": "user", "content": f"Here is a summary of the previous section: {previous_summary}. Now, please summarize the following text into brief and concise bullet points with two or three sub-points for each main point: {text}"}
            ],
            max_tokens=500  # Adjust based on how detailed the summary should be
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

# Helper function to summarize the entire PDF using rolling context
def summarize_pdf_text_with_context(pdf_text):
    chunks = list(split_text_with_overlap(pdf_text, max_tokens=1500, overlap=100))
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
        return "PDF Summary"  # Fallback title if generation fails

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/summarize', methods=['POST'])
def summarize():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']

    # Check if the file is a valid PDF
    if file.filename == '' or not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Invalid file format'}), 400

    # Extract text from the PDF
    try:
        reader = PdfReader(file)
        pdf_text = ""
        for page in reader.pages:
            pdf_text += page.extract_text()

        # If the PDF has no extractable text, return an error
        if not pdf_text.strip():
            return jsonify({'error': 'The PDF has no readable text'}), 400

    except Exception as e:
        print(f'Error extracting text: {e}')
        return jsonify({'error': f'Error processing PDF: {str(e)}'}), 500

    # Generate title using the first chunk of the text
    first_chunk = next(split_text_with_overlap(pdf_text, max_tokens=1500), "")
    generated_title = openai_generate_title(first_chunk)
    
    # remove word 'summary' if present
    if 'summary' in generated_title.lower():
        generated_title = re.sub(r'\b[Ss]ummary\b', '', generated_title).strip()

    # Summarize the extracted text using OpenAI API with rolling context
    try:
        structured_summary = summarize_pdf_text_with_context(pdf_text)
        formatted_summary = process_summary(structured_summary)
    except Exception as e:
        return jsonify({'error': f'Error summarizing PDF: {str(e)}'}), 500

    # Return the structured summary as JSON
    return jsonify({'title': f"{generated_title} Summary", 'summary': formatted_summary})

'''if __name__ == '__main__':
    app.run(debug=True)
'''