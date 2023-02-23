import urllib.request
import os
from tqdm import tqdm
import requests
import re
from urllib.parse import unquote

save_dir = 'E:/REM Detection/Data'
url_path = './data/psg_audio/data_url.txt'

# rml and edf subdirectories are created only if they do not exist
rml_dir = os.path.join(save_dir, 'rml')
if not os.path.exists(rml_dir):
    os.makedirs(rml_dir)

# Create subdirectory for alternate .rml files with same name
rml_alter_dir = os.path.join(save_dir, 'rml_alter')
if not os.path.exists(rml_alter_dir):
    os.makedirs(rml_alter_dir)

# Dictionary to store the number of times each base .rml filename appears
rml_counts = {}

with open(url_path, 'r') as file:
    urls = file.readlines() 

for url in tqdm(urls):
    url = url.strip()  # Remove any leading/trailing white space
    filename = re.findall(r'fileName=(.+)', url)[0]  # Extract the file name using regex
    file_extension = os.path.splitext(filename)[1].lower()  # Extract the file extension
    if file_extension == '.edf':
        # Replace %5B and %5D with [ and ] using unquote()
        filename = unquote(filename)
        # Remove '-100507' substring from filename
        filename = filename.replace('-100507', '').replace('[', '_').replace(']', '')
        # Split the file name to extract the base name without the extension
        basename = os.path.splitext(filename)[0].split('_')[0]
        # Create a subdirectory for the file
        subdir = os.path.join(save_dir, basename)
        if not os.path.exists(subdir):
            os.makedirs(subdir)
        # Construct the file path as save_dir/basename/filename
        file_path = os.path.join(subdir, filename)
    elif file_extension == '.rml':
        # Check if the base filename already exists in the rml directory
        basename = os.path.splitext(filename)[0]
        if basename in rml_counts:
            # If the base filename already exists, move the file to the rml_alter directory
            file_path = os.path.join(rml_alter_dir, filename)
        else:
            # If the base filename does not exist, increment the count and save the file to the rml directory
            rml_counts[basename] = 1
            file_path = os.path.join(rml_dir, filename)
    else:
        file_path = os.path.join(save_dir, filename)
    urllib.request.urlretrieve(url, file_path)