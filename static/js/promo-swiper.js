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
        ytCards().forEach(function (card) {
            if (!active || !active.contains(card)) {
                if (ytFrame(card)) ytStop(card);
                return;
            }
            if (card.getAttribute("data-autoplay") === "1" && !card._manual && !ytFrame(card)) {
                ytPlay(card, true);
            }
        });
        videos().forEach(function (v) {
            var card = v.closest(".mcard--video");
            if (!active || !active.contains(v)) {
                if (!v.paused) { try { v.pause(); } catch (e) { /* ignore */ } }
                // an explicit unmute never leaks: leaving the slide returns
                // the card to its muted poster state
                if (v._manualSound) { v._manualSound = false; v.muted = true; }
                return;
            }
            if (card && card.getAttribute("data-autoplay") === "1" && !v._manual && v.paused) {
                v.muted = true;
                var p = v.play();
                if (p && p.catch) p.catch(function () { /* autoplay blocked, poster stays */ });
            }
        });
    }

    // Tap a video card (or its glass play button): inline playback with sound.
    // YouTube first: it has no <video> element, only the embed. From here a
    // card is manual, so the muted autoplay above leaves it alone.
    strip.addEventListener("click", function (e) {
        var ycard = e.target.closest(".mcard--yt");
        if (ycard) {
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
        pauseAll(null);
        swiper.destroy(true, true);
        swiper = null;
    }
    function sync() { if (mq.matches) init(); else destroy(); }
    if (mq.addEventListener) mq.addEventListener("change", sync);
    else if (mq.addListener) mq.addListener(sync);
    window.addEventListener("load", function () { if (mq.matches) init(); });
    sync();
})();
