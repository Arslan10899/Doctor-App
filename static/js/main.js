// Doctor App - main JS

document.addEventListener("DOMContentLoaded", function () {
    // Mobile nav toggle
    const navToggle = document.getElementById("navToggle");
    const mainNav = document.getElementById("mainNav");
    if (navToggle && mainNav) {
        navToggle.addEventListener("click", function () {
            mainNav.classList.toggle("open");
        });
    }

    // Auto-dismiss flash messages
    document.querySelectorAll(".flash").forEach(function (flash) {
        setTimeout(function () {
            if (flash && flash.parentElement) flash.remove();
        }, 6000);
    });

    // FAQ accordion
    document.querySelectorAll(".faq-question").forEach(function (q) {
        q.addEventListener("click", function () {
            const item = q.parentElement;
            const answer = item.querySelector(".faq-answer");
            const isOpen = item.classList.contains("open");

            document.querySelectorAll(".faq-item.open").forEach(function (openItem) {
                openItem.classList.remove("open");
                const a = openItem.querySelector(".faq-answer");
                if (a) a.style.maxHeight = null;
            });

            if (!isOpen) {
                item.classList.add("open");
                answer.style.maxHeight = answer.scrollHeight + "px";
            }
        });
    });

    // Appointment date -> loads dynamic slots
    const dateInput = document.getElementById("appointmentDate");
    const slotContainer = document.getElementById("slotGrid");
    const slotsHidden = document.getElementById("slot");
    const doctorId = dateInput ? dateInput.getAttribute("data-doctor-id") : null;

    if (dateInput && slotContainer && doctorId) {
        renderSlots(dateInput.value);

        dateInput.addEventListener("change", function () {
            renderSlots(dateInput.value);
        });
    }

    function renderSlots(dateValue) {
        slotContainer.innerHTML = '<p class="slot-loading">Loading available slots...</p>';
        slotContainer.classList.add("loading");
        if (slotsHidden) slotsHidden.value = "";

        fetch("/slots?doctor_id=" + doctorId + "&date=" + dateValue)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                slotContainer.classList.remove("loading");
                if (!data.slots || data.slots.length === 0) {
                    slotContainer.innerHTML = '<p class="slot-none">No slots available for this date. Please pick another day.</p>';
                    return;
                }
                slotContainer.innerHTML = "";
                data.slots.forEach(function (slot) {
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.className = "slot-btn";
                    btn.textContent = slot[0];
                    btn.addEventListener("click", function () {
                        document.querySelectorAll(".slot-btn").forEach(function (b) { b.classList.remove("selected"); });
                        btn.classList.add("selected");
                        if (slotsHidden) slotsHidden.value = slot[0];
                    });
                    slotContainer.appendChild(btn);
                });
            })
            .catch(function () {
                slotContainer.classList.remove("loading");
                slotContainer.innerHTML = '<p class="slot-none">Could not load slots. Please try again.</p>';
            });
    }

    // Mobile promo cards (mobile only). The frame picks its own layout from the
    // number of media inside (one / two / many, set server side). Only "many"
    // is a carousel: the track is a CSS scroll-snap scroller, so swipe already
    // works there, and this adds dots, autoplay and the loop on top. There are no
    // arrows: three tiles fill the frame, so there is nothing to step past - the
    // strip advances itself and the dots are the only manual control.
    const mcardStrip = document.getElementById("mcardStrip");
    if (mcardStrip && mcardStrip.dataset.mode === "many") {
        const track = document.getElementById("mcardTrack");
        const cards = Array.prototype.slice.call(mcardStrip.querySelectorAll(".mcard"));
        const dotsWrap = document.getElementById("mcardDots");
        let index = 0;
        let timer = null;
        let resumeTimer = null;
        let loopSpan = 0;          // cloned tiles sitting at the end, 0 when not looping
        let firstClone = null;    // the copy that marks the wrap point
        const MCARD_INTERVAL = 4000;
        const RESUME_AFTER = 6000;

        function gap() {
            return parseFloat(getComputedStyle(track).columnGap || "0") || 0;
        }
        function cardStep() {
            if (!cards.length) return 0;
            // one full tile plus the gap, measured from the live layout
            return cards[0].getBoundingClientRect().width + gap();
        }
        function perView() {
            // how many tiles the frame actually shows at once
            const step = cardStep();
            if (!step || !track.clientWidth) return 1;
            return Math.max(1, Math.min(cards.length, Math.round((track.clientWidth + gap()) / step)));
        }
        function lastIndex() {
            // the furthest position that still shows only real cards
            return Math.max(0, cards.length - perView());
        }
        function virtualLast() {
            // the furthest the strip can actually sit, cloned tiles included
            return lastIndex() + loopSpan;
        }
        function wrapIndex(i) {
            const n = cards.length;
            return n ? ((i % n) + n) % n : 0;
        }
        function nearestIndex() {
            const step = cardStep();
            if (!step) return 0;
            return Math.max(0, Math.min(virtualLast(), Math.round(track.scrollLeft / step)));
        }
        function paint() {
            if (dotsWrap) {
                const dots = dotsWrap.querySelectorAll("button");
                for (let i = 0; i < dots.length; i++) {
                    // one dot per card, and it tracks the card on the left, so the
                    // dot never lies about which offer is being shown
                    dots[i].classList.toggle("active", i === wrapIndex(index));
                }
            }
            // center-focus: the middle tile of the visible trio is the featured
            // one. index is the leftmost position and perView() is 3 here, so the
            // middle sits one step right of index. A plain class toggle; the zoom
            // itself is pure CSS transform, so layout and scroll math are untouched.
            const tiles = track.querySelectorAll(".mcard");
            const middle = tiles[Math.min(tiles.length - 1, index + Math.floor(perView() / 2))] || null;
            for (let t = 0; t < tiles.length; t++) {
                tiles[t].classList.toggle("is-center", tiles[t] === middle);
            }
        }
        function syncMedia() {
            // a cloned tile is never allowed to autoplay, so the video that is
            // actually on screen is the one real card that belongs there
            const shown = cards[wrapIndex(index)];
            cards.forEach(function (card) {
                const v = card.querySelector("video");
                if (!v) return;
                if (card === shown && v.hasAttribute("autoplay")) {
                    if (v.paused) { const p = v.play(); if (p && p.catch) p.catch(function () { }); }
                } else if (!v.paused) {
                    v.pause();
                }
            });
        }
        function settle() {
            const step = cardStep();
            if (!step) return;
            if (firstClone) {
                // Measured off the copy's own edge rather than off scrollLeft.
                // scrollLeft lands on fractional values on a scaled screen, and
                // comparing that to a computed target is how a loop ends up
                // parked on the last card waiting for a pixel it cannot reach.
                // Asking the layout where the copy actually is cannot drift.
                //
                // drift is how far the copy sits to the right of the track's left
                // edge, so it starts large and falls to zero as the copy comes up
                // flush, then goes negative once the copy is past. The wrap is
                // therefore drift at or below a pixel, not at or above one: the
                // other way round folds the strip back to the start on every
                // scroll and the loop never leaves the first card.
                const drift = firstClone.getBoundingClientRect().left
                    - track.getBoundingClientRect().left;
                if (drift <= 1) {
                    // the copy is exactly where card one was, so putting the scroll
                    // back to zero moves nothing the eye can catch. The strip has
                    // come all the way round without the jump a wrap would show.
                    index = 0;
                    track.scrollTo({ left: 0, behavior: "auto" });
                    paint();
                    syncMedia();
                    return;
                }
            }
            index = nearestIndex();
            paint();
            syncMedia();
        }
        function scrollToCard(i, smooth) {
            const step = cardStep();
            if (!step) return;
            index = Math.max(0, Math.min(virtualLast(), i));
            track.scrollTo({ left: index * step, behavior: smooth ? "smooth" : "auto" });
            paint();
            syncMedia();
        }
        function stop() {
            if (timer) { clearInterval(timer); timer = null; }
        }
        function play() {
            stop();
            if (resumeTimer) { clearTimeout(resumeTimer); resumeTimer = null; }
            if (virtualLast() < 1) return;   // everything already fits, nothing to advance
            timer = setInterval(function () {
                if (document.hidden) return;
                // wrap round rather than stopping: past the last real position the
                // strip is sitting on the copies, which settle() folds back to zero
                scrollToCard(index + 1, true);
            }, MCARD_INTERVAL);
        }
        function scheduleResume() {
            // a swipe stops the loop, but a loop that never starts again is not a
            // loop, so it picks itself back up once the finger has been still
            if (resumeTimer) clearTimeout(resumeTimer);
            resumeTimer = setTimeout(function () {
                resumeTimer = null;
                play();
            }, RESUME_AFTER);
        }

        // ---- the loop -------------------------------------------------------
        // A native scroll-snap scroller stops dead at the end of its own content
        // and cannot go past it, so looping means repeating the leading tiles at
        // the end. Scrolling onto the copy is what makes the wrap seamless, and
        // the moment the copy is flush left the scroll is folded back to zero
        // without moving. This is only worth doing past two cards: with one or
        // two the layout is a static grid rather than a strip, and with four or
        // more the frame only ever shows a trio, so there is always another
        // offer waiting and stopping used to leave a dead strip with a tile
        // half off. (With exactly three every tile already fits, so the strip
        // stays static and the loop bails out below.)
        function clearLoop() {
            Array.prototype.slice.call(track.querySelectorAll(".mcard-clone"))
                .forEach(function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
            loopSpan = 0;
            firstClone = null;
        }
        function buildLoop() {
            clearLoop();
            if (cards.length < 3) return;   // one or two: a grid, not a strip
            if (lastIndex() < 1) return;    // the last pair is already in frame
            // One tile more than the frame shows, and the spare is the point.
            // Repeating exactly perView() copies puts the wrap position at the
            // very last pixel the scroller can reach, so a rounding difference in
            // the 50% tile widths leaves the target one pixel out of bounds and the
            // loop silently stalls on the final card. One extra copy leaves about
            // half a frame of slack past the wrap, which is comfortably enough.
            cards.slice(0, perView() + 1).forEach(function (card) {
                const copy = card.cloneNode(true);
                copy.classList.add("mcard-clone");
                // a copy is scenery for the loop and never a second way to the
                // same offer: out of the tab order and away from a screen reader
                copy.setAttribute("aria-hidden", "true");
                copy.setAttribute("tabindex", "-1");
                copy.removeAttribute("href");
                copy.removeAttribute("target");
                Array.prototype.slice.call(copy.querySelectorAll("a[href], button, video, [tabindex]"))
                    .forEach(function (el) {
                        el.setAttribute("tabindex", "-1");
                        // two copies of one autoplaying video is double audio
                        el.removeAttribute("autoplay");
                        el.removeAttribute("loop");
                    });
                track.appendChild(copy);
                if (!firstClone) firstClone = copy;
                loopSpan++;
            });
        }
        function buildDots() {
            if (!dotsWrap) return;
            dotsWrap.innerHTML = "";
            // one dot per card, so a dot is a card and not an ambiguous offset
            for (let i = 0; i < cards.length; i++) {
                const d = document.createElement("button");
                d.type = "button";
                d.setAttribute("aria-label", "Go to promo " + (i + 1) + " of " + cards.length);
                d.addEventListener("click", function () {
                    stop();
                    scrollToCard(i, true);
                    scheduleResume();
                });
                dotsWrap.appendChild(d);
            }
        }
        buildLoop();
        buildDots();
        paint();
        syncMedia();
        let rafPending = false;
        track.addEventListener("scroll", function () {
            // scroll fires a lot during momentum; only re-read the index once
            // per frame instead of on every event
            if (rafPending) return;
            rafPending = true;
            requestAnimationFrame(function () {
                rafPending = false;
                settle();
            });
        });
        ["touchstart", "pointerdown", "wheel"].forEach(function (ev) {
            track.addEventListener(ev, function () { stop(); scheduleResume(); }, { passive: true });
        });
        document.addEventListener("visibilitychange", function () {
            if (document.hidden) stop();
            else if (!timer) play();
        });
        // a rotate or a window resize can change how many tiles fit, which changes
        // both the step and how many copies the loop needs
        let resizeTimer = null;
        window.addEventListener("resize", function () {
            if (resizeTimer) clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function () {
                resizeTimer = null;
                buildLoop();
                buildDots();
                settle();
            }, 200);
        });
        // only autoplay once the strip is actually on screen
        if ("IntersectionObserver" in window) {
            const io = new IntersectionObserver(function (entries) {
                entries.forEach(function (en) {
                    if (en.isIntersecting) play();
                    else stop();
                });
            }, { threshold: 0.35 });
            io.observe(mcardStrip);
        } else {
            play();
        }
    }

    // Hero image slider (3 per view on desktop, 2 on phones, auto-play).
    // Phones hide the arrow buttons and swipe instead (touch handlers below).
    const heroSlider = document.getElementById("heroSlider");
    if (heroSlider) {
        const slides = heroSlider.querySelectorAll(".slide");
        const slidesWrap = heroSlider.querySelector(".slides-wrap");
        const viewport = heroSlider.querySelector(".slider-viewport");
        const dotsWrap = heroSlider.querySelector(".slide-dots");
        const prevBtn = heroSlider.querySelector(".car-nav.prev");
        const nextBtn = heroSlider.querySelector(".car-nav.next");
        const total = slides.length;
        const isPhone = function () { return window.matchMedia("(max-width: 768px)").matches; };
        function perView() {
            if (total <= 1) return 1;
            if (isPhone()) return 2;
            return total >= 3 ? 3 : 2;
        }
        function stepPct() { return 100 / perView(); }
        function maxIdx() { return Math.max(0, total - perView()); }
        function paintClasses() {
            heroSlider.classList.toggle("single-view", !isPhone() && total < 3);
            heroSlider.classList.toggle("solo-view", total === 1);
        }
        let current = 0;
        let timer = null;
        const INTERVAL = 3500;

        function buildDots() {
            const dotCount = maxIdx() + 1;
            dotsWrap.innerHTML = "";
            for (let i = 0; i < dotCount; i++) {
                const dot = document.createElement("button");
                dot.setAttribute("aria-label", "Go to slide " + (i + 1));
                dot.addEventListener("click", function () {
                    go(i);
                    restart();
                });
                dotsWrap.appendChild(dot);
            }
        }
        function go(i) {
            current = Math.max(0, Math.min(i, maxIdx()));
            slidesWrap.style.transform = "translateX(" + (-current * stepPct()) + "%)";
            const dots = dotsWrap.querySelectorAll("button");
            dots.forEach(function (d, idx) {
                d.classList.toggle("active", idx === current);
            });
        }
        function restart() {
            clearInterval(timer);
            timer = setInterval(function () {
                go(current >= maxIdx() ? 0 : current + 1);
            }, INTERVAL);
        }
        function start() {
            if (heroSlider._paused) return;
            restart();
        }
        function stop() {
            clearInterval(timer);
            heroSlider._paused = true;
        }
        heroSlider.addEventListener("mouseenter", stop);
        heroSlider.addEventListener("mouseleave", function () {
            heroSlider._paused = false;
            restart();
        });
        // touch swipe (phones have no arrows): a mostly-horizontal swipe
        // steps one slide, vertical movement stays with the page scroll
        if (viewport) {
            let tx = 0, ty = 0, tracking = false;
            viewport.addEventListener("touchstart", function (e) {
                if (!e.touches.length) return;
                tracking = true;
                tx = e.touches[0].clientX;
                ty = e.touches[0].clientY;
            }, { passive: true });
            viewport.addEventListener("touchend", function (e) {
                if (!tracking) return;
                tracking = false;
                if (!e.changedTouches.length) return;
                const dx = e.changedTouches[0].clientX - tx;
                const dy = e.changedTouches[0].clientY - ty;
                if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) {
                    go(dx < 0 ? current + 1 : current - 1);
                    restart();
                }
            });
        }
        // crossing the phone/desktop breakpoint re-lays the track
        const slideMq = window.matchMedia("(max-width: 768px)");
        const resync = function () { paintClasses(); buildDots(); go(current); };
        if (slideMq.addEventListener) slideMq.addEventListener("change", resync);
        else if (slideMq.addListener) slideMq.addListener(resync);
        paintClasses();
        buildDots();
        if (prevBtn) prevBtn.addEventListener("click", function () { go(current - 1); restart(); });
        if (nextBtn) nextBtn.addEventListener("click", function () { go(current + 1); restart(); });
        go(0);
        start();
    }

    // Appointment type toggle
    const typeBtns = document.querySelectorAll(".type-btn, .dp-type-btn");
    const typeHidden = document.getElementById("appointmentType");
    typeBtns.forEach(function (btn) {
        btn.addEventListener("click", function () {
            typeBtns.forEach(function (b) { b.classList.remove("selected"); });
            btn.classList.add("selected");
            if (typeHidden) typeHidden.value = btn.getAttribute("data-type");
        });
    });

    // Booking form validation
    const bookingForm = document.getElementById("bookingForm");
    if (bookingForm) {
        bookingForm.addEventListener("submit", function (e) {
            const slot = document.getElementById("slot");
            if (!slot || !slot.value) {
                e.preventDefault();
                alert("Please select an appointment time from the available slots.");
            }
        });
    }

    // Booking request modal
    const bookingModal = document.getElementById("bookingModal");
    if (bookingModal) {
        const form = document.getElementById("bookingRequestForm");
        const doctorInput = document.getElementById("bkDoctor");
        const doctorIdInput = document.getElementById("bkDoctorId");
        const suggestBox = document.getElementById("bkSuggest");
        const submitBtn = form.querySelector(".book-submit");
        const errorBox = document.getElementById("bkError");
        const successBox = document.getElementById("bkSuccess");
        const stepType = document.getElementById("bkStepType");
        const visitInput = document.getElementById("bkVisitTypeInput");
        const visitSummary = document.getElementById("bkVisitSummary");
        const visitTypeLabel = document.getElementById("bkVisitType");
        const visitIconBox = document.getElementById("bkVisitIcon");
        const changeBtn = document.getElementById("bkChangeVisit");
        const modalBackBtn = document.getElementById("bkModalBack");
        const stepDots = document.getElementById("bkStepDots");
        const modalSub = document.getElementById("bkModalSub");
        const callBtn = document.getElementById("bkCallBtn");
        const waBtn = document.getElementById("bkWaBtn");
        const profileBtn = document.getElementById("bkProfileBtn");
        // Server-rendered fallbacks (site phone / WhatsApp / browse-all) kept so
        // the shortcuts still do something before a doctor is picked.
        const SITE_CALL = callBtn ? callBtn.getAttribute("href") : "";
        const SITE_WA = waBtn ? waBtn.getAttribute("href") : "";
        const SITE_PROFILE = profileBtn ? profileBtn.getAttribute("href") : "";
        const SUB_FORM = "Fill in your details and our team will confirm your booking.";
        const ICONS = {
            "Clinic Visit": '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M19 8h-2V5a1 1 0 0 0-1-1h-3a1 1 0 0 0-1 1v3H5a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1zm-8-3h2v3h-2V5zm6 14H7v-3h4v1h2v-1h4v3zm-4-5H7v-2h2v-2h2v2h2v2h-2z"/></svg>',
            "Online Check-up": '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M17 1H7a2 2 0 0 0-2 2v18a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3a2 2 0 0 0-2-2zm-5 20a1.2 1.2 0 1 1 0-2.4 1.2 1.2 0 0 1 0 2.4zm5-4H7V4h10v13z"/></svg>'
        };
        const THEMES = {
            "Clinic Visit": { c: "#12876f", bg: "#e3f6ef", bd: "rgba(18,135,111,.28)" },
            "Online Check-up": { c: "#2b6fd4", bg: "#e6f0fe", bd: "rgba(43,111,212,.28)" }
        };
        let doctorCache = [];
        let debounceTimer = null;
        let currentStep = "type";
        let stepHistory = [];
        let chosenVisit = "";
        const MOBILE_MQ = window.matchMedia("(max-width: 768px)");

        function setStep(step, opts) {
            opts = opts || {};
            if (opts.reset) {
                stepHistory = [];
            } else if (!opts.back && currentStep !== step) {
                stepHistory.push(currentStep);
            }
            currentStep = step;
            // lets CSS target the active step (phones hide the modal heading
            // and the close button on the form step)
            bookingModal.dataset.step = step;
            if (step === "type") {
                stepType.hidden = false;
                form.hidden = true;
                modalSub.textContent = "Choose how you would like to meet the doctor.";
                if (stepDots) stepDots.hidden = false;
                setStepDot(0);
            } else {
                stepType.hidden = true;
                form.hidden = false;
                visitSummary.hidden = false;
                modalSub.textContent = SUB_FORM;
                if (stepDots) stepDots.hidden = true;
                // the date field is hidden on phones, so default it or the
                // time slots and the submit check would both fail
                if (ensureMobileDate() && slotGrid) loadSlots();
                setTimeout(function () { if (doctorInput && !doctorInput.value) doctorInput.focus(); }, 100);
            }
        }
        function setStepDot(idx) {
            if (!stepDots) return;
            stepDots.querySelectorAll(".book-step-dot").forEach(function (d, i) {
                d.classList.toggle("active", i === idx);
            });
        }
        function selectVisitType(value) {
            chosenVisit = value;
            visitInput.value = value;
            visitTypeLabel.textContent = value;
            visitIconBox.innerHTML = ICONS[value] || "";
            const th = THEMES[value];
            if (th) {
                visitSummary.style.setProperty("--vs-c", th.c);
                visitSummary.style.setProperty("--vs-bg", th.bg);
                visitSummary.style.setProperty("--vs-bd", th.bd);
            }
            // A doctor picked under the old type may not fit the new one (an
            // in-person doctor after switching to Online Check-up); drop it so
            // the suggestion list and the summary stay consistent.
            if (doctorIdInput.value) {
                const sel = doctorCache.filter(function (d) { return String(d.id) === String(doctorIdInput.value); })[0];
                if (sel && !doctorFitsVisit(sel)) {
                    doctorInput.value = "";
                    doctorIdInput.value = "";
                    updateContact(null);
                }
            }
            setStep("form");
        }

        function doctorFitsVisit(d) {
            // Online Check-up only lists doctors who actually consult online.
            return chosenVisit !== "Online Check-up" || !!d.online;
        }
        function doctorPool() {
            return doctorCache.filter(doctorFitsVisit);
        }

        function waDigits(raw) {
            // WhatsApp needs a full international number; local Pakistani
            // numbers written as 0300... are upgraded to 92300...
            var d = String(raw || "").replace(/[^0-9]/g, "");
            if (!d) return "";
            if (d.charAt(0) === "0") d = "92" + d.slice(1);
            return d;
        }
        function updateContact(doc) {
            if (!callBtn || !waBtn || !profileBtn) return;
            var dial = doc ? (doc.phone || doc.whatsapp_number || "") : "";
            var waNum = doc ? (doc.whatsapp_number || doc.phone || "") : "";
            callBtn.href = dial ? ("tel:" + String(dial).replace(/[^0-9+]/g, "")) : SITE_CALL;
            var wa = waDigits(waNum);
            waBtn.href = wa ? ("https://wa.me/" + wa) : SITE_WA;
            profileBtn.href = (doc && doc.id) ? ("/doctor/" + doc.id) : SITE_PROFILE;
        }

        function openModal() {
            bookingModal.hidden = false;
            document.body.style.overflow = "hidden";
            successBox.hidden = true;
            errorBox.hidden = true;
            visitSummary.style.removeProperty("--vs-c");
            visitSummary.style.removeProperty("--vs-bg");
            visitSummary.style.removeProperty("--vs-bd");
            setStep("type", { reset: true });
            updateContact(null);
            if (doctorCache.length === 0) {
                fetch("/api/doctors-list")
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        doctorCache = data;
                        // the field may already be focused while the list was
                        // loading; fill the panel now that it is here
                        if (document.activeElement === doctorInput && !doctorInput.value.trim()) {
                            renderSuggestions(doctorPool());
                        }
                    })
                    .catch(function () {});
            }
        }
        function closeModal() {
            bookingModal.hidden = true;
            document.body.style.overflow = "";
            suggestBox.classList.remove("open");
        }

        document.querySelectorAll(".js-book-now").forEach(function (btn) {
            btn.addEventListener("click", function () {
                openModal();
                // Mobile hero buttons preselect the visit type so the user does
                // not have to tap through the "type" step again.
                var preset = btn.getAttribute("data-book-visit");
                if (preset) selectVisitType(preset);
            });
        });
        bookingModal.querySelectorAll("[data-book-close]").forEach(function (el) {
            el.addEventListener("click", closeModal);
        });
        stepType.querySelectorAll(".book-type-card").forEach(function (card) {
            card.addEventListener("click", function () {
                selectVisitType(card.getAttribute("data-visit"));
            });
        });
        if (changeBtn) {
            changeBtn.addEventListener("click", function () { setStep("type"); });
        }
        if (modalBackBtn) {
            modalBackBtn.addEventListener("click", function () {
                // On phones the form is the only step worth going back to, and
                // re-showing the bare visit-type window underneath it just
                // looked unfinished - leave the booking instead. Change on the
                // visit chip is what reopens it.
                if (MOBILE_MQ.matches) {
                    closeModal();
                    return;
                }
                // walk back through the steps we came from; if the type step is
                // where the modal was opened, there is nothing to go back to
                // except the page itself
                if (stepHistory.length) {
                    setStep(stepHistory.pop(), { back: true });
                } else {
                    closeModal();
                }
            });
        }
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && !bookingModal.hidden) closeModal();
        });

        doctorInput.addEventListener("input", function () {
            const q = doctorInput.value.trim();
            clearTimeout(debounceTimer);
            // Any edit invalidates the current pick, so shortcuts fall back to
            // the site line until a suggestion is chosen again.
            if (doctorIdInput.value) updateContact(null);
            doctorIdInput.value = "";
            if (q.length < 1) {
                suggestBox.classList.remove("open");
                doctorIdInput.value = "";
                renderSuggestions(doctorPool());
                return;
            }
            debounceTimer = setTimeout(function () {
                const matches = doctorPool().filter(
                    function (d) {
                        return (d.doctor_name + " " + d.specialty_name + " " + d.city_name).toLowerCase().indexOf(q.toLowerCase()) !== -1;
                    }
                );
                renderSuggestions(matches);
            }, 160);
        });

        function hmToMin(t) {
            // "7:00 AM" / "12:30 PM" -> minutes past midnight
            var m = /(\d{1,2}):(\d{2})\s*([AP]M)/i.exec(String(t || ""));
            if (!m) return null;
            var h = parseInt(m[1], 10) % 12;
            if (/PM/i.test(m[3])) h += 12;
            return h * 60 + parseInt(m[2], 10);
        }
        function doctorTimingText(d) {
            if (chosenVisit !== "Online Check-up") return "";
            if (d.today_closed) return "Closed today";
            if (d.today_open && d.today_close) return d.today_open + " \u2013 " + d.today_close;
            if (d.today_open) return d.today_open + " onwards";
            return "";
        }
        function nowMinutes() {
            var n = new Date();
            return n.getHours() * 60 + n.getMinutes();
        }
        function doctorOnlineNow(d) {
            // Green "Online" only while the current clock time sits inside the
            // doctor's own timing for today; outside it the label stays but
            // loses its colour.
            if (!d.online || d.today_closed) return false;
            var o = hmToMin(d.today_open), c = hmToMin(d.today_close), now = nowMinutes();
            if (o === null) return false;
            if (c === null) return now >= o;
            return now >= o && now <= c;
        }

        function renderSuggestions(matches) {
            suggestBox.innerHTML = "";
            if (matches.length === 0) {
                suggestBox.classList.remove("open");
                return;
            }
            const head = document.createElement("div");
            head.className = "book-suggest-head";
            head.textContent = matches.length + (matches.length === 1 ? " doctor found" : " doctors found");
            suggestBox.appendChild(head);
            matches.forEach(function (d) {
                const item = document.createElement("div");
                item.className = "book-suggest-item";
                const main = document.createElement("div");
                main.className = "bs-main";
                const fee = d.fee && d.fee > 0 ? "Rs " + d.fee : "Fee on request";
                const online = d.online
                    ? '<span class="bs-badge bs-online ' + (doctorOnlineNow(d) ? "on" : "off") + '">Online</span>'
                    : '<span class="bs-badge bs-offline">In person</span>';
                const left = document.createElement("div");
                left.className = "bs-left";
                const nm = document.createElement("strong");
                nm.textContent = d.doctor_name;
                const meta = document.createElement("small");
                meta.textContent = d.specialty_name + " \u00b7 " + d.city_name;
                left.appendChild(nm);
                left.appendChild(meta);
                const right = document.createElement("div");
                right.className = "bs-right";
                const feeEl = document.createElement("span");
                feeEl.className = "bs-fee";
                feeEl.textContent = fee;
                right.appendChild(feeEl);
                right.insertAdjacentHTML("beforeend", online);
                main.appendChild(left);
                main.appendChild(right);
                item.appendChild(main);
                const timing = doctorTimingText(d);
                if (timing) {
                    const tm = document.createElement("span");
                    tm.className = "bs-timing";
                    tm.innerHTML = '<svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg><span></span>';
                    tm.querySelector("span").textContent = timing;
                    item.appendChild(tm);
                }
                item.addEventListener("mousedown", function (e) {
                    e.preventDefault();
                    selectDoctor(d);
                });
                suggestBox.appendChild(item);
                item.addEventListener("mousedown", function (e) {
                    e.preventDefault();
                    selectDoctor(d);
                });
                suggestBox.appendChild(item);
            });
            suggestBox.classList.add("open");
        }
        function selectDoctor(d) {
            doctorInput.value = d.doctor_name;
            doctorIdInput.value = d.id;
            suggestBox.classList.remove("open");
            updateContact(d);
            loadSlots();
        }
        doctorInput.addEventListener("focus", function () {
            if (doctorCache.length && !doctorInput.value.trim()) {
                renderSuggestions(doctorPool());
            }
        });
        doctorInput.addEventListener("blur", function () {
            setTimeout(function () { suggestBox.classList.remove("open"); }, 150);
        });

        // --- date + time slots -------------------------------------------
        const dateInput = document.getElementById("bkDate");
        const slotGrid = document.getElementById("bkSlotGrid");
        const slotInput = document.getElementById("bkSlot");
        const GENERIC_SLOTS = [
            "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM",
            "12:00 PM", "12:30 PM", "05:00 PM", "05:30 PM", "06:00 PM", "06:30 PM",
            "07:00 PM", "07:30 PM"
        ];

        function setSlotHint(text) {
            if (!slotGrid) return;
            slotGrid.innerHTML = "";
            var p = document.createElement("p");
            p.className = "book-slots-hint";
            p.textContent = text;
            slotGrid.appendChild(p);
        }

        function ensureMobileDate() {
            // The Preferred Date field is hidden on phones, so the appointment
            // would otherwise have no date and fail the submit check.
            if (!dateInput || !MOBILE_MQ.matches) return false;
            if (dateInput.value) return false;
            var today = new Date();
            var iso = today.getFullYear() + "-" + String(today.getMonth() + 1).padStart(2, "0") + "-" + String(today.getDate()).padStart(2, "0");
            dateInput.value = (dateInput.min && dateInput.min > iso) ? dateInput.min : iso;
            return true;
        }

        function autoPickSlot() {
            // Preferred Time is hidden on phones, so pre-select the first
            // available slot - otherwise submit fails with no way to pick one.
            if (!MOBILE_MQ.matches || !slotGrid) return;
            var first = slotGrid.querySelector(".book-slot");
            if (first) first.click();
        }

        function loadSlots() {
            if (!slotGrid) return;
            var dateVal = dateInput ? dateInput.value : "";
            var doctorId = doctorIdInput.value || "";
            slotInput.value = "";
            if (!dateVal) {
                if (ensureMobileDate()) dateVal = dateInput.value;
                else return setSlotHint("Pick a date first");
            }
            if (dateInput.min && dateVal < dateInput.min) return setSlotHint("Please pick today or a later date");

            slotGrid.innerHTML = '<p class="book-slots-hint">Loading slots...</p>';
            var url = "/slots";
            var parts = [];
            if (doctorId) parts.push("doctor_id=" + encodeURIComponent(doctorId));
            parts.push("date=" + encodeURIComponent(dateVal));
            fetch(url + "?" + parts.join("&"))
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    var list = (data && data.slots && data.slots.length) ? data.slots : GENERIC_SLOTS;
                    slotGrid.innerHTML = "";
                    if (!list.length) {
                        return setSlotHint("No slots available on this date. Please try another day.");
                    }
                    list.forEach(function (t) {
                        var b = document.createElement("button");
                        b.type = "button";
                        b.className = "book-slot";
                        b.textContent = t;
                        b.addEventListener("click", function () {
                            slotInput.value = t;
                            slotGrid.querySelectorAll(".book-slot").forEach(function (x) {
                                x.classList.remove("selected");
                            });
                            b.classList.add("selected");
                        });
                        slotGrid.appendChild(b);
                    });
                    autoPickSlot();
                })
                .catch(function () {
                    slotGrid.innerHTML = "";
                    GENERIC_SLOTS.forEach(function (t) {
                        var b = document.createElement("button");
                        b.type = "button";
                        b.className = "book-slot";
                        b.textContent = t;
                        b.addEventListener("click", function () {
                            slotInput.value = t;
                            slotGrid.querySelectorAll(".book-slot").forEach(function (x) {
                                x.classList.remove("selected");
                            });
                            b.classList.add("selected");
                        });
                        slotGrid.appendChild(b);
                    });
                    autoPickSlot();
                });
        }
        if (dateInput) {
            dateInput.addEventListener("change", loadSlots);
        }

        form.addEventListener("submit", function (e) {
            e.preventDefault();
            const doctor = doctorInput.value.trim();
            const name = document.getElementById("bkName").value.trim();
            const whatsapp = document.getElementById("bkWhatsapp").value.trim();
            const visitType = visitInput.value;
            const dateVal = dateInput ? dateInput.value : "";
            const slotVal = slotInput ? slotInput.value : "";

            errorBox.hidden = true;
            if (!name) return showError("Please enter the patient name.");
            if (!whatsapp) return showError("Please enter your WhatsApp number.");
            if (!/^\+?92?\d{10,13}$/.test(whatsapp.replace(/[\s-]/g, ""))) {
                return showError("Please enter a valid WhatsApp number (e.g. 0300 1234567).");
            }
            if (!dateVal) return showError("Please choose your preferred date.");
            if (!slotVal) return showError("Please choose a time slot.");

            const payload = new URLSearchParams();
            payload.append("doctor_id", doctorIdInput.value || "");
            payload.append("doctor_name", doctor);
            payload.append("patient_name", name);
            payload.append("whatsapp", whatsapp);
            payload.append("visit_type", visitType);
            payload.append("appointment_date", dateVal);
            payload.append("slot", slotVal);
            payload.append("notes", document.getElementById("bkNotes").value.trim());

            submitBtn.disabled = true;
            submitBtn.classList.add("loading");
            fetch("/booking-request", {
                method: "POST",
                body: payload,
                headers: { "Content-Type": "application/x-www-form-urlencoded" }
            })
                .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
                .then(function (res) {
                    submitBtn.disabled = false;
                    submitBtn.classList.remove("loading");
                    if (res.ok && res.data.ok) {
                        form.hidden = true;
                        successBox.hidden = false;
                        form.reset();
                        doctorIdInput.value = "";
                        if (slotGrid) setSlotHint("Pick a date first");
                        visitInput.value = chosenVisit || "Clinic Visit";
                    } else {
                        showError((res.data && res.data.error) || "Something went wrong. Please try again.");
                    }
                })
                .catch(function () {
                    submitBtn.disabled = false;
                    submitBtn.classList.remove("loading");
                    showError("Could not send your request. Please try again.");
                });
        });

        function showError(msg) {
            errorBox.textContent = msg;
            errorBox.hidden = false;
        }
    }

    // Hero search: rotating placeholder hints on phones. One hint at a time
    // (doctor, specialty, hospital, condition) so the short mobile bar never
    // truncates into "condi...xyz". Pauses while the user types or focuses,
    // desktop keeps the full static text.
    const heroQ = document.querySelector('.hero-search input[name="q"]');
    if (heroQ) {
        const PH_FULL = "Search by doctor, specialty, hospital or condition...";
        const PH_HINTS = [
            "Search by doctor...",
            "Search by specialty...",
            "Search by hospital...",
            "Search by condition..."
        ];
        const phMq = window.matchMedia("(max-width: 768px)");
        let phIdx = 0;
        let phTimer = null;
        function phStop() {
            if (phTimer) { clearInterval(phTimer); phTimer = null; }
            heroQ.classList.remove("ph-fade");
        }
        function phTick() {
            if (document.activeElement === heroQ || heroQ.value) return;
            heroQ.classList.add("ph-fade");
            setTimeout(function () {
                if (document.activeElement === heroQ || heroQ.value) {
                    heroQ.classList.remove("ph-fade");
                    return;
                }
                phIdx = (phIdx + 1) % PH_HINTS.length;
                heroQ.setAttribute("placeholder", PH_HINTS[phIdx]);
                heroQ.classList.remove("ph-fade");
            }, 300);
        }
        function phSync() {
            phStop();
            if (!phMq.matches) {
                heroQ.setAttribute("placeholder", PH_FULL);
                return;
            }
            phIdx = 0;
            heroQ.setAttribute("placeholder", PH_HINTS[0]);
            phTimer = setInterval(phTick, 3000);
        }
        if (phMq.addEventListener) phMq.addEventListener("change", phSync);
        else if (phMq.addListener) phMq.addListener(phSync);
        phSync();
    }
});