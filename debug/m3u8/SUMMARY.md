# M3U8 Black Box Test

Target: `https://bldcmprod-cdn.toffeelive.com/cdn/live/somoy_tv/playlist.m3u8`

## Without Cookie
curl: (6) Could not resolve host: bldcmprod-cdn.toffeelive.com
HTTP_STATUS=000
CONTENT_TYPE=
SIZE=0
TIME=0.007337
CURL_EXIT=6

## With Cookie
curl: (6) Could not resolve host: bldcmprod-cdn.toffeelive.com
HTTP_STATUS=000
CONTENT_TYPE=
SIZE=0
TIME=0.007291
CURL_EXIT=6

## DNS
===== GETENT =====

===== NSLOOKUP =====
Server:		127.0.0.53
Address:	127.0.0.53#53

Non-authoritative answer:
*** Can't find bldcmprod-cdn.toffeelive.com: No answer


===== DIG A =====

===== DIG AAAA =====
