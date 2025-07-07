import os
import json
import ollama
import re
from datetime import datetime
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image
import PyPDF2
import pdfplumber

# Configuration for troubleshooting
SOURCE_FOLDER = "documents"  # Local folder with test PDFs
JSON_OUTPUT_FOLDER = "troubleshoot_output"
IMAGES_FOLDER = "troubleshoot_images"
MODEL_NAME = "gemma3:27b"

def detect_pdf_type(pdf_path, debug=True):
    """
    Detect if PDF has extractable text (true PDF) or is scanned images.
    Returns: 'true_pdf', 'scanned_pdf', or 'error'
    """
    print(f"🔍 Detecting PDF type for: {pdf_path}")
    
    try:
        # Method 1: Try PyPDF2 first (faster)
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_text = ""
            
            # Sample first few pages (up to 3) to determine type
            pages_to_check = min(3, len(pdf_reader.pages))
            
            for page_num in range(pages_to_check):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                total_text += page_text
        
        # Clean and analyze extracted text
        clean_text = total_text.strip().replace('\n', ' ').replace('\r', ' ')
        text_length = len(clean_text)
        word_count = len(clean_text.split()) if clean_text else 0
        
        print(f"  📊 PyPDF2 extracted {text_length} chars, {word_count} words")
        if clean_text:
            print(f"  📖 Sample text: {clean_text[:150]}...")
        
        # Heuristics to determine if it's a true PDF
        if text_length > 100 and word_count > 10:
            # Check if text looks meaningful (not just garbled characters)
            alpha_ratio = sum(c.isalpha() for c in clean_text) / len(clean_text) if clean_text else 0
            
            if alpha_ratio > 0.5:  # At least 50% alphabetic characters
                print(f"  ✅ Decision: TRUE_PDF (alpha_ratio: {alpha_ratio:.2f})")
                return 'true_pdf'
        
        # If PyPDF2 fails, try pdfplumber (more robust)
        print("  🔄 PyPDF2 extraction poor, trying pdfplumber...")
            
        with pdfplumber.open(pdf_path) as pdf:
            total_text_plumber = ""
            pages_to_check = min(3, len(pdf.pages))
            
            for page_num in range(pages_to_check):
                page = pdf.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    total_text_plumber += page_text
        
        clean_text_plumber = total_text_plumber.strip().replace('\n', ' ').replace('\r', ' ')
        text_length_plumber = len(clean_text_plumber)
        word_count_plumber = len(clean_text_plumber.split()) if clean_text_plumber else 0
        
        print(f"  📊 pdfplumber extracted {text_length_plumber} chars, {word_count_plumber} words")
        if clean_text_plumber:
            print(f"  📖 Sample text: {clean_text_plumber[:150]}...")
        
        if text_length_plumber > 100 and word_count_plumber > 10:
            alpha_ratio = sum(c.isalpha() for c in clean_text_plumber) / len(clean_text_plumber) if clean_text_plumber else 0
            if alpha_ratio > 0.5:
                print(f"  ✅ Decision: TRUE_PDF via pdfplumber (alpha_ratio: {alpha_ratio:.2f})")
                return 'true_pdf'
        
        # If both methods produce minimal text, likely scanned
        print("  📷 Decision: SCANNED_PDF (insufficient extractable text)")
        return 'scanned_pdf'
        
    except Exception as e:
        print(f"  ❌ ERROR detecting PDF type: {e}")
        return 'error'

def extract_text_from_true_pdf(pdf_path, debug=True):
    """
    Extract text from a true PDF using pdfplumber (best layout preservation).
    Returns formatted text with page separators.
    """
    print(f"📄 Extracting text from true PDF: {pdf_path}")
    
    try:
        full_text_parts = []
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"  📋 Processing {total_pages} pages...")
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"    Page {page_num}/{total_pages}")
                
                # Extract text with layout preservation
                page_text = page.extract_text()
                
                if page_text:
                    # Add page separator
                    if page_num > 1:
                        full_text_parts.append(f"\n--- Page {page_num} ---\n")
                    else:
                        full_text_parts.append(f"--- Page {page_num} ---\n")
                    
                    full_text_parts.append(page_text)
                    print(f"      ✅ Extracted {len(page_text)} characters")
                else:
                    print(f"      ⚠️  No text found on page {page_num}")
        
        full_text = "".join(full_text_parts)
        
        print(f"  ✅ Total extracted text: {len(full_text)} characters")
        if full_text:
            print(f"  📖 First 200 chars: {full_text[:200]}...")
        
        return full_text
        
    except Exception as e:
        print(f"  ❌ ERROR extracting text from true PDF: {e}")
        return "EXTRACTION_FAILED"

def extract_text_from_scanned_pdf(image_paths, debug=True):
    """
    Extract text from scanned PDF using AI vision.
    """
    print("📷 Extracting text from scanned PDF using AI vision...")
    
    full_text_parts = []
    failed_pages = []

    for page_num, image_path in enumerate(image_paths, 1):
        print(f"  🤖 AI processing page {page_num}/{len(image_paths)}...")
            
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

            page_text = res['message']['content'].strip()
            
            if page_text and page_text != "EXTRACTION_FAILED":
                # Add page separator
                if page_num > 1:
                    full_text_parts.append(f"\n--- Page {page_num} ---\n")
                else:
                    full_text_parts.append(f"--- Page {page_num} ---\n")
                
                full_text_parts.append(page_text)
                print(f"    ✅ Extracted {len(page_text)} characters")
            else:
                failed_pages.append(page_num)
                print(f"    ❌ Failed to extract text from page {page_num}")
                
        except Exception as e:
            print(f"    ❌ ERROR on page {page_num}: {e}")
            failed_pages.append(page_num)

    if failed_pages:
        print(f"  ⚠️  AI extraction failed on pages: {failed_pages}")
        if len(failed_pages) == len(image_paths):
            return "EXTRACTION_FAILED"

    full_text = "".join(full_text_parts)
    print(f"  ✅ AI extracted total: {len(full_text)} characters")

    return full_text

def extract_full_document_text_hybrid(pdf_path, debug=True):
    """
    Hybrid text extraction: detect PDF type and use optimal method.
    """
    print("🔄 Starting hybrid text extraction...")
    pdf_type = detect_pdf_type(pdf_path, debug=debug)
    
    if pdf_type == 'true_pdf':
        print("  ➡️  Using direct PDF text extraction")
        return extract_text_from_true_pdf(pdf_path, debug=debug), pdf_type
        
    elif pdf_type == 'scanned_pdf':
        print("  ➡️  Using AI vision extraction")
        # Convert to images first
        image_paths = convert_pdf_to_images(pdf_path, IMAGES_FOLDER)
        if not image_paths:
            return "EXTRACTION_FAILED", pdf_type
        return extract_text_from_scanned_pdf(image_paths, debug=debug), pdf_type
        
    else:  # error case
        print("  ⚠️  Could not determine PDF type - falling back to AI vision")
        image_paths = convert_pdf_to_images(pdf_path, IMAGES_FOLDER)
        if not image_paths:
            return "EXTRACTION_FAILED", 'error'
        return extract_text_from_scanned_pdf(image_paths, debug=debug), 'error'

def crop_image_to_header(image_path, crop_fraction=0.33):
    """Crop image to top portion (header section only)."""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            crop_height = int(height * crop_fraction)
            crop_box = (0, 0, width, crop_height)
            cropped_img = img.crop(crop_box)
            cropped_img.save(image_path, "PNG")
            print(f"    ✂️  Cropped to {width}x{crop_height} (top {int(crop_fraction*100)}%)")
            return image_path
    except Exception as e:
        print(f"    ⚠️  Failed to crop header image: {e}")
        return image_path

def extract_electronic_signature_date(image_path, debug=True):
    """Extract electronic signature date from last-page image via Ollama."""
    print(f"✍️  Extracting signature date from: {os.path.basename(image_path)}")

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
        print(f"  🤖 AI Response: {response_text}")

        # Regex patterns for dates
        date_patterns = [
            r'(\d{2}/\d{2}/\d{4})',      # MM/DD/YYYY
            r'(\d{1,2}/\d{1,2}/\d{4})',  # M/D/YYYY or variations
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, response_text)
            if matches:
                extracted_date = matches[0]
                print(f"  ✅ Extracted date: {extracted_date}")
                return extracted_date

        # Fallback: if response contains '/', try to clean up
        if 'N/A' not in response_text and '/' in response_text:
            cleaned = re.sub(r'[^\d/]', '', response_text)
            if len(cleaned) >= 8 and cleaned.count('/') == 2:
                print(f"  ✅ Cleaned date: {cleaned}")
                return cleaned

        print("  ❌ No valid date found")
        return "N/A"

    except Exception as e:
        print(f"  ❌ ERROR extracting signature date: {e}")
        return "N/A"

def ollama_process_image(image_path, debug=True):
    """Process first-page image: header cropping + structured extraction."""
    print(f"📋 Processing header from: {os.path.basename(image_path)}")

    # Crop header portion
    image_path = crop_image_to_header(image_path, crop_fraction=0.33)

    # Structured JSON extraction
    structured_prompt = """
    Looking at this medical document image, please extract the following information and format it as JSON.

    Pay special attention to:
    - Patient name: appears after "Patient:"
    - MRN: appears after "MRN:"
    - DOB: appears after "DOB/Age/Sex:" in MM/DD/YYYY format
    - Gender: appears after the age in the DOB/Age/Sex line
    - Admit/Disch dates: appears after "Admit/Disch.:" (this could be admission or discharge date)
    - Attending physician: appears after "Attending:"
    - Location: appears as "LD:" followed by location code (include the "LD:" prefix)
    - Facility name: Use the specific medical center name, not the parent organization
    - Document name: appears after "DOCUMENT NAME:" or can be inferred
    - Document status: appears after "DOCUMENT STATUS:" or look for "Verified"/"Auth" status
    - Authentication: appears in "AUTHENTICATED BY:" section

    {
        "patient_name": "patient's full name",
        "date_of_birth": "DOB in MM/DD/YYYY format",
        "medical_record_number": "Medical Record Number (MRN) if available",
        "gender": "Male/Female/Other",
        "admit_date": "first date from Admit/Disch field (before the / if two dates present)",
        "discharge_date": "second date from Admit/Disch field (after the / if two dates present, otherwise N/A)",
        "attending_physician": "attending doctor's name",
        "location": "patient location including LD: prefix if present",
        "facility_name": "facility name",
        "facility_address": "facility street address",
        "facility_city": "facility city",
        "facility_state": "facility state",
        "facility_zip": "facility zip code",
        "document_name": "type of document",
        "document_status": "document status (look for Verified, Auth, etc.)",
        "performed_by": "who performed/created the document",
        "authenticated_by": "who authenticated the document with timestamp"
    }

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

        print(f"  🤖 AI Response received ({len(structured_res['message']['content'])} chars)")
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
        print(f"  ✅ Successfully parsed JSON with {len(extracted_data)} fields")

        return extracted_data

    except (json.JSONDecodeError, ValueError) as e:
        print(f"  ❌ JSON PARSING ERROR: {e}")
        print(f"  📄 Raw response: {response_text[:300]}...")

        # Return error data
        error_data = {
            "patient_name": "EXTRACTION_FAILED",
            "date_of_birth": "EXTRACTION_FAILED", 
            "medical_record_number": "EXTRACTION_FAILED",
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
    """Convert all pages of PDF to PNG images."""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Clear existing images
    for fname in os.listdir(output_folder):
        if fname.lower().endswith((".png", ".jpg", ".jpeg")):
            os.remove(os.path.join(output_folder, fname))

    try:
        info = pdfinfo_from_path(pdf_path)
        total_pages = info.get("Pages", 0)
        print(f"  📄 Converting {total_pages} pages to images...")

        all_images = convert_from_path(pdf_path)
        image_paths = []

        for i, image in enumerate(all_images, 1):
            image_path = os.path.join(output_folder, f"page_{i}.png")
            image.save(image_path, "PNG")
            image_paths.append(image_path)

        print(f"  ✅ Created {len(image_paths)} image files")
        return image_paths

    except Exception as e:
        print(f"  ❌ ERROR converting PDF: {e}")
        return []

def main():
    print("🚀 PDF Troubleshoot Extractor")
    print("=" * 60)
    
    # Ensure folders exist
    for folder in [IMAGES_FOLDER, JSON_OUTPUT_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"📁 Created folder: {folder}")

    # Check source folder
    if not os.path.exists(SOURCE_FOLDER):
        print(f"❌ Source folder '{SOURCE_FOLDER}' not found!")
        print("Please create a 'documents' folder with test PDFs")
        return

    # Get all PDFs
    all_pdfs = [
        fname for fname in os.listdir(SOURCE_FOLDER)
        if fname.lower().endswith(".pdf")
    ]

    if not all_pdfs:
        print(f"❌ No PDF files found in '{SOURCE_FOLDER}'")
        return

    print(f"📋 Found {len(all_pdfs)} PDFs to process:")
    for i, pdf in enumerate(all_pdfs, 1):
        print(f"  {i}. {pdf}")
    print("=" * 60)

    # Process each PDF
    for idx, filename in enumerate(all_pdfs, start=1):
        print(f"\n📄 [{idx}/{len(all_pdfs)}] PROCESSING: {filename}")
        print("=" * 40)
        pdf_path = os.path.join(SOURCE_FOLDER, filename)

        try:
            # Convert first page for header (always needed)
            print("🖼️  Converting first page for header extraction...")
            image_paths = convert_pdf_to_images(pdf_path, IMAGES_FOLDER)
            if not image_paths:
                print("❌ Failed to convert PDF - skipping")
                continue

            # Extract header data
            header_info = ollama_process_image(image_paths[0], debug=True)

            # Extract signature date
            sig_date = extract_electronic_signature_date(image_paths[-1], debug=True)

            # Extract full document text using hybrid approach
            full_text, pdf_type = extract_full_document_text_hybrid(pdf_path, debug=True)

            # Combine results
            final_data = header_info.copy()
            final_data["electronically_signed_date"] = sig_date
            final_data["full_document_text"] = full_text
            final_data["document_filename"] = filename
            final_data["processed_timestamp"] = datetime.now().isoformat()
            final_data["total_pages"] = len(image_paths)
            final_data["pdf_type"] = pdf_type
            final_data["extraction_method"] = "pdf_direct" if pdf_type == 'true_pdf' else "ai_vision"

            # Save JSON
            json_filename = filename.replace('.pdf', '.json').replace('.PDF', '.json')
            json_path = os.path.join(JSON_OUTPUT_FOLDER, json_filename)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)

            # Summary
            patient_name = header_info.get("patient_name", "Unknown")
            text_chars = len(full_text) if full_text != "EXTRACTION_FAILED" else 0
            
            print(f"\n✅ COMPLETED: {filename}")
            print(f"   Patient: {patient_name}")
            print(f"   PDF Type: {pdf_type}")
            print(f"   Signature: {sig_date}")
            print(f"   Text Length: {text_chars} chars")
            print(f"   Saved: {json_path}")

        except Exception as e:
            print(f"❌ ERROR processing {filename}: {e}")
            continue

    print(f"\n🎉 TROUBLESHOOTING COMPLETE!")
    print(f"Check '{JSON_OUTPUT_FOLDER}' for results")

if __name__ == "__main__":
    main()