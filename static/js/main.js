let config = {
    page: 1,
    rows: 4,
    cols: 5,
    totalPages: 0
};

let currentLabels = {}; // 后端加载的标签数据
let currentFiles = []; // 当前页的文件列表
let activeLabel = null; // 当前选中的用于打标的标签名

const gridContainer = document.getElementById('gridContainer');
const labelList = document.getElementById('labelList');

// 初始化
window.onload = function() {
    loadData();
    setupEvents();
};

function setupEvents() {
    // 布局调整
    document.getElementById('inputRows').onchange = (e) => { config.rows = e.target.value; renderGrid(); };
    document.getElementById('inputCols').onchange = (e) => { config.cols = e.target.value; renderGrid(); };
    
    // 翻页输入框 (回车跳转)
    document.getElementById('inputPage').onkeydown = (e) => {
        if(e.key === 'Enter') {
            let p = parseInt(e.target.value);
            if(p >= 1 && p <= config.totalPages) {
                config.page = p;
                loadData();
            }
        }
    };

    // 键盘翻页
    document.addEventListener('keydown', (e) => {
        // 避免在输入框打字时触发
        if(e.target.tagName === 'INPUT') return;

        if (e.key === 'a' || e.key === 'A') {
            if (config.page > 1) { config.page--; loadData(); }
        } else if (e.key === 'd' || e.key === 'D') {
            if (config.page < config.totalPages) { config.page++; loadData(); }
        }
    });

    // 新建标签
    document.getElementById('btnNewTag').onclick = createLabel;
}

// 加载数据
function loadData() {
    fetch(`/get_data?page=${config.page}&rows=${config.rows}&cols=${config.cols}`)
        .then(res => res.json())
        .then(data => {
            currentFiles = data.files;
            config.page = data.page;
            config.totalPages = data.total_pages;
            currentLabels = data.labels;
            
            // 更新底部UI
            document.getElementById('inputPage').value = config.page;
            document.getElementById('totalPages').innerText = config.totalPages;
            
            renderLabels();
            renderGrid();
        });
}

// 渲染网格
function renderGrid() {
    gridContainer.innerHTML = '';
    // 设置CSS Grid
    gridContainer.style.gridTemplateColumns = `repeat(${config.cols}, 1fr)`;
    gridContainer.style.gridTemplateRows = `repeat(${config.rows}, 1fr)`;

    // 如果文件数少于格子数，可以处理一下，或者直接留白。这里按行列截断显示
    let limit = config.rows * config.cols;
    let displayFiles = currentFiles.slice(0, limit);

    displayFiles.forEach(file => {
        let item = document.createElement('div');
        item.className = 'grid-item';
        item.onclick = () => toggleFileLabel(file.filename);

        // 内容区域
        let contentDiv = document.createElement('div');
        contentDiv.className = 'grid-content';
        
        if (DATA_TYPE === 'i') {
            contentDiv.innerHTML = `<img src="${file.content}">`;
        } else if (DATA_TYPE === 'v') {
            contentDiv.innerHTML = `<video src="${file.content}" controls></video>`;
        } else {
            contentDiv.innerHTML = `<div class="text-content">${file.content}</div>`;
        }

        // 文件名
        let nameDiv = document.createElement('div');
        nameDiv.className = 'filename';
        nameDiv.innerText = file.filename;

        item.appendChild(contentDiv);
        item.appendChild(nameDiv);

        // 渲染已有的标签框
        updateItemBorder(item, file.filename);

        gridContainer.appendChild(item);
    });
}

// 根据标签给Item画框
function updateItemBorder(domElement, filename) {
    // 找出该文件属于哪些标签
    let fileLabels = [];
    for (let lname in currentLabels) {
        if (currentLabels[lname].files.includes(filename)) {
            fileLabels.push(currentLabels[lname].color);
        }
    }

    if (fileLabels.length > 0) {
        // 如果有多个标签，这里简单的展示最外层一个，或者可以用 box-shadow 多重展示
        // 这里做一个多重边框效果
        let shadow = '';
        fileLabels.forEach((color, index) => {
            let width = (index + 1) * 3;
            shadow += `0 0 0 ${width}px ${color},`;
        });
        domElement.style.boxShadow = shadow.slice(0, -1);
        // 如果需要内部边框，可以用 border
        domElement.style.border = `2px solid ${fileLabels[0]}`; 
    } else {
        domElement.style.boxShadow = 'none';
        domElement.style.border = '1px solid #ddd';
    }
}

// 渲染右侧标签列表
function renderLabels() {
    labelList.innerHTML = '';
    for (let name in currentLabels) {
        let l = currentLabels[name];
        let div = document.createElement('div');
        div.className = `label-item ${activeLabel === name ? 'active' : ''}`;
        
        div.innerHTML = `
            <div class="label-color" style="background:${l.color}"></div>
            <div class="label-name" onclick="selectLabel('${name}')">${name}</div>
            <div class="label-actions">
                <span onclick="renameLabel('${name}')">改</span>
                <span class="del" onclick="deleteLabel('${name}')">删</span>
            </div>
        `;
        labelList.appendChild(div);
    }
}

function selectLabel(name) {
    if (activeLabel === name) {
        activeLabel = null; // 取消选中
        document.getElementById('activeLabelDisplay').innerText = "无";
        document.getElementById('activeLabelDisplay').style.color = "gray";
    } else {
        activeLabel = name;
        document.getElementById('activeLabelDisplay').innerText = name;
        document.getElementById('activeLabelDisplay').style.color = currentLabels[name].color;
    }
    renderLabels();
}

// 颜色生成
function getRandomColor() {
    var letters = '0123456789ABCDEF';
    var color = '#';
    for (var i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

// API交互：新建标签
function createLabel() {
    let name = prompt("请输入新标签名称:");
    if (!name) return;
    if (currentLabels[name]) { alert("标签已存在"); return; }
    
    let color = getRandomColor();
    fetch('/manage_label', {
        method: 'POST',
        body: JSON.stringify({ action: 'create', name: name, color: color })
    }).then(() => loadData());
}

// API交互：重命名
function renameLabel(oldName) {
    let newName = prompt("请输入新名称:", oldName);
    if (!newName || newName === oldName) return;
    
    fetch('/manage_label', {
        method: 'POST',
        body: JSON.stringify({ action: 'rename', name: oldName, new_name: newName })
    }).then(() => {
        if (activeLabel === oldName) activeLabel = newName;
        loadData();
    });
}

// API交互：删除
function deleteLabel(name) {
    if (!confirm(`确定删除标签 ${name} 吗？`)) return;
    fetch('/manage_label', {
        method: 'POST',
        body: JSON.stringify({ action: 'delete', name: name })
    }).then(() => {
        if (activeLabel === name) activeLabel = null;
        loadData();
    });
}

// API交互：打标/取消打标
function toggleFileLabel(filename) {
    if (!activeLabel) {
        alert("请先在右侧选择一个标签！");
        return;
    }
    
    fetch('/update_tag', {
        method: 'POST',
        body: JSON.stringify({ label: activeLabel, filename: filename })
    }).then(() => {
        // 前端手动更新一下状态，避免全量刷新闪烁
        let fileList = currentLabels[activeLabel].files;
        let idx = fileList.indexOf(filename);
        if (idx > -1) fileList.splice(idx, 1);
        else fileList.push(filename);
        
        renderGrid(); // 重新渲染边框
    });
}