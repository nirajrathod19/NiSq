import os
import uuid
from PIL import Image
import img2pdf
import tempfile
import logging
from io import BytesIO

def images_to_pdf(image_paths):
    """
    Convert multiple images to a single PDF.
    Returns the path to the created PDF file.
    """
    if not image_paths:
        raise ValueError("No image paths provided")
    
    # Validate all images exist
    for path in image_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Image file not found: {path}")
    
    # Generate output PDF path
    output_dir = os.path.dirname(image_paths[0])
    output_filename = f"{uuid.uuid4()}_combined.pdf"
    output_path = os.path.join(output_dir, output_filename)
    
    # Try using img2pdf first (better quality)
    try:
        # Create a list of PIL images to check formats
        pil_images = []
        img2pdf_compatible = True
        
        for img_path in image_paths:
            try:
                img = Image.open(img_path)
                pil_images.append(img)
                # img2pdf only supports RGB/RGBA for JPG/PNG and 1 for monochrome
                if img.mode not in ('RGB', 'RGBA', '1', 'L'):
                    img2pdf_compatible = False
            except Exception as e:
                logging.warning(f"Error opening image {img_path}: {str(e)}")
                img2pdf_compatible = False
        
        if img2pdf_compatible:
            with open(output_path, "wb") as f:
                f.write(img2pdf.convert(image_paths))
            return output_path
    
    except Exception as e:
        logging.warning(f"img2pdf conversion failed: {str(e)}")
    
    # Fallback method using PIL
    try:
        # Convert images to RGB mode if needed
        processed_images = []
        
        for img_path in image_paths:
            try:
                img = Image.open(img_path)
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                processed_images.append(img)
            except Exception as e:
                logging.warning(f"Error processing image {img_path}: {str(e)}")
        
        if not processed_images:
            raise ValueError("No valid images to convert")
        
        # Save as PDF using Pillow
        first_image = processed_images[0]
        if len(processed_images) > 1:
            first_image.save(output_path, save_all=True, append_images=processed_images[1:])
        else:
            first_image.save(output_path)
        
        return output_path
        
    except Exception as e:
        logging.error(f"Error converting images to PDF: {str(e)}")
        raise
