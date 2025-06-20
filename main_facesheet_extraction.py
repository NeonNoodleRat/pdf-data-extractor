import os
import json
import ollama
import pandas as pd
from datetime import datetime
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image
from pydantic import BaseModel
from typing import List, Optional
import time

# Configuration - Updated for your test setup
SOURCE_FOLDER = "facesheet_pdfs"  # Your new test folder
CHECKPOINT_FILE = "processed_facesheets.json"
OUTPUT_FOLDER = "facesheet_json_output"
IMAGES_FOLDER = "facesheet_images"
model_name = "gemma3:27b"

# Updated Pydantic Models - FLATTENED STRUCTURE
class Address(BaseModel):
    line_one: Optional[str] = None
    line_two: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None

class PatientInformation(BaseModel):
    # Removed account_number - now at top level only
    race: Optional[str] = None
    ssn: Optional[str] = None
    encrypted_ssn: Optional[str] = None
    bed: Optional[str] = None
    mothers_maiden_name: Optional[str] = None
    alias: Optional[str] = None
    marital_status: Optional[str] = None
    veteran_status: Optional[str] = None
    address: Optional[Address] = None
    home_phone: Optional[str] = None
    business_phone: Optional[str] = None
    primary_language: Optional[str] = None
    county_code: Optional[str] = None
    drivers_license_number: Optional[str] = None

class GuarantorInformation(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    ssn: Optional[str] = None
    encrypted_ssn: Optional[str] = None
    address: Optional[Address] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_relation: Optional[str] = None
    employer_name: Optional[str] = None
    employer_phone: Optional[str] = None
    employer_address: Optional[Address] = None

class InsurancePlan(BaseModel):
    plan_id: Optional[str] = None
    policy_number: Optional[str] = None
    group_number: Optional[str] = None
    group_name: Optional[str] = None
    insurance_name: Optional[str] = None
    insurance_company_id: Optional[str] = None
    insurance_phone_number: Optional[str] = None
    insurance_address: Optional[Address] = None
    insured_name: Optional[str] = None
    insured_dob: Optional[str] = None
    insured_address: Optional[Address] = None
    insured_relation: Optional[str] = None
    authorization_number: Optional[str] = None

# Flattened FacesheetObject - merged facesheet_text and pdf_information
class FacesheetObject(BaseModel):
    # Top-level fields (formerly from facesheet_text and pdf_information)
    date: Optional[str] = None
    display_date: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    admit_date_time: Optional[str] = None
    room: Optional[str] = None
    medical_record_number: Optional[str] = None
    account_number: Optional[str] = None
    visit_number: Optional[str] = None
    location_name: Optional[str] = None
    referring_physician: Optional[str] = None
    
    # Nested information objects
    patient_information: Optional[PatientInformation] = None
    guarantor_information: Optional[GuarantorInformation] = None
    insurance_plan_one: Optional[InsurancePlan] = None
    insurance_plan_two: Optional[InsurancePlan] = None
    insurance_plan_three: Optional[InsurancePlan] = None
    
    # Processing metadata
    processed_timestamp: Optional[str] = None
    source_filename: Optional[str] = None

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

def convert_pdf_to_images(pdf_path, output_folder=IMAGES_FOLDER):
    """
    Convert ALL pages of a PDF to PNG images for facesheet processing.
    Returns a list of image paths.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Clear any existing PNG/JPG files
    for fname in os.listdir(output_folder):
        if fname.lower().endswith((".png", ".jpg", ".jpeg")):
            os.remove(os.path.join(output_folder, fname))

    try:
        # Get page count
        info = pdfinfo_from_path(pdf_path)
        total_pages = info.get("Pages", 0)

        # Convert ALL pages
        images = convert_from_path(pdf_path)
        image_paths = []
        
        for i, image in enumerate(images, 1):
            image_path = os.path.join(output_folder, f"page_{i}.png")
            image.save(image_path, "PNG")
            image_paths.append(image_path)

        print(f"  📄 Converted PDF ({total_pages} pages) → {len(image_paths)} images")
        return image_paths

    except Exception as e:
        print(f"  ❌ ERROR converting PDF {pdf_path}: {e}")
        return []

def extract_facesheet_data(image_paths, debug=False):
    """
    Extract comprehensive facesheet data from all page images using Ollama.
    Returns extracted data as a dictionary with FLATTENED structure.
    """
    if debug:
        print(f"Processing {len(image_paths)} facesheet images")
        print("=" * 60)

    # Updated extraction prompt for FLATTENED structure
    extraction_prompt = """
    Looking at this facesheet document, please extract ALL available information and format it as JSON.
    
    CRITICAL: If SSN is redacted (shows *** or XXX), set it to null.
    CRITICAL: If any field is not clearly visible, use null (not empty string).
    
    Extract the following comprehensive information:
    
    PATIENT INFORMATION:
    - Race, marital status, veteran status  
    - SSN (null if redacted), bed/room number
    - Home address (street, city, state, zip)
    - Phone numbers (home, business/work)
    - Primary language, county code
    - Mother's maiden name, alias
    - Driver's license number
    
    GUARANTOR INFORMATION:
    - Guarantor name, phone, SSN (null if redacted)
    - Guarantor address
    - Emergency contact information (name, phone, relation)
    - Employer information (name, phone, address)
    
    INSURANCE INFORMATION (up to 3 plans):
    - Insurance company name, plan ID, policy number, group number/name
    - Insurance company phone and address
    - Insured person's name, DOB, address, relation to patient
    - Authorization numbers
    
    TOP LEVEL INFORMATION:
    - Patient gender, date of birth
    - Account number, medical record number, visit number
    - Admit date/time, room/bed assignment
    - Attending/referring physician, location/department name
    
    Format as JSON with this FLATTENED structure (note: account_number at TOP level only):
    {
        "gender": "",
        "date_of_birth": "",
        "admit_date_time": "",
        "room": "",
        "medical_record_number": "",
        "account_number": "",
        "visit_number": "",
        "location_name": "",
        "referring_physician": "",
        "patient_information": {
            "race": "",
            "ssn": null,
            "encrypted_ssn": "",
            "bed": "",
            "mothers_maiden_name": "",
            "alias": "",
            "marital_status": "",
            "veteran_status": "",
            "address": {
                "line_one": "",
                "line_two": "",
                "city": "",
                "state": "",
                "zip": ""
            },
            "home_phone": "",
            "business_phone": "",
            "primary_language": "",
            "county_code": "",
            "drivers_license_number": ""
        },
        "guarantor_information": {
            "name": "",
            "phone": "",
            "ssn": null,
            "encrypted_ssn": "",
            "address": {
                "line_one": "",
                "line_two": "",
                "city": "",
                "state": "",
                "zip": ""
            },
            "contact_name": "",
            "contact_phone": "",
            "contact_relation": "",
            "employer_name": "",
            "employer_phone": "",
            "employer_address": {
                "line_one": "",
                "line_two": "",
                "city": "",
                "state": "",
                "zip": ""
            }
        },
        "insurance_plan_one": {
            "plan_id": "",
            "policy_number": "",
            "group_number": "",
            "group_name": "",
            "insurance_name": "",
            "insurance_phone_number": "",
            "insurance_address": {
                "line_one": "",
                "line_two": "",
                "city": "",
                "state": "",
                "zip": ""
            },
            "insured_name": "",
            "insured_dob": "",
            "insured_address": {
                "line_one": "",
                "line_two": "",
                "city": "",
                "state": "",
                "zip": ""
            },
            "insured_relation": "",
            "authorization_number": ""
        },
        "insurance_plan_two": null,
        "insurance_plan_three": null
    }
    
    Return ONLY the JSON - no explanations or markdown formatting.
    """

    try:
        # Send all images to Ollama for comprehensive extraction
        res = ollama.chat(
            model=model_name,
            messages=[
                {
                    'role': 'user',
                    'content': extraction_prompt,
                    'images': image_paths
                }
            ]
        )

        if debug:
            print("FACESHEET EXTRACTION RESPONSE:")
            print(res['message']['content'])
            print("=" * 60)

        response_text = res['message']['content']

        # Extract JSON from response
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
            print("SUCCESSFULLY PARSED FACESHEET JSON:")
            print(json.dumps(extracted_data, indent=2))
            print("=" * 60)

        return extracted_data

    except (json.JSONDecodeError, ValueError) as e:
        if debug:
            print(f"JSON PARSING FAILED: {e}")
        else:
            print(f"  ❌ JSON PARSING ERROR: {e}")
        return None

    except Exception as e:
        if debug:
            print(f"ERROR extracting facesheet data: {e}")
        else:
            print(f"  ❌ ERROR extracting facesheet data: {e}")
        return None

def process_facesheet_pdf(pdf_path, output_folder, debug=False):
    """
    Process a single facesheet PDF and save results as JSON with FLATTENED structure.
    """
    filename = os.path.basename(pdf_path)
    base_name = os.path.splitext(filename)[0]
    output_json_path = os.path.join(output_folder, f"{base_name}.json")

    try:
        # Convert PDF to images
        print("  📄 Converting PDF to images...")
        image_paths = convert_pdf_to_images(pdf_path, IMAGES_FOLDER)
        if not image_paths:
            print("  ❌ ERROR: Failed to convert PDF to images")
            return False

        # Extract facesheet data
        print("  📋 Extracting facesheet data...")
        extracted_data = extract_facesheet_data(image_paths, debug=debug)
        if extracted_data is None:
            print("  ❌ ERROR: Failed to extract facesheet data")
            return False

        # Create FacesheetObject with FLATTENED structure
        today = datetime.now()
        
        facesheet_obj = FacesheetObject(
            # Top-level fields (flattened)
            date=today.strftime("%Y-%m-%d"),
            display_date=today.strftime("%m/%d/%Y"),
            gender=extracted_data.get("gender"),
            date_of_birth=extracted_data.get("date_of_birth"),
            admit_date_time=extracted_data.get("admit_date_time"),
            room=extracted_data.get("room"),
            medical_record_number=extracted_data.get("medical_record_number"),
            account_number=extracted_data.get("account_number"),
            visit_number=extracted_data.get("visit_number"),
            location_name=extracted_data.get("location_name"),
            referring_physician=extracted_data.get("referring_physician"),
            
            # Nested information objects
            patient_information=PatientInformation(**extracted_data.get("patient_information", {})) if extracted_data.get("patient_information") else None,
            guarantor_information=GuarantorInformation(**extracted_data.get("guarantor_information", {})) if extracted_data.get("guarantor_information") else None,
            insurance_plan_one=InsurancePlan(**extracted_data.get("insurance_plan_one", {})) if extracted_data.get("insurance_plan_one") else None,
            insurance_plan_two=InsurancePlan(**extracted_data.get("insurance_plan_two", {})) if extracted_data.get("insurance_plan_two") else None,
            insurance_plan_three=InsurancePlan(**extracted_data.get("insurance_plan_three", {})) if extracted_data.get("insurance_plan_three") else None,
            
            # Processing metadata
            processed_timestamp=datetime.now().isoformat(),
            source_filename=filename
        )

        # Save as JSON with proper null handling
        with open(output_json_path, 'w') as f:
            json.dump(facesheet_obj.model_dump(exclude_none=False), f, indent=2, default=str)

        print(f"  ✅ SUCCESS: Saved to {output_json_path}")
        return True

    except Exception as e:
        print(f"  ❌ ERROR processing {filename}: {e}")
        return False

def generate_schema():
    """Generate and save the JSON schema for the FacesheetObject model."""
    schema = FacesheetObject.model_json_schema()
    schema_path = os.path.join(OUTPUT_FOLDER, "facesheet_schema.json")
    
    with open(schema_path, 'w') as f:
        json.dump(schema, f, indent=2)
    
    print(f"📋 JSON Schema saved to: {schema_path}")
    return schema_path

def main():
    # Ensure output folders exist
    for folder in [OUTPUT_FOLDER, IMAGES_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    # Generate and save the schema
    generate_schema()

    # Load checkpoint
    processed = load_checkpoint()

    # Check if source folder exists
    if not os.path.exists(SOURCE_FOLDER):
        print(f"❌ Source folder '{SOURCE_FOLDER}' not found!")
        print(f"Please create the folder and add your facesheet PDFs there.")
        return

    # Fetch list of all PDFs in source folder
    all_pdfs = [
        fname for fname in os.listdir(SOURCE_FOLDER)
        if fname.lower().endswith(".pdf")
    ]

    # Filter out already-processed
    to_process = [f for f in all_pdfs if f not in processed]

    if not to_process:
        if not all_pdfs:
            print(f"No PDF files found in '{SOURCE_FOLDER}' folder.")
            print("Please add your facesheet PDFs to test with.")
        else:
            print("All facesheet PDF files have already been processed.")
        return

    print(f"Found {len(all_pdfs)} total PDFs, {len(to_process)} to process")
    print("=" * 50)

    # Track counts and time
    successful_count = 0
    error_count = 0
    start_time = datetime.now()

    for idx, filename in enumerate(to_process, start=1):
        print(f"[{idx}/{len(to_process)}] Processing: {filename}")
        pdf_path = os.path.join(SOURCE_FOLDER, filename)

        try:
            success = process_facesheet_pdf(pdf_path, OUTPUT_FOLDER, debug=True)  # Enable debug for testing
            
            if success:
                successful_count += 1
            else:
                error_count += 1

            # Mark as processed regardless of success (to avoid infinite retries)
            processed.add(filename)
            save_checkpoint(processed)

            # Progress update every 5 files (lower for testing)
            if successful_count % 5 == 0 and successful_count > 0:
                elapsed = datetime.now() - start_time
                avg_time = elapsed.total_seconds() / (successful_count + error_count)
                remaining = len(to_process) - idx
                est_remaining = avg_time * remaining / 60  # minutes
                print(f"  ⏱️  Progress: {successful_count}/{len(to_process)} | Est. remaining: {est_remaining:.1f} min")

        except Exception as e:
            print(f"  ❌ UNEXPECTED ERROR processing {filename}: {e}")
            error_count += 1
            processed.add(filename)
            save_checkpoint(processed)
            continue

    # Final summary
    total_time = datetime.now() - start_time
    print("\n" + "="*50)
    print("FACESHEET PROCESSING COMPLETE")
    print("="*50)
    print(f"Successfully processed: {successful_count}")
    print(f"Errors: {error_count}")
    print(f"Total time: {total_time}")
    print(f"JSON files saved to: {OUTPUT_FOLDER}")
    print(f"Checkpoint saved at: {CHECKPOINT_FILE}")
    print("="*50)

if __name__ == "__main__":
    print("Updated Facesheet PDF Data Extractor v2.0")
    print("=" * 60)
    print(f"Source folder: {SOURCE_FOLDER}")
    print(f"Checkpoint file: {CHECKPOINT_FILE}")
    print(f"Output folder: {OUTPUT_FOLDER}")
    print(f"Images temporary folder: {IMAGES_FOLDER}")
    print("🔧 UPDATES: Flattened structure + single account_number + SSN handling")
    print("=" * 60)
    
    # Add command line options
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--schema-only":
        # Just generate schema and exit
        if not os.path.exists(OUTPUT_FOLDER):
            os.makedirs(OUTPUT_FOLDER)
        schema_path = generate_schema()
        print(f"Schema generated at: {schema_path}")
        print("Use 'python script.py --view-schema' to view the schema")
    elif len(sys.argv) > 1 and sys.argv[1] == "--view-schema":
        # Display the schema
        schema = FacesheetObject.model_json_schema()
        print("FACESHEET JSON SCHEMA:")
        print("=" * 60)
        print(json.dumps(schema, indent=2))
    else:
        # Normal processing
        main()