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
        const stepType = document.getElementById("bkStepType");
        const visitInput = document.getElementById("bkVisitTypeInput");
        const visitSummary = document.getElementById("bkVisitSummary");
        const visitTypeLabel = document.getElementById("bkVisitType");
        const visitIconBox = document.getElementById("bkVisitIcon");
        const changeBtn = document.getElementById("bkChangeVisit");
        const modalBackBtn = document.getElementById("bkModalBack");
        const stepDots = document.getElementById("bkStepDots");
        const modalSub = document.getElementById("bkModalSub");
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
            setStep("form");
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
            if (q.length < 1) {
                suggestBox.classList.remove("open");
                doctorIdInput.value = "";
                renderSuggestions(doctorCache);
                return;
            }
            debounceTimer = setTimeout(function () {
                const matches = doctorCache.filter(
                    function (d) {
                        return (d.doctor_name + " " + d.specialty_name + " " + d.city_name).toLowerCase().indexOf(q.toLowerCase()) !== -1;
                    }
                );
                renderSuggestions(matches);
            }, 160);
        });

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
                const fee = d.fee && d.fee > 0 ? "Rs " + d.fee : "Fee on request";
                const online = d.online ? '<span class="bs-badge bs-online">Online</span>' : '<span class="bs-badge bs-offline">In person</span>';
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
                item.appendChild(left);
                item.appendChild(right);
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
            loadSlots();
        }
        doctorInput.addEventListener("focus", function () {
            if (doctorCache.length && !doctorInput.value.trim()) {
                renderSuggestions(doctorCache);
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
});