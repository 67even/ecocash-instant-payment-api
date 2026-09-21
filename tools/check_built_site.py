#!/usr/bin/env python3
"""Check every internal link, anchor and image in a BUILT site.

tools/check_links.py checks the Markdown sources. This checks what Jekyll
actually rendered, which catches what the sources cannot show: an anchor id that
kramdown generated differently from GitHub, an image path that relative_url
resolved wrongly, or a page that silently failed to render.

    python3 tools/check_built_site.py _site/ecocash-instant-payment-api /ecocash-instant-payment-api
"""

import html
import io
import os
import re
import sys
from urllib.parse import urljoin, urlparse, unquote


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "_site"
    baseurl = (sys.argv[2] if len(sys.argv) > 2 else "").rstrip("/")
    if not os.path.isdir(root):
        print("::error::no such directory: %s" % root)
        return 1

    pages, ids = {}, {}
    for dp, _, fn in os.walk(root):
        for f in fn:
            if f.endswith(".html"):
                path = os.path.join(dp, f)
                url = baseurl + "/" + os.path.relpath(path, root).replace(os.sep, "/")
                url = re.sub(r"index\.html$", "", url)
                body = io.open(path, encoding="utf-8").read()
                pages[url] = body
                ids[url] = set(re.findall(r'\bid="([^"]+)"', body))

    bad, n_links, n_imgs = [], 0, 0
    for url, body in pages.items():
        main_html = body.split('<div id="main-content"', 1)[-1]
        for attr, target in re.findall(r'<(?:a|img)\b[^>]*?\b(href|src)="([^"]+)"', main_html):
            target = html.unescape(target)
            if target.startswith(("mailto:", "tel:", "javascript:", "data:")):
                continue
            full = urljoin("https://site" + url, target)
            u = urlparse(full)
            if u.netloc != "site":
                continue
            path = unquote(u.path)
            if attr == "src" or re.search(r"\.(png|jpe?g|svg|gif|webp|css|js|xml|txt)$", path):
                n_imgs += 1
                rel = path[len(baseurl):].lstrip("/") if path.startswith(baseurl) else None
                if rel is None or not os.path.isfile(os.path.join(root, rel)):
                    bad.append("%s -> %s (no such file)" % (url, target))
                continue
            n_links += 1
            page = path if path.endswith("/") else path + "/"
            if page not in pages:
                bad.append("%s -> %s (no such page)" % (url, target))
            elif u.fragment and u.fragment not in ids[page]:
                bad.append("%s -> %s (no id=%s on that page)" % (url, target, u.fragment))

    print("%d page(s): %d internal link(s), %d asset reference(s) checked"
          % (len(pages), n_links, n_imgs))
    if not bad:
        print("\nevery internal link, anchor and image in the built site resolves")
        return 0
    print()
    for b in bad:
        print("::error::built site: %s" % b)
    print("\n%d problem(s)" % len(bad))
    return 1


if __name__ == "__main__":
    sys.exit(main())
