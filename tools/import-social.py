#!/usr/bin/env python3
"""Importa i nuovi post di Facebook e Instagram da feed esterni.

Legge uno o più feed (JSON Feed, RSS o Atom, come quelli di RSS.app), salva
l'immagine di ogni post nuovo in assets/img/ (JPG e WebP, al massimo 720 px),
aggiunge la voce in tools/social.json e rigenera le card con build-social.py.

Uso:
  SOCIAL_FEEDS="URL_FEED_FACEBOOK URL_FEED_INSTAGRAM" python3 tools/import-social.py
  python3 tools/import-social.py URL_O_FILE [URL_O_FILE ...]

Serve Pillow (pip install pillow). Lo esegue ogni giorno la GitHub Action
.github/workflows/social.yml, che prende gli URL dal secret SOCIAL_FEEDS.

Regole:
  - un post è nuovo se il suo link non è già in social.json e non è più
    vecchio del post più recente già presente per la stessa rete;
  - i post senza immagine vengono saltati;
  - social.json tiene al massimo MAX_POSTS post: i più vecchi escono, e con
    loro le immagini social-* che non servono più;
  - per togliere un post dal sito, mettere "nascosto": true nella sua voce.
"""
import email.utils
import hashlib
import html
import io
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Europe/Rome")
except Exception:  # sistema senza database dei fusi orari
    LOCAL_TZ = timezone.utc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

DATA_FILE = "tools/social.json"
MAX_POSTS = 24
MAX_NEW = 12
MAX_TEXT = 220
MAX_IMAGE_BYTES = 15 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (compatible; noiperte-social/1.0; +https://www.noiperte.it)"
MIN_TEXT = 12
FALLBACK_TEXT = {
    "facebook": "Un nuovo {} sulla nostra pagina Facebook.",
    "instagram": "Un nuovo {} sul nostro profilo Instagram.",
}
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


def fetch(source):
    if os.path.exists(source):
        with open(source, "rb") as fh:
            return fh.read()
    request = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read(MAX_IMAGE_BYTES + 1)


# ------------------------------------------------------------- lettura feed --
def first_img(markup):
    match = re.search(r'<img[^>]+src="([^"]+)"', markup or "")
    return html.unescape(match.group(1)) if match else ""


def parse_date(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_json_feed(feed):
    for item in feed.get("items", []):
        image = item.get("image") or item.get("banner_image") or first_img(item.get("content_html"))
        video = False
        for attachment in item.get("attachments") or []:
            mime = attachment.get("mime_type", "")
            if mime.startswith("image/") and not image:
                image = attachment.get("url", "")
            video = video or mime.startswith("video/")
        yield {
            "url": item.get("url") or item.get("external_url") or item.get("id", ""),
            "date": parse_date(item.get("date_published") or item.get("date_modified")),
            "text": item.get("content_text") or item.get("content_html") or item.get("summary") or item.get("title") or "",
            "image": image,
            "video": video,
        }


def parse_xml_feed(root):
    for item in root.iter("item"):
        description = item.findtext("description") or ""
        encoded = item.findtext("content:encoded", namespaces=NS) or ""
        image = ""
        for media in item.findall("media:content", NS) + item.findall("media:thumbnail", NS):
            if media.get("medium", "image") == "image" or media.get("type", "").startswith("image/"):
                image = image or media.get("url", "")
        enclosure = item.find("enclosure")
        if not image and enclosure is not None and enclosure.get("type", "").startswith("image/"):
            image = enclosure.get("url", "")
        yield {
            "url": (item.findtext("link") or item.findtext("guid") or "").strip(),
            "date": parse_date(item.findtext("pubDate")),
            "text": description or encoded or item.findtext("title") or "",
            "image": image or first_img(encoded) or first_img(description),
            "video": enclosure is not None and enclosure.get("type", "").startswith("video/"),
        }
    for entry in root.iter("{%s}entry" % NS["atom"]):
        # Niente "or" tra elementi: un Element senza figli vale False.
        link = entry.find("atom:link[@rel='alternate']", NS)
        if link is None:
            link = entry.find("atom:link", NS)
        content = entry.findtext("atom:content", namespaces=NS) or entry.findtext("atom:summary", namespaces=NS) or ""
        media = entry.find("media:thumbnail", NS)
        if media is None:
            media = entry.find("media:content", NS)
        yield {
            "url": link.get("href", "") if link is not None else "",
            "date": parse_date(entry.findtext("atom:published", namespaces=NS) or entry.findtext("atom:updated", namespaces=NS)),
            "text": content or entry.findtext("atom:title", namespaces=NS) or "",
            "image": (media.get("url", "") if media is not None else "") or first_img(content),
            "video": False,
        }


def read_feed(source):
    raw = fetch(source)
    text = raw.decode("utf-8-sig", errors="replace").lstrip()
    if text.startswith("{"):
        return list(parse_json_feed(json.loads(text)))
    return list(parse_xml_feed(ET.fromstring(raw)))


# ------------------------------------------------------- normalizzazione --
def network_of(url):
    host = urllib.parse.urlsplit(url).netloc.lower()
    if host.endswith(("facebook.com", "fb.com", "fb.watch")):
        return "facebook"
    if host.endswith("instagram.com"):
        return "instagram"
    return None


def canonical_url(url):
    """Una forma unica per lo stesso post, per riconoscere i duplicati."""
    parts = urllib.parse.urlsplit(url.strip())
    if network_of(url) == "instagram":
        match = re.search(r"/(p|reel|tv)/([A-Za-z0-9_-]+)", parts.path)
        if match:
            return f"https://www.instagram.com/{match.group(1)}/{match.group(2)}/"
    keep = {"fbid", "set", "type", "story_fbid", "id", "v"}
    query = urllib.parse.urlencode([(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k in keep])
    host = "www.facebook.com" if network_of(url) == "facebook" and parts.netloc != "fb.watch" else parts.netloc
    return urllib.parse.urlunsplit(("https", host, parts.path.rstrip("/") or "/", query, ""))


def post_key(url):
    """Chiave per i duplicati: Instagram usa lo stesso codice per /p/ e /reel/."""
    if network_of(url) == "instagram":
        match = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)", urllib.parse.urlsplit(url).path)
        if match:
            return "instagram:" + match.group(1)
    return canonical_url(url)


def image_key(url):
    """Lo stesso file immagine può arrivare da server CDN diversi."""
    return os.path.basename(urllib.parse.urlsplit(url).path)


def is_video(url, flagged):
    return flagged or bool(re.search(r"/(reel|reels|tv|videos|watch)\b|fb\.watch", url))


# Titoli che RSS.app mette al posto del testo, come "Associazione Noi per Te Posted".
GENERIC_TITLE = re.compile(r"\b(posted|shared|updated|ha pubblicato|ha condiviso)\b", re.I)


def clean_text(raw, network, video):
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw or ""))
    # Le lettere "in grassetto" Unicode (𝗰𝗲𝗿𝗰𝗮) tornano lettere normali.
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    words = len(text.split())
    # Senza testo, solo un nome ("Alice Cantoni") o un titolo generico: testo di riserva.
    if len(text) < MIN_TEXT or words <= 3 or (words <= 8 and GENERIC_TITLE.search(text)):
        return FALLBACK_TEXT[network].format("video" if video else "post")
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT].rsplit(" ", 1)[0].rstrip(" ,.;:") + "…"
    return text


# ----------------------------------------------------------------- immagini --
def save_image(url, name):
    """Salva JPG e WebP (lato massimo 720 px). Restituisce larghezza e altezza."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        sys.exit("Serve Pillow: pip install pillow")
    data = fetch(url)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("immagine troppo grande")
    with Image.open(io.BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    image.thumbnail((720, 720), Image.LANCZOS)
    image.save(f"assets/img/{name}.jpg", "JPEG", quality=82, optimize=True, progressive=True)
    image.save(f"assets/img/{name}.webp", "WEBP", quality=80, method=6)
    return image.size


def remove_unused_images(removed, kept):
    """Cancella le immagini social-* dei post usciti, se nessuna pagina le usa più."""
    still_used = {post["immagine"] for post in kept}
    pages = ""
    for base, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "sorgenti"]
        for name in files:
            if name.endswith(".html"):
                with open(os.path.join(base, name), encoding="utf-8") as fh:
                    pages += fh.read()
    for post in removed:
        name = post["immagine"]
        if not name.startswith("social-") or name in still_used or name in pages:
            continue
        for ext in ("jpg", "webp"):
            path = f"assets/img/{name}.{ext}"
            if os.path.exists(path):
                os.remove(path)


# --------------------------------------------------------------------- main --
def main():
    sys.stdout.reconfigure(line_buffering=True)  # log in ordine anche nella GitHub Action
    sources = sys.argv[1:] or os.environ.get("SOCIAL_FEEDS", "").split()
    if not sources:
        sys.exit("Nessun feed: imposta SOCIAL_FEEDS o passa gli URL come argomenti.")

    with open(DATA_FILE, encoding="utf-8") as fh:
        posts = json.load(fh)
    known = {post_key(post["url"]) for post in posts}
    seen_images = set()
    # Data del post più recente per ciascuna rete: i più vecchi non si reimportano.
    newest = {}
    for post in posts:
        newest[post["rete"]] = max(newest.get(post["rete"], ""), post["data"])

    items, failures = [], 0
    for source in sources:
        try:
            found = read_feed(source)
            print(f"Feed letto: {len(found)} post")
            items += found
        except Exception as exc:  # un feed rotto non deve bloccare gli altri
            failures += 1
            print(f"ATTENZIONE: feed non leggibile ({exc})")
    if failures == len(sources):
        sys.exit("Nessun feed leggibile: controlla il servizio esterno e il secret SOCIAL_FEEDS.")

    added = []
    for item in sorted(items, key=lambda i: i["date"] or datetime.min.replace(tzinfo=timezone.utc)):
        network = network_of(item["url"] or "")
        if not network or not item["date"]:
            continue
        url = canonical_url(item["url"])
        day = item["date"].astimezone(LOCAL_TZ).strftime("%Y-%m-%d")
        if post_key(url) in known or day < newest.get(network, ""):
            continue
        if not item["image"]:
            print(f"Saltato (senza immagine): {url}")
            continue
        if image_key(item["image"]) in seen_images:
            print(f"Saltato (stessa immagine di un altro post): {url}")
            continue
        name = f"social-{day}-{network}-{hashlib.sha1(url.encode()).hexdigest()[:6]}"
        try:
            width, height = save_image(item["image"], name)
        except Exception as exc:
            print(f"Saltato (immagine non scaricabile: {exc}): {url}")
            continue
        video = is_video(url, item["video"])
        post = {"data": day, "rete": network, "url": url, "immagine": name,
                "testo": clean_text(item["text"], network, video)}
        if video:
            post["video"] = True
        if not 0.85 <= width / height <= 1.18:
            post["intera"] = True
        added.append(post)
        known.add(post_key(url))
        seen_images.add(image_key(item["image"]))
        print(f"Nuovo post {day} {network}: {url}")
        if len(added) >= MAX_NEW:
            break

    if not added:
        print("Nessun post nuovo.")
        return

    posts = sorted(posts + added, key=lambda p: p["data"], reverse=True)
    kept, removed = posts[:MAX_POSTS], posts[MAX_POSTS:]
    with open(DATA_FILE, "w", encoding="utf-8") as fh:
        json.dump(kept, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    subprocess.run([sys.executable, "tools/build-social.py"], check=True)
    remove_unused_images(removed, kept)
    print(f"Importati {len(added)} post nuovi.")


if __name__ == "__main__":
    main()
