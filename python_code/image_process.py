import os

def get_files(path):
    extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
    files = [f for f in os.listdir(path) if os.path.splitext(f)[1].lower() in extensions]
    files.sort()
    return files

def process_content(file_path):
    # 对于web展示，直接返回相对路径即可，浏览器会处理resize
    return f"/get_file/{os.path.basename(file_path)}"