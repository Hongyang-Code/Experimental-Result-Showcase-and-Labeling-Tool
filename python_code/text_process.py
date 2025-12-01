import os

def get_files(path):
    extensions = {'.txt', '.log', '.csv'}
    files = [f for f in os.listdir(path) if os.path.splitext(f)[1].lower() in extensions]
    files.sort()
    return files

def process_content(file_path):
    # 文本需要读取内容
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return "Error reading file."