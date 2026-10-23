/* ==========================================================================
   Associazione Noi per Te ODV — interazioni (vanilla JS, nessuna dipendenza)
   ========================================================================== */
(function () {
  "use strict";

  var doc = document;
  var root = doc.documentElement;

  /* ------------------------------------------------ header on scroll ----- */
  var header = doc.querySelector("[data-header]");
  if (header) {
    var onScroll = function () {
      header.classList.toggle("is-scrolled", window.scrollY > 8);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ------------------------------------------------ mobile navigation ---- */
  var toggle = doc.querySelector("[data-nav-toggle]");
  var drawer = doc.querySelector("[data-drawer]");
  if (toggle && drawer) {
    var closeDrawer = function () {
      toggle.setAttribute("aria-expanded", "false");
      drawer.hidden = true;
      doc.body.classList.remove("nav-open");
    };
    var openDrawer = function () {
      toggle.setAttribute("aria-expanded", "true");
      drawer.hidden = false;
      doc.body.classList.add("nav-open");
      drawer.focus();
    };
    toggle.addEventListener("click", function () {
      if (toggle.getAttribute("aria-expanded") === "true") closeDrawer();
      else openDrawer();
    });
    drawer.addEventListener("click", function (e) {
      if (e.target.closest("a")) closeDrawer();
    });
    // Mantiene il focus dentro il menu finché è aperto (Tab / Shift+Tab).
    drawer.addEventListener("keydown", function (e) {
      if (e.key !== "Tab") return;
      var focusables = drawer.querySelectorAll("a[href], button:not([disabled])");
      if (!focusables.length) return;
      var first = focusables[0];
      var last = focusables[focusables.length - 1];
      if (e.shiftKey && doc.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && doc.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    });
    doc.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !drawer.hidden) {
        closeDrawer();
        toggle.focus();
      }
    });
    window.addEventListener("resize", function () {
      if (window.innerWidth > 1080 && !drawer.hidden) closeDrawer();
    });
  }

  /* ------------------------------------------------ reveal on scroll ----- */
  var reveals = [].slice.call(doc.querySelectorAll(".reveal"));
  var noReveal = /(^|[?&])noreveal(=|&|$)/.test(window.location.search);
  if (reveals.length && noReveal) {
    reveals.forEach(function (el) { el.classList.add("is-in"); });
  } else if (reveals.length) {
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              entry.target.classList.add("is-in");
              io.unobserve(entry.target);
            }
          });
        },
        { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
      );
      reveals.forEach(function (el) { io.observe(el); });
    } else {
      reveals.forEach(function (el) { el.classList.add("is-in"); });
    }
  }

  /* ------------------------------------------------ gallery filters ------ */
  var filters = doc.querySelectorAll("[data-filter]");
  var galleryItems = [].slice.call(doc.querySelectorAll("[data-gallery-item]"));
  filters.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var value = btn.getAttribute("data-filter");
      filters.forEach(function (b) {
        b.setAttribute("aria-pressed", String(b === btn));
      });
      galleryItems.forEach(function (li) {
        var cat = li.getAttribute("data-cat");
        li.hidden = value !== "tutte" && cat !== value;
      });
    });
  });

  /* ------------------------------------------------ lightbox ------------- */
  var lightbox = doc.getElementById("lightbox");
  var visibleItems = function () {
    return galleryItems.filter(function (li) { return !li.hidden; });
  };
  if (lightbox && galleryItems.length) {
    var lbImg = lightbox.querySelector("img");
    var lbCaption = lightbox.querySelector("[data-lb-caption]");
    var lbCount = lightbox.querySelector("[data-lb-count]");
    var current = 0;

    var render = function (index) {
      var list = visibleItems();
      if (!list.length) return;
      current = (index + list.length) % list.length;
      var btn = list[current].querySelector("[data-gallery-open]");
      if (!btn) return;
      lbImg.src = btn.getAttribute("data-full");
      lbImg.alt = btn.getAttribute("data-alt") || "";
      if (lbCaption) lbCaption.textContent = btn.getAttribute("data-caption") || lbImg.alt;
      if (lbCount) lbCount.textContent = current + 1 + " / " + list.length;
      // preload neighbours
      [current + 1, current - 1].forEach(function (i) {
        var n = list[(i + list.length) % list.length];
        if (!n) return;
        var b = n.querySelector("[data-gallery-open]");
        if (b) {
          var pre = new Image();
          pre.src = b.getAttribute("data-full");
        }
      });
    };

    var open = function (btn) {
      var li = btn.closest("[data-gallery-item]");
      var list = visibleItems();
      if (!li || !list.length) return;
      render(list.indexOf(li));
      if (typeof lightbox.showModal === "function") lightbox.showModal();
      else lightbox.setAttribute("open", "");
    };

    doc.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-gallery-open]");
      if (btn) {
        e.preventDefault();
        open(btn);
      }
    });

    lightbox.querySelector("[data-lb-prev]").addEventListener("click", function () {
      render(current - 1);
    });
    lightbox.querySelector("[data-lb-next]").addEventListener("click", function () {
      render(current + 1);
    });
    lightbox.querySelector("[data-lb-close]").addEventListener("click", function () {
      lightbox.close();
    });
    lightbox.addEventListener("click", function (e) {
      if (e.target === lightbox) lightbox.close();
    });
    lightbox.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight") { e.preventDefault(); render(current + 1); }
      if (e.key === "ArrowLeft") { e.preventDefault(); render(current - 1); }
    });
    lightbox.addEventListener("close", function () {
      lbImg.removeAttribute("src");
    });
  }

  /* ------------------------------------------------ video modal --------- */
  var videoModal = doc.getElementById("video-modal");
  if (videoModal) {
    var video = videoModal.querySelector("video");
    var source = videoModal.querySelector("source");

    var openVideo = function (btn) {
      var isMobile = window.innerWidth < 720;
      var src = (isMobile && btn.getAttribute("data-video-mobile")) || btn.getAttribute("data-video");
      source.src = src;
      video.setAttribute("poster", btn.getAttribute("data-poster") || "");
      video.load();
      if (typeof videoModal.showModal === "function") videoModal.showModal();
      var playing = video.play();
      if (playing && playing.catch) playing.catch(function () {});
    };

    doc.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-video]");
      if (btn) {
        e.preventDefault();
        openVideo(btn);
      }
    });

    videoModal.querySelector("[data-video-close]").addEventListener("click", function () {
      videoModal.close();
    });
    videoModal.addEventListener("click", function (e) {
      if (e.target === videoModal) videoModal.close();
    });
    videoModal.addEventListener("close", function () {
      video.pause();
      video.removeAttribute("src");
      source.removeAttribute("src");
      video.load();
    });
  }

  /* ------------------------------------------------ copy to clipboard ---- */
  doc.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-copy]");
    if (!btn) return;
    e.preventDefault();
    var value = btn.getAttribute("data-copy");
    var done = function () {
      var label = btn.querySelector("[data-copy-label]");
      var old = label ? label.textContent : btn.textContent;
      btn.classList.add("is-copied");
      if (label) label.textContent = "Copiato!";
      window.setTimeout(function () {
        btn.classList.remove("is-copied");
        if (label) label.textContent = old;
      }, 2200);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(value).then(done, function () {
        window.prompt("Copia il codice fiscale:", value);
      });
    } else {
      window.prompt("Copia il codice fiscale:", value);
    }
  });

  /* ------------------------------------------------ contact form --------- */
  var form = doc.querySelector("[data-contact-form]");
  if (form) {
    var status = form.querySelector("[data-form-status]");
    var email = form.getAttribute("data-email") || "ass.noiperte2010@gmail.com";

    var setStatus = function (state, message) {
      if (!status) return;
      status.setAttribute("data-state", state);
      status.textContent = message;
    };

    var buildMessage = function (data) {
      return [
        "Nome: " + data.nome,
        "Email: " + data.email,
        data.telefono ? "Telefono: " + data.telefono : null,
        "Motivo: " + data.motivo,
        "",
        data.messaggio
      ].filter(Boolean).join("\n");
    };

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var data = {
        nome: (form.elements.nome.value || "").trim(),
        email: (form.elements.email.value || "").trim(),
        telefono: (form.elements.telefono.value || "").trim(),
        motivo: form.elements.motivo.value,
        messaggio: (form.elements.messaggio.value || "").trim()
      };
      var invalid = [];
      if (!data.nome) invalid.push(form.elements.nome);
      if (!data.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) invalid.push(form.elements.email);
      if (!data.messaggio) invalid.push(form.elements.messaggio);
      if (!form.elements.privacy.checked) invalid.push(form.elements.privacy);

      [].slice.call(form.querySelectorAll("[aria-invalid]")).forEach(function (el) {
        el.removeAttribute("aria-invalid");
      });
      if (invalid.length) {
        invalid.forEach(function (el) { el.setAttribute("aria-invalid", "true"); });
        setStatus("error", "Controlla i campi segnalati: servono nome, un indirizzo email valido, il messaggio e il consenso al trattamento dei dati.");
        invalid[0].focus();
        return;
      }

      var subject = "Richiesta dal sito — " + data.motivo;
      var body = buildMessage(data);
      var mailto = "mailto:" + email + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
      var wa = "https://wa.me/393453244032?text=" + encodeURIComponent(subject + "\n\n" + body);

      var waLink = form.querySelector("[data-wa-link]");
      if (waLink) waLink.href = wa;

      // Se è configurato un endpoint (es. Formspree / FormSubmit), invia lì.
      // Altrimenti apre il client di posta dell'utente con il messaggio pronto.
      var endpoint = form.getAttribute("data-endpoint");
      if (endpoint) {
        var submitBtn = form.querySelector("button[type=submit]");
        if (submitBtn) submitBtn.disabled = true;
        setStatus("ok", "Invio in corso…");
        fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Accept": "application/json" },
          body: JSON.stringify(data)
        })
          .then(function (res) {
            if (!res.ok) throw new Error("HTTP " + res.status);
            form.reset();
            setStatus("ok", "Grazie! La tua richiesta è stata inviata. Ti risponderemo il prima possibile.");
          })
          .catch(function () {
            setStatus("error", "Non siamo riusciti a inviare la richiesta. Scrivici a " + email + " oppure chiama il 345 3244032.");
          })
          .then(function () {
            if (submitBtn) submitBtn.disabled = false;
          });
        return;
      }

      setStatus("ok", "Si aprirà il tuo programma di posta con il messaggio già compilato. Se non succede, scrivi a " + email + " oppure usa WhatsApp.");
      window.location.href = mailto;
      window.setTimeout(function () {
        if (waLink) waLink.hidden = false;
      }, 1200);
    });
  }

  /* ------------------------------------------------ year ----------------- */
  var yearEls = doc.querySelectorAll("[data-year]");
  var year = String(new Date().getFullYear());
  [].slice.call(yearEls).forEach(function (el) { el.textContent = year; });
})();
