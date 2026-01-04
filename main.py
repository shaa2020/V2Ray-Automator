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

TIMEOUT = 1.5  # Lower timeout = Only high quality servers
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
            # Categorize by Speed
            if latency < 200: icon = "🚀"
            elif latency < 500: icon = "🟢"
            else: icon = "🟡"
            
            clean_name = f"{icon}_Ping_{latency}ms"
            final_link = link.split('#')[0] + "#" + clean_name
            return {"link": final_link, "latency": latency, "name": clean_name}
        return None
    except: return None

def send_telegram_premium(valid_servers):
    if not TG_TOKEN or not TG_CHAT_ID: return
    
    # Sort and Count
    valid_servers.sort(key=lambda x: x['latency'])
    fast = sum(1 for s in valid_servers if s['latency'] < 200)
    medium = sum(1 for s in valid_servers if s['latency'] < 500)
    
    date_str = datetime.now(pytz.utc).strftime("%H:%M UTC")
    
    # 1. Send Beautiful Status Report
    msg = (
        f"💎 <b>VIP V2Ray Update</b> ({date_str})\n\n"
        f"⚡ <b>Total Online:</b> {len(valid_servers)}\n"
        f"🚀 <b>Ultra Fast:</b> {fast}\n"
        f"🟢 <b>Stable:</b> {medium}\n\n"
        f"<i>Full list uploaded below 👇</i>"
    )
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"})

    # 2. Upload the File Directly (Premium Feature!)
    # Users can click the file to import instantly
    file_content = "\n".join([x['link'] for x in valid_servers])
    files = {'document': ('vless_premium.txt', file_content)}
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendDocument", data={"chat_id": TG_CHAT_ID, "caption": "📂 <b>Import this file directly!</b>", "parse_mode": "HTML"}, files=files)

def main():
    raw = fetch_links()
    if not raw: return

    valid = []
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        results = executor.map(check_server, raw)
        for res in results:
            if res: valid.append(res)
    
    # Save standard files for GitHub URL
    links = [x['link'] for x in valid]
    with open("vless.txt", "w") as f: f.write("\n".join(links))
    encoded = base64.b64encode("\n".join(links).encode()).decode()
    with open("sub.txt", "w") as f: f.write(encoded)
    
    # Trigger Premium Telegram Alert
    send_telegram_premium(valid)

if __name__ == "__main__":
    main()
