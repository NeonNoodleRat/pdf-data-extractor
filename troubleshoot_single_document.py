import os
import json
import ollama
import re
import tempfile
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image

# Just change this filename to whatever PDF you want to test
filename = ""
model_name = "gemma3:27b"

SOURCE_FOLDER = "/home/shared/usacs_documents"

def crop_image_to_header(image, crop_fraction=0.33):
    """Crop image to top portion and save to temp file."""
    try:
        width, height = image.size
        crop_height = int(height * crop_fraction)
        crop_box = (0, 0, width, crop_height)
        cropped_img = image.crop(crop_box)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        cropped_img.save(temp_file.name, "PNG")
        
        print(f"Cropped header image from {width}x{height} to {width}x{crop_height}")
        return temp_file.name
    except Exception as e:
        print(f"Error cropping image: {e}")
        return None

def extract_electronic_signature_date(image):
    """Extract electronic signature date from last-page image."""
    print(f"\n=== EXTRACTING SIGNATURE DATE ===")
    
    # Save image to temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    image.save(temp_file.name, "PNG")
    
    try:
        res = ollama.chat(
            model=model_name,
            messages=[
                {
                    'role': 'user',
                    'content': (
                        'Look at this image and find any text that says '
                        '"ELECTRONICALLY SIGNED ON" followed by a date and time. '
                        'Extract just the date portion in MM/DD/YYYY format. '
                        'If you cannot find this text, respond with "N/A".'
                    ),
                    'images': [temp_file.name]
                }
            ]
        )

        response_text = res['message']['content'].strip()
        print(f"\nModel Response: {response_text}")

        # Regex patterns for dates
        date_patterns = [
            r'(\d{2}/\d{2}/\d{4})',      # MM/DD/YYYY
            r'(\d{1,2}/\d{1,2}/\d{4})',  # M/D/YYYY or variations
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, response_text)
            if matches:
                extracted_date = matches[0]
                print(f"Extracted Date: {extracted_date}")
                return extracted_date

        print("No valid date found - returning N/A")
        return "N/A"

    except Exception as e:
        print(f"Error extracting signature date: {e}")
        return "N/A"
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_file.name)
        except:
            pass

def extract_header_info(image):
    """Extract header info from first page."""
    print(f"\n=== EXTRACTING HEADER INFO ===")
    
    # Crop to header and get temp file path
    cropped_image_path = crop_image_to_header(image, crop_fraction=0.33)
    if not cropped_image_path:
        return {}
    
    try:
        # Get raw description first
        res = ollama.chat(
            model=model_name,
            messages=[
                {
                    'role': 'user',
                    'content': 'What do you see in this image? Describe all text you can read.',
                    'images': [cropped_image_path]
                }
            ]
        )
        
        print(f"\nRaw Description: {res['message']['content']}")
        
        # Try structured extraction
        structured_res = ollama.chat(
            model=model_name,
            messages=[
                {
                    'role': 'user',
                    'content': '''
                    Looking at this medical document image, extract information as JSON:
                    {
                        "patient_name": "patient's full name",
                        "date_of_birth": "DOB in MM/DD/YYYY format", 
                        "gender": "Male/Female/Other",
                        "attending_physician": "attending doctor's name",
                        "facility_name": "medical center name"
                    }
                    
                    If any field is not visible, use "N/A".
                    ''',
                    'images': [cropped_image_path]
                }
            ]
        )
        
        response_text = structured_res['message']['content']
        print(f"\nStructured Response: {response_text}")
        
        # Try to extract JSON
        if '```json' in response_text:
            json_start = response_text.find('```json') + 7
            json_end = response_text.find('```', json_start)
            json_text = response_text[json_start:json_end].strip()
        elif '{' in response_text and '}' in response_text:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_text = response_text[json_start:json_end]
        else:
            print("No JSON found in response")
            return {}
        
        extracted_data = json.loads(json_text)
        print(f"\nExtracted JSON: {json.dumps(extracted_data, indent=2)}")
        return extracted_data
        
    except Exception as e:
        print(f"Error extracting header info: {e}")
        return {}
    finally:
        # Clean up temp file
        try:
            os.unlink(cropped_image_path)
        except:
            pass

def convert_pdf_to_images(pdf_path):
    """Convert first and last pages to images in memory."""
    try:
        info = pdfinfo_from_path(pdf_path)
        total_pages = info.get("Pages", 0)
        print(f"PDF has {total_pages} pages")
        
        image_paths = {}
        
        # First page
        first_page_images = convert_from_path(pdf_path, first_page=1, last_page=1)
        image_paths["first"] = first_page_images[0]
        
        # Last page
        if total_pages > 1:
            last_page_images = convert_from_path(pdf_path, first_page=total_pages, last_page=total_pages)
            image_paths["last"] = last_page_images[0]
        else:
            image_paths["last"] = first_page_images[0]
        
        print(f"Converted PDF to images: {list(image_paths.keys())}")
        return image_paths
        
    except Exception as e:
        print(f"Error converting PDF: {e}")
        return {}

def main():
    print("=" * 60)
    print(f"TROUBLESHOOTING: {filename}")
    print("=" * 60)
    
    pdf_path = os.path.join(SOURCE_FOLDER, filename)
    
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return
    
    # Convert to images
    image_paths = convert_pdf_to_images(pdf_path)
    if not image_paths:
        print("Failed to convert PDF to images")
        return
    
    # Extract header info
    header_info = extract_header_info(image_paths["first"])
    
    # Extract signature date
    sig_date = extract_electronic_signature_date(image_paths["last"])
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    print("=" * 60)
    print(f"Header Info: {json.dumps(header_info, indent=2)}")
    print(f"Signature Date: {sig_date}")
    print("=" * 60)

if __name__ == "__main__":
    main()