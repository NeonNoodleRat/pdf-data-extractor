import json
import os
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
import random

# Flattened Pydantic models based on Person 1's feedback
class Address(BaseModel):
    line_one: Optional[str] = None
    line_two: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None

class PatientInformation(BaseModel):
    # Removed account_number - now at top level only
    race: Optional[str] = None
    ssn: Optional[str] = None  # Will be null if redacted
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
    ssn: Optional[str] = None  # Will be null if redacted
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

def generate_fake_address():
    """Generate a realistic fake address"""
    streets = ["Main St", "Oak Ave", "First St", "Second Ave", "Park Blvd", "Elm St", "Maple Ave", "Broadway"]
    cities = ["Springfield", "Franklin", "Georgetown", "Madison", "Riverside", "Oakland", "Bristol", "Salem"]
    states = ["CA", "TX", "FL", "NY", "PA", "IL", "OH", "GA", "NC", "MI"]
    
    return Address(
        line_one=f"{random.randint(100, 9999)} {random.choice(streets)}",
        line_two=f"Apt {random.randint(1, 99)}" if random.choice([True, False, False]) else None,
        city=random.choice(cities),
        state=random.choice(states),
        zip=f"{random.randint(10000, 99999)}"
    )

def generate_phone_number():
    """Generate a fake phone number"""
    area_code = random.randint(200, 999)
    exchange = random.randint(200, 999)
    number = random.randint(1000, 9999)
    return f"({area_code}) {exchange}-{number}"

def generate_fake_patient_info(account_number):
    """Generate fake patient information (account_number removed - now at top level)"""
    races = ["Caucasian", "African American", "Hispanic", "Asian", "Other", "Declined"]
    marital_statuses = ["Single", "Married", "Divorced", "Widowed", "Separated"]
    languages = ["English", "Spanish", "French", "Other"]
    
    # SSN handling: null if redacted (per Person 1's request)
    ssn_redacted = random.choice([True, False, False])  # 33% chance of redaction
    
    return PatientInformation(
        # account_number removed - now at top level
        race=random.choice(races),
        ssn=None if ssn_redacted else f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}",
        encrypted_ssn="ENCRYPTED_SSN_HASH_12345" if not ssn_redacted else None,
        bed=f"{random.randint(100, 500)}{random.choice(['A', 'B'])}",
        mothers_maiden_name="Smith" if random.choice([True, False]) else None,
        alias=None,
        marital_status=random.choice(marital_statuses),
        veteran_status="No" if random.choice([True, False, False]) else "Yes",
        address=generate_fake_address(),
        home_phone=generate_phone_number(),
        business_phone=generate_phone_number() if random.choice([True, False]) else None,
        primary_language=random.choice(languages),
        county_code=f"CTY{random.randint(1, 99):02d}",
        drivers_license_number=f"DL{random.randint(10000000, 99999999)}"
    )

def generate_fake_guarantor_info():
    """Generate fake guarantor information"""
    employers = ["ABC Corporation", "XYZ Industries", "Healthcare Partners", "Tech Solutions Inc", "Retail Group LLC"]
    relations = ["Self", "Spouse", "Parent", "Child", "Other"]
    
    # SSN handling: null if redacted
    ssn_redacted = random.choice([True, False])
    
    return GuarantorInformation(
        name="John Smith" if random.choice([True, False]) else "Self",
        phone=generate_phone_number(),
        ssn=None if ssn_redacted else f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}",
        encrypted_ssn="ENCRYPTED_GUARANTOR_SSN_67890" if not ssn_redacted else None,
        address=generate_fake_address(),
        contact_name="Emergency Contact Name",
        contact_phone=generate_phone_number(),
        contact_relation=random.choice(relations),
        employer_name=random.choice(employers),
        employer_phone=generate_phone_number(),
        employer_address=generate_fake_address()
    )

def generate_fake_insurance_plan(plan_type="Primary"):
    """Generate fake insurance plan"""
    insurance_companies = [
        "Blue Cross Blue Shield",
        "Aetna",
        "Cigna", 
        "UnitedHealthcare",
        "Humana",
        "Kaiser Permanente",
        "Anthem"
    ]
    
    relations = ["Self", "Spouse", "Child", "Other"]
    
    return InsurancePlan(
        plan_id=f"PLN{random.randint(1000, 9999)}",
        policy_number=f"POL{random.randint(100000000, 999999999)}",
        group_number=f"GRP{random.randint(10000, 99999)}",
        group_name=f"Employee Group {random.randint(100, 999)}",
        insurance_name=random.choice(insurance_companies),
        insurance_company_id=f"INS{random.randint(1000, 9999)}",
        insurance_phone_number=generate_phone_number(),
        insurance_address=generate_fake_address(),
        insured_name="Patient Name",
        insured_dob="01/15/1980",
        insured_address=generate_fake_address(),
        insured_relation=random.choice(relations),
        authorization_number=f"AUTH{random.randint(100000, 999999)}" if random.choice([True, False]) else None
    )

def generate_complete_facesheet():
    """Generate a complete fake facesheet object with flattened structure"""
    today = datetime.now()
    genders = ["Male", "Female", "Other"]
    locations = ["Emergency Department", "Medical/Surgical Unit", "ICU", "Outpatient", "Observation"]
    physicians = ["Dr. Johnson", "Dr. Williams", "Dr. Brown", "Dr. Davis", "Dr. Miller"]
    
    admit_date = datetime.now().strftime("%m/%d/%Y %H:%M")
    
    # Generate single account number to use consistently
    account_number = f"ACC{random.randint(100000, 999999)}"
    
    return FacesheetObject(
        # Top-level fields (flattened from nested objects)
        date=today.strftime("%Y-%m-%d"),
        display_date=today.strftime("%m/%d/%Y"),
        gender=random.choice(genders),
        date_of_birth="01/15/1980",
        admit_date_time=admit_date,
        room=f"{random.randint(100, 500)}{random.choice(['A', 'B'])}",
        medical_record_number=f"MRN{random.randint(1000000, 9999999)}",
        account_number=account_number,  # Single source of truth
        visit_number=f"VIS{random.randint(100000, 999999)}",
        location_name=random.choice(locations),
        referring_physician=random.choice(physicians),
        
        # Nested information objects (account_number removed from patient_information)
        patient_information=generate_fake_patient_info(account_number),
        guarantor_information=generate_fake_guarantor_info(),
        insurance_plan_one=generate_fake_insurance_plan("Primary"),
        insurance_plan_two=generate_fake_insurance_plan("Secondary") if random.choice([True, False]) else None,
        insurance_plan_three=generate_fake_insurance_plan("Tertiary") if random.choice([True, False, False]) else None,
        
        # Processing metadata
        processed_timestamp=datetime.now().isoformat(),
        source_filename="test_facesheet_fake_data.pdf"
    )

def generate_multiple_facesheets(count=5):
    """Generate multiple fake facesheet objects"""
    facesheets = []
    for i in range(count):
        facesheet = generate_complete_facesheet()
        facesheets.append(facesheet)
    return facesheets

def save_test_data():
    """Generate and save test data files"""
    output_folder = "test_facesheet_data_v2"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    print("🏥 Generating UPDATED fake facesheet test data...")
    print("📋 Changes: Flattened structure + null SSN handling + single account number")
    print("=" * 50)
    
    # Generate single facesheet
    single_facesheet = generate_complete_facesheet()
    single_path = os.path.join(output_folder, "sample_facesheet.json")
    
    with open(single_path, 'w') as f:
        json.dump(single_facesheet.model_dump(exclude_none=False), f, indent=2, default=str)
    
    print(f"✅ Single facesheet saved: {single_path}")
    
    # Generate multiple facesheets
    multiple_facesheets = generate_multiple_facesheets(5)
    multiple_path = os.path.join(output_folder, "multiple_facesheets.json")
    
    facesheets_data = [fs.model_dump(exclude_none=False) for fs in multiple_facesheets]
    with open(multiple_path, 'w') as f:
        json.dump(facesheets_data, f, indent=2, default=str)
    
    print(f"✅ Multiple facesheets saved: {multiple_path}")
    
    # Generate JSON schema
    schema = FacesheetObject.model_json_schema()
    schema_path = os.path.join(output_folder, "facesheet_schema.json")
    
    with open(schema_path, 'w') as f:
        json.dump(schema, f, indent=2)
    
    print(f"✅ JSON schema saved: {schema_path}")
    
    # Generate a "realistic" incomplete example with redacted SSN
    incomplete_facesheet = generate_complete_facesheet()
    incomplete_facesheet.insurance_plan_two = None
    incomplete_facesheet.insurance_plan_three = None
    incomplete_facesheet.patient_information.business_phone = None
    incomplete_facesheet.patient_information.ssn = None  # Redacted SSN
    incomplete_facesheet.guarantor_information.ssn = None  # Redacted SSN
    incomplete_facesheet.guarantor_information.employer_address = None
    
    incomplete_path = os.path.join(output_folder, "incomplete_facesheet.json")
    with open(incomplete_path, 'w') as f:
        json.dump(incomplete_facesheet.model_dump(exclude_none=False), f, indent=2, default=str)
    
    print(f"✅ Incomplete example saved: {incomplete_path}")
    
    print("\n" + "=" * 50)
    print("📋 UPDATED SUMMARY FOR PERSON 1:")
    print("=" * 50)
    print(f"Test data generated in: {output_folder}/")
    print("Files created:")
    print("  • sample_facesheet.json - Single complete example (FLATTENED)")
    print("  • multiple_facesheets.json - Array of 5 examples") 
    print("  • incomplete_facesheet.json - Example with redacted SSNs + missing fields")
    print("  • facesheet_schema.json - Updated JSON schema")
    print("\n🔧 CHANGES MADE:")
    print("  ✅ Flattened structure - date, gender, etc. at top level")
    print("  ✅ SSN handling - null when redacted (not '***-**-****')")
    print("  ✅ Single account_number - removed duplicate from patient_information")
    print("\n💡 Use 'sample_facesheet.json' for initial testing!")

def preview_sample():
    """Show a preview of what the flattened data looks like"""
    sample = generate_complete_facesheet()
    print("📋 SAMPLE FLATTENED FACESHEET DATA PREVIEW:")
    print("=" * 60)
    
    # Show the flattened structure
    print(f"🔝 TOP LEVEL FIELDS:")
    print(f"   Date: {sample.date}")
    print(f"   Display Date: {sample.display_date}")
    print(f"   Gender: {sample.gender}")
    print(f"   DOB: {sample.date_of_birth}")
    print(f"   Account: {sample.account_number}")
    print(f"   MRN: {sample.medical_record_number}")
    print(f"   Room: {sample.room}")
    print(f"   Physician: {sample.referring_physician}")
    
    print(f"\n📋 NESTED OBJECTS:")
    patient = sample.patient_information
    insurance = sample.insurance_plan_one
    print(f"   Patient Address: {patient.address.line_one}, {patient.address.city}")
    print(f"   Patient Phone: {patient.home_phone}")
    print(f"   Patient SSN: {patient.ssn if patient.ssn else 'null (redacted)'}")
    print(f"   Insurance: {insurance.insurance_name}")
    print(f"   Policy: {insurance.policy_number}")
    
    print(f"\n📁 METADATA:")
    print(f"   Timestamp: {sample.processed_timestamp}")
    print(f"   Source: {sample.source_filename}")
    
    print("\n🔍 This is fake data - safe for testing!")
    print("🔧 Notice: Flattened structure + proper null handling!")

if __name__ == "__main__":
    print("🏥 UPDATED FACESHEET TEST DATA GENERATOR")
    print("=" * 60)
    print("🔧 UPDATED based on Person 1's feedback + C# structure review:")
    print("   1. Flattened structure (merged facesheet_text + pdf_information)")
    print("   2. Proper SSN handling (null when redacted)")
    print("   3. Single account_number (removed duplicate from patient_information)")
    print("=" * 60)
    print("This script generates realistic fake facesheet data for testing.")
    print("All data is completely fictional and safe for development/testing.")
    print("=" * 60)
    
    print("\nOptions:")
    print("1. Generate updated test files")
    print("2. Preview flattened sample data")
    print("3. Both")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice in ["1", "3"]:
        save_test_data()
    
    if choice in ["2", "3"]:
        print("\n")
        preview_sample()
    
    print("\n✅ Done! Send the UPDATED JSON files to Person 1 for testing.")
    print("💡 The structure is now flattened and SSN handling is improved!")