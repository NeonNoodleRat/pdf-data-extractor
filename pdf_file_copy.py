import os
import shutil

# Just change this filename to whatever PDF you want to copy
filename = ""

SOURCE_FOLDER = "/home/shared/usacs_documents"
DEST_FOLDER = "documents"

# Create documents folder if it doesn't exist
os.makedirs(DEST_FOLDER, exist_ok=True)

# Copy the file
source_path = os.path.join(SOURCE_FOLDER, filename)
dest_path = os.path.join(DEST_FOLDER, filename)

shutil.copy2(source_path, dest_path)
print(f"Copied {filename} to {DEST_FOLDER}/")