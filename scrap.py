import json
import os
import time
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

OUTPUT = "output"
os.makedirs(OUTPUT, exist_ok=True)

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
    """Toffee page থেকে cookie এবং user-agent সংগ্রহ"""

    print("🔑 Getting auth...")

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            viewport={"width": 1366, "height": 768}
        )

        page = context.new_page()

        try:
            print("🌐 Opening Toffee...")

            page.goto(
                "https://toffeelive.com/en/watch",
                wait_until="domcontentloaded",
                timeout=60000
            )

            print("✅ Page loaded")

            # JS/app initialise হওয়ার জন্য একটু সময়
            page.wait_for_timeout(5000)

            cookies = context.cookies()

            user_agent = page.evaluate(
                "() => navigator.userAgent"
            )

            print(f"🍪 Cookies collected: {len(cookies)}")
            print(f"🧭 User-Agent: {user_agent[:80]}...")

            cookie_str = "; ".join(
                f"{c['name']}={c['value']}"
                for c in cookies
            )

            return {
                "cookies": cookie_str,
                "cookie_list": cookies,
                "user_agent": user_agent
            }

        except PlaywrightTimeoutError as e:

            print(f"❌ Page timeout: {e}")

            try:
                page.screenshot(
                    path=f"{OUTPUT}/auth_timeout.png",
                    full_page=True
                )
                print("📸 Debug screenshot saved")
            except Exception:
                pass

            return None

        except Exception as e:

            print(f"❌ Auth error: {e}")

            try:
                page.screenshot(
                    path=f"{OUTPUT}/auth_error.png",
                    full_page=True
                )
            except Exception:
                pass

            return None

        finally:
            browser.close()


def content_api(hash_id, auth):
    """Content API কল"""

    url = (
        "https://content-prod.services.toffeelive.com/"
        f"toffee/BD/DK/web/rail/generic/editorial-dynamic/{hash_id}"
    )

    headers = {
        "User-Agent": auth["user_agent"],
        "Cookie": auth["cookies"],
        "Accept": "application/json",
        "Referer": "https://toffeelive.com/",
        "Origin": "https://toffeelive.com"
    }

    try:

        r = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        print(
            f"   HTTP {r.status_code} | "
            f"{hash_id[:8]}"
        )

        r.raise_for_status()

        data = r.json()

        return {
            "success": True,
            "hash": hash_id,
            "data": data
        }

    except Exception as e:

        return {
            "success": False,
            "hash": hash_id,
            "error": str(e)
        }


def playback_api(content_id, auth):
    """Playback API কল"""

    url = (
        "https://entitlement-prod.services.toffeelive.com/"
        f"toffee/BD/DK/web/playback/{content_id}"
    )

    headers = {
        "User-Agent": auth["user_agent"],
        "Cookie": auth["cookies"],
        "Accept": "application/json",
        "Referer": "https://toffeelive.com/",
        "Origin": "https://toffeelive.com"
    }

    try:

        r = requests.post(
            url,
            headers=headers,
            json={},
            timeout=30
        )

        r.raise_for_status()

        data = r.json()

        m3u8 = (
            data.get("url")
            or data.get("playback_url")
            or data.get("stream_url")
        )

        return {
            "success": True,
            "m3u8": m3u8,
            "data": data
        }

    except Exception as e:

        return {
            "success": False,
            "m3u8": None,
            "data": None,
            "error": str(e)
        }


def extract_channels(result):
    """API response থেকে channel extract"""

    channels = []

    if not result.get("success"):
        return channels

    data = result.get("data", {})

    if not isinstance(data, dict):
        return channels

    items = (
        data.get("items")
        or data.get("content")
        or data.get("contents")
        or []
    )

    if not isinstance(items, list):
        return channels

    for item in items:

        if not isinstance(item, dict):
            continue

        content_id = (
            item.get("content_id")
            or item.get("id")
        )

        if not content_id:
            continue

        channel = {
            "id": item.get("id") or content_id,

            "name": (
                item.get("title")
                or item.get("name")
                or "Unknown"
            ),

            "logo": (
                item.get("image")
                or item.get("logo")
                or item.get("thumbnail")
                or ""
            ),

            "category": (
                item.get("category")
                or item.get("genre")
                or "General"
            ),

            "content_id": content_id
        }

        channels.append(channel)

    return channels


def save_json(filename, data):

    path = os.path.join(OUTPUT, filename)

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"💾 Saved: {path}")


def main():

    print("🚀 Starting scraper")
    print("=" * 60)

    # --------------------------------------------------
    # AUTH
    # --------------------------------------------------

    auth = get_auth()

    if not auth:

        print("❌ Could not get authentication")
        print("🛑 Scraper stopped")

        return

    print(
        f"✅ Auth OK: "
        f"{auth['user_agent'][:60]}..."
    )

    # --------------------------------------------------
    # CONTENT API
    # --------------------------------------------------

    print("\n📺 Fetching channels...")

    all_channels = []
    content_results = []

    for index, hash_id in enumerate(HASHES, 1):

        print(
            f"\n[{index}/{len(HASHES)}] "
            f"Hash: {hash_id[:8]}"
        )

        result = content_api(
            hash_id,
            auth
        )

        content_results.append(result)

        if result["success"]:

            channels = extract_channels(result)

            all_channels.extend(channels)

            print(
                f"✅ Found "
                f"{len(channels)} channels"
            )

        else:

            print(
                f"❌ Failed: "
                f"{result.get('error')}"
            )

        time.sleep(1)

    # --------------------------------------------------
    # UNIQUE CHANNELS
    # --------------------------------------------------

    seen = set()
    unique = []

    for channel in all_channels:

        cid = channel.get("content_id")

        if not cid:
            continue

        if cid in seen:
            continue

        seen.add(cid)
        unique.append(channel)

    print("\n" + "=" * 60)
    print(
        f"📊 Total unique channels: "
        f"{len(unique)}"
    )
    print("=" * 60)

    # --------------------------------------------------
    # SAVE RAW CHANNEL DATA
    # --------------------------------------------------

    save_json(
        "channels.json",
        unique
    )

    # --------------------------------------------------
    # PLAYBACK
    # --------------------------------------------------

    print("\n🎬 Fetching streams...")

    with_streams = []

    for index, channel in enumerate(
        unique,
        1
    ):

        cid = channel.get("content_id")

        if not cid:
            continue

        print(
            f"[{index}/{len(unique)}] "
            f"{channel['name']}"
        )

        playback = playback_api(
            cid,
            auth
        )

        item = {
            **channel,

            "m3u8_url": (
                playback.get("m3u8")
                if playback.get("success")
                else None
            ),

            "stream_data": (
                playback.get("data")
                if playback.get("success")
                else None
            ),

            "error": (
                None
                if playback.get("success")
                else playback.get("error")
            )
        }

        with_streams.append(item)

        if playback.get("success") and playback.get("m3u8"):

            print("   ✅ M3U8 found")

        else:

            print(
                "   ❌ No M3U8 | "
                f"{playback.get('error', 'Unknown error')}"
            )

        time.sleep(1.5)

    # --------------------------------------------------
    # REPORT
    # --------------------------------------------------

    report = {

        "scraped_at": time.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "auth": {

            "user_agent": auth["user_agent"],

            "cookies": auth["cookies"],

            "raw_cookies": [
                {
                    "name": c.get("name"),
                    "value": c.get("value"),
                    "domain": c.get("domain"),
                    "path": c.get("path")
                }

                for c in auth["cookie_list"]
            ]
        },

        "stats": {

            "total_channels": len(unique),

            "streams_checked": len(with_streams),

            "streams_found": sum(
                1
                for c in with_streams
                if c.get("m3u8_url")
            )
        },

        "channels": unique,

        "with_streams": with_streams,

        "content_api_results": content_results
    }

    save_json(
        "data.json",
        report
    )

    # --------------------------------------------------
    # M3U
    # --------------------------------------------------

    print("\n📝 Creating M3U...")

    m3u = [
        "#EXTM3U"
    ]

    stream_count = 0

    for channel in with_streams:

        m3u8 = channel.get("m3u8_url")

        if not m3u8:
            continue

        name = channel.get(
            "name",
            "Unknown"
        )

        logo = channel.get(
            "logo",
            ""
        )

        category = channel.get(
            "category",
            "General"
        )

        m3u.append(
            f'#EXTINF:-1 '
            f'tvg-logo="{logo}" '
            f'group-title="{category}",'
            f'{name}'
        )

        m3u.append(
            f'#EXTVLCOPT:http-user-agent='
            f'{auth["user_agent"]}'
        )

        m3u.append(
            '#EXTVLCOPT:http-referrer='
            'https://toffeelive.com/'
        )

        m3u.append(m3u8)

        m3u.append("")

        stream_count += 1

    m3u_path = os.path.join(
        OUTPUT,
        "playlist.m3u"
    )

    with open(
        m3u_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(m3u)
        )

    print(
        f"💾 M3U saved: {m3u_path}"
    )

    # --------------------------------------------------
    # MARKDOWN REPORT
    # --------------------------------------------------

    md = f"""# Toffee Scrape Report

**Time:** {time.strftime('%Y-%m-%d %H:%M:%S')}

## Statistics

- Total channels: **{len(unique)}**
- Streams checked: **{len(with_streams)}**
- M3U8 found: **{stream_count}**

## Auth

- User-Agent: `{auth["user_agent"]}`
- Cookies collected: **{len(auth["cookie_list"])}**

## Channels

| Name | Category | M3U8 |
|------|----------|------|
"""

    for channel in with_streams:

        has_stream = (
            "✅"
            if channel.get("m3u8_url")
            else "❌"
        )

        md += (
            f"| {channel.get('name', 'Unknown')} "
            f"| {channel.get('category', 'General')} "
            f"| {has_stream} |\n"
        )

    md_path = os.path.join(
        OUTPUT,
        "report.md"
    )

    with open(
        md_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(md)

    print(
        f"💾 Report saved: {md_path}"
    )

    # --------------------------------------------------
    # FINAL
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("🎉 SCRAPER FINISHED")
    print("=" * 60)

    print(
        f"📺 Channels: {len(unique)}"
    )

    print(
        f"🎬 Streams checked: "
        f"{len(with_streams)}"
    )

    print(
        f"🔗 M3U8 found: "
        f"{stream_count}"
    )

    print(
        f"📁 Output: {OUTPUT}/"
    )


if __name__ == "__main__":
    main()
