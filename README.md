# Associazione Noi per Te ODV — sito web

Sito statico, multipagina, in italiano, pensato per sostituire il vecchio sito
`noiperte.it`. Non ha build step, non ha dipendenze: sono solo file HTML, CSS,
JavaScript e immagini. Si può pubblicare così com'è su Cloudflare Pages, Vercel,
Netlify o qualsiasi hosting statico.

- **Nessun framework**, nessun `npm install`, nessun database.
- **1 solo foglio di stile** (`assets/css/style.css`) e **1 solo file JS** (`assets/js/main.js`).
- **Font self-hosted** (nessuna chiamata a Google Fonts).
- **Nessun cookie**, nessun analytics, nessun banner da mostrare.

---

## 1. Com'è organizzato il progetto

```
/
├── index.html                     Home
├── chi-siamo/index.html
├── servizi/index.html             Servizi + FAQ
├── diventa-volontario/index.html
├── galleria/index.html            Galleria con filtri e lightbox
├── notizie/index.html
│   ├── 15-anni-di-servizio/
│   ├── nuovi-mezzi-per-il-trasporto/
│   └── premio-marco-biagi-2016/
├── sostienici/index.html          5x1000 e donazioni
├── contatti/index.html            Contatti + modulo + mappa
├── privacy/index.html
├── 404.html
├── sitemap.xml
├── robots.txt
├── site.webmanifest
├── og-image.jpg                   Immagine per la condivisione social
├── favicon.ico / favicon.svg / icon-*.png
├── _headers                       Header HTTP per Cloudflare Pages
├── vercel.json                    Header HTTP per Vercel
├── assets/
│   ├── css/style.css
│   ├── js/main.js
│   ├── fonts/                     Playfair Display (woff2, ~77 KB)
│   ├── img/                       Foto e logo ottimizzati (WebP + JPEG)
│   └── video/                     Spot e video (MP4 H.264) + poster
└── sorgenti/                      File originali (NON vanno pubblicati)
```

I file in `sorgenti/` (video originali, PDF del logo) sono esclusi dal deploy tramite
`.assetsignore` (Cloudflare) e `.vercelignore` (Vercel).

---

## 2. Vederlo in locale

Serve solo Python (già presente su macOS/Linux) o qualsiasi server statico:

```bash
cd NoiPerTe
python3 -m http.server 8000
```

Poi apri <http://localhost:8000>.

> Aprire direttamente `index.html` con doppio clic **non** funziona bene, perché i
> link usano percorsi assoluti (`/servizi/`). Usa sempre un server locale.

---

## 3. Pubblicare online

### Cloudflare Pages (consigliato)

1. Crea un repository Git con questi file (oppure usa il caricamento diretto dalla dashboard).
2. Nella dashboard Cloudflare: **Workers & Pages → Create → Pages → Connect to Git**.
3. Impostazioni di build:
   - **Framework preset:** `None`
   - **Build command:** *(vuoto)*
   - **Build output directory:** `/` (la root del progetto)
4. Deploy. Il file `_headers` applica automaticamente cache e header di sicurezza.

In alternativa, dalla dashboard: **Upload assets** e trascina la cartella del sito.
Il file `_headers` viene rispettato anche in questo caso.

### Vercel

1. Importa il repository su Vercel.
2. **Framework preset:** `Other`, **Build command:** *(vuoto)*,
   **Output directory:** `.` (la root).
3. `vercel.json` imposta URL con slash finale, header di sicurezza e cache.

### Netlify

Trascina la cartella su Netlify Drop. Il file `_headers` funziona anche lì.

### Dominio

Tutti i link interni sono assoluti e il sito presume il dominio
`https://www.noiperte.it`. Se pubblichi su un dominio diverso, fai una sostituzione
globale **prima del deploy**:

```bash
grep -rl "https://www.noiperte.it" --include="*.html" --include="*.xml" --include="*.txt" . \
  | xargs sed -i '' 's|https://www.noiperte.it|https://NUOVO-DOMINIO.it|g'
```

(Su Linux togli `''` dopo `-i`.)

Poi aggiorna anche `robots.txt` e `sitemap.xml` se la sostituzione non li ha inclusi.

---

## 4. Modificare i contenuti

Ogni pagina è un file HTML completo e leggibile. Non serve compilare nulla.

- **Testi**: apri il file della pagina e modifica il testo tra i tag.
- **Telefono / email**: sono ripetuti in header, footer e pagine. Usa la ricerca del
  tuo editor:
  - telefono: `345 3244032` e `+393453244032`
  - email: `ass.noiperte2010@gmail.com`
- **Codice fiscale 5x1000**: `90062550406` (in `index.html` e `sostienici/index.html`).
- **Anno nel footer**: è aggiornato automaticamente da JavaScript (`data-year`).
- **Indirizzo**: `Viale della Cooperazione 170, 47522 Pievesestina di Cesena (FC)`.
- **Social**: i link a Facebook, Instagram e WhatsApp sono in header (menu mobile),
  footer e nella pagina contatti. Sostituisci gli URL se cambiano.

### Aggiungere una notizia

1. Copia una cartella esistente, per esempio `notizie/nuovi-mezzi-per-il-trasporto/`,
   e rinominala con lo slug della nuova notizia.
2. Modifica `index.html` dentro la cartella: titolo, data, testo e immagine.
3. Aggiungi la card nella pagina `notizie/index.html` (e, se vuoi, in home).
4. Aggiungi l'URL in `sitemap.xml`.

### Aggiungere foto alla galleria

Le immagini vanno preparate in due misure (es. `-720` e `-1500`) in **WebP + JPEG**,
poi si aggiunge un `<li data-gallery-item>` in `galleria/index.html` copiando un blocco
esistente e cambiando `src`, `data-full`, `alt`, `data-caption` e `data-cat`.

Consiglio: usa immagini quadrate, lato massimo 1500 px, qualità 80.

---

## 5. Modulo di contatto

Il modulo **non invia dati a un server**: compone un messaggio e apre il programma di
posta dell'utente (`mailto:`). In alternativa la pagina offre telefono e WhatsApp.

Se in futuro volete ricevere i messaggi direttamente (senza client di posta), basta
aggiungere un servizio gratuito come [Formspree](https://formspree.io/) o
[FormSubmit](https://formsubmit.co/) e mettere l'URL nell'attributo `data-endpoint`
del modulo, in `contatti/index.html` (e in `diventa-volontario/index.html`):

```html
<form class="form-card" data-contact-form data-email="ass.noiperte2010@gmail.com"
      data-endpoint="https://formspree.io/f/IL_TUO_CODICE">
```

Il JavaScript invierà i dati in JSON e mostrerà il messaggio di conferma. Senza
`data-endpoint` continua a funzionare il `mailto:`.

> Se attivate un servizio esterno, aggiornate la pagina Privacy indicando il fornitore
> e il trattamento dei dati.

---

## 6. SEO — cosa è già fatto

- URL puliti e stabili (`/servizi/`, `/notizie/...`).
- Un solo `<h1>` per pagina, titoli e descrizioni unici e ottimizzati.
- `canonical`, Open Graph, Twitter Card, `og:image` 1200×630.
- Dati strutturati JSON-LD: `NGO`, `WebSite`, `WebPage`, `BreadcrumbList`, `Article`,
  `FAQPage`, `Service`, `ContactPage`.
- `sitemap.xml` e `robots.txt`.
- Immagini con `alt` descrittivi, `width`/`height`, `loading="lazy"` e `srcset`.
- Font e immagini serviti dal dominio, nessuna dipendenza esterna.
- Header di sicurezza e cache in `_headers` / `vercel.json`.

### Dopo il deploy

1. Verifica il sito su [Google Search Console](https://search.google.com/search-console/)
   e invia `https://www.noiperte.it/sitemap.xml`.
2. Crea/aggiorna la scheda **Google Business Profile** con indirizzo, telefono e orari.
3. Controlla che `https://www.noiperte.it/og-image.jpg` si veda bene condividendo il link
   su WhatsApp/Facebook.
4. Se cambi dominio, aggiorna canonical, sitemap e Search Console.

---

## 7. Accessibilità e prestazioni

- Contrasto colori conforme WCAG AA, focus visibile, skip link, `aria-current`.
- Menu mobile con gestione del focus e chiusura con `Esc`.
- Lightbox e video in `<dialog>` nativi (focus trap e `Esc` gratuiti).
- Rispetto di `prefers-reduced-motion`.
- Immagini in WebP con fallback JPEG; video MP4 H.264 con poster.
- I video partono solo su richiesta (nessun autoplay): in tutto pesano meno di 8 MB.
- Lighthouse (mobile e desktop): **100 Accessibilità, 100 Best Practices, 100 SEO**.

Per rigenerare le immagini ottimizzate servono `cwebp` e `ffmpeg`; i file già pronti
sono in `assets/`. Se ti servono, chiedi: possiamo preparare uno script.

---

## 8. Cose da verificare con l'associazione

Prima di pubblicare, è bene confermare:

- [ ] Indirizzo esatto: **Viale** o **Via** della Cooperazione 170.
- [ ] Numeri aggiornati (mezzi, volontari, km, persone accompagnate): nel sito sono
      indicati i dati 2025 raccontati dalla stampa locale.
- [ ] Link social ufficiali (Facebook `NoiPerTe`, Instagram `gabriellagu57`).
- [ ] Consenso all'uso delle foto con volontari e utenti riconoscibili.
- [ ] Eventuale numero di iscrizione RUNTS da mostrare in modo più preciso.
- [ ] Testi della Privacy (titolare, tempi di conservazione, hosting scelto).
- [ ] Eventuale IBAN o modalità di donazione da pubblicare (ora si invita a contattare).

---

## 9. Crediti

Contenuti e fotografie: Associazione Noi per Te ODV.
Logo: file fornito dall'associazione.
Carattere tipografico: Playfair Display (SIL Open Font License).
Mappa: © OpenStreetMap contributors.
