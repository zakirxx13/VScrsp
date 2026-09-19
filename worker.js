const CDN_HOST = "bldcmprod-cdn.toffeelive.com";
const CDN_USER_AGENT = "okhttp/4.11.0";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: corsHeaders()
      });
    }

    if (!["GET", "HEAD"].includes(request.method)) {
      return new Response("Method Not Allowed", {
        status: 405
      });
    }

    /*
     * Browser requests:
     *
     * /cdn/live/somoy_tv/playlist.m3u8
     *
     * /proxy/cdn/live/somoy_tv/segment.ts
     */

    let targetPath = url.pathname;

    if (targetPath.startsWith("/proxy/")) {
      targetPath = targetPath.substring("/proxy".length);
    }

    const target = new URL(
      `https://${CDN_HOST}${targetPath}${url.search}`
    );

    const headers = new Headers();

    headers.set("User-Agent", CDN_USER_AGENT);
    headers.set("Accept", "*/*");
    headers.set("Accept-Encoding", "identity");

    /*
     * Secret stored inside Cloudflare,
     * NOT inside GitHub code.
     */
    if (env.EDGE_CACHE_COOKIE) {
      headers.set(
        "Cookie",
        env.EDGE_CACHE_COOKIE
      );
    }

    const range = request.headers.get("Range");

    if (range) {
      headers.set("Range", range);
    }

    let response;

    try {
      response = await fetch(target.toString(), {
        method: request.method,
        headers,
        redirect: "follow"
      });
    } catch (error) {
      return json({
        error: "CDN request failed",
        message: String(error)
      }, 502);
    }

    const contentType =
      response.headers.get("Content-Type") || "";

    const isPlaylist =
      targetPath.endsWith(".m3u8") ||
      contentType.includes("mpegurl") ||
      contentType.includes("vnd.apple.mpegurl");

    /*
     * M3U8 playlist
     */
    if (isPlaylist) {

      const body = await response.text();

      const rewritten =
        rewritePlaylist(body, target);

      const outputHeaders =
        new Headers(response.headers);

      outputHeaders.set(
        "Content-Type",
        contentType ||
        "application/vnd.apple.mpegurl"
      );

      outputHeaders.set(
        "Cache-Control",
        "no-store"
      );

      applyCors(outputHeaders);

      outputHeaders.delete("Set-Cookie");

      return new Response(
        rewritten,
        {
          status: response.status,
          statusText: response.statusText,
          headers: outputHeaders
        }
      );
    }

    /*
     * Video/audio segments
     */
    const outputHeaders =
      new Headers(response.headers);

    applyCors(outputHeaders);

    outputHeaders.delete("Set-Cookie");

    return new Response(
      response.body,
      {
        status: response.status,
        statusText: response.statusText,
        headers: outputHeaders
      }
    );
  }
};


/*
 * Rewrite URLs inside M3U8
 */
function rewritePlaylist(body, currentUrl) {

  return body
    .split(/\r?\n/)
    .map(line => {

      const trimmed = line.trim();

      if (!trimmed) {
        return line;
      }

      /*
       * HLS tags containing URI="..."
       */
      if (trimmed.startsWith("#")) {

        return line.replace(
          /URI="([^"]+)"/g,
          (match, uri) => {

            const proxied =
              makeProxyUrl(uri, currentUrl);

            return `URI="${proxied}"`;
          }
        );
      }

      /*
       * Normal segment / playlist URL
       */
      return makeProxyUrl(
        trimmed,
        currentUrl
      );

    })
    .join("\n");
}


/*
 * Convert CDN resource URL
 * into Worker proxy URL
 */
function makeProxyUrl(resource, currentUrl) {

  try {

    const absolute =
      new URL(resource, currentUrl);

    if (
      absolute.hostname !== CDN_HOST
    ) {
      return resource;
    }

    return `/proxy${absolute.pathname}${absolute.search}`;

  } catch {
    return resource;
  }
}


/*
 * CORS
 */
function corsHeaders() {

  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods":
      "GET, HEAD, OPTIONS",
    "Access-Control-Allow-Headers":
      "*"
  };
}


function applyCors(headers) {

  headers.set(
    "Access-Control-Allow-Origin",
    "*"
  );

  headers.set(
    "Access-Control-Allow-Methods",
    "GET, HEAD, OPTIONS"
  );

  headers.set(
    "Access-Control-Allow-Headers",
    "*"
  );
}


function json(data, status = 200) {

  return new Response(
    JSON.stringify(data, null, 2),
    {
      status,
      headers: {
        "Content-Type":
          "application/json",
        ...corsHeaders()
      }
    }
  );
  }
