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

    // Hero image slider (3 per view, auto-play)
    const heroSlider = document.getElementById("heroSlider");
    if (heroSlider) {
        const slides = heroSlider.querySelectorAll(".slide");
        const slidesWrap = heroSlider.querySelector(".slides-wrap");
        const dotsWrap = heroSlider.querySelector(".slide-dots");
        const prevBtn = heroSlider.querySelector(".car-nav.prev");
        const nextBtn = heroSlider.querySelector(".car-nav.next");
        const total = slides.length;
        const STEP = total >= 3 ? 100 / 3 : 100;
        const maxIndex = total >= 3 ? total - 3 : 0;
        if (total < 3) heroSlider.classList.add("single-view");
        let current = 0;
        let timer = null;
        const INTERVAL = 3500;

        function buildDots() {
            const dotCount = maxIndex + 1;
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
            current = Math.max(0, Math.min(i, maxIndex));
            slidesWrap.style.transform = "translateX(" + (-current * STEP) + "%)";
            const dots = dotsWrap.querySelectorAll("button");
            dots.forEach(function (d, idx) {
                d.classList.toggle("active", idx === current);
            });
        }
        function restart() {
            clearInterval(timer);
            timer = setInterval(function () {
                go(current >= maxIndex ? 0 : current + 1);
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
        let doctorCache = [];
        let debounceTimer = null;

        function openModal() {
            bookingModal.hidden = false;
            document.body.style.overflow = "hidden";
            successBox.hidden = true;
            form.hidden = false;
            errorBox.hidden = true;
            setTimeout(function () {
                const d = document.getElementById("bkDoctor");
                if (d && !d.value) d.focus();
            }, 100);
            if (doctorCache.length === 0) {
                fetch("/api/doctors-list")
                    .then(function (r) { return r.json(); })
                    .then(function (data) { doctorCache = data; })
                    .catch(function () {});
            }
        }
        function closeModal() {
            bookingModal.hidden = true;
            document.body.style.overflow = "";
            suggestBox.classList.remove("open");
        }

        document.querySelectorAll(".js-book-now").forEach(function (btn) {
            btn.addEventListener("click", openModal);
        });
        bookingModal.querySelectorAll("[data-book-close]").forEach(function (el) {
            el.addEventListener("click", closeModal);
        });
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && !bookingModal.hidden) closeModal();
        });

        doctorInput.addEventListener("input", function () {
            const q = doctorInput.value.trim();
            clearTimeout(debounceTimer);
            if (q.length < 2) {
                suggestBox.classList.remove("open");
                doctorIdInput.value = "";
                return;
            }
            debounceTimer = setTimeout(function () {
                const matches = doctorCache.filter(
                    function (d) {
                        return (d.doctor_name + " " + d.specialty_name + " " + d.city_name).toLowerCase().indexOf(q.toLowerCase()) !== -1;
                    }
                ).slice(0, 6);
                renderSuggestions(matches);
            }, 160);
        });

        function renderSuggestions(matches) {
            suggestBox.innerHTML = "";
            if (matches.length === 0) {
                suggestBox.classList.remove("open");
                return;
            }
            matches.forEach(function (d, idx) {
                const item = document.createElement("div");
                item.className = "book-suggest-item";
                item.innerHTML = "<strong>" + d.doctor_name + "</strong><small>" + d.specialty_name + " \u00b7 " + d.city_name + "</small>";
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
        }
        doctorInput.addEventListener("blur", function () {
            setTimeout(function () { suggestBox.classList.remove("open"); }, 150);
        });

        form.querySelectorAll(".book-visit-opt").forEach(function (opt) {
            opt.addEventListener("click", function () {
                form.querySelectorAll(".book-visit-opt").forEach(function (o) { o.classList.remove("selected"); });
                opt.classList.add("selected");
                opt.querySelector("input").checked = true;
            });
        });

        form.addEventListener("submit", function (e) {
            e.preventDefault();
            const doctor = doctorInput.value.trim();
            const name = document.getElementById("bkName").value.trim();
            const whatsapp = document.getElementById("bkWhatsapp").value.trim();
            const visitType = form.querySelector('input[name="visit_type"]:checked').value;

            errorBox.hidden = true;
            if (!doctor) return showError("Please select a doctor.");
            if (!name) return showError("Please enter your name.");
            if (!whatsapp) return showError("Please enter your WhatsApp number.");

            const payload = new URLSearchParams();
            payload.append("doctor_id", doctorIdInput.value || "");
            payload.append("doctor_name", doctor);
            payload.append("patient_name", name);
            payload.append("whatsapp", whatsapp);
            payload.append("mobile", document.getElementById("bkMobile").value.trim());
            payload.append("visit_type", visitType);
            payload.append("notes", document.getElementById("bkNotes").value.trim());

            submitBtn.disabled = true;
            submitBtn.classList.add("loading");
            fetch("/booking-request", {
                method: "POST",
                body: payload,
                headers: { "Content-Type": "application/x-www-form-urlencoded" }
            })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    submitBtn.disabled = false;
                    submitBtn.classList.remove("loading");
                    if (data.ok) {
                        form.hidden = true;
                        successBox.hidden = false;
                        form.reset();
                        doctorIdInput.value = "";
                    } else {
                        showError(data.error || "Something went wrong. Please try again.");
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

    // Hero banners drag / pin / resize (admin edit mode)
    const hbWrap = document.getElementById("heroBanners");
    if (hbWrap && hbWrap.getAttribute("data-admin") === "1") {
        const editToggle = document.getElementById("hbEditToggle");
        const saveBtn = document.getElementById("hbSave");
        const boxes = Array.prototype.slice.call(hbWrap.querySelectorAll(".hero-banner-box"));
        let editing = false;

        function toPct(v) { return v; }

        function applySavedPositions() {
            boxes.forEach(function (box) {
                const x = box.getAttribute("data-x");
                const y = box.getAttribute("data-y");
                const w = box.getAttribute("data-w");
                const h = box.getAttribute("data-h");
                if (x !== "" && y !== "") {
                    box.style.left = x + "%";
                    box.style.top = y + "px";
                }
                if (w) box.style.width = w + "px";
                if (h) box.style.height = h + "px";
            });
        }

        function layoutFlow() {
            // initial flow: center them in a row
            const gap = 14;
            let x = 0;
            boxes.forEach(function (box) {
                box.style.left = x + "px";
                box.style.top = "16px";
                box.style.width = "";
                box.style.height = "";
                x += (box.offsetWidth > 0 ? box.offsetWidth : 200) + gap;
            });
            hbWrap.style.minHeight = "190px";
        }

        function collectState() {
            return boxes.map(function (box) {
                const r = box.getBoundingClientRect();
                const wrapR = hbWrap.getBoundingClientRect();
                const px = Math.round(((r.left - wrapR.left) / wrapR.width) * 100 * 10) / 10;
                const py = Math.round(r.top - wrapR.top);
                const img = box.querySelector("img");
                return {
                    id: parseInt(box.getAttribute("data-id"), 10),
                    pos_x: Math.max(0, Math.min(100, px)),
                    pos_y: Math.max(0, py),
                    bw: Math.round(r.width),
                    bh: img ? Math.round(r.height) : Math.round(r.height),
                };
            });
        }

        function saveLayout() {
            saveBtn.disabled = true;
            saveBtn.textContent = "Saving...";
            fetch("/admin/hero-banners/save", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(collectState()),
            })
                .then(function (r) { return r.json(); })
                .then(function (d) {
                    saveBtn.disabled = false;
                    saveBtn.textContent = "Save";
                    if (d.ok) {
                        const st = document.querySelector(".hb-status");
                        if (st) { st.textContent = "\u2713 Position saved"; setTimeout(function () { st.textContent = ""; }, 2500); }
                    } else {
                        alert("Save failed. Try again.");
                    }
                })
                .catch(function () {
                    saveBtn.disabled = false;
                    saveBtn.textContent = "Save";
                    alert("Save failed. Try again.");
                });
        }

        function enterEdit() {
            editing = true;
            hbWrap.classList.add("editing");
            editToggle.querySelector("#hbEditLabel").textContent = "Done";
            boxes.forEach(function (box) { box.style.margin = "0"; box.style.position = "absolute"; });
            if (hbWrap.classList.contains("pinned")) {
                applySavedPositions();
            } else if (!hbWrap.dataset.posInit) {
                layoutFlow();
                hbWrap.dataset.posInit = "1";
            } else {
                applySavedPositions();
            }
        }

        function exitEdit() {
            editing = false;
            hbWrap.classList.remove("editing");
            editToggle.querySelector("#hbEditLabel").textContent = "Edit";
            boxes.forEach(function (box) {
                box.style.position = "";
                box.style.left = "";
                box.style.top = "";
            });
        }

        editToggle.addEventListener("click", function () {
            if (editing) exitEdit();
            else enterEdit();
        });
        saveBtn.addEventListener("click", saveLayout);

        // Drag
        function bindDrag(box) {
            let startX = 0, startY = 0, origLeft = 0, origTop = 0, dragging = false;
            box.addEventListener("pointerdown", function (e) {
                if (!editing || e.target.closest(".hb-resize")) return;
                e.preventDefault();
                dragging = true;
                startX = e.clientX;
                startY = e.clientY;
                origLeft = box.offsetLeft;
                origTop = box.offsetTop;
                box.classList.add("dragging");
                box.setPointerCapture(e.pointerId);
            });
            box.addEventListener("pointermove", function (e) {
                if (!dragging) return;
                const dx = e.clientX - startX;
                const dy = e.clientY - startY;
                box.style.left = (origLeft + dx) + "px";
                box.style.top = (origTop + dy) + "px";
            });
            box.addEventListener("pointerup", function (e) {
                if (!dragging) return;
                dragging = false;
                box.classList.remove("dragging");
                try { box.releasePointerCapture(e.pointerId); } catch (err) {}
            });
        }

        // Resize
        function bindResize(box) {
            const handle = box.querySelector(".hb-resize");
            if (!handle) return;
            let startX = 0, startY = 0, origW = 0, origH = 0, resizing = false;
            handle.addEventListener("pointerdown", function (e) {
                if (!editing) return;
                e.preventDefault();
                e.stopPropagation();
                resizing = true;
                startX = e.clientX;
                startY = e.clientY;
                origW = box.offsetWidth;
                origH = box.offsetHeight;
                const ratio = origW / origH;
                box._ratio = ratio;
                box.classList.add("dragging");
                handle.setPointerCapture(e.pointerId);
            });
            handle.addEventListener("pointermove", function (e) {
                if (!resizing) return;
                const dx = e.clientX - startX;
                const dy = e.clientY - startY;
                let w = Math.max(80, origW + dx);
                let h = Math.max(50, origH + dy);
                const ratio = box._ratio || (w / h);
                // maintain aspect ratio based on the larger delta
                if (Math.abs(dx) >= Math.abs(dy)) h = Math.round(w / ratio);
                else w = Math.round(h * ratio);
                box.style.width = w + "px";
                box.style.height = h + "px";
            });
            handle.addEventListener("pointerup", function (e) {
                if (!resizing) return;
                resizing = false;
                box.classList.remove("dragging");
                try { handle.releasePointerCapture(e.pointerId); } catch (err) {}
            });
        }

        boxes.forEach(function (box) {
            box.style.opacity = "1";
            bindDrag(box);
            bindResize(box);
        });

        if (hbWrap.dataset.posInit === "1") applySavedPositions();
    }
});