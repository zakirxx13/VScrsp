# M3U8 Black Box Test

**Target:** `https://bldcmprod-cdn.toffeelive.com/cdn/live/somoy_tv/playlist.m3u8`

**User-Agent:** `okhttp/4.11.0`

## Without Cookie
```text
curl: (6) Could not resolve host: bldcmprod-cdn.toffeelive.com
HTTP_STATUS=000
CONTENT_TYPE=
SIZE=0
TIME=0.015360
REMOTE_IP=
CURL_EXIT=6
```

## With Cookie
```text
curl: (6) Could not resolve host: bldcmprod-cdn.toffeelive.com
HTTP_STATUS=000
CONTENT_TYPE=
SIZE=0
TIME=0.015355
REMOTE_IP=
CURL_EXIT=6
```

## HLS Detection
```text
===== WITHOUT COOKIE =====
HLS_PLAYLIST=NO

===== WITH COOKIE =====
HLS_PLAYLIST=NO
```

## DNS
```text
===== TARGET =====
https://bldcmprod-cdn.toffeelive.com/cdn/live/somoy_tv/playlist.m3u8

===== HOST =====
bldcmprod-cdn.toffeelive.com

===== GETENT =====

===== NSLOOKUP =====
Server:		127.0.0.53
Address:	127.0.0.53#53

Non-authoritative answer:
*** Can't find bldcmprod-cdn.toffeelive.com: No answer


===== DIG A =====

===== DIG AAAA =====
```
