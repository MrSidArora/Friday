import os

# Settings
root_dir = "."  # Or use "." if running from the same level
output_file = "compiled_friday_dump.txt"
valid_extensions = {'.py', '.json', '.txt', '.md', '.bat', '.html', '.css', '.js'}
excluded_dirs = {'__pycache__', 'node_modules', 'logs', 'assets'}

with open(output_file, 'w', encoding='utf-8') as outfile:
    for foldername, subfolders, filenames in os.walk(root_dir):
        # Skip excluded folders
        if any(excluded in foldername for excluded in excluded_dirs):
            continue

        for filename in filenames:
            ext = os.path.splitext(filename)[1]
            if ext.lower() in valid_extensions:
                file_path = os.path.join(foldername, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                    outfile.write(f"\n======== File: {filename} ========\n")
                    outfile.write(f"Path: {os.path.abspath(file_path)}\n\n")
                    outfile.write(content)
                    outfile.write("\n\n-------------------------------------\n")
                except Exception as e:
                    print(f"[WARN] Could not read {file_path}: {e}")
