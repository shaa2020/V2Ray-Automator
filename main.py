import requests
import base64
import socket
import time
import os
import pytz
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs

# --- CONFIGURATION ---
SOURCES = [
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/vless.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/Splitted-By-Protocol/vless.txt",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt"
]

TIMEOUT = 1.5  # Stricter timeout for "Premium" quality
MAX_THREADS = 40
TG_TOKEN = os.getenv("TG_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def fetch_links():
    links = set()
    print("🚀 Fetching links...")
    session = requests.Session()
    for url in SOURCES:
        try:
            resp = session.get(url, timeout=10)
            if resp.status_code == 200:
                content = resp.text.strip()
                if " " not in content and len(content) > 200:
                    try: content = base64.b64decode(content).decode('utf-8', errors='ignore')
                    except: pass
                for line in content.splitlines():
                    if line.strip().startswith("vless://"): links.add(line.strip())
        except: pass
    return list(links)

def check_server(link):
    try:
        parsed = urlparse(link)
        host = parsed.hostname
        port = parsed.port
        params = parse_qs(parsed.query)
        check_host = host
        if 'sni' in params and params['sni'][0]: check_host = params['sni'][0]
        elif 'host' in params and params['host'][0]: check_host = params['host'][0]

        if not check_host or not port: return None

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        start = time.time()
        result = sock.connect_ex((check_host, int(port)))
        sock.close()
        end = time.time()
        
        if result == 0:
            latency = int((end - start) * 1000)
            # Speed Categories
            if latency < 200: icon = "🚀"
            elif latency < 500: icon = "🟢"
            else: icon = "🟡"
            
            clean_name = f"{icon}_Ping_{latency}ms"
            final_link = link.split('#')[0] + "#" + clean_name
            return {"link": final_link, "latency": latency, "name": clean_name}
        return None
    except: return None

def generate_dashboard(valid_servers):
    valid_servers.sort(key=lambda x: x['latency'])
    date_str = datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>V2Ray Premium Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background: #0f0f0f; color: #e0e0e0; padding: 20px; }}
            .card {{ background: #1e1e1e; border: 1px solid #333; border-radius: 8px; padding: 15px; margin-bottom: 15px; }}
            .status {{ color: #4caf50; font-weight: bold; }}
            .copy-btn {{ background: #2196F3; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; }}
            input {{ background: #2c2c2c; border: 1px solid #444; color: #fff; padding: 5px; width: 60%; }}
        </style>
    </head>
    <body>
        <h1 style="text-align:center; color: #2196F3;">💎 Premium Servers: {len(valid_servers)}</h1>
        <p style="text-align:center">Last Update: {date_str}</p>
    """
    
    for i, s in enumerate(valid_servers[:50]): 
        qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={requests.utils.quote(s['link'])}"
        html += f"""
        <div class="card">
            <div style="float:right"><img src="{qr_api}"></div>
            <h3>{s['name']}</h3>
            <p>Ping: <span class="status">{s['latency']}ms</span></p>
            <input type="text" value="{s['link']}" id="link_{i}">
            <button class="copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('link_{i}').value)">Copy</button>
        </div>
        """
    html += "</body></html>"
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

def send_telegram_premium(valid_servers):
    if not TG_TOKEN or not TG_CHAT_ID: return
    
    valid_servers.sort(key=lambda x: x['latency'])
    fast = sum(1 for s in valid_servers if s['latency'] < 200)
    
    date_str = datetime.now(pytz.utc).strftime("%H:%M UTC")
    
    # 1. Send Report
    msg = (
        f"💎 <b>VIP V2Ray Update</b> ({date_str})\n\n"
        f"⚡ <b>Total Online:</b> {len(valid_servers)}\n"
        f"🚀 <b>Ultra Fast:</b> {fast}\n\n"
        f"<i>📂 Download the file below for 1-click import!</i>"
    )
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"})

    # 2. Upload File (The Premium Feature)
    file_content = "\n".join([x['link'] for x in valid_servers])
    files = {'document': ('vless_premium.txt', file_content)}
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendDocument", data={"chat_id": TG_CHAT_ID, "caption": "🚀 <b>Premium List</b>"}, files=files)

def main():
    raw = fetch_links()
    if not raw: return

    valid = []
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        results = executor.map(check_server, raw)
        for res in results:
            if res: valid.append(res)
    
    # Save standard files
    links = [x['link'] for x in valid]
    with open("vless.txt", "w") as f: f.write("\n".join(links))
    encoded = base64.b64encode("\n".join(links).encode()).decode()
    with open("sub.txt", "w") as f: f.write(encoded)
    
    # Run Premium Features
    generate_dashboard(valid)
    send_telegram_premium(valid)

if __name__ == "__main__":
    main()
