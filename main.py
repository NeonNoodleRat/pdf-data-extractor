import os
import json
import ollama
import re
import pandas as pd
from datetime import datetime
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image

# Path to the folder containing all PDFs
SOURCE_FOLDER = "/home/shared/usacs_documents"
# Name of the checkpoint file in the working directory
CHECKPOINT_FILE = "processed_files.json"
# Name of the CSV where results are saved
CSV_PATH = "data.csv"
# Folder where temporary images will be written
IMAGES_FOLDER = "images"
model_name = "gemma3:27b"
#model_name = "gemma3:4b"

def load_checkpoint():
    """Load the set of already-processed filenames from JSON checkpoint."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            processed_list = json.load(f)
        return set(processed_list)
    return set()

def save_checkpoint(processed_set):
    """Write the processed filenames set back to the JSON checkpoint."""
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(sorted(processed_set), f, indent=2)
        #SHAH_47863014_20250521_Progress-Note-Physician_LANDMORGAN_RIEFONDIA_20250527_e6daed3e-76aa-4e91-ae87-5aa9b4c4aea9.pdf

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

def extract_electronic_signature_date(image_path, debug=False):
    """Extract electronic signature date from last-page image via Ollama."""
    if debug:
        print(f"Extracting signature date from: {image_path}")
        print("=" * 60)

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
                    'images': [image_path]
                }
            ]
        )

        response_text = res['message']['content'].strip()
        if debug:
            print("SIGNATURE EXTRACTION RESPONSE:")
            print(response_text)
            print("=" * 60)

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

    # Facility name correction
    facility_name = validated.get('facility_name', '')
    if 'adventist' in facility_name.lower() and 'white oak' not in facility_name.lower():
        validated['facility_name'] = "White Oak Medical Center"

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
        print("=" * 60)

    # Crop header portion
    image_path = crop_image_to_header(image_path, crop_fraction=0.33)

    # Step 1: Raw description prompt
    res = ollama.chat(
        model=model_name,
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
        print("=" * 60)

    # Step 2: Structured JSON extraction
    structured_prompt = f"""
    Looking at this medical document image, please extract the following information and format it as JSON.

    Pay special attention to:
    - Patient name: appears after "Patient:"
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
        "gender": "Male/Female/Other",
        "admit_date": "admission date if this appears to be an admission",
        "discharge_date": "discharge date if this appears to be a discharge", 
        "attending_physician": "attending doctor's name",
        "location": "patient location including LD: prefix if present",
        "facility_name": "specific medical center name (not parent organization)",
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
            model=model_name,
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
            print("=" * 60)

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
            print("=" * 60)

        return validated_data

    except (json.JSONDecodeError, ValueError) as e:
        if debug:
            print(f"JSON PARSING FAILED: {e}")
            print("Returning debug data...")
            print("=" * 60)
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
    Convert only the first page and last page of a PDF to PNG images.
    Returns a dict: {'first': path_to_first, 'last': path_to_last}
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

        image_paths = {}

        # Convert first page only
        first_page_images = convert_from_path(pdf_path, first_page=1, last_page=1)
        first_page_path = os.path.join(output_folder, "page_1.png")
        first_page_images[0].save(first_page_path, "PNG")
        image_paths["first"] = first_page_path

        # Convert last page only (if more than one page)
        if total_pages > 1:
            last_page_images = convert_from_path(
                pdf_path, first_page=total_pages, last_page=total_pages
            )
            last_page_path = os.path.join(output_folder, f"page_{total_pages}.png")
            last_page_images[0].save(last_page_path, "PNG")
            image_paths["last"] = last_page_path
        else:
            # Single-page PDF: reuse first-page image
            image_paths["last"] = first_page_path

        print(f"  📄 Converted PDF ({total_pages} pages) → first & last page images")
        return image_paths

    except Exception as e:
        print(f"  ❌ ERROR converting PDF {pdf_path}: {e}")
        return {}

def main():
    # Ensure images folder exists
    if not os.path.exists(IMAGES_FOLDER):
        os.makedirs(IMAGES_FOLDER)

    # Load checkpoint
    processed = load_checkpoint()

    # Fetch list of all PDFs in source folder
    all_pdfs = [
        fname for fname in os.listdir(SOURCE_FOLDER)
        if fname.lower().endswith(".pdf")
    ]

    # Filter out already-processed
    to_process = [f for f in all_pdfs if f not in processed]

    if not to_process:
        print("No unprocessed PDF files found in the source folder.")
        return

    print(f"Found {len(all_pdfs)} total PDFs, {len(to_process)} to process")
    print("=" * 50)

    # Prepare CSV: if it doesn't exist, write headers now
    expected_columns = [
        "patient_name", "date_of_birth", "gender", "admit_date", "discharge_date",
        "attending_physician", "location", "facility_name", "facility_address",
        "facility_city", "facility_state", "facility_zip", "document_name",
        "document_status", "performed_by", "authenticated_by", "electronically_signed_date"
    ]
    if not os.path.exists(CSV_PATH):
        # Create empty DataFrame with headers
        pd.DataFrame(columns=expected_columns).to_csv(CSV_PATH, index=False)

    # Track counts and time
    successful_count = 0
    error_count = 0
    start_time = datetime.now()

    for idx, filename in enumerate(to_process, start=1):
        print(f"[{idx}/{len(to_process)}] Processing: {filename}")
        pdf_path = os.path.join(SOURCE_FOLDER, filename)

        try:
            # Convert first and last pages
            image_paths = convert_pdf_to_images(pdf_path, IMAGES_FOLDER)
            if not image_paths or "first" not in image_paths:
                print("  ❌ ERROR: Failed to convert PDF to images")
                error_count += 1
                continue

            # Extract header data from first page
            print("  📋 Extracting header info...")
            header_info = ollama_process_image(image_paths["first"], debug=False)

            # Extract signature date from last page
            print("  ✍️  Extracting signature date...")
            sig_date = extract_electronic_signature_date(image_paths["last"], debug=False)

            # Combine results
            header_info["electronically_signed_date"] = sig_date
            header_info["document_name"] = filename
            header_info["processed_timestamp"] = datetime.now().isoformat()

            # Append a row to CSV
            row_df = pd.DataFrame([[header_info.get(col, "N/A") for col in expected_columns]],
                                  columns=expected_columns)
            row_df.to_csv(CSV_PATH, mode="a", header=False, index=False)

            # Mark as processed and update checkpoint
            processed.add(filename)
            save_checkpoint(processed)

            successful_count += 1
            patient_name = header_info.get("patient_name", "Unknown")
            sig_out = sig_date if sig_date != "N/A" else "No signature"
            print(f"  ✅ SUCCESS: {patient_name} | Sig: {sig_out}")

            # Progress update every 25 files
            if successful_count % 25 == 0:
                elapsed = datetime.now() - start_time
                avg_time = elapsed.total_seconds() / successful_count
                remaining = len(to_process) - idx
                est_remaining = avg_time * remaining / 60  # minutes
                print(f"  ⏱️  Progress: {successful_count}/{len(to_process)} | Est. remaining: {est_remaining:.1f} min")

        except Exception as e:
            print(f"  ❌ ERROR processing {filename}: {e}")
            error_count += 1
            # Still save checkpoint so we don’t retry on next run
            processed.add(filename)
            save_checkpoint(processed)
            continue

    # Final summary
    total_time = datetime.now() - start_time
    print("\n" + "="*50)
    print("BATCH PROCESSING COMPLETE")
    print("="*50)
    print(f"Successfully processed: {successful_count}")
    print(f"Errors: {error_count}")
    print(f"Total time: {total_time}")
    print(f"Results appended to: {CSV_PATH}")
    print(f"Checkpoint saved at: {CHECKPOINT_FILE}")
    print("="*50)

if __name__ == "__main__":
    print("Enhanced PDF Data Extractor v3.1")
    print("=" * 60)
    print(f"Source folder: {SOURCE_FOLDER}")
    print(f"Checkpoint file: {CHECKPOINT_FILE}")
    print(f"Output CSV: {CSV_PATH}")
    print(f"Images temporary folder: {IMAGES_FOLDER}")
    print("=" * 60)
    main()
