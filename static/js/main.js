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
        const stepDots = document.getElementById("bkStepDots");
        const modalSub = document.getElementById("bkModalSub");
        const SUB_FORM = "Fill in your details and our team will confirm your booking.";
        const ICONS = {
            "Clinic Visit": '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M12 2 1 9l11 7 9-5.72V17h2V9L12 2zm0 12.13L4.98 9.5 12 5.64l7.02 3.86L12 14.13z"/><path d="M5 15v3c0 2.21 3.13 4 7 4s7-1.79 7-4v-3l-7 4-7-4z"/></svg>',
            "Online Check-up": '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M4 13h16a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-5a1 1 0 0 1 1-1zm2.5-2a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5zM4 6a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6z"/></svg>'
        };
        let doctorCache = [];
        let debounceTimer = null;
        let currentStep = "type";
        let chosenVisit = "";

        function setStep(step) {
            currentStep = step;
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
            setStep("form");
        }

        function openModal() {
            bookingModal.hidden = false;
            document.body.style.overflow = "hidden";
            successBox.hidden = true;
            errorBox.hidden = true;
            setStep("type");
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
        stepType.querySelectorAll(".book-type-card").forEach(function (card) {
            card.addEventListener("click", function () {
                selectVisitType(card.getAttribute("data-visit"));
            });
        });
        if (changeBtn) {
            changeBtn.addEventListener("click", function () { setStep("type"); });
        }
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

        form.addEventListener("submit", function (e) {
            e.preventDefault();
            const doctor = doctorInput.value.trim();
            const name = document.getElementById("bkName").value.trim();
            const whatsapp = document.getElementById("bkWhatsapp").value.trim();
            const visitType = visitInput.value;

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
                        visitInput.value = chosenVisit || "Clinic Visit";
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
});