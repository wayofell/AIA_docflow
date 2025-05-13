import os
import PyPDF2
from PIL import Image
import pytesseract
from pdfminer.high_level import extract_text
import io
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF file using a combination of PyPDF2 and pdfminer.six
    """
    if not os.path.exists(file_path):
        logger.error(f"PDF file not found: {file_path}")
        return ""
        
    # First try with PyPDF2
    text = ""
    try:
        with open(file_path, "rb") as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        logger.info(f"PyPDF2 extracted {len(text)} characters from {file_path}")
    except Exception as e:
        logger.error(f"PyPDF2 extraction failed: {e}")
    
    # If PyPDF2 didn't get much text, try with pdfminer
    if len(text.strip()) < 50:
        try:
            text = extract_text(file_path)
            logger.info(f"pdfminer extracted {len(text)} characters from {file_path}")
        except Exception as e:
            logger.error(f"pdfminer extraction failed: {e}")
    
    return text

def extract_text_from_image(file_path):
    """
    Extract text from image files (JPG, JPEG) using pytesseract
    """
    if not os.path.exists(file_path):
        logger.error(f"Image file not found: {file_path}")
        return ""
        
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        logger.info(f"pytesseract extracted {len(text)} characters from {file_path}")
        return text
    except Exception as e:
        logger.error(f"Image text extraction failed: {e}")
        return ""

def extract_text_from_file(file_path):
    """
    Extract text from a file based on its extension
    """
    if not file_path or not os.path.exists(file_path):
        logger.error(f"File not found or invalid path: {file_path}")
        return ""
        
    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower().replace('.', '')
    
    logger.info(f"Extracting text from file: {file_path} with extension: {file_extension}")
    
    if file_extension == 'pdf':
        return extract_text_from_pdf(file_path)
    elif file_extension in ['jpg', 'jpeg']:
        return extract_text_from_image(file_path)
    else:
        logger.warning(f"Unsupported file extension: {file_extension}")
        return "" 