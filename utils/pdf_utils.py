import os
import uuid
import tempfile
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import lightgrey
import fitz  # PyMuPDF
import logging

def pdf_to_images(pdf_path, dpi=300, output_format='png'):
    """
    Convert a PDF to a series of images.
    Returns a list of paths to the created image files.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    output_dir = os.path.dirname(pdf_path)
    image_paths = []
    
    try:
        # Open the PDF using PyMuPDF (fitz)
        doc = fitz.open(pdf_path)
        
        if len(doc) == 0:
            raise ValueError("PDF has no pages")
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Set the matrix for higher quality rendering
            zoom = dpi / 72  # PDF uses 72 dpi by default
            matrix = fitz.Matrix(zoom, zoom)
            
            # Render page to an image
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            
            # Generate output path for this image
            image_filename = f"page_{page_num+1}_{uuid.uuid4()}"
            if output_format.lower() in ('jpg', 'jpeg'):
                image_path = os.path.join(output_dir, f"{image_filename}.jpg")
                pix.save(image_path, "jpeg")
            else:  # Default to PNG
                image_path = os.path.join(output_dir, f"{image_filename}.png")
                pix.save(image_path)
            
            image_paths.append(image_path)
            logging.debug(f"Created image: {image_path}")
        
        return image_paths
    
    except Exception as e:
        logging.error(f"Error converting PDF to images: {str(e)}")
        raise

def add_watermark_to_pdf(pdf_path, watermark_text):
    """
    Add a text watermark to each page of a PDF.
    Returns the path to the watermarked PDF.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    if not watermark_text or not watermark_text.strip():
        raise ValueError("Watermark text cannot be empty")
    
    output_dir = os.path.dirname(pdf_path)
    watermarked_filename = f"watermarked_{uuid.uuid4()}.pdf"
    output_path = os.path.join(output_dir, watermarked_filename)
    
    # Create a temporary PDF with the watermark
    watermark_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False).name
    
    try:
        # Create the watermark using reportlab
        c = canvas.Canvas(watermark_pdf, pagesize=letter)
        width, height = letter
        
        # Watermark properties
        c.setFont("Helvetica", 60)
        c.setFillColor(lightgrey)
        c.setFillAlpha(0.5)  # Make it semi-transparent
        c.saveState()
        
        # Rotate and position the watermark
        c.translate(width/2, height/2)
        c.rotate(45)
        c.drawCentredString(0, 0, watermark_text)
        c.restoreState()
        c.save()
        
        # Apply the watermark to each page
        with open(pdf_path, 'rb') as input_file, open(output_path, 'wb') as output_file:
            try:
                pdf_reader = PdfReader(input_file)
                watermark_reader = PdfReader(watermark_pdf)
                pdf_writer = PdfWriter()
                
                # Check if we have valid PDFs
                if len(pdf_reader.pages) == 0:
                    raise ValueError("Input PDF has no pages")
                
                if len(watermark_reader.pages) == 0:
                    raise ValueError("Watermark PDF has no pages")
                
                # Get the watermark page
                watermark_page = watermark_reader.pages[0]
                
                # Apply to each page
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    # Use merge_page to add the watermark underneath the content
                    page.merge_page(watermark_page)
                    pdf_writer.add_page(page)
                
                # Write the output file
                pdf_writer.write(output_file)
                
            except Exception as pdf_error:
                logging.error(f"PyPDF2 error: {str(pdf_error)}")
                raise
        
        return output_path
        
    except Exception as e:
        logging.error(f"Error adding watermark to PDF: {str(e)}")
        # If the output file was created but is incomplete, remove it
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        raise
    
    finally:
        # Clean up the temporary watermark file
        try:
            if os.path.exists(watermark_pdf):
                os.unlink(watermark_pdf)
        except Exception as e:
            logging.error(f"Error removing temporary file: {str(e)}")
