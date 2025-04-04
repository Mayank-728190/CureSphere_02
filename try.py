import os
import time
import markdown
import tempfile
import PyPDF2
import google.generativeai as genai
from flask import Flask, render_template, request, redirect, flash, url_for
from dotenv import load_dotenv
from PIL import Image, ImageDraw

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "supersecretkey"  # Required for flashing messages

# Configure Gemini AI model
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ Gemini API key not found! Set GEMINI_API_KEY in environment variables.")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Function to analyze medical reports using AI
def analyze_medical_report(content, content_type):
    prompt = """Analyze this medical report in detail. Identify and summarize the key findings, diagnoses, and observations.
    Provide actionable recommendations, recovery tips, and potential home remedies where applicable.
    Additionally, suggest any lifestyle adjustments or further diagnostic tests required.
    Explain complex medical terms in simple language for better clarity.
    """

    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content([prompt, content]) if content_type == "image" else model.generate_content(f"{prompt}\n\n{content}")
            return response.text
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                return f"AI analysis failed after {MAX_RETRIES} attempts. Error: {str(e)}"

# Function to extract text from a PDF
def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = "".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
    return text or "No text found in PDF."

# Home Route
@app.route('/')
def index():
    return render_template('index.html')

# Route for handling file uploads
@app.route('/analyze', methods=['POST'])
def analyze_report():
    if 'file' not in request.files:
        flash("⚠️ No file uploaded. Ensure the form has enctype='multipart/form-data'.")
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        flash("⚠️ No file selected. Please upload a valid file.")
        return redirect(request.url)

    file_type = file.filename.split('.')[-1].lower()
    
    if file_type in ['jpg', 'jpeg', 'png']:
        content_type = "image"
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type}') as tmp_file:
            tmp_file.write(file.read())
            tmp_file_path = tmp_file.name
        image = Image.open(tmp_file_path)
        
        # Add text overlay
        draw = ImageDraw.Draw(image)
        draw.text((10, 10), "Analysis: Example text", fill="red")
        
        # Save image
        analyzed_image_path = os.path.join("static", "analyzed_image.png")
        image.save(analyzed_image_path)
        
        # Analyze with AI
        analysis = analyze_medical_report(image, "image")
        os.unlink(tmp_file_path)
    elif file_type == 'pdf':
        content_type = "text"
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(file.read())
            tmp_file_path = tmp_file.name
        with open(tmp_file_path, 'rb') as pdf_file:
            pdf_text = extract_text_from_pdf(pdf_file)
        analysis = analyze_medical_report(pdf_text, "text")
        os.unlink(tmp_file_path)
        analyzed_image_path = None  # No image output for PDFs
    else:
        flash("⚠️ Unsupported file type. Please upload a PDF or image.")
        return redirect(request.url)

    return render_template('index.html', analysis=markdown.markdown(analysis), image_path=analyzed_image_path)

if __name__ == '__main__':
    app.run(debug=True)
