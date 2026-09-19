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

    // Hero image slider (auto-play)
    const heroSlider = document.getElementById("heroSlider");
    if (heroSlider) {
        const slides = heroSlider.querySelectorAll(".slide");
        const dotsWrap = heroSlider.querySelector(".slide-dots");
        const prevBtn = heroSlider.querySelector(".prev");
        const nextBtn = heroSlider.querySelector(".next");
        const progBar = heroSlider.querySelector(".slider-progress span");
        const total = slides.length;
        let current = 0;
        let timer = null;
        const INTERVAL = 4000;

        slides.forEach(function (s, i) {
            const dot = document.createElement("button");
            dot.setAttribute("aria-label", "Go to slide " + (i + 1));
            dot.addEventListener("click", function () {
                go(i);
                restart();
            });
            dotsWrap.appendChild(dot);
        });
        const dots = dotsWrap.querySelectorAll("button");

        function resetProgress() {
            if (!progBar) return;
            progBar.style.transition = "none";
            progBar.style.width = "0";
            void progBar.offsetWidth;
            progBar.style.transition = "width " + INTERVAL + "ms linear";
            requestAnimationFrame(function () {
                progBar.style.width = "100%";
            });
        }

        function go(i) {
            current = (i + total) % total;
            slides.forEach(function (s, idx) {
                s.classList.toggle("active", idx === current);
            });
            dots.forEach(function (d, idx) {
                d.classList.toggle("active", idx === current);
            });
            resetProgress();
        }
        function restart() {
            clearInterval(timer);
            timer = setInterval(function () { go(current + 1); }, INTERVAL);
        }
        if (prevBtn) prevBtn.addEventListener("click", function () { go(current - 1); restart(); });
        if (nextBtn) nextBtn.addEventListener("click", function () { go(current + 1); restart(); });

        let touchX = null;
        heroSlider.addEventListener("touchstart", function (e) {
            touchX = e.touches[0].clientX;
        }, { passive: true });
        heroSlider.addEventListener("touchend", function (e) {
            if (touchX === null) return;
            const dx = e.changedTouches[0].clientX - touchX;
            if (Math.abs(dx) > 40) {
                if (dx < 0) { go(current + 1); restart(); }
                else { go(current - 1); restart(); }
            }
            touchX = null;
        }, { passive: true });

        go(0);
        timer = setInterval(function () { go(current + 1); }, INTERVAL);
    }

    // Appointment type toggle
    const typeBtns = document.querySelectorAll(".type-btn");
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
});