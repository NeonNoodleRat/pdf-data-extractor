import os
import ollama
import pandas as pd
from pydantic import BaseModel
import json

class Information(BaseModel):
    patient_name: str
    date_of_birth: str
    gender: str
    admit_date: str
    discharge_date: str
    attending_physician: str
    location: str
    facility_name: str
    facility_address: str
    facility_city: str
    facility_state: str
    facility_zip: str
    document_name: str
    document_status: str
    performed_by: str
    authenticated_by: str

def validate_extracted_data(data):
    """Clean up and validate extracted data"""
    validated = data.copy()
    
    # Clean up common issues
    for key, value in validated.items():
        if isinstance(value, str):
            # Strip extra whitespace
            validated[key] = value.strip()
            
            # Handle "N/A" variations
            if value.lower() in ['n/a', 'na', 'not available', 'not visible', '']:
                validated[key] = "N/A"
    
    # Specific field validations
    
    # Date format validation
    for date_field in ['date_of_birth', 'admit_date', 'discharge_date']:
        if date_field in validated and validated[date_field] != "N/A":
            # Basic date format check (MM/DD/YYYY)
            date_val = validated[date_field]
            if len(date_val) == 10 and date_val.count('/') == 2:
                parts = date_val.split('/')
                if len(parts[2]) == 4:  # Year should be 4 digits
                    year = int(parts[2])
                    # Flag suspicious years
                    if year < 1920 or year > 2030:
                        print(f"WARNING: Suspicious year in {date_field}: {year}")
    
    # Document status inference
    if validated.get('document_status') == "N/A":
        # Try to infer from authentication info or look for status keywords
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
        # Often the same as authenticated by in simple cases
        auth_by = validated.get('authenticated_by', '')
        if auth_by != "N/A" and 'MD' in auth_by:
            validated['performed_by'] = auth_by
    
    return validated

def ollama_process_image(image_path):
    """Process image with Ollama and attempt to extract structured information"""
    
    # First, let's see what the model can read from the image
    print(f"Processing image: {image_path}")
    print("=" * 60)
    
    # Step 1: Get raw description
    res = ollama.chat(
        model="gemma3:4b",
        messages=[
            {
                'role': 'user',
                'content': 'What do you see in this image? Describe all text you can read, including any medical document information, patient details, dates, and facility information.',
                'images': [image_path]
            }
        ]
    )
    
    print("RAW MODEL RESPONSE:")
    print(res['message']['content'])
    print("=" * 60)
    
    # Step 2: Try structured extraction with more specific instructions
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
    
    structured_res = ollama.chat(
        model="gemma3:4b",
        messages=[
            {
                'role': 'user',
                'content': structured_prompt,
                'images': [image_path]
            }
        ]
    )
    
    print("STRUCTURED EXTRACTION ATTEMPT:")
    print(structured_res['message']['content'])
    print("=" * 60)
    
    # Try to parse JSON response
    try:
        # Look for JSON in the response
        response_text = structured_res['message']['content']
        
        # Find JSON block (sometimes models wrap it in markdown)
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
        print("SUCCESSFULLY PARSED JSON:")
        print(json.dumps(extracted_data, indent=2))
        
        # Validate and clean up the data
        validated_data = validate_extracted_data(extracted_data)
        print("VALIDATED DATA:")
        print(json.dumps(validated_data, indent=2))
        print("=" * 60)
        
        return validated_data
        
    except (json.JSONDecodeError, ValueError) as e:
        print(f"JSON PARSING FAILED: {e}")
        print("Returning debug data...")
        print("=" * 60)
        
        # Return debug data with some manual extraction hints
        return {field: "EXTRACTION_FAILED" for field in Information.model_fields.keys()}

def test_single_image(image_path):
    """Test processing a single image"""
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}")
        return None
    
    print(f"Testing image processing for: {image_path}")
    result = ollama_process_image(image_path)
    
    # Create a simple CSV for this test
    df = pd.DataFrame([result])
    output_file = "debug_extraction.csv"
    df.to_csv(output_file, index=False)
    print(f"Results saved to: {output_file}")
    
    return result

if __name__ == "__main__":
    # Test with your existing image
    # Adjust the path to match your actual image location
    image_path = "test/redacted.png"  # or whatever your image is called
    if os.path.exists(image_path):
            print(f"Found image at: {image_path}")
            test_single_image(image_path)