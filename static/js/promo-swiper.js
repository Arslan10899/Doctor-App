/* Mobile promo cards: 3D coverflow slider (mobile only).
   The strip markup carries data-mode="coverflow", so the legacy scroll-snap
   carousel in main.js skips it on its own. Swiper is vendored locally under
   static/vendor/swiper, no CDN needed at runtime. Videos never autoplay with
   sound: muted autoplay follows the active slide for cards flagged autoplay,
   and one tap plays inline with sound + native controls. */
(function () {
    var strip = document.getElementById("mcardStrip");
    if (!strip || strip.dataset.mode !== "coverflow") return;

    var mq = window.matchMedia("(max-width: 768px)");
    var swiper = null;
    var loop = strip.dataset.loop === "1";
    var visWired = false;
    var hoverPaused = false; // mouse over the strip holds the auto-slide

    function pad(n) { return (n < 10 ? "0" : "") + n; }
    function fmt(sec) {
        if (!isFinite(sec) || sec < 0) return null;
        sec = Math.floor(sec);
        var h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
        return (h ? h + ":" + pad(m) : m) + ":" + pad(s);
    }
    function videos() {
        return Array.prototype.slice.call(strip.querySelectorAll(".mcard--video video"));
    }
    function wireVideo(v) {
        if (v._promoWired) return;
        v._promoWired = true;
        var card = v.closest(".mcard--video");
        var dur = card ? card.querySelector(".mcard-duration") : null;
        var bar = card ? card.querySelector(".mcard-progress i") : null;
        v.addEventListener("loadedmetadata", function () {
            var t = fmt(v.duration);
            if (dur && t) { dur.textContent = t; dur.hidden = false; }
        });
        v.addEventListener("timeupdate", function () {
            if (bar && v.duration) bar.style.width = (100 * v.currentTime / v.duration) + "%";
        });
        v.addEventListener("play", function () { if (card) card.classList.add("is-playing"); soundCheck(); });
        v.addEventListener("pause", function () { if (card) card.classList.remove("is-playing"); soundCheck(); });
    }
    function pauseAll(except) {
        videos().forEach(function (v) {
            if (v !== except && !v.paused) { try { v.pause(); } catch (e) { /* no video, no problem */ } }
        });
    }
    // YouTube cards play inline in the frame, never as a link out. Poster is
    // the video thumbnail; tap swaps in the embed, leaving the slide destroys
    // it again so no two videos (and no background audio) ever overlap.
    function ytCards() {
        return Array.prototype.slice.call(strip.querySelectorAll(".mcard--yt"));
    }
    function ytFrame(card) { return card.querySelector("iframe.mcard-frame"); }
    function ytPoster(card) { return card.querySelector(".mcard-poster"); }
    function ytPlay(card, muted) {
        var id = card.getAttribute("data-yt");
        if (!id) return null;
        var f = ytFrame(card);
        if (!f) {
            f = document.createElement("iframe");
            f.className = "mcard-frame";
            f.src = "https://www.youtube.com/embed/" + id + "?autoplay=1&rel=0&enablejsapi=1&playsinline=1"
                + (muted ? "&mute=1&loop=1&playlist=" + id : "");
            f.setAttribute("allow", "autoplay; encrypted-media; picture-in-picture");
            f.setAttribute("frameborder", "0");
            f.setAttribute("allowfullscreen", "");
            f.setAttribute("title", card.getAttribute("data-name") || "Video");
            card.insertBefore(f, card.firstChild);
        } else if (!muted) {
            try {
                f.contentWindow.postMessage(JSON.stringify({ event: "command", func: "unMute", args: "" }), "*");
                f.contentWindow.postMessage(JSON.stringify({ event: "command", func: "playVideo", args: "" }), "*");
            } catch (e) { /* player not ready yet */ }
        }
        var poster = ytPoster(card);
        if (poster) poster.style.display = "none";
        card.classList.add("is-playing");
        return f;
    }
    function ytStop(card) {
        var f = ytFrame(card);
        if (f && f.parentNode) f.parentNode.removeChild(f);
        var poster = ytPoster(card);
        if (poster) poster.style.display = "";
        card.classList.remove("is-playing");
        if (card._ytSound) card._ytSound = false;
    }
    // While a video plays WITH sound the slider holds still, so the slide is
    // never yanked away mid-watch. Muted autoplay does not hold the slider.
    function soundCheck() {
        if (!swiper || !swiper.autoplay) return;
        var sounding = videos().some(function (v) { return !v.paused && !v.muted; })
            || ytCards().some(function (card) { return !!card._ytSound && !!ytFrame(card); });
        if (sounding) swiper.autoplay.stop();
        else if (!hoverPaused) swiper.autoplay.start();
    }
    function settleVideos() {
        if (!swiper) return;
        var active = swiper.slides[swiper.activeIndex];
        // No autoplay: a clip is only ever started by an explicit tap, so
        // leaving the active slide just stops anything that was playing and
        // returns a muted-unmute card to its poster state.
        ytCards().forEach(function (card) {
            if (!active || !active.contains(card)) {
                if (ytFrame(card)) ytStop(card);
            }
            if (card._ytSound) card._ytSound = false;
        });
        videos().forEach(function (v) {
            var card = v.closest(".mcard--video");
            if (!active || !active.contains(v)) {
                if (!v.paused) { try { v.pause(); } catch (e) { /* ignore */ } }
                // an explicit unmute never leaks: leaving the slide returns
                // the card to its muted poster state
                if (v._manualSound) { v._manualSound = false; v.muted = true; }
            }
        });
    }

    // ----- Fullscreen-ish lightbox -----
    // On phones the inline frame is small, so playing a clip lifts it out of the
    // card into a big 16:9 stage over a dark blurred backdrop. The <video> is
    // moved (not cloned) so playback state is preserved; closing moves it back
    // into the card exactly where it was. A <video> already being played inline
    // (native controls) is left alone, so native fullscreen keeps priority.
    var promoOverlay = null;
    function ensureOverlay() {
        if (promoOverlay) return promoOverlay;
        promoOverlay = document.createElement("div");
        promoOverlay.className = "promo-vid";
        promoOverlay.id = "promoVid";
        promoOverlay.hidden = true;
        promoOverlay.innerHTML =
            '<div class="promo-vid-backdrop"></div>' +
            '<div class="promo-vid-panel">' +
                '<button type="button" class="promo-vid-close" aria-label="Close video">' +
                    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>' +
                '</button>' +
                '<div class="promo-vid-stage"></div>' +
            '</div>';
        promoOverlay.querySelector(".promo-vid-backdrop").addEventListener("click", closePromoOverlay);
        promoOverlay.querySelector(".promo-vid-close").addEventListener("click", closePromoOverlay);
        promoOverlay.addEventListener("click", function (e) {
            if (e.target === promoOverlay) closePromoOverlay();
        });
        document.body.appendChild(promoOverlay);
        return promoOverlay;
    }
    function showOverlay() {
        var ov = ensureOverlay();
        ov.classList.remove("closing");
        ov.hidden = false;
        void ov.offsetHeight; // restart the fade/scale transition
        ov.classList.add("open");
    }
    function openLocalOverlay(card, v) {
        var ov = ensureOverlay();
        if (ov.contains(v)) return;
        ov._ownerCard = card;
        ov.querySelector(".promo-vid-stage").appendChild(v);
        v.muted = false;
        v.controls = true;
        showOverlay();
        document.body.classList.add("promo-vid-lock");
        if (swiper && swiper.autoplay) swiper.autoplay.stop();
        var p = v.play();
        if (p && p.catch) p.catch(function () { v.muted = true; v.play().catch(function () {}); });
    }
    function openYtOverlay(card) {
        var ov = ensureOverlay();
        ytStop(card); // drop any muted autoplay frame in the card first
        pauseAll(null);
        var stage = ov.querySelector(".promo-vid-stage");
        var id = card.getAttribute("data-yt");
        var f = document.createElement("iframe");
        f.className = "mcard-frame";
        f.src = "https://www.youtube.com/embed/" + id + "?autoplay=1&rel=0&enablejsapi=1&playsinline=1";
        f.setAttribute("allow", "autoplay; encrypted-media; picture-in-picture");
        f.setAttribute("frameborder", "0");
        f.setAttribute("allowfullscreen", "");
        f.setAttribute("title", card.getAttribute("data-name") || "Video");
        stage.appendChild(f);
        card._manual = true;
        card._ytSound = true;
        ov._ownerCard = card;
        showOverlay();
        document.body.classList.add("promo-vid-lock");
        if (swiper && swiper.autoplay) swiper.autoplay.stop();
    }
    function closePromoOverlay() {
        if (!promoOverlay || promoOverlay.hidden || promoOverlay._closing) return;
        var ov = promoOverlay;
        ov._closing = true;
        ov.classList.remove("open");
        // Let the fade/scale-out play, then hide and put the media back exactly
        // where it came from.
        setTimeout(function () {
            ov.hidden = true;
            ov._closing = false;
            document.body.classList.remove("promo-vid-lock");
            var stage = ov.querySelector(".promo-vid-stage");
            var v = stage.querySelector("video");
            if (v) {
                try { v.pause(); } catch (e) { /* nothing playing */ }
                v.muted = true;
                v.controls = false;
                var card = ov._ownerCard;
                if (card) { card.insertBefore(v, card.firstChild); card.classList.remove("is-playing"); }
            }
            var ifr = stage.querySelector("iframe.mcard-frame");
            if (ifr) stage.removeChild(ifr);
            var oc = ov._ownerCard;
            if (oc && oc.classList.contains("mcard--yt") && oc._ytSound) { oc._ytSound = false; oc.classList.remove("is-playing"); }
            ov._ownerCard = null;
            soundCheck();
        }, 280);
    }

    // Tap a video card (or its glass play button): inline playback with sound.
    // YouTube first: it has no <video> element, only the embed. From here a
    // card is manual, so the muted autoplay above leaves it alone.
    strip.addEventListener("click", function (e) {
        var ycard = e.target.closest(".mcard--yt");
        if (ycard) {
            if (mq.matches) { openYtOverlay(ycard); return; }
            ycard._manual = true;
            ycard._ytSound = true;
            pauseAll(null);
            ytCards().forEach(function (o) { if (o !== ycard && ytFrame(o)) ytStop(o); });
            if (ytFrame(ycard)) ytStop(ycard); // drop a muted autoplay frame, replay with sound
            ytPlay(ycard, false);
            soundCheck();
            return;
        }
        var card = e.target.closest(".mcard--video");
        if (!card) return;
        var v = card.querySelector("video");
        if (!v || v.controls) return; // native controls own it from here on
        if (mq.matches) { openLocalOverlay(card, v); return; }
        v._manual = true;
        v._manualSound = true;
        v.controls = true;
        v.muted = false;
        pauseAll(v);
        var p = v.play();
        if (p && p.catch) p.catch(function () { v.muted = true; v.play().catch(function () {}); });
    });

    function init() {
        if (swiper || typeof Swiper === "undefined") return;
        var box = document.getElementById("promoSwiper");
        if (!box) return;
        videos().forEach(wireVideo);
        var total = strip.querySelectorAll(".swiper-slide").length;
        swiper = new Swiper(box, {
            effect: "coverflow",
            grabCursor: true,
            centeredSlides: true,
            slidesPerView: "auto",
            loop: loop,
            loopedSlides: total,
            speed: 550,
            coverflowEffect: {
                rotate: 45,
                stretch: 0,
                depth: 200,
                modifier: 1,
                slideShadows: true
            },
            // auto-slide loop: keeps going after a swipe (disableOnInteraction
            // false), single-card strips have nothing to advance to. Hover
            // pause is manual below so it respects the sound hold above.
            autoplay: total > 1 ? { delay: 4000, disableOnInteraction: false } : false
        });
        swiper.on("slideChange", settleVideos);
        settleVideos();
        // Mouse over the cards holds the slide; moving away resumes normally
        // (unless a video is playing with sound, which keeps holding).
        if (box && !box._promoHover) {
            box._promoHover = true;
            box.addEventListener("mouseenter", function () {
                if (!swiper || !swiper.autoplay) return;
                hoverPaused = true;
                swiper.autoplay.stop();
            });
            box.addEventListener("mouseleave", function () {
                hoverPaused = false;
                soundCheck();
            });
        }
        if (!visWired) {
            visWired = true;
            document.addEventListener("visibilitychange", function () {
                if (!swiper || !swiper.autoplay) return;
                if (document.hidden) swiper.autoplay.stop();
                else soundCheck();
            });
        }
    }
    function destroy() {
        if (!swiper) return;
        if (promoOverlay && !promoOverlay.hidden) closePromoOverlay();
        pauseAll(null);
        swiper.destroy(true, true);
        swiper = null;
    }
    if (!window._promoEscWired) {
        window._promoEscWired = true;
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && promoOverlay && !promoOverlay.hidden) closePromoOverlay();
        });
    }
    function sync() { if (mq.matches) init(); else destroy(); }
    if (mq.addEventListener) mq.addEventListener("change", sync);
    else if (mq.addListener) mq.addListener(sync);
    window.addEventListener("load", function () { if (mq.matches) init(); });
    sync();
})();
