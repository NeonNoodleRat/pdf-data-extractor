import json
import os
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
import random

# Pydantic model based on main_json_extractor.py structure
class MedicalDocumentObject(BaseModel):
    patient_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    medical_record_number: Optional[str] = None
    gender: Optional[str] = None
    admit_date: Optional[str] = None
    discharge_date: Optional[str] = None
    attending_physician: Optional[str] = None
    location: Optional[str] = None
    facility_name: Optional[str] = None
    facility_address: Optional[str] = None
    facility_city: Optional[str] = None
    facility_state: Optional[str] = None
    facility_zip: Optional[str] = None
    document_name: Optional[str] = None
    document_status: Optional[str] = None
    performed_by: Optional[str] = None
    authenticated_by: Optional[str] = None
    electronically_signed_date: Optional[str] = None
    full_document_text: Optional[str] = None
    document_filename: Optional[str] = None
    processed_timestamp: Optional[str] = None
    total_pages: Optional[int] = None

def generate_fake_patient_name():
    """Generate a realistic fake patient name"""
    first_names = ["John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa", "James", "Maria", 
                   "Christopher", "Jessica", "Daniel", "Ashley", "Matthew", "Amanda", "Anthony", "Stephanie"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", 
                  "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def generate_fake_physician_name():
    """Generate a realistic fake physician name"""
    first_names = ["Dr. Michael", "Dr. Sarah", "Dr. David", "Dr. Emily", "Dr. Robert", "Dr. Lisa", 
                   "Dr. James", "Dr. Maria", "Dr. Christopher", "Dr. Jessica"]
    last_names = ["Anderson", "Johnson", "Williams", "Davis", "Miller", "Wilson", "Moore", "Taylor", 
                  "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia", "Martinez"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def generate_facility_info():
    """Generate realistic fake facility information"""
    facilities = [
        {
            "name": "White Oak Medical Center",
            "address": "1234 Healthcare Blvd",
            "city": "Dallas",
            "state": "TX",
            "zip": "75201"
        },
        {
            "name": "Memorial Hospital",
            "address": "5678 Medical Drive",
            "city": "Houston", 
            "state": "TX",
            "zip": "77002"
        },
        {
            "name": "Regional Medical Center",
            "address": "9101 Hospital Way",
            "city": "San Antonio",
            "state": "TX", 
            "zip": "78201"
        },
        {
            "name": "Community Health Center",
            "address": "2468 Wellness Street",
            "city": "Austin",
            "state": "TX",
            "zip": "73301"
        }
    ]
    
    facility = random.choice(facilities)
    return facility["name"], facility["address"], facility["city"], facility["state"], facility["zip"]

def generate_fake_document_text(document_type="Progress Note"):
    """Generate realistic fake medical document text based on document type"""
    
    age = random.randint(25, 85)
    gender_full = random.choice(["male", "female"])
    admit_date = "12/15/2023"
    discharge_date = "12/18/2023"
    
    templates = {
        "Progress Note": f"""PROGRESS NOTE

CHIEF COMPLAINT: Follow-up visit for diabetes management.

HISTORY OF PRESENT ILLNESS: Patient is a {age}-year-old {gender_full} with type 2 diabetes mellitus who presents for routine follow-up. Patient reports good adherence to medications and dietary modifications. Blood glucose levels have been stable.

PHYSICAL EXAMINATION: 
Vital Signs: BP 128/82, HR 72, Temp 98.6°F
General: Patient appears well, no acute distress
HEENT: Normocephalic, atraumatic
Cardiovascular: Regular rate and rhythm, no murmurs
Pulmonary: Clear to auscultation bilaterally
Extremities: No edema

ASSESSMENT AND PLAN:
1. Type 2 Diabetes Mellitus - well controlled
   - Continue current medications
   - Recheck HbA1c in 3 months
   - Continue dietary counseling

2. Hypertension - well controlled
   - Continue current antihypertensive therapy
   - Monitor blood pressure at home

FOLLOW-UP: Return in 3 months or sooner if concerns.""",

        "Discharge Summary": f"""DISCHARGE SUMMARY

ADMISSION DATE: {admit_date}
DISCHARGE DATE: {discharge_date}

PRINCIPAL DIAGNOSIS: Community-acquired pneumonia
SECONDARY DIAGNOSES: 
1. Type 2 diabetes mellitus
2. Hypertension

HOSPITAL COURSE: Patient is a {age}-year-old {gender_full} admitted with symptoms of cough, fever, and shortness of breath. Chest X-ray confirmed right lower lobe pneumonia. Patient was started on antibiotic therapy and supportive care.

Patient responded well to treatment with improvement in symptoms and oxygen saturation. Repeat chest X-ray showed clearing of infiltrates. Blood glucose levels were monitored and remained stable throughout admission.

DISCHARGE MEDICATIONS:
1. Amoxicillin 500mg twice daily x 7 days
2. Albuterol inhaler as needed for shortness of breath
3. Metformin 1000mg twice daily
4. Lisinopril 10mg daily

DISCHARGE INSTRUCTIONS:
- Complete full course of antibiotics
- Follow up with primary care physician in 1 week
- Return to ED if symptoms worsen
- Continue diabetic diet and medications

CONDITION ON DISCHARGE: Stable, improved""",

        "History and Physical": f"""HISTORY AND PHYSICAL EXAMINATION

CHIEF COMPLAINT: Chest pain

HISTORY OF PRESENT ILLNESS: {age}-year-old {gender_full} presents to the emergency department with complaint of chest pain that started 2 hours ago. Pain is described as sharp, substernal, 7/10 intensity. No radiation. Associated with shortness of breath. No nausea or diaphoresis.

PAST MEDICAL HISTORY:
1. Hypertension
2. Hyperlipidemia
3. Type 2 diabetes mellitus

MEDICATIONS:
1. Lisinopril 10mg daily
2. Atorvastatin 20mg daily
3. Metformin 1000mg twice daily

ALLERGIES: NKDA

SOCIAL HISTORY: Non-smoker, occasional alcohol use

FAMILY HISTORY: Father with CAD, mother with diabetes

REVIEW OF SYSTEMS: Positive for chest pain and shortness of breath. Negative for fever, chills, nausea, vomiting.

PHYSICAL EXAMINATION:
Vital Signs: BP 145/92, HR 88, RR 20, Temp 98.4°F, O2 Sat 97% on RA
General: {gender_full.capitalize()} in mild distress
HEENT: Normocephalic, atraumatic, PERRLA, EOMI
Neck: No JVD, no lymphadenopathy
Cardiovascular: Regular rate and rhythm, no murmurs, rubs, or gallops
Pulmonary: Clear to auscultation bilaterally
Abdomen: Soft, non-tender, non-distended
Extremities: No edema, pulses intact
Neurologic: Alert and oriented x3, grossly intact

ASSESSMENT AND PLAN:
1. Chest pain - rule out acute coronary syndrome
   - EKG, cardiac enzymes, chest X-ray
   - Cardiology consultation
   - Serial cardiac monitoring

2. Hypertension - continue home medications
3. Diabetes - monitor blood glucose"""
    }
    
    return templates.get(document_type, templates["Progress Note"])

def generate_complete_medical_doc(document_type="Progress Note"):
    """Generate a complete fake medical document object with specified type"""
    # Generate basic info
    patient_name = generate_fake_patient_name()
    physician_name = generate_fake_physician_name()
    facility_name, facility_address, facility_city, facility_state, facility_zip = generate_facility_info()
    
    # Generate dates
    admit_date = f"{random.randint(1, 12):02d}/{random.randint(1, 28):02d}/2023"
    discharge_date = f"{random.randint(1, 12):02d}/{random.randint(1, 28):02d}/2023" if document_type == "Discharge Summary" else None
    dob = f"{random.randint(1, 12):02d}/{random.randint(1, 28):02d}/{random.randint(1940, 2000)}"
    signed_date = f"{random.randint(1, 12):02d}/{random.randint(1, 28):02d}/2023" if random.choice([True, False, False]) else None
    
    # Document statuses and locations
    document_statuses = ["Verified", "Authenticated", "Signed", "Final"]
    locations = ["LD: ICU", "LD: Med/Surg", "LD: Emergency", "LD: Outpatient", "LD: OR"]
    genders = ["Male", "Female"]
    
    return MedicalDocumentObject(
        patient_name=patient_name,
        date_of_birth=dob,
        medical_record_number=f"MRN{random.randint(1000000, 9999999)}",
        gender=random.choice(genders),
        admit_date=admit_date,
        discharge_date=discharge_date,
        attending_physician=physician_name,
        location=random.choice(locations),
        facility_name=facility_name,
        facility_address=facility_address,
        facility_city=facility_city,
        facility_state=facility_state,
        facility_zip=facility_zip,
        document_name=document_type,
        document_status=random.choice(document_statuses),
        performed_by=physician_name,
        authenticated_by=f"{physician_name} on {datetime.now().strftime('%m/%d/%Y %H:%M')}",
        electronically_signed_date=signed_date,
        full_document_text=generate_fake_document_text(document_type),
        document_filename=f"{document_type.lower().replace(' ', '_')}_{random.randint(1000, 9999)}.pdf",
        processed_timestamp=datetime.now().isoformat(),
        total_pages=random.randint(1, 8)
    )

def generate_multiple_medical_docs(count=5, document_type=None):
    """Generate multiple fake medical document objects"""
    medical_docs = []
    for i in range(count):
        if document_type:
            doc = generate_complete_medical_doc(document_type)
        else:
            # Mix of document types
            doc_types = ["Progress Note", "Discharge Summary", "History and Physical"]
            doc = generate_complete_medical_doc(random.choice(doc_types))
        medical_docs.append(doc)
    return medical_docs

def save_test_data(document_type=None):
    """Generate and save test data files"""
    output_folder = "test_medical_docs_data"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    print("🏥 Generating fake medical document test data...")
    print("📋 Based on main_json_extractor.py structure")
    if document_type:
        print(f"📄 Document Type: {document_type}")
    else:
        print("📄 Document Type: Mixed (Progress Note, Discharge Summary, History and Physical)")
    print("=" * 50)
    
    # Generate single medical document
    if document_type:
        single_doc = generate_complete_medical_doc(document_type)
        filename_prefix = document_type.lower().replace(' ', '_').replace('&', 'and')
    else:
        single_doc = generate_complete_medical_doc("Progress Note")  # Default
        filename_prefix = "sample"
    
    single_path = os.path.join(output_folder, f"{filename_prefix}_medical_doc.json")
    
    with open(single_path, 'w') as f:
        json.dump(single_doc.model_dump(exclude_none=False), f, indent=2, default=str)
    
    print(f"✅ Single medical doc saved: {single_path}")
    
    # Generate multiple medical documents
    multiple_docs = generate_multiple_medical_docs(5, document_type)
    multiple_path = os.path.join(output_folder, f"multiple_{filename_prefix}_docs.json")
    
    docs_data = [doc.model_dump(exclude_none=False) for doc in multiple_docs]
    with open(multiple_path, 'w') as f:
        json.dump(docs_data, f, indent=2, default=str)
    
    print(f"✅ Multiple medical docs saved: {multiple_path}")
    
    # Generate JSON schema (same regardless of document type)
    schema = MedicalDocumentObject.model_json_schema()
    schema_path = os.path.join(output_folder, "medical_doc_schema.json")
    
    with open(schema_path, 'w') as f:
        json.dump(schema, f, indent=2)
    
    print(f"✅ JSON schema saved: {schema_path}")
    
    # Generate a "realistic" incomplete example (some fields missing)
    incomplete_doc = generate_complete_medical_doc(document_type if document_type else "Progress Note")
    incomplete_doc.discharge_date = None  # Not discharged yet
    incomplete_doc.electronically_signed_date = None  # Not signed yet
    incomplete_doc.medical_record_number = None  # MRN not captured
    incomplete_doc.location = None  # Location not specified
    
    incomplete_path = os.path.join(output_folder, f"incomplete_{filename_prefix}_doc.json")
    with open(incomplete_path, 'w') as f:
        json.dump(incomplete_doc.model_dump(exclude_none=False), f, indent=2, default=str)
    
    print(f"✅ Incomplete example saved: {incomplete_path}")
    
    print("\n" + "=" * 50)
    print("📋 SUMMARY FOR PERSON 1:")
    print("=" * 50)
    print(f"Test data generated in: {output_folder}/")
    print("Files created:")
    print(f"  • {filename_prefix}_medical_doc.json - Single complete example")
    print(f"  • multiple_{filename_prefix}_docs.json - Array of 5 examples") 
    print(f"  • incomplete_{filename_prefix}_doc.json - Example with missing fields")
    print("  • medical_doc_schema.json - JSON schema for validation")
    print("\n📋 STRUCTURE: Matches main_json_extractor.py output (nested format)")
    if document_type:
        print(f"📄 DOCUMENT TYPE: All generated documents are {document_type}")
    print("💡 Use the single document file for initial testing!")

def preview_sample(document_type=None):
    """Show a preview of what the medical document data looks like"""
    sample = generate_complete_medical_doc(document_type if document_type else "Progress Note")
    print("📋 SAMPLE MEDICAL DOCUMENT DATA PREVIEW:")
    print("=" * 60)
    
    # Show key fields for quick review
    print(f"📄 DOCUMENT INFO:")
    print(f"   Document Type: {sample.document_name}")
    print(f"   Document Status: {sample.document_status}")
    print(f"   Filename: {sample.document_filename}")
    print(f"   Total Pages: {sample.total_pages}")
    
    print(f"\n👤 PATIENT INFO:")
    print(f"   Name: {sample.patient_name}")
    print(f"   DOB: {sample.date_of_birth}")
    print(f"   Gender: {sample.gender}")
    print(f"   MRN: {sample.medical_record_number}")
    
    print(f"\n🏥 FACILITY INFO:")
    print(f"   Facility: {sample.facility_name}")
    print(f"   Address: {sample.facility_address}")
    print(f"   City: {sample.facility_city}, {sample.facility_state} {sample.facility_zip}")
    print(f"   Location: {sample.location}")
    
    print(f"\n👨‍⚕️ CLINICAL INFO:")
    print(f"   Attending: {sample.attending_physician}")
    print(f"   Admit Date: {sample.admit_date}")
    print(f"   Discharge Date: {sample.discharge_date if sample.discharge_date else 'Not discharged'}")
    print(f"   Performed By: {sample.performed_by}")
    print(f"   Signed Date: {sample.electronically_signed_date if sample.electronically_signed_date else 'Not signed'}")
    
    print(f"\n📝 DOCUMENT TEXT (first 200 chars):")
    text_preview = sample.full_document_text[:200] + "..." if len(sample.full_document_text) > 200 else sample.full_document_text
    print(f"   {text_preview}")
    
    print(f"\n⏰ PROCESSING:")
    print(f"   Processed: {sample.processed_timestamp}")
    
    print("\n🔍 This is fake data - safe for testing!")
    print("📋 Structure matches main_json_extractor.py output!")

if __name__ == "__main__":
    print("🏥 MEDICAL DOCUMENT TEST DATA GENERATOR")
    print("=" * 60)
    print("📋 Based on main_json_extractor.py structure")
    print("🔧 Generates realistic fake medical document data for testing")
    print("💼 For Person 1's integration testing of regular medical docs")
    print("=" * 60)
    print("This script generates realistic fake medical document data.")
    print("All data is completely fictional and safe for development/testing.")
    print("=" * 60)
    
    print("\nDocument Type Options:")
    print("1. Progress Note")
    print("2. Discharge Summary") 
    print("3. History and Physical")
    print("4. Mixed (all types)")
    
    doc_choice = input("\nChoose document type (1-4): ").strip()
    
    document_types = {
        "1": "Progress Note",
        "2": "Discharge Summary", 
        "3": "History and Physical",
        "4": None  # Mixed
    }
    
    selected_doc_type = document_types.get(doc_choice)
    
    if doc_choice not in document_types:
        print("Invalid choice, defaulting to mixed document types.")
        selected_doc_type = None
    
    print("\nGeneration Options:")
    print("1. Generate test files")
    print("2. Preview sample data")
    print("3. Both")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice in ["1", "3"]:
        save_test_data(selected_doc_type)
    
    if choice in ["2", "3"]:
        print("\n")
        preview_sample(selected_doc_type)
    
    print("\n✅ Done! Send the JSON files to Person 1 for medical document testing.")
    print("💡 This covers regular medical docs (main_json_extractor.py structure)!")
    print("🎯 Combined with facesheet test data, Person 1 has complete test coverage!")