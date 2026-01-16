import web
import sys
import os
import json
import time # 引入时间库用于缓存控制
from python_code import image_process, video_process, text_process

# === 配置: 定义配置文件名 ===
CONFIG_FILE = 'templates/server_config.json'

# === 内存缓存类 (新加功能) ===
# 用于存储文件列表和标签，避免每次请求都读硬盘
class DataCache:
    def __init__(self):
        self.files_list = None
        self.labels_data = None
        self.last_reload_time = 0

    def get_files(self, processor, path):
        # 如果缓存为空，或者你想强制刷新(比如每隔几分钟)，可以在这里加逻辑
        # 目前逻辑：只有第一次请求时扫描硬盘，之后都用内存里的数据
        if self.files_list is None:
            print("Scanning files from disk...") # 调试用
            try:
                self.files_list = processor.get_files(path)
            except Exception as e:
                print(f"Error scanning files: {e}")
                self.files_list = []
        return self.files_list

    def get_labels(self, label_path):
        # 标签可能变动比较频繁（比如新建标签），这里我们做个简单的策略：
        # 每次读取前判断内存里有没有，如果没有则读取。
        # 注意：每次修改标签(ManageLabel/UpdateTag)后，我们需要手动清空这个缓存
        if self.labels_data is None:
            # print("Loading labels from disk...") 
            labels = {}
            if not os.path.exists(label_path):
                try: os.makedirs(label_path)
                except: pass
            
            if os.path.exists(label_path):
                for filename in os.listdir(label_path):
                    if not filename.endswith('.txt'): continue
                    label_name = os.path.splitext(filename)[0]
                    file_path = os.path.join(label_path, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.read().splitlines()
                            color = lines[0] if lines else "#FF0000"
                            files = lines[1:] if len(lines) > 1 else []
                            labels[label_name] = {"color": color, "files": files}
                    except: pass
            self.labels_data = labels
        return self.labels_data

    def invalidate_labels(self):
        # 当标签发生改变时调用，强制下次读取硬盘
        self.labels_data = None

# 初始化全局缓存对象
data_cache = DataCache()

# === 基础配置加载 ===
def load_config():
    default_config = {'DATA_TYPE': 'i', 'DATA_PATH': '', 'LABEL_PATH': ''}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return default_config

config_data = load_config()

urls = (
    '/', 'Index',
    '/get_data', 'GetData',
    '/get_file/(.*)', 'GetFile',
    '/manage_label', 'ManageLabel',
    '/update_tag', 'UpdateTag'
)

# === 关键修改：关闭自动重载 (autoreload=False) ===
# 这样全局变量 data_cache 才能在内存中持久保存
app = web.application(urls, globals(), autoreload=False)
render = web.template.render('templates/')

# 辅助函数：获取处理器
def get_processor():
    DATA_TYPE = config_data.get('DATA_TYPE', 'i')
    if DATA_TYPE == 'i': return image_process
    if DATA_TYPE == 'v': return video_process
    if DATA_TYPE == 't': return text_process
    return image_process

class Index:
    def GET(self):
        DATA_TYPE = config_data.get('DATA_TYPE', 'i')
        return render.index(DATA_TYPE)

class GetFile:
    def GET(self, filename):
        DATA_PATH = config_data.get('DATA_PATH', '')
        file_path = os.path.join(DATA_PATH, filename)
        
        if os.path.exists(file_path):
            # === 优化：添加浏览器缓存头 ===
            # 告诉浏览器：这张图片在 1 小时内(3600秒)不需要再问服务器要，直接用本地缓存
            web.header('Cache-Control', 'public, max-age=3600')
            # 也可以根据文件类型设置 Content-Type，虽然浏览器通常能自动识别
            # ext = os.path.splitext(filename)[1].lower()
            # if ext in ['.jpg', '.jpeg']: web.header('Content-Type', 'image/jpeg')
            
            with open(file_path, 'rb') as f:
                return f.read()
        else:
            return web.notfound()

class GetData:
    def GET(self):
        web.header('Content-Type', 'application/json')
        user_data = web.input(page=1, rows=4, cols=5)
        page = int(user_data.page)
        rows = int(user_data.rows)
        cols = int(user_data.cols)
        per_page = rows * cols

        DATA_PATH = config_data.get('DATA_PATH', '')
        LABEL_PATH = config_data.get('LABEL_PATH', '')

        if not DATA_PATH:
            return json.dumps({"files": [], "page": 1, "total_pages": 0, "labels": {}})

        processor = get_processor()
        
        # === 优化：使用内存缓存获取文件列表 ===
        # 不再每次都 listdir
        all_files = data_cache.get_files(processor, DATA_PATH)
        
        total_files = len(all_files)
        total_pages = (total_files + per_page - 1) // per_page
        
        if page < 1: page = 1
        if page > total_pages: page = total_pages if total_pages > 0 else 1

        start = (page - 1) * per_page
        end = start + per_page
        current_files = all_files[start:end]

        file_data = []
        for f in current_files:
            full_path = os.path.join(DATA_PATH, f)
            content = processor.process_content(full_path)
            file_data.append({
                "filename": f,
                "content": content
            })

        # === 优化：使用内存缓存获取标签 ===
        labels = data_cache.get_labels(LABEL_PATH)

        return json.dumps({
            "files": file_data,
            "page": page,
            "total_pages": total_pages,
            "labels": labels
        })

class ManageLabel:
    def POST(self):
        LABEL_PATH = config_data.get('LABEL_PATH', '')
        data = json.loads(web.data())
        action = data.get('action')
        name = data.get('name')
        new_name = data.get('new_name', '')
        color = data.get('color', '#000000')

        if not os.path.exists(LABEL_PATH):
            os.makedirs(LABEL_PATH)

        if action == 'create':
            path = os.path.join(LABEL_PATH, f"{name}.txt")
            if not os.path.exists(path):
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(f"{color}\n")
        
        elif action == 'rename':
            old_path = os.path.join(LABEL_PATH, f"{name}.txt")
            new_path = os.path.join(LABEL_PATH, f"{new_name}.txt")
            if os.path.exists(old_path):
                os.rename(old_path, new_path)

        elif action == 'delete':
            path = os.path.join(LABEL_PATH, f"{name}.txt")
            if os.path.exists(path):
                os.remove(path)
        
        # === 关键：修改数据后，标记缓存失效，下次读取时会重新扫描硬盘 ===
        data_cache.invalidate_labels()
        
        return "success"

class UpdateTag:
    def POST(self):
        LABEL_PATH = config_data.get('LABEL_PATH', '')
        data = json.loads(web.data())
        label_name = data.get('label')
        filename = data.get('filename')
        
        file_path = os.path.join(LABEL_PATH, f"{label_name}.txt")
        if not os.path.exists(file_path): return "error"

        # 这里为了确保数据一致性，建议读一次文件（或者读缓存然后回写）
        # 简单起见，读文件修改
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        
        header_color = lines[0]
        files = set(lines[1:])

        if filename in files:
            files.remove(filename)
        else:
            files.add(filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"{header_color}\n")
            for fn in files:
                f.write(f"{fn}\n")
        
        # === 关键：数据变了，清空缓存 ===
        data_cache.invalidate_labels()
        
        return "success"

if __name__ == "__main__":
    if len(sys.argv) < 5: 
        print("Usage: python app.py [i/v/t] [data_path] [label_path] [port]")
    
    _type = sys.argv[1] if len(sys.argv) > 1 else 'i'
    _dpath = sys.argv[2] if len(sys.argv) > 2 else './exp_result'
    _lpath = sys.argv[3] if len(sys.argv) > 3 else './label'
    _port = sys.argv[4] if len(sys.argv) > 4 else '8080'

    print(f"Saving config to {CONFIG_FILE}...")
    config_to_save = {
        'DATA_TYPE': _type,
        'DATA_PATH': _dpath,
        'LABEL_PATH': _lpath
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_to_save, f)

    config_data.update(config_to_save)
    
    print(f"Data Type: {_type}")
    print(f"Data Path: {_dpath}")
    print(f"Label Path: {_lpath}")
    print(f"Port: {_port}")
    print("-" * 30)
    print("Optimization enabled: Autoreload OFF, Cache ON")
    print("-" * 30)
    
    sys.argv[1] = _port
    sys.argv[2:] = []
    
    app.run()
