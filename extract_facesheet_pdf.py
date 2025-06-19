import os

def detect_file_type(hex_string):
    """Detect file type from hex data"""
    # Remove 0x prefix if present
    if hex_string.startswith("0x") or hex_string.startswith("0X"):
        hex_string = hex_string[2:]
    
    # Get first few bytes
    start = hex_string[:20].upper()
    
    if start.startswith('FFD8'):
        return 'jpg', '.jpg'
    elif start.startswith('89504E47'):
        return 'png', '.png'
    elif start.startswith('25504446'):  # %PDF
        return 'pdf', '.pdf'
    elif start.startswith('504B0304'):  # ZIP/Office docs
        return 'zip', '.zip'
    elif start.startswith('D0CF11E0'):  # Old Office docs
        return 'doc', '.doc'
    else:
        return 'unknown', '.bin'

def extract_file_from_hex(hex_string, output_path=None):
    """
    Convert a hexadecimal string to a file.
    
    Args:
        hex_string (str): Hexadecimal string representation of file data
        output_path (str): Path where the file will be saved (auto-detected if None)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Remove the '0x' prefix if present
        if hex_string.startswith("0x") or hex_string.startswith("0X"):
            hex_string = hex_string[2:]
        
        # Debug info
        print(f"📊 Hex string length: {len(hex_string)} characters")
        print(f"📊 First 50 characters: {hex_string[:50]}")
        print(f"📊 Last 50 characters: {hex_string[-50:]}")
        
        # Detect file type
        file_type, extension = detect_file_type("0x" + hex_string)
        print(f"🔍 Detected file type: {file_type.upper()}")
        
        # Set output path if not provided
        if output_path is None:
            output_path = f"extracted_file{extension}"
        
        # Remove any whitespace, newlines, or other non-hex characters
        original_length = len(hex_string)
        hex_string = ''.join(c for c in hex_string if c in '0123456789abcdefABCDEF')
        cleaned_length = len(hex_string)
        
        if original_length != cleaned_length:
            print(f"🧹 Removed {original_length - cleaned_length} non-hex characters")
        
        # Validate hex string format
        if not hex_string:
            raise ValueError("No valid hex characters found")
        
        # Handle odd length
        if len(hex_string) % 2 != 0:
            if file_type in ['jpg', 'png', 'pdf']:  # Known file types
                print(f"⚠️  Hex string has odd length ({len(hex_string)}), removing last character (likely incomplete)")
                hex_string = hex_string[:-1]
            else:
                print(f"⚠️  Hex string has odd length ({len(hex_string)}), padding with leading zero")
                hex_string = "0" + hex_string
        
        # Convert hex string to bytes
        file_bytes = bytes.fromhex(hex_string)
        
        # Validate file headers
        if file_type == 'jpg' and not file_bytes.startswith(b'\xff\xd8'):
            print("Warning: Data doesn't appear to start with JPEG header")
        elif file_type == 'pdf' and not file_bytes.startswith(b'%PDF'):
            print("Warning: Data doesn't appear to start with PDF header")
        elif file_type == 'png' and not file_bytes.startswith(b'\x89PNG'):
            print("Warning: Data doesn't appear to start with PNG header")
        
        # Write to file
        with open(output_path, "wb") as f:
            f.write(file_bytes)
        
        print(f"✅ {file_type.upper()} successfully saved to {output_path}")
        print(f"📄 File size: {len(file_bytes):,} bytes")
        
        # Try to get additional info based on file type
        if file_type in ['jpg', 'png']:
            try:
                from PIL import Image
                with Image.open(output_path) as img:
                    print(f"📐 Image dimensions: {img.size[0]} x {img.size[1]} pixels")
                    print(f"🎨 Image mode: {img.mode}")
            except ImportError:
                print("💡 Install Pillow (pip install Pillow) to see image details")
            except Exception as e:
                print(f"⚠️  Could not read image details: {e}")
        
        elif file_type == 'pdf':
            # Basic PDF validation
            try:
                with open(output_path, 'rb') as f:
                    first_line = f.readline().decode('ascii', errors='ignore')
                    if first_line.startswith('%PDF-'):
                        version = first_line.strip()
                        print(f"📋 PDF version: {version}")
                    else:
                        print("⚠️  File may not be a valid PDF")
            except Exception as e:
                print(f"⚠️  Could not read PDF details: {e}")
        
        return True
        
    except ValueError as e:
        print(f"❌ Error: Invalid hex string - {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    # Option 1: Read from file (RECOMMENDED for long hex strings)
    hex_file = "hex_data.txt"  # Create this file and paste your hex string there
    
    if os.path.exists(hex_file):
        print(f"📁 Reading hex data from {hex_file}...")
        try:
            with open(hex_file, 'r') as f:
                hex_string = f.read().strip()
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return
    else:
        # Option 2: Paste directly in code (for shorter hex strings)
        hex_string = "PASTE_YOUR_HEX_STRING_HERE"
        
        if hex_string == "PASTE_YOUR_HEX_STRING_HERE":
            print("❌ No hex data found!")
            print("Either:")
            print("1. Create a file called 'hex_data.txt' and paste your hex string there, OR")
            print("2. Replace 'PASTE_YOUR_HEX_STRING_HERE' with your hex data")
            return
    
    # Extract the file (auto-detects type and extension)
    success = extract_file_from_hex(hex_string)
    
    if success:
        print("✅ Extraction completed successfully!")
    else:
        print("❌ Extraction failed!")

if __name__ == "__main__":
    main()