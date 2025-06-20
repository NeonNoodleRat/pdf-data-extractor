import os
import shutil

# # Just change this filename to whatever PDF you want to copy
# filename = ""

# SOURCE_FOLDER = "/home/shared/facesheets"
# #SOURCE_FOLDER = "/home/shared/usacs_documents"
# DEST_FOLDER = "documents"

# # Create documents folder if it doesn't exist
# os.makedirs(DEST_FOLDER, exist_ok=True)

# # Copy the file
# source_path = os.path.join(SOURCE_FOLDER, filename)
# dest_path = os.path.join(DEST_FOLDER, filename)

# shutil.copy2(source_path, dest_path)
# print(f"Copied {filename} to {DEST_FOLDER}/")

source_dir = '/home/shared/facesheets/'
dest_dir = '/home/eenis@ins.healthcareintel.com/development/pdf-data-extractor/'

# Filter for only .pdf files and ignore hidden/system files
files = [f for f in os.listdir(source_dir)
         if f.lower().endswith('.pdf') and not f.startswith('.') and os.path.isfile(os.path.join(source_dir, f))]
files.sort()

if files:
    first_file = files[0]
    source_path = os.path.join(source_dir, first_file)
    dest_path = os.path.join(dest_dir, first_file)
    shutil.copy2(source_path, dest_path)
    print(f"Copied: {first_file}")
else:
    print("No PDF files found in source directory.")