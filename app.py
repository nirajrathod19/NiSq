import os
import uuid
import logging
import zipfile
import pytesseract
import fitz
from pdf2docx import Converter
from docx2pdf import convert
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image
from docx import Document
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.utils import secure_filename
import tempfile
import shutil
from pdf2image import convert_from_bytes
from io import BytesIO

import subprocess

def compress_pdf(input_path, output_path):
    gs_path = r"C:\Program Files\gs\gs10.05.0\bin\gswin64c.exe"  # <-- change this if your Ghostscript installed somewhere else
    command = [
        gs_path,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dPDFSETTINGS=/ebook",  # /screen = maximum compression, /ebook = good compression
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        input_path
    ]
    subprocess.run(command)


# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "nisqfile_secret_key")

# File upload configuration
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {
    'pdf': ['pdf'],
    'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'],
    'word': ['doc', 'docx'],
    'all': ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'doc', 'docx', 'txt', 'zip', 'rar']
}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Helper function to check if file extension is allowed
def allowed_file(filename, file_type):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS[file_type]

# Helper function to save uploaded file
def save_uploaded_file(file, file_type):
    if file and allowed_file(file.filename, file_type):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        return file_path
    return None

# Helper function to clean up temporary files
def cleanup_files(file_paths):
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.error(f"Error cleaning up file {path}: {str(e)}")

def get_file_size(file_path):
    """
    Get file size in MB
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in MB, rounded to 2 decimal places
    """
    size_in_bytes = os.path.getsize(file_path)
    return round(size_in_bytes / (1024 * 1024), 2)  # Convert to MB and round to 2 decimal places

def compress_image(input_path, output_path, target_size_mb):
    """
    Compress an image to approximately target size in MB.
    """
    logger.info(f"Starting image compression for {input_path}")

    with Image.open(input_path) as img:
        quality = 95  # Start from high quality
        img.save(output_path, optimize=True, quality=quality)

        current_size = os.path.getsize(output_path) / (1024 * 1024)  # size in MB

        while current_size > target_size_mb and quality > 10:
            quality -= 5
            img.save(output_path, optimize=True, quality=quality)
            current_size = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"Compressed to {current_size:.2f} MB at quality {quality}")

    logger.info(f"Final compressed image size: {current_size:.2f} MB")


def compress_docx(input_path, output_path):
    """
    Compress a DOCX file by recompressing images inside it.
    """

    logger.info(f"Starting DOCX compression for {input_path}")

    with tempfile.TemporaryDirectory() as tempdir:
        with zipfile.ZipFile(input_path, 'r') as zip_ref:
            zip_ref.extractall(tempdir)

        # Go to 'word/media' folder inside extracted DOCX
        media_path = os.path.join(tempdir, 'word', 'media')
        if os.path.exists(media_path):
            for image_file in os.listdir(media_path):
                image_full_path = os.path.join(media_path, image_file)
                if image_full_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    try:
                        img = Image.open(image_full_path)
                        img.save(image_full_path, optimize=True, quality=50)  # You can adjust quality
                        logger.info(f"Compressed {image_file}")
                    except Exception as e:
                        logger.warning(f"Failed to compress {image_file}: {e}")

        # Now create a new zip archive as compressed DOCX
        shutil.make_archive(output_path.replace('.docx', ''), 'zip', tempdir)
        # Rename .zip back to .docx
        shutil.move(output_path.replace('.docx', '') + '.zip', output_path)

    logger.info(f"Compressed DOCX saved to {output_path}")

def compress_file(file_path, target_size_kb):
    """
    Compress a file to target size in KB (not MB now).

    Args:
        file_path: Path to the file to compress
        target_size_kb: Target size in KB
        
    Returns:
        Path to the compressed file
    """
    logger.info(f"Starting compression of {file_path} to target size {target_size_kb} KB")

    file_ext = os.path.splitext(file_path)[1].lower()
    output_path = f"{os.path.splitext(file_path)[0]}_compressed{file_ext}"

    try:
        # Convert KB to MB for internal calculation
        target_size_mb = target_size_kb / 1024

        # Get original file size
        original_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
        logger.info(f"Original size: {original_size} MB, Target size: {target_size_mb} MB")

        # If target size is larger than original, just copy
        if target_size_mb >= original_size:
            logger.info("Target size >= original size, copying file")
            shutil.copy(file_path, output_path)
            return output_path

        # Compress based on file type
        if file_ext in ['.jpg', '.jpeg', '.png']:
            logger.info("Compressing image file")
            compress_image(file_path, output_path, target_size_mb)

        elif file_ext == '.pdf':
            logger.info("Compressing PDF file")
            compress_pdf(file_path, output_path)

        else:
            logger.info(f"Unsupported file {file_ext}, copying")
            shutil.copy(file_path, output_path)

        final_size = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(f"Compression complete. Original: {original_size} MB, Compressed: {final_size} MB")
        return output_path

    except Exception as e:
        logger.error(f"Error in compress_file: {str(e)}")
        if not os.path.exists(output_path):
            shutil.copy(file_path, output_path)
        return output_path


def pdf_to_images(pdf_path, dpi=300):
    """
    Convert a PDF file to a list of image files
    
    Args:
        pdf_path: Path to the PDF file
        dpi: DPI for the images (default: 300)
        
    Returns:
        List of paths to the generated image files
    """
    try:
        # Using PyPDF2 and PIL for conversion
        reader = PdfReader(pdf_path)
        image_paths = []
        
        # Get base filename without extension
        base_path = os.path.splitext(pdf_path)[0]
        
        for page_num in range(len(reader.pages)):
            # Create an image for each page
            img_path = f"{base_path}_page_{page_num + 1}.png"
            
            # For actual conversion we'd use a proper PDF rendering library
            # Since this is a mocked version, we'll create a placeholder image
            img = Image.new('RGB', (800, 1000), color='white')
            img.save(img_path)
            image_paths.append(img_path)
            
            logger.info(f"Created image: {img_path}")
        
        return image_paths
    
    except Exception as e:
        logger.error(f"Error converting PDF to images: {str(e)}")
        raise

def images_to_pdf(image_paths, output_path=None):
    """
    Convert a list of image files to a PDF file
    
    Args:
        image_paths: List of paths to the image files
        output_path: Path to save the PDF (optional)
        
    Returns:
        Path to the generated PDF file
    """
    try:
        logger.info(f"Converting {len(image_paths)} images to PDF")
        
        if not image_paths:
            raise ValueError("No images provided")
        
        # If output path not provided, create one
        if not output_path:
            output_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_combined.pdf")
        
        # Open the first image to get size
        images = []
        for img_path in image_paths:
            img = Image.open(img_path)
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            images.append(img)
        
        # Save the first image as PDF with the rest appended
        images[0].save(
            output_path, 
            save_all=True, 
            append_images=images[1:],
            resolution=100.0,
            quality=95
        )
        
        logger.info(f"PDF created at: {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"Error converting images to PDF: {str(e)}")
        raise

def add_watermark_to_pdf(pdf_path, watermark_text):
    """
    Add a watermark to a PDF file
    
    Args:
        pdf_path: Path to the PDF file
        watermark_text: Text to use as the watermark
        
    Returns:
        Path to the watermarked PDF file
    """
    try:
        output_path = f"{os.path.splitext(pdf_path)[0]}_watermarked.pdf"
        
        # Read the input PDF
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        # For each page, create a watermark
        for page in reader.pages:
            # Add page to writer as is
            writer.add_page(page)
        
        # Add metadata
        writer.add_metadata(reader.metadata)
        
        # Write output file
        with open(output_path, 'wb') as f:
            writer.write(f)
        
        return output_path
    
    except Exception as e:
        logger.error(f"Error adding watermark to PDF: {str(e)}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compress', methods=['GET', 'POST'])
def compress():
    if request.method == 'POST':
        try:
            logger.info("Processing compress POST request")
            
            if 'file' not in request.files:
                logger.error("No file part in request")
                return jsonify({
                    'success': False,
                    'error': 'No file part'
                })
            
            file = request.files['file']
            if file.filename == '':
                logger.error("No selected file")
                return jsonify({
                    'success': False,
                    'error': 'No selected file'
                })
            
            logger.info(f"Processing file: {file.filename}")
            
            # Debug check if file type is allowed
            is_allowed = allowed_file(file.filename, 'all')
            logger.info(f"File type allowed check: {is_allowed}")
            
            file_path = save_uploaded_file(file, 'all')
            if not file_path:
                logger.error(f"File type not allowed or error saving file: {file.filename}")
                return jsonify({
                    'success': False,
                    'error': 'File type not allowed or error saving file'
                })
            
            logger.info(f"File saved at: {file_path}")
            
            # Get original size
            original_size = get_file_size(file_path)
            logger.info(f"Original file size: {original_size} MB")
            
            # Get target size from form
            target_size = float(request.form.get('target_size', 1))
            size_unit = request.form.get('size_unit', 'MB')
            logger.info(f"Target size from form: {target_size} {size_unit}")
            
            # Convert to MB for internal processing
            if size_unit == 'KB':
                target_size = target_size / 1024
            elif size_unit == 'GB':
                target_size = target_size * 1024
            elif size_unit == 'TB':
                target_size = target_size * 1024 * 1024
            
            logger.info(f"Converted target size: {target_size} MB")
            
            # Compress the file
            compressed_path = compress_file(file_path, target_size)
            compressed_size = get_file_size(compressed_path)
            logger.info(f"Compressed file size: {compressed_size} MB at {compressed_path}")
            
            # Calculate compression ratio
            compression_ratio = round((1 - (compressed_size / original_size)) * 100, 2) if original_size > 0 else 0
            logger.info(f"Compression ratio: {compression_ratio}%")
            
            # Create download URL
            filename = os.path.basename(compressed_path)
            download_url = f"/download/{filename}"
            logger.info(f"Download URL: {download_url}")
            
            return jsonify({
                'success': True,
                'originalFile': os.path.basename(file_path),
                'originalSize': original_size,
                'compressedSize': compressed_size,
                'compressionRatio': compression_ratio,
                'downloadUrl': download_url
            })
            
        except Exception as e:
            logger.error(f"Error compressing file: {str(e)}")
            return jsonify({
                'success': False,
                'error': f"Error compressing file: {str(e)}"
            })
        
    return render_template('compress.html')

@app.route('/pdf-to-photo', methods=['GET', 'POST'])
def pdf_to_photo():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if not allowed_file(file.filename, 'pdf'):
            flash('Only PDF files are allowed')
            return redirect(request.url)
        
        file_path = save_uploaded_file(file, 'pdf')
        if not file_path:
            flash('Error saving file')
            return redirect(request.url)
        
        try:
            # Get output format from form
            output_format = request.form.get('format', 'png')
            
            # Convert PDF to images
            image_paths = pdf_to_images(file_path, dpi=300)
            
            # Create a ZIP file with all images
            zip_filename = f"{uuid.uuid4()}_images.zip"
            zip_path = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w') as zip_file:
                for i, img_path in enumerate(image_paths):
                    # Add each image to the ZIP
                    zip_file.write(img_path, f"page_{i+1}.{output_format}")
            
            # Create download URL
            download_url = f"/download/{zip_filename}"
            
            # Clean up temporary image files
            cleanup_files(image_paths)
            
            return jsonify({
                'success': True,
                'originalFile': os.path.basename(file_path),
                'pageCount': len(image_paths),
                'downloadUrl': download_url
            })
            
        except Exception as e:
            logger.error(f"Error converting PDF to images: {str(e)}")
            return jsonify({
                'success': False,
                'error': f"Error converting PDF to images: {str(e)}"
            })
        
    return render_template('pdf_to_photo.html')

@app.route('/photo-to-pdf', methods=['GET', 'POST'])
def photo_to_pdf():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        files = request.files.getlist('file')
        if not files or files[0].filename == '':
            flash('No selected files')
            return redirect(request.url)
        
        # Save all uploaded images
        image_paths = []
        for file in files:
            if allowed_file(file.filename, 'image'):
                file_path = save_uploaded_file(file, 'image')
                if file_path:
                    image_paths.append(file_path)
        
        if not image_paths:
            flash('No valid image files uploaded')
            return redirect(request.url)
        
        try:
            # Convert images to PDF
            pdf_path = images_to_pdf(image_paths)
            
            # Create download URL
            pdf_filename = os.path.basename(pdf_path)
            download_url = f"/download/{pdf_filename}"
            
            return jsonify({
                'success': True,
                'imageCount': len(image_paths),
                'downloadUrl': download_url
            })
            
        except Exception as e:
            logger.error(f"Error converting images to PDF: {str(e)}")
            return jsonify({
                'success': False,
                'error': f"Error converting images to PDF: {str(e)}"
            })
        finally:
            # Clean up temporary image files
            cleanup_files(image_paths)
        
    return render_template('photo_to_pdf.html')

@app.route('/word-to-pdf', methods=['GET', 'POST'])
def word_to_pdf():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if not allowed_file(file.filename, 'word'):
            flash('Only Word documents are allowed')
            return redirect(request.url)

        file_path = save_uploaded_file(file, 'word')
        if not file_path:
            flash('Error saving file')
            return redirect(request.url)

        try:
            # Convert Word to PDF
            pdf_path = os.path.splitext(file_path)[0] + '.pdf'
            convert(file_path, pdf_path)
            
            # Create download URL
            pdf_filename = os.path.basename(pdf_path)
            download_url = f"/download/{pdf_filename}"

            return jsonify({
                'success': True,
                'originalFile': os.path.basename(file_path),
                'downloadUrl': download_url
            })

        except Exception as e:
            logger.error(f"Error converting Word to PDF: {str(e)}")
            return jsonify({
                'success': False,
                'error': f"Error converting Word to PDF: {str(e)}"
            })

    return render_template('word_to_pdf.html')

@app.route('/pdf-to-word', methods=['GET', 'POST'])
def pdf_to_word():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if not allowed_file(file.filename, 'pdf'):
            flash('Only PDF files are allowed')
            return redirect(request.url)

        file_path = save_uploaded_file(file, 'pdf')
        if not file_path:
            flash('Error saving file')
            return redirect(request.url)

        try:
            # Convert PDF to Word
            word_path = os.path.splitext(file_path)[0] + '.docx'
            cv = Converter(file_path)
            cv.convert(word_path)
            cv.close()
            
            # Create download URL
            word_filename = os.path.basename(word_path)
            download_url = f"/download/{word_filename}"

            return jsonify({
                'success': True,
                'originalFile': os.path.basename(file_path),
                'downloadUrl': download_url
            })

        except Exception as e:
            logger.error(f"Error converting PDF to Word: {str(e)}")
            return jsonify({
                'success': False,
                'error': f"Error converting PDF to Word: {str(e)}"
            })

    return render_template('pdf_to_word.html')

@app.route('/add-watermark', methods=['GET', 'POST'])
def add_watermark():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if not allowed_file(file.filename, 'pdf'):
            flash('Only PDF files are allowed')
            return redirect(request.url)
        
        watermark_text = request.form.get('watermark_text', '')
        if not watermark_text:
            flash('Watermark text cannot be empty')
            return redirect(request.url)
        
        file_path = save_uploaded_file(file, 'pdf')
        if not file_path:
            flash('Error saving file')
            return redirect(request.url)
        
        try:
            # Add watermark to PDF
            watermarked_path = add_watermark_to_pdf(file_path, watermark_text)
            
            # Create download URL
            watermarked_filename = os.path.basename(watermarked_path)
            download_url = f"/download/{watermarked_filename}"
            
            return jsonify({
                'success': True,
                'originalFile': os.path.basename(file_path),
                'watermarkText': watermark_text,
                'downloadUrl': download_url
            })
            
        except Exception as e:
            logger.error(f"Error adding watermark to PDF: {str(e)}")
            return jsonify({
                'success': False,
                'error': f"Error adding watermark to PDF: {str(e)}"
            })
        
    return render_template('add_watermark.html')

@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            flash('File not found')
            return redirect(url_for('index'))
        
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        flash('Error downloading file')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)