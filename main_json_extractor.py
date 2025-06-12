import os
import json
import ollama
import re
from datetime import datetime
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image

# Path to the folder containing all PDFs
SOURCE_FOLDER = "documents"
# Folder where JSON results are saved
JSON_OUTPUT_FOLDER = "json_output"
# Folder where temporary images will be written
IMAGES_FOLDER = "images"
MODEL_NAME = "gemma3:27b"

def crop_image_to_header(image_path, crop_fraction=0.33):
    """Crop image to top portion (header section only)."""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            crop_height = int(height * crop_fraction)
            crop_box = (0, 0, width, crop_height)
            cropped_img = img.crop(crop_box)
            cropped_img.save(image_path, "PNG")
            print(f"  Cropped header image from {width}x{height} to {width}x{crop_height} (top {int(crop_fraction*100)}%)")
            return image_path
    except Exception as e:
        print(f"  Warning: Failed to crop header image {image_path}: {e}")
        return image_path

def extract_text_from_image(image_path, debug=False):
    """Extract all text from a single page image via Ollama."""
    if debug:
        print(f"Extracting text from: {image_path}")

    try:
        res = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {
                    'role': 'user',
                    'content': (
                        'Please extract all text from this image. '
                        'Return only the text content, maintaining line breaks and formatting where possible. '
                        'Do not add any commentary or descriptions.'
                    ),
                    'images': [image_path]
                }
            ]
        )

        extracted_text = res['message']['content'].strip()
        if debug:
            print(f"EXTRACTED TEXT ({len(extracted_text)} chars):")
            print(extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text)

        return extracted_text

    except Exception as e:
        if debug:
            print(f"ERROR extracting text from {image_path}: {e}")
        else:
            print(f"  ❌ ERROR extracting text from {image_path}: {e}")
        return "EXTRACTION_FAILED"

def extract_full_document_text(image_paths, debug=False):
    """Extract text from all pages and concatenate with page separators."""
    if debug:
        print("Extracting full document text from all pages...")

    full_text_parts = []
    failed_pages = []

    for page_num, image_path in enumerate(image_paths, 1):
        print(f"  📄 Processing page {page_num}...")
        page_text = extract_text_from_image(image_path, debug=debug)
        
        if page_text == "EXTRACTION_FAILED":
            failed_pages.append(page_num)
            continue
        
        # Add page separator
        if page_num > 1:
            full_text_parts.append(f"\n--- Page {page_num} ---\n")
        else:
            full_text_parts.append(f"--- Page {page_num} ---\n")
        
        full_text_parts.append(page_text)

    if failed_pages:
        print(f"  ❌ Failed to extract text from pages: {failed_pages}")
        if len(failed_pages) == len(image_paths):
            return "EXTRACTION_FAILED"

    full_text = "".join(full_text_parts)
    
    if debug:
        print(f"FULL DOCUMENT TEXT ({len(full_text)} chars total)")
        print("First 300 chars:")
        print(full_text[:300] + "..." if len(full_text) > 300 else full_text)

    return full_text

def extract_electronic_signature_date(image_path, debug=False):
    """Extract electronic signature date from last-page image via Ollama."""
    if debug:
        print(f"Extracting signature date from: {image_path}")

    try:
        res = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {
                    'role': 'user',
                    'content': (
                        'Look at this image and find any text that says '
                        '"ELECTRONICALLY SIGNED ON" followed by a date and time. '
                        'Extract just the date portion in MM/DD/YYYY format. '
                        'If you cannot find this text, respond with "N/A".'
                    ),
                    'images': [image_path]
                }
            ]
        )

        response_text = res['message']['content'].strip()
        if debug:
            print("SIGNATURE EXTRACTION RESPONSE:")
            print(response_text)

        # Regex patterns for dates
        date_patterns = [
            r'(\d{2}/\d{2}/\d{4})',      # MM/DD/YYYY
            r'(\d{1,2}/\d{1,2}/\d{4})',  # M/D/YYYY or variations
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, response_text)
            if matches:
                extracted_date = matches[0]
                if debug:
                    print(f"EXTRACTED DATE: {extracted_date}")
                return extracted_date

        # Fallback: if response contains '/', try to clean up
        if 'N/A' not in response_text and '/' in response_text:
            cleaned = re.sub(r'[^\d/]', '', response_text)
            if len(cleaned) >= 8 and cleaned.count('/') == 2:
                return cleaned

        if debug:
            print("NO VALID DATE FOUND - returning N/A")
        return "N/A"

    except Exception as e:
        if debug:
            print(f"ERROR extracting signature date: {e}")
        else:
            print(f"  ❌ ERROR extracting signature date: {e}")
        return "N/A"

def validate_extracted_data(data):
    """Clean up and validate fields returned from Ollama extraction."""
    validated = data.copy()

    for key, value in validated.items():
        if isinstance(value, str):
            validated[key] = value.strip()
            if value.lower() in ['n/a', 'na', 'not available', 'not visible', '', 'unclear']:
                validated[key] = "N/A"

    # Document status inference
    if validated.get('document_status') == "N/A":
        auth_info = validated.get('authenticated_by', '').lower()
        if 'verified' in auth_info or 'auth' in auth_info:
            validated['document_status'] = "Verified"

    # Facility name cleanup - remove ** markdown formatting
    facility_name = validated.get('facility_name', '')
    if facility_name.startswith('**') and facility_name.endswith('**'):
        validated['facility_name'] = facility_name.strip('*').strip()

    # Location format check
    location = validated.get('location', '')
    if location != "N/A" and not location.startswith('LD:') and ('TR' in location or 'tr' in location):
        validated['location'] = f"LD: {location}"

    # Performed by inference
    if validated.get('performed_by') == "N/A":
        auth_by = validated.get('authenticated_by', '')
        if auth_by != "N/A" and 'MD' in auth_by:
            validated['performed_by'] = auth_by

    return validated

def ollama_process_image(image_path, debug=False):
    """Process first-page image: header cropping + two-step Ollama extraction."""
    if debug:
        print(f"Processing header image: {image_path}")

    # Crop header portion
    image_path = crop_image_to_header(image_path, crop_fraction=0.33)

    # Step 1: Raw description prompt
    res = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {
                'role': 'user',
                'content': (
                    'What do you see in this image? Describe all text you can read, '
                    'including any medical document information, patient details, dates, '
                    'and facility information.'
                ),
                'images': [image_path]
            }
        ]
    )

    if debug:
        print("RAW MODEL RESPONSE:")
        print(res['message']['content'])

    # Step 2: Structured JSON extraction
    structured_prompt = f"""
    Looking at this medical document image, please extract the following information and format it as JSON.

    Pay special attention to:
    - Patient name: appears after "Patient:"
    - MRN: appears after "MRN:"
    - DOB: appears after "DOB/Age/Sex:" in MM/DD/YYYY format
    - Gender: appears after the age in the DOB/Age/Sex line
    - Admit/Disch dates: appears after "Admit/Disch.:" (this could be admission or discharge date)
    - Attending physician: appears after "Attending:"
    - Location: appears as "LD:" followed by location code (include the "LD:" prefix)
    - Facility name: Use the specific medical center name (White Oak Medical Center), not the parent organization
    - Document name: appears after "DOCUMENT NAME:" or can be inferred
    - Document status: appears after "DOCUMENT STATUS:" or look for "Verified"/"Auth" status
    - Authentication: appears in "AUTHENTICATED BY:" section

    {{
        "patient_name": "patient's full name",
        "date_of_birth": "DOB in MM/DD/YYYY format",
        "medical_record_number": "Medical Record Number (MRN) if available",
        "gender": "Male/Female/Other",
        "admit_date": "first date from Admit/Disch field (before the / if two dates present)",
        "discharge_date": "second date from Admit/Disch field (after the / if two dates present, otherwise N/A)",
        "attending_physician": "attending doctor's name",
        "location": "patient location including LD: prefix if present",
        "facility_name": "facility name in bold text located in the top right area above the address",
        "facility_address": "facility street address",
        "facility_city": "facility city",
        "facility_state": "facility state",
        "facility_zip": "facility zip code",
        "document_name": "type of document",
        "document_status": "document status (look for Verified, Auth, etc.)",
        "performed_by": "who performed/created the document",
        "authenticated_by": "who authenticated the document with timestamp"
    }}

    If any field is not clearly visible, use "N/A". Only extract what you can clearly read.
    """

    try:
        structured_res = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {
                    'role': 'user',
                    'content': structured_prompt,
                    'images': [image_path]
                }
            ]
        )

        if debug:
            print("STRUCTURED EXTRACTION ATTEMPT:")
            print(structured_res['message']['content'])

        response_text = structured_res['message']['content']

        # Extract the JSON block
        if '```json' in response_text:
            json_start = response_text.find('```json') + 7
            json_end = response_text.find('```', json_start)
            json_text = response_text[json_start:json_end].strip()
        elif '{' in response_text and '}' in response_text:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_text = response_text[json_start:json_end]
        else:
            raise ValueError("No JSON found in response")

        extracted_data = json.loads(json_text)

        if debug:
            print("SUCCESSFULLY PARSED JSON:")
            print(json.dumps(extracted_data, indent=2))

        validated_data = validate_extracted_data(extracted_data)

        if debug:
            print("VALIDATED DATA:")
            print(json.dumps(validated_data, indent=2))

        return validated_data

    except (json.JSONDecodeError, ValueError) as e:
        if debug:
            print(f"JSON PARSING FAILED: {e}")
            print("Returning debug data...")
        else:
            print(f"  ❌ JSON PARSING ERROR: {e}")

        # Return all fields marked as failed
        error_data = {
            "patient_name": "EXTRACTION_FAILED",
            "date_of_birth": "EXTRACTION_FAILED",
            "gender": "EXTRACTION_FAILED",
            "admit_date": "EXTRACTION_FAILED",
            "discharge_date": "EXTRACTION_FAILED",
            "attending_physician": "EXTRACTION_FAILED",
            "location": "EXTRACTION_FAILED",
            "facility_name": "EXTRACTION_FAILED",
            "facility_address": "EXTRACTION_FAILED",
            "facility_city": "EXTRACTION_FAILED",
            "facility_state": "EXTRACTION_FAILED",
            "facility_zip": "EXTRACTION_FAILED",
            "document_name": "EXTRACTION_FAILED",
            "document_status": "EXTRACTION_FAILED",
            "performed_by": "EXTRACTION_FAILED",
            "authenticated_by": "EXTRACTION_FAILED"
        }
        return error_data

    except Exception as e:
        if debug:
            print(f"ERROR processing image {image_path}: {e}")
        else:
            print(f"  ❌ ERROR processing image {image_path}: {e}")

        error_data = {
            "patient_name": "EXTRACTION_FAILED",
            "date_of_birth": "EXTRACTION_FAILED",
            "gender": "EXTRACTION_FAILED",
            "admit_date": "EXTRACTION_FAILED",
            "discharge_date": "EXTRACTION_FAILED",
            "attending_physician": "EXTRACTION_FAILED",
            "location": "EXTRACTION_FAILED",
            "facility_name": "EXTRACTION_FAILED",
            "facility_address": "EXTRACTION_FAILED",
            "facility_city": "EXTRACTION_FAILED",
            "facility_state": "EXTRACTION_FAILED",
            "facility_zip": "EXTRACTION_FAILED",
            "document_name": "EXTRACTION_FAILED",
            "document_status": "EXTRACTION_FAILED",
            "performed_by": "EXTRACTION_FAILED",
            "authenticated_by": "EXTRACTION_FAILED"
        }
        return error_data

def convert_pdf_to_images(pdf_path, output_folder=IMAGES_FOLDER):
    """
    Convert ALL pages of a PDF to PNG images.
    Returns a list of image paths in page order.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Clear any existing PNG/JPG files
    for fname in os.listdir(output_folder):
        if fname.lower().endswith((".png", ".jpg", ".jpeg")):
            os.remove(os.path.join(output_folder, fname))

    try:
        # Get page count via pdfinfo_from_path (Poppler must be installed)
        info = pdfinfo_from_path(pdf_path)
        total_pages = info.get("Pages", 0)

        # Convert ALL pages
        all_images = convert_from_path(pdf_path)
        image_paths = []

        for i, image in enumerate(all_images, 1):
            image_path = os.path.join(output_folder, f"page_{i}.png")
            image.save(image_path, "PNG")
            image_paths.append(image_path)

        print(f"  📄 Converted PDF ({total_pages} pages) → {len(image_paths)} images")
        return image_paths

    except Exception as e:
        print(f"  ❌ ERROR converting PDF {pdf_path}: {e}")
        return []

def main():
    # Ensure folders exist
    for folder in [IMAGES_FOLDER, JSON_OUTPUT_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    # Fetch list of all PDFs in source folder
    if not os.path.exists(SOURCE_FOLDER):
        print(f"Source folder '{SOURCE_FOLDER}' not found!")
        return

    all_pdfs = [
        fname for fname in os.listdir(SOURCE_FOLDER)
        if fname.lower().endswith(".pdf")
    ]

    # only process the first 4 PDFs
    all_pdfs = all_pdfs[:4]

    if not all_pdfs:
        print("No PDF files found in the source folder.")
        return

    print(f"Found {len(all_pdfs)} PDFs to process")
    print("=" * 50)

    # Track counts and time
    successful_count = 0
    error_count = 0
    start_time = datetime.now()

    for idx, filename in enumerate(all_pdfs, start=1):
        print(f"[{idx}/{len(all_pdfs)}] Processing: {filename}")
        pdf_path = os.path.join(SOURCE_FOLDER, filename)

        try:
            # Convert all pages to images
            image_paths = convert_pdf_to_images(pdf_path, IMAGES_FOLDER)
            if not image_paths:
                print("  ❌ ERROR: Failed to convert PDF to images")
                error_count += 1
                continue

            # Extract header data from first page
            print("  📋 Extracting header info...")
            header_info = ollama_process_image(image_paths[0], debug=False)

            # Extract signature date from last page
            print("  ✍️  Extracting signature date...")
            sig_date = extract_electronic_signature_date(image_paths[-1], debug=False)

            # Extract full document text from all pages
            print("  📖 Extracting full document text...")
            full_text = extract_full_document_text(image_paths, debug=False)

            # Combine all results
            final_data = header_info.copy()
            final_data["electronically_signed_date"] = sig_date
            final_data["full_document_text"] = full_text
            final_data["document_filename"] = filename
            final_data["processed_timestamp"] = datetime.now().isoformat()
            final_data["total_pages"] = len(image_paths)

            # Save JSON file
            json_filename = filename.replace('.pdf', '.json').replace('.PDF', '.json')
            json_path = os.path.join(JSON_OUTPUT_FOLDER, json_filename)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)

            successful_count += 1
            patient_name = header_info.get("patient_name", "Unknown")
            sig_out = sig_date if sig_date != "N/A" else "No signature"
            text_chars = len(full_text) if full_text != "EXTRACTION_FAILED" else 0
            print(f"  ✅ SUCCESS: {patient_name} | Sig: {sig_out} | Text: {text_chars} chars")
            print(f"  💾 Saved: {json_path}")

        except Exception as e:
            print(f"  ❌ ERROR processing {filename}: {e}")
            error_count += 1
            continue

    # Final summary
    total_time = datetime.now() - start_time
    print("\n" + "="*50)
    print("BATCH PROCESSING COMPLETE")
    print("="*50)
    print(f"Successfully processed: {successful_count}")
    print(f"Errors: {error_count}")
    print(f"Total time: {total_time}")
    print(f"JSON files saved to: {JSON_OUTPUT_FOLDER}/")
    print("="*50)

if __name__ == "__main__":
    print("PDF to JSON Data Extractor v1.0")
    print("=" * 60)
    print(f"Source folder: {SOURCE_FOLDER}")
    print(f"JSON output folder: {JSON_OUTPUT_FOLDER}")
    print(f"Images temporary folder: {IMAGES_FOLDER}")
    print("=" * 60)
    main()