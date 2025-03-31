import os
import magic
from datetime import datetime

# Current time in the standard format
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(current_time)


def add_extension_if_missing(file_path, extension):
    # Add the extension to the file name if it's missing
    if not file_path.endswith(extension):
        new_file_path = file_path + extension
        os.rename(file_path, new_file_path)  # Rename the file to add the extension
        # print(f"Renamed {file_path} to {new_file_path}")
    else:
        # print(f"File {file_path} already has the correct extension.")
        pass

        

def get_file_type(file_path):
    try:
        mime = magic.Magic(mime=True)
        return mime.from_file(file_path)
    except Exception as e:
        print(f"Error detecting file type for {file_path}: {e}")
        return None

downloads_folder = 'Downloads'

i = 0
types_set = {}
for root, dirs, files in os.walk(downloads_folder):
    
    # Skip files not in folders (e.g. .part)
    if root == downloads_folder:
        continue
    
    for file in files:
        file_path = os.path.join(root, file)
        file_type = get_file_type(file_path)
        # print(f"File: {file_path}, Type: {file_type}")
        if file_type in types_set: 
            types_set[file_type] +=1
        else :
            types_set[file_type] = 1
        if file_type not in ['application/pdf', 'application/epub+zip'] :  # Check if the file is a text file
            print(dirs, file, file_type)
        else:
            if file_type == 'application/pdf':
                add_extension_if_missing(file_path, '.pdf')
                
            elif file_type == 'application/epub+zip':
                add_extension_if_missing(file_path, '.epub')
            
            i+=1
        
            
print(f'Total DOwnloaded?(maybe incomplete but created) books: {i}')
print(types_set)

