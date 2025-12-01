import os

def get_files(path):
    extensions = {'.mp4', '.webm', '.ogg'}
    files = [f for f in os.listdir(path) if os.path.splitext(f)[1].lower() in extensions]
    files.sort()
    return files

def process_content(file_path):
    return f"/get_file/{os.path.basename(file_path)}"