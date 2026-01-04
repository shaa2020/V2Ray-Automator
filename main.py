import requests
import base64
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor

# --- SOURCES ---
# You can add more URLs here later
SOURCES = [
    "https://raw.githubusercontent.com/barry-far/V2ray-config/main/Splitted-By-Protocol/vless.txt",
    "https://raw.githubusercontent.com/MatinGhanbari/v2ray-configs/main/Splitted-By-Protocol/vless.txt",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt"
]

TIMEOUT = 2  # Seconds to wait for a connection
MAX_THREADS = 40  # Speed of scanning

def fetch_links():
    links = set()
    print("🚀 Fetching links...")
    try:
        for url in SOURCES:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                content = resp.text.strip()
                # Attempt to decode if it looks like Base64
                if " " not in content and len(content) > 200:
                    try:
                        content = base64.b64decode(content).decode('utf-8', errors='ignore')
                    except:
                        pass
                
                for line in content.splitlines():
                    if line.strip().startswith("vless://"):
                        links.add(line.strip())
    except Exception as e:
        print(f"Error fetching links: {e}")
        
    print(f"✅ Found {len(links)} raw links.")
    return list(links)

def check_server(link):
    try:
        # Regex to extract host and port
        match = re.search(r'vless://[^@]+@([^:]+):(\d+)', link)
        if not match: return None
        
        host = match.group(1)
        port = int(match.group(2))
        
        # Override if host/sni params exist
        if 'sni=' in link:
            host = link.split('sni=')[1].split('&')[0]
        elif 'host=' in link:
            host = link.split('host=')[1].split('&')[0]

        # TCP Ping Test
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        start = time.time()
        result = sock.connect_ex((host, port))
        sock.close()
        end = time.time()
        
        if result == 0:
            latency = int((end - start) * 1000)
            clean_name = f"⚡_Live_{latency}ms"
            # Replace the old name after # with new name
            return link.split('#')[0] + "#" + clean_name
        return None
    except:
        return None

def main():
    raw_links = fetch_links()
    if not raw_links:
        return

    print(f"🔍 Testing {len(raw_links)} links...")
    valid_links = []
    
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        results = executor.map(check_server, raw_links)
        for res in results:
            if res:
                valid_links.append(res)
    
    print(f"🎉 Found {len(valid_links)} working servers.")
    
    # Save VLESS Text
    with open("vless.txt", "w") as f:
        f.write("\n".join(valid_links))
        
    # Save Subscription (Base64)
    encoded = base64.b64encode("\n".join(valid_links).encode()).decode()
    with open("sub.txt", "w") as f:
        f.write(encoded)

if __name__ == "__main__":
    main()
