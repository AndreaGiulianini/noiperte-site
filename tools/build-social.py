#!/usr/bin/env python3
"""Genera le card dei post social a partire da tools/social.json.

Le card finiscono nella home (gli ultimi 4 post) e nella pagina Notizie
(gli ultimi 8), tra i commenti <!-- social:inizio --> e <!-- social:fine -->.

Per aggiungere un post:
  1. salva l'immagine in assets/img/ come NOME.jpg e NOME.webp
     (per esempio: cwebp -q 80 NOME.jpg -o NOME.webp);
  2. aggiungi una voce in tools/social.json con data, rete (facebook o
     instagram), url del post, immagine (NOME, senza estensione) e testo;
     "intera": true per locandine e foto da non ritagliare,
     "video": true per reel e video;
  3. esegui:  python3 tools/build-social.py

I nuovi post arrivano anche da soli con tools/import-social.py (vedi lì).
Per togliere un post dal sito senza che venga reimportato, aggiungi
"nascosto": true alla sua voce invece di cancellarla.

Con --check non scrive nulla ed esce con codice 1 se le pagine non sono
allineate a social.json (lo usa la CI).
"""
import json
import os
import re
import struct
import sys
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

PAGES = {"index.html": 4, "notizie/index.html": 8}
START, END = "<!-- social:inizio -->", "<!-- social:fine -->"
NETWORKS = {"facebook": "Facebook", "instagram": "Instagram"}
MONTHS = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
          "agosto", "settembre", "ottobre", "novembre", "dicembre"]


def jpeg_size(path):
    """Larghezza e altezza di un JPEG, lette dal marcatore SOF."""
    with open(path, "rb") as fh:
        data = fh.read()
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        if marker == 0xFF:
            i += 1
            continue
        length = struct.unpack(">H", data[i + 2:i + 4])[0]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", data[i + 5:i + 9])
            return width, height
        i += 2 + length
    raise ValueError(f"{path}: dimensioni JPEG non trovate")


def load_posts():
    with open("tools/social.json", encoding="utf-8") as fh:
        posts = json.load(fh)
    errors = []
    for n, post in enumerate(posts, 1):
        where = f"tools/social.json, post {n}"
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", post.get("data", "")):
            errors.append(f"{where}: data mancante o non in formato AAAA-MM-GG")
        if post.get("rete") not in NETWORKS:
            errors.append(f"{where}: rete deve essere facebook o instagram")
        if not post.get("url", "").startswith("https://"):
            errors.append(f"{where}: url mancante o non https")
        if not post.get("testo"):
            errors.append(f"{where}: testo mancante")
        for ext in ("jpg", "webp"):
            if not os.path.exists(f"assets/img/{post.get('immagine')}.{ext}"):
                errors.append(f"{where}: manca assets/img/{post.get('immagine')}.{ext}")
    if errors:
        sys.exit("\n".join(errors))
    visible = [post for post in posts if not post.get("nascosto")]
    # Dal più recente; a parità di data resta l'ordine del file.
    return sorted(visible, key=lambda p: p["data"], reverse=True)


def render_card(post):
    image = post["immagine"]
    width, height = jpeg_size(f"assets/img/{image}.jpg")
    year, month, day = (int(part) for part in post["data"].split("-"))
    media = "social-card__media social-card__media--intera" if post.get("intera") else "social-card__media"
    lines = [
        "<li>",
        f'  <a class="social-card" href="{escape(post["url"])}" target="_blank" rel="noopener">',
        f'    <span class="{media}">',
        f'      <picture><source type="image/webp" srcset="/assets/img/{image}.webp">'
        f'<img src="/assets/img/{image}.jpg" alt="" width="{width}" height="{height}" loading="lazy" decoding="async"></picture>',
    ]
    if post.get("video"):
        lines.append('      <span class="social-card__badge"><svg class="icon" aria-hidden="true"><use href="#i-play"/></svg> Video</span>')
    lines += [
        "    </span>",
        '    <span class="social-card__body">',
        f'      <span class="social-card__meta"><svg class="icon" aria-hidden="true"><use href="#i-{post["rete"]}"/></svg>'
        f'<span class="sr-only">{NETWORKS[post["rete"]]}, </span>'
        f'<time datetime="{post["data"]}">{day} {MONTHS[month - 1]} {year}</time></span>',
        f'      <span class="social-card__text">{escape(post["testo"], quote=False)}</span>',
        f'      <span class="link-arrow">{"Guarda il video" if post.get("video") else "Apri il post"} '
        '<svg class="icon" aria-hidden="true"><use href="#i-external"/></svg></span>',
        "    </span>",
        "  </a>",
        "</li>",
    ]
    return lines


def render_block(posts, indent):
    lines = ['<ul class="social-grid">']
    for post in posts:
        lines += ["  " + line for line in render_card(post)]
    lines.append("</ul>")
    return "\n".join(indent + line for line in lines)


def main():
    check = "--check" in sys.argv[1:]
    posts = load_posts()
    stale = []
    for page, count in PAGES.items():
        with open(page, encoding="utf-8") as fh:
            html = fh.read()
        match = re.search(r"^([ \t]*)" + re.escape(START) + r"\n.*?^[ \t]*" + re.escape(END), html, re.S | re.M)
        if not match:
            sys.exit(f"{page}: mancano i commenti {START} e {END}")
        indent = match.group(1)
        block = f"{indent}{START}\n{render_block(posts[:count], indent)}\n{indent}{END}"
        updated = html[:match.start()] + block + html[match.end():]
        if updated == html:
            continue
        stale.append(page)
        if not check:
            with open(page, "w", encoding="utf-8") as fh:
                fh.write(updated)
            print(f"aggiornata {page}")
    if check and stale:
        sys.exit("Card social non aggiornate in: " + ", ".join(stale) + "\nEsegui: python3 tools/build-social.py")
    if not stale:
        print("Card social già aggiornate.")


if __name__ == "__main__":
    main()
