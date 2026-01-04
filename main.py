import requests
import base64
import re
import socket
import time
import os
import pytz
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs

# --- SOURCES ---
SOURCES = [
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/vless.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/Splitted-By-Protocol/vless.txt",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt"
]

# --- SETTINGS ---
TIMEOUT = 2  # Connection timeout (Seconds)
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
                    try:
                        content = base64.b64decode(content).decode('utf-8', errors='ignore')
                    except: pass
                
                for line in content.splitlines():
                    if line.strip().startswith("vless://"):
                        links.add(line.strip())
        except: pass
    print(f"✅ Found {len(links)} raw links.")
    return list(links)

def check_server(link):
    try:
        parsed = urlparse(link)
        host = parsed.hostname
        port = parsed.port
        params = parse_qs(parsed.query)
        
        # Check SNI/Host Override
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
            clean_name = f"⚡_Live_{latency}ms"
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
        <title>V2Ray Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }}
            .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 15px; margin-bottom: 15px; }}
            .status {{ color: #3fb950; font-weight: bold; }}
            .copy-btn {{ background: #238636; color: white; border: none; padding: 5px 10px; cursor: pointer; }}
            input {{ background: #0d1117; border: 1px solid #30363d; color: #fff; width: 60%; }}
        </style>
    </head>
    <body>
        <h1 style="text-align:center; color: #58a6ff;">🚀 Active Servers: {len(valid_servers)}</h1>
        <p style="text-align:center">Last Update: {date_str}</p>
    """
    
    for i, s in enumerate(valid_servers[:50]): # Show top 50
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

def send_telegram(count):
    if not TG_TOKEN or not TG_CHAT_ID: return
    msg = f"✅ <b>V2Ray Update</b>\n\n⚡ Found {count} working servers.\n🔗 Dashboard updated."
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"})

def main():
    raw = fetch_links()
    if not raw: return

    print(f"🔍 Testing {len(raw)} links...")
    valid = []
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        results = executor.map(check_server, raw)
        for res in results:
            if res: valid.append(res)
            
    print(f"🎉 Success! {len(valid)} alive.")
    
    links = [x['link'] for x in valid]
    with open("vless.txt", "w") as f: f.write("\n".join(links))
    
    encoded = base64.b64encode("\n".join(links).encode()).decode()
    with open("sub.txt", "w") as f: f.write(encoded)
    
    generate_dashboard(valid)
    send_telegram(len(valid))

if __name__ == "__main__":
    main()
