#!/usr/bin/env python3
"""Controlli di qualità del sito statico.

Verifica, senza dipendenze esterne:
  - link e asset interni (href, src, srcset, poster)
  - una sola <h1> per pagina
  - title, meta description, canonical, og:image
  - JSON-LD valido
  - URL del sitemap presenti come file
  - manifest e JSON di configurazione validi

Uso:  python3 tools/check-site.py
Esce con codice 1 se trova errori.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

errors = []
warnings = []


def pages():
    for base, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "sorgenti"]
        for name in files:
            if name.endswith(".html"):
                yield os.path.join(base, name).lstrip("./")


def local_target(url):
    if not url or url.startswith(("http", "mailto:", "tel:", "#", "data:")):
        return None
    path = url.split("#")[0].split("?")[0]
    if path in ("", "/"):
        return "index.html"
    path = path.lstrip("/")
    if path.endswith("/"):
        path += "index.html"
    return path


def check_links(page, html):
    urls = re.findall(r'(?:href|src|poster)="([^"]+)"', html)
    for srcset in re.findall(r'srcset="([^"]+)"', html):
        urls += [part.strip().split(" ")[0] for part in srcset.split(",")]
    for url in urls:
        target = local_target(url)
        if target and not os.path.exists(target):
            errors.append(f"{page}: link/asset mancante -> {url}")
    for name in ("index.html",):
        pass


def check_seo(page, html):
    h1 = len(re.findall(r"<h1\b", html))
    if h1 != 1:
        errors.append(f"{page}: {h1} tag <h1> (atteso 1)")

    title = re.search(r"<title>(.*?)</title>", html, re.S)
    if not title:
        errors.append(f"{page}: manca <title>")
    elif len(title.group(1)) > 70:
        warnings.append(f"{page}: title lungo {len(title.group(1))} caratteri")

    desc = re.search(r'<meta name="description" content="([^"]*)"', html)
    if not desc:
        errors.append(f"{page}: manca meta description")
    elif len(desc.group(1)) > 165:
        warnings.append(f"{page}: description lunga {len(desc.group(1))} caratteri")

    if page != "404.html":
        if not re.search(r'<link rel="canonical" href="https://', html):
            errors.append(f"{page}: manca canonical assoluto")
        if not re.search(r'<meta property="og:image" content="https://', html):
            errors.append(f"{page}: manca og:image assoluto")

    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            json.loads(block)
        except json.JSONDecodeError as exc:
            errors.append(f"{page}: JSON-LD non valido ({exc})")


def check_sitemap():
    try:
        tree = ET.parse("sitemap.xml")
    except (OSError, ET.ParseError) as exc:
        errors.append(f"sitemap.xml non valido ({exc})")
        return
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for loc in tree.findall(".//s:loc", ns):
        url = (loc.text or "").replace("https://www.noiperte.it", "")
        target = local_target(url)
        if target and not os.path.exists(target):
            errors.append(f"sitemap.xml: URL senza file -> {loc.text}")


def check_json_files():
    for name in ("site.webmanifest", "vercel.json"):
        try:
            json.load(open(name, encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{name} non valido ({exc})")


def main():
    count = 0
    for page in sorted(pages()):
        count += 1
        with open(page, encoding="utf-8") as fh:
            html = fh.read()
        check_links(page, html)
        check_seo(page, html)

    check_sitemap()
    check_json_files()

    print(f"Pagine controllate: {count}")
    for warning in warnings:
        print(f"  ATTENZIONE  {warning}")
    for error in errors:
        print(f"  ERRORE      {error}")

    if errors:
        print(f"\n{len(errors)} errori trovati.")
        return 1
    print("Tutto ok.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
