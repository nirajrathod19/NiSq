import os
import logging
import tempfile
from PIL import Image
import PyPDF2
import shutil
import subprocess

def get_file_size(file_path, unit='MB'):
    """Get the size of a file in the specified unit."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    size_bytes = os.path.getsize(file_path)
    
    if unit.upper() == 'KB':
        return round(size_bytes / 1024, 2)
    elif unit.upper() == 'MB':
        return round(size_bytes / (1024 * 1024), 2)
    elif unit.upper() == 'GB':
        return round(size_bytes / (1024 * 1024 * 1024), 2)
    else:
        return size_bytes

def compress_file(file_path, target_size_mb):
    """
    Compress a file to a target size (approximately)
    Returns the path to the compressed file
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Generate output path with uuid to avoid overwriting
    file_root, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower()
    file_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    output_path = os.path.join(file_dir, f"compressed_{file_name}")
    
    # Get current file size
    current_size = get_file_size(file_path, unit='MB')
    
    # If the file is already smaller than target size, just make a copy
    if current_size <= target_size_mb:
        shutil.copy(file_path, output_path)
        logging.info(f"File is already smaller than target size ({current_size}MB <= {target_size_mb}MB)")
        return output_path
    
    logging.info(f"Current file size: {current_size}MB, target size: {target_size_mb}MB")
    
    # Determine file type and use appropriate compression
    if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif']:
        return compress_image(file_path, output_path, target_size_mb)
    elif file_extension == '.pdf':
        return compress_pdf(file_path, output_path, target_size_mb)
    elif file_extension in ['.doc', '.docx']:
        # For Word docs, convert to PDF and then compress
        try:
            from utils.doc_utils import word_to_pdf
            logging.info("Converting Word document to PDF for compression")
            temp_pdf = word_to_pdf(file_path)
            pdf_output_path = output_path.replace(file_extension, '.pdf')
            compressed_pdf = compress_pdf(temp_pdf, pdf_output_path, target_size_mb)
            try:
                os.remove(temp_pdf)  # Clean up temporary PDF
            except Exception as e:
                logging.warning(f"Failed to remove temp PDF: {str(e)}")
            return compressed_pdf
        except Exception as e:
            logging.error(f"Error compressing Word document: {str(e)}")
            # If conversion fails, create a copy of the original
            shutil.copy(file_path, output_path)
            return output_path
    else:
        # For unsupported types, just create a copy
        shutil.copy(file_path, output_path)
        logging.warning(f"No compression available for {file_extension} files")
        return output_path

def compress_image(input_path, output_path, target_size_mb):
    """Compress an image to target size by reducing quality"""
    # Ensure output path has correct extension
    root, ext = os.path.splitext(output_path)
    if not ext:
        ext = os.path.splitext(input_path)[1]
        output_path = f"{root}{ext}"
    
    try:
        img = Image.open(input_path)
        
        # If image is not in RGB/RGBA mode and is not supported by compression formats
        if img.mode not in ['RGB', 'RGBA'] and ext.lower() in ['.jpg', '.jpeg']:
            img = img.convert('RGB')
        
        # Start with quality 90 and gradually reduce until reaching target size
        quality = 90
        min_quality = 20  # Don't go below this quality
        
        while quality >= min_quality:
            # Save with current quality settings
            img.save(output_path, optimize=True, quality=quality)
            
            # Check current size
            current_size = get_file_size(output_path)
            
            if current_size <= target_size_mb:
                return output_path
            
            # Reduce quality and try again
            quality -= 10
        
        # If still too large, try reducing the dimensions
        original_width, original_height = img.size
        scale_factor = 0.9  # Start with 90% of original size
        min_scale = 0.3  # Don't go below 30% of original size
        
        while scale_factor >= min_scale:
            # Calculate new dimensions
            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)
            
            # Resize image
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Save with current quality and size
            resized_img.save(output_path, optimize=True, quality=quality)
            
            # Check current size
            current_size = get_file_size(output_path)
            
            if current_size <= target_size_mb:
                return output_path
            
            # Reduce scale and try again
            scale_factor -= 0.1
        
        # If we still couldn't compress enough, return the smallest version we created
        logging.warning(f"Could not compress image to target size of {target_size_mb}MB")
        return output_path
        
    except Exception as e:
        logging.error(f"Error compressing image: {str(e)}")
        # If compression fails, return original file path
        shutil.copy(input_path, output_path)
        return output_path

def compress_pdf(input_path, output_path, target_size_mb):
    """Compress a PDF file to target size"""
    # Make sure output has PDF extension
    if not output_path.lower().endswith('.pdf'):
        output_path += '.pdf'
    
    # Try using ghostscript for PDF compression if available
    gs_compression_succeeded = False
    
    try:
        # Define compression levels from highest to lowest quality
        compression_levels = [
            '/default',  # Default - good quality
            '/ebook',    # Medium quality
            '/screen',   # Low quality
            '/printer'   # High quality
        ]
        
        for level in compression_levels:
            gs_output = output_path
            
            # Construct GhostScript command
            gs_cmd = [
                'gs', '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
                f'-dPDFSETTINGS={level}', '-dNOPAUSE', '-dQUIET', '-dBATCH',
                f'-sOutputFile={gs_output}', input_path
            ]
            
            try:
                # Run GhostScript
                subprocess.run(gs_cmd, check=True, stderr=subprocess.PIPE)
                
                # Check if file was created and is below target size
                if os.path.exists(gs_output) and get_file_size(gs_output) <= target_size_mb:
                    gs_compression_succeeded = True
                    return gs_output
            except subprocess.CalledProcessError as e:
                logging.warning(f"GhostScript compression error: {e}")
                continue
    except Exception as e:
        logging.warning(f"GhostScript not available or error: {str(e)}")
    
    # If ghostscript failed or isn't available, use PyPDF2 as fallback
    if not gs_compression_succeeded:
        try:
            pdf_reader = PyPDF2.PdfReader(input_path)
            pdf_writer = PyPDF2.PdfWriter()
            
            # Copy all pages from original PDF
            for page_num in range(len(pdf_reader.pages)):
                pdf_writer.add_page(pdf_reader.pages[page_num])
            
            # Save with compression
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            # If still too large, we've done our best
            if get_file_size(output_path) > target_size_mb:
                logging.warning(f"Could not compress PDF to target size of {target_size_mb}MB with PyPDF2")
            
            return output_path
            
        except Exception as e:
            logging.error(f"Error in PyPDF2 compression: {str(e)}")
            # If all compression methods fail, copy the original
            shutil.copy(input_path, output_path)
            return output_path
    
    return output_path
