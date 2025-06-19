import os

def extract_jpeg_from_hex(hex_string, output_path="extracted_image.jpg"):
    """
    Convert a hexadecimal string to a JPEG image file.
    
    Args:
        hex_string (str): Hexadecimal string representation of JPEG data
        output_path (str): Path where the JPEG file will be saved
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Remove the '0x' prefix if present
        if hex_string.startswith("0x") or hex_string.startswith("0X"):
            hex_string = hex_string[2:]
        
        # Validate hex string format
        if not all(c in '0123456789abcdefABCDEF' for c in hex_string):
            raise ValueError("Invalid hexadecimal characters found")
        
        if len(hex_string) % 2 != 0:
            raise ValueError("Hex string must have an even number of characters")
        
        # Convert hex string to bytes
        jpeg_bytes = bytes.fromhex(hex_string)
        
        # Basic JPEG validation - check if it starts with JPEG header
        if not jpeg_bytes.startswith(b'\xff\xd8'):
            print("Warning: Data doesn't appear to start with JPEG header")
        
        # Write to JPEG file
        with open(output_path, "wb") as f:
            f.write(jpeg_bytes)
        
        print(f"✅ JPEG successfully saved to {output_path}")
        print(f"📷 File size: {len(jpeg_bytes):,} bytes")
        
        # Try to get basic image info
        try:
            from PIL import Image
            with Image.open(output_path) as img:
                print(f"📐 Image dimensions: {img.size[0]} x {img.size[1]} pixels")
                print(f"🎨 Image mode: {img.mode}")
        except ImportError:
            print("💡 Install Pillow (pip install Pillow) to see image details")
        except Exception as e:
            print(f"⚠️  Could not read image details: {e}")
        
        return True
        
    except ValueError as e:
        print(f"❌ Error: Invalid hex string - {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    # PASTE YOUR HEX STRING HERE (replace the placeholder)
    hex_string = "PASTE_YOUR_HEX_STRING_HERE"
    
    # Example of what it should look like:
    # hex_string = "0xFFD8FFE000104A464946..."
    
    if hex_string == "PASTE_YOUR_HEX_STRING_HERE":
        print("❌ Please paste your hex string in the 'hex_string' variable!")
        print("Replace 'PASTE_YOUR_HEX_STRING_HERE' with your actual hex data.")
        return
    
    # Extract the image
    success = extract_jpeg_from_hex(hex_string, "extracted_image.jpg")
    
    if success:
        print("✅ Extraction completed successfully!")
    else:
        print("❌ Extraction failed!")

if __name__ == "__main__":
    main()