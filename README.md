# BFS-PDF-Summarizer with OpenAI API

This is a Flask web application that uses the OpenAI API to generate structured summaries from PDF files. The app takes a PDF as input, processes the text, and produces a concise summary with main points and sub-points. The application also supports deployment on platforms like Render.

---

## Features

- Extracts text from uploaded PDF files.
- Generates structured and concise summaries using OpenAI's GPT models.
- Displays summaries with bold main points and bullet-style sub-points for readability.
- Dynamically generates a title for each summary based on the content.
- Secure handling of API keys using environment variables.

---

## Live Web App

You can access the deployed web application here:  
[PDF Summarizer on Render](https://bfs-pdf-summarizer.onrender.com)  

---

## Technologies Used

- **Python** (Flask)
- **OpenAI API** (GPT-3.5 Turbo)
- **PyPDF2** (for PDF text extraction)
- **Gunicorn** (for production deployment)
- **HTML/CSS/JavaScript** (for the frontend)

---

## Installation

### Prerequisites

- Python 3.6 or higher
- OpenAI API key (create one from [OpenAI](https://platform.openai.com/))
- A terminal or command prompt with Git installed

### Steps

1. **Clone the Repository**
   ```
   git clone https://github.com/Sayanss99/BFS-PDF-Summarizer.git
   cd BFS-PDF-Summarizer
   ```
