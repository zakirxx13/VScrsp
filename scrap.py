import json
import os
import time
import requests
from playwright.sync_api import sync_playwright

OUTPUT = "output"
os.makedirs(OUTPUT, exist_ok=True)

# তোমার রিপোজিটরির API হ্যাশ
HASHES = [
    "cceb01a3ecb01516539b0adad38c1400",
    "08d90cecf964eb9a5f6be2e1887066fd",
    "55fdb2bedaca2de399b470fb0ce14117",
    "911e8f640af3a8892b628714d4acc133",
    "84a2451df95d2eb3d2b0d09c5fc34fb1",
    "9988b22058e87ba742a8d734e640e759",
    "be7d42854f019db42fbc22153674b888",
    "36eff4e5ed817e63c4a0859a0e11f1d5",
    "cb7ea308e7742680ea8df1aae153bc9b"
]

def get_auth():
    """কুকি ও ইউজার এজেন্ট সংগ্রহ"""
    print("🔑 Getting auth...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        page.goto("https://toffeelive.com/en/watch", wait_until="networkidle")
        
        cookies = context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        user_agent = page.evaluate("() => navigator.userAgent")
        
        browser.close()
    
    return {
        "cookies": cookie_str,
        "cookie_list": cookies,
        "user_agent": user_agent
    }

def content_api(hash_id, auth):
    """কন্টেন্ট API কল"""
    url = f"https://content-prod.services.toffeelive.com/toffee/BD/DK/web/rail/generic/editorial-dynamic/{hash_id}"
    
    try:
        r = requests.get(url, headers={
            "User-Agent": auth["user_agent"],
            "Cookie": auth["cookies"],
            "Accept": "application/json",
            "Referer": "https://toffeelive.com/",
            "Origin": "https://toffeelive.com"
        }, timeout=15)
        
        return {"success": True, "hash": hash_id, "data": r.json()}
    except Exception as e:
        return {"success": False, "hash": hash_id, "error": str(e)}

def playback_api(content_id, auth):
    """প্লেব্যাক API কল"""
    url = f"https://entitlement-prod.services.toffeelive.com/toffee/BD/DK/web/playback/{content_id}"
    
    try:
        r = requests.post(url, headers={
            "User-Agent": auth["user_agent"],
            "Cookie": auth["cookies"],
            "Accept": "application/json",
            "Referer": "https://toffeelive.com/",
            "Origin": "https://toffeelive.com"
        }, json={}, timeout=15)
        
        data = r.json()
        m3u8 = data.get("url") or data.get("playback_url") or data.get("stream_url")
        
        return {"success": True, "m3u8": m3u8, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

def extract_channels(result):
    """চ্যানেল এক্সট্রাক্ট"""
    channels = []
    if not result.get("success"):
        return channels
    
    items = result["data"].get("items") or result["data"].get("content") or []
    if not isinstance(items, list):
        return channels
    
    for item in items:
        channels.append({
            "id": item.get("id") or item.get("content_id"),
            "name": item.get("title") or item.get("name") or "Unknown",
            "logo": item.get("image") or item.get("logo") or item.get("thumbnail") or "",
            "category": item.get("category") or item.get("genre") or "General",
            "content_id": item.get("content_id") or item.get("id")
        })
    return channels

def main():
    print("🚀 Starting scraper")
    
    # Auth
    auth = get_auth()
    print(f"✅ Auth: {auth['user_agent'][:50]}...")
    
    # Content APIs
    print("\n📺 Fetching channels...")
    all_channels = []
    content_results = []
    
    for h in HASHES:
        r = content_api(h, auth)
        content_results.append(r)
        
        if r["success"]:
            chs = extract_channels(r)
            all_channels.extend(chs)
            print(f"✅ {h[:8]}: {len(chs)} channels")
        else:
            print(f"❌ {h[:8]}: Failed")
        
        time.sleep(1)
    
    # Unique channels
    seen = set()
    unique = []
    for c in all_channels:
        cid = c.get("content_id")
        if cid and cid not in seen:
            seen.add(cid)
            unique.append(c)
    
    print(f"\n📊 Total: {len(unique)} channels")
    
    # Playback APIs
    print("\n🎬 Fetching streams...")
    with_streams = []
    
    for c in unique[:15]:  # প্রথম ১৫টা
        cid = c.get("content_id")
        if cid:
            p = playback_api(cid, auth)
            
            with_streams.append({
                **c,
                "m3u8_url": p.get("m3u8") if p["success"] else None,
                "stream_data": p.get("data") if p["success"] else None,
                "error": None if p["success"] else p.get("error")
            })
            
            status = "✅" if p["success"] and p.get("m3u8") else "❌"
            print(f"{status} {c['name']}")
            time.sleep(1.5)
    
    # Save JSON
    report = {
        "scraped_at": json.dumps(str(time.time())),
        "auth": {
            "user_agent": auth["user_agent"],
            "cookies": auth["cookies"],
            "raw_cookies": [{k: c[k] for k in ["name", "value", "domain"]} for c in auth["cookie_list"]]
        },
        "channels": unique,
        "with_streams": with_streams
    }
    
    with open(f"{OUTPUT}/data.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Save M3U
    m3u = ["#EXTM3U"]
    for c in with_streams:
        if c.get("m3u8_url"):
            m3u.append(f'#EXTINF:-1 tvg-logo="{c["logo"]}" group-title="{c["category"]}",{c["name"]}')
            m3u.append(f'#EXTVLCOPT:http-user-agent={auth["user_agent"]}')
            m3u.append(f'#EXTVLCOPT:http-referrer=https://toffeelive.com/')
            m3u.append(c["m3u8_url"])
            m3u.append("")
    
    with open(f"{OUTPUT}/playlist.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(m3u))
    
    # Save Markdown
    md = f"""# Toffee Scrape Report

**Time:** {time.strftime('%Y-%m-%d %H:%M:%S')}

## Auth
- **User Agent:** `{auth["user_agent"]}`
- **Cookies:** `{auth["cookies"][:100]}...`

## Channels: {len(unique)}

| Name | Category | M3U8 |
|------|----------|------|
"""
    for c in with_streams:
        has = "✅" if c.get("m3u8_url") else "❌"
        md += f"| {c['name']} | {c['category']} | {has} |\n"
    
    with open(f"{OUTPUT}/report.md", "w", encoding="utf-8") as f:
        f.write(md)
    
    print(f"\n✅ Done! {len(with_streams)} streams")
    print(f"💾 Saved to {OUTPUT}/")

if __name__ == "__main__":
    main()
