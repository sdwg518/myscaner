# -*- coding: utf-8 -*-
"""
22端口扫描器 - 全功能单文件版
支持：Win10直接运行Flask调试 / Kivy+WebView手机应用
"""

import socket
import threading
import ipaddress
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template_string, jsonify, request
import sys
import os

# ---------- 内嵌HTML模板（完全替代templates/index.html）----------
INDEX_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>22端口扫描器</title>
    <style>
        body {
            font-family: system-ui, sans-serif;
            background: #0a0f1e;
            color: #e0e0e0;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
        }
        h1 {
            font-size: 24px;
            color: #00ff9d;
            margin-bottom: 10px;
        }
        .network-info {
            background: #1e2630;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
            word-break: break-all;
        }
        .btn {
            background: #00ff9d;
            color: #0a0f1e;
            border: none;
            padding: 14px 24px;
            font-size: 16px;
            font-weight: bold;
            border-radius: 40px;
            width: 100%;
            cursor: pointer;
            transition: 0.2s;
        }
        .btn:active {
            background: #00cc7a;
            transform: scale(0.98);
        }
        .btn:disabled {
            background: #5a5a5a;
            cursor: not-allowed;
        }
        .status {
            margin: 15px 0;
            padding: 12px;
            background: #1e2a3a;
            border-radius: 8px;
            border-left: 4px solid #00ff9d;
        }
        .result-list {
            margin-top: 20px;
        }
        .ip-item {
            background: #1e2630;
            padding: 14px 18px;
            margin-bottom: 8px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            transition: 0.1s;
        }
        .ip-item:active {
            background: #2a3542;
        }
        .ip-address {
            font-family: monospace;
            font-size: 16px;
            font-weight: 500;
        }
        .port-badge {
            background: #00ff9d20;
            color: #00ff9d;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            border: 1px solid #00ff9d;
        }
        .footer {
            margin-top: 30px;
            text-align: center;
            font-size: 12px;
            color: #808080;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 王刚老师服务器扫描器</h1>
        <div class="network-info" id="networkDisplay">
            正在检测网段...
        </div>
        
        <button class="btn" id="scanBtn" onclick="startScan()">开始扫描</button>
        
        <div class="status" id="statusArea">
            状态: 准备就绪
        </div>
        
        <div class="result-list" id="resultList">
            <!-- IP列表动态插入 -->
        </div>
        
        <div class="footer">
            点击IP地址复制到剪贴板
        </div>
    </div>

    <script>
        // 全局变量
        let pollInterval = null;

        // 页面加载时获取网络信息
        window.onload = function() {
            updateNetworkInfo();
            checkStatus(); // 获取初始状态
            // 启动定时轮询（每1秒）
            pollInterval = setInterval(checkStatus, 1000);
        };

        // 获取网络信息
        function updateNetworkInfo() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('networkDisplay').innerHTML = 
                        `🌐 当前网段: <strong>${data.network}</strong>`;
                });
        }

        // 检查扫描状态
        function checkStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    const statusEl = document.getElementById('statusArea');
                    const scanBtn = document.getElementById('scanBtn');
                    
                    if (data.status === 'idle') {
                        statusEl.innerHTML = '状态: 准备就绪';
                        scanBtn.disabled = false;
                        scanBtn.innerText = '开始扫描';
                    } else if (data.status === 'scanning') {
                        statusEl.innerHTML = '状态: ⏳ 扫描中... 请稍后';
                        scanBtn.disabled = true;
                        scanBtn.innerText = '扫描中...';
                    } else if (data.status === 'done') {
                        statusEl.innerHTML = `状态: ✅ 扫描完成 (找到 ${data.results.length} 个开放端口)`;
                        scanBtn.disabled = false;
                        scanBtn.innerText = '重新扫描';
                        // 显示结果
                        renderResults(data.results);
                    } else if (data.status === 'error') {
                        statusEl.innerHTML = '状态: ❌ 扫描出错，请重试';
                        scanBtn.disabled = false;
                        scanBtn.innerText = '重新扫描';
                    }
                });
        }

        // 渲染IP列表
        function renderResults(ips) {
            const container = document.getElementById('resultList');
            if (ips.length === 0) {
                container.innerHTML = '<div style="text-align:center; padding:30px; color:#aaa;">没有发现开放22端口的设备</div>';
                return;
            }
            
            let html = '';
            ips.forEach(ip => {
                html += `
                    <div class="ip-item" onclick="copyIP('${ip}')">
                        <span class="ip-address">${ip}</span>
                        <span class="port-badge">端口 22 开放</span>
                    </div>
                `;
            });
            container.innerHTML = html;
        }

        // 开始扫描
        function startScan() {
            fetch('/api/scan', {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'started') {
                        // 清空旧结果
                        document.getElementById('resultList').innerHTML = '';
                    } else if (data.status === 'scanning') {
                        alert('已有扫描任务进行中');
                    }
                });
        }

        // 复制IP到剪贴板
        function copyIP(ip) {
            // 创建临时输入框
            const input = document.createElement('input');
            input.value = ip;
            document.body.appendChild(input);
            input.select();
            document.execCommand('copy');
            document.body.removeChild(input);
            
            // 简单提示（可改为toast）
            alert(`已复制: ${ip}`);
        }
    </script>
</body>
</html>
'''

# ---------- 端口扫描模块 ----------
def get_local_network():
    """自动获取本机IP所在网段（/24）"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        ip_parts = local_ip.split('.')
        network = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
        return ipaddress.ip_network(network, strict=False)
    except Exception:
        # 默认C段
        return ipaddress.ip_network('192.168.1.0/24')

def check_port(ip, port=22, timeout=1.0):
    """检测单个IP端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((str(ip), port))
        sock.close()
        return result == 0
    except:
        return False

def scan_network(network=None, port=22, max_workers=50):
    """并发扫描网段内所有IP的指定端口"""
    if network is None:
        network = get_local_network()
    hosts = list(network.hosts())
    open_ips = []
    def scan_host(ip):
        if check_port(ip, port):
            open_ips.append(str(ip))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(scan_host, hosts)
    return open_ips

# ---------- Flask Web服务 ----------
app = Flask(__name__)

# 全局扫描状态
scan_status = "idle"   # idle, scanning, done, error
scan_result = []

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/api/scan', methods=['POST'])
def start_scan():
    global scan_status, scan_result
    if scan_status == "scanning":
        return jsonify({'status': 'scanning'})
    
    def scan_task():
        global scan_status, scan_result
        scan_status = "scanning"
        scan_result = []
        try:
            network = get_local_network()
            scan_result = scan_network(network)
            scan_status = "done"
        except Exception as e:
            print("扫描错误:", e)
            scan_status = "error"
    
    thread = threading.Thread(target=scan_task)
    thread.daemon = True
    thread.start()
    return jsonify({'status': 'started'})

@app.route('/api/status')
def get_status():
    global scan_status, scan_result
    network = str(get_local_network())
    return jsonify({
        'status': scan_status,
        'network': network,
        'results': scan_result
    })

@app.route('/api/reset', methods=['POST'])
def reset_scan():
    global scan_status, scan_result
    scan_status = "idle"
    scan_result = []
    return jsonify({'status': 'reset'})

def run_flask():
    """启动Flask服务（供后台线程调用）"""
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

# ---------- Kivy WebView 应用 ----------
def start_kivy_app():
    """启动Kivy GUI（仅在打包Android或桌面测试时使用）"""
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy_garden.webview import WebView

    class PortScannerApp(App):
        def build(self):
            # 启动Flask后台线程
            flask_thread = threading.Thread(target=run_flask, daemon=True)
            flask_thread.start()
            
            layout = BoxLayout()
            webview = WebView(url='http://127.0.0.1:5000')
            layout.add_widget(webview)
            return layout
    
    PortScannerApp().run()

# ---------- 程序入口 ----------
if __name__ == '__main__':
    # 判断运行环境：如果有Kivy相关参数，则启动Kivy应用，否则直接启动Flask（桌面调试）
    if len(sys.argv) > 1 and sys.argv[1] == '--kivy':
        # 手动指定用Kivy启动
        start_kivy_app()
    elif 'ANDROID_ARGUMENT' in os.environ:
        # 在Android上（通过python-for-android）会自动设置此环境变量
        start_kivy_app()
    else:
        # 默认：在Win10/Mac/Linux直接启动Flask（通过浏览器访问）
        print("🚀 启动Flask调试服务器，请访问 http://127.0.0.1:5000")
        run_flask()