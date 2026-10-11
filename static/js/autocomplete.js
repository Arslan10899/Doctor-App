(function () {
    function initAutocomplete(input) {
        if (!input || input.dataset.acInit) return;
        input.dataset.acInit = "1";

        var wrap = document.createElement("div");
        wrap.className = "ac-wrap";
        input.parentNode.insertBefore(wrap, input);
        wrap.appendChild(input);

        var box = document.createElement("div");
        box.className = "ac-box";
        box.style.display = "none";
        wrap.appendChild(box);

        var form = input.closest("form");
        if (form) form.autocomplete = "off";

        var timer = null;
        var items = [];

        function getScrim() {
            var s = document.querySelector("body > .ac-scrim");
            if (!s) {
                s = document.createElement("div");
                s.className = "ac-scrim";
                s.addEventListener("click", closeBox);
                document.body.appendChild(s);
            }
            return s;
        }

        function closeBox() {
            box.style.display = "none";
            box.innerHTML = "";
            items = [];
            var s = document.querySelector("body > .ac-scrim");
            if (s) s.style.display = "none";
        }

        function shortTime(t) {
            // "7:00 AM" -> "7 AM", "12:00 PM" -> "12 PM"; keep minutes when non-zero.
            var m = /(\d{1,2}):(\d{2})\s*([AP]M)/i.exec(String(t || "").trim());
            if (!m) return String(t || "").trim();
            var h = parseInt(m[1], 10);
            var min = parseInt(m[2], 10);
            var hh = (min === 0) ? String(h) : (String(h) + ":" + (min < 10 ? "0" + min : String(min)));
            return hh + " " + m[3].toUpperCase();
        }
        function timingText(d) {
            // Today's clinic hours, shown for every doctor.
            if (d.today_closed) return "On leave today";
            if (d.today_open && d.today_close) return shortTime(d.today_open) + " \u2013 " + shortTime(d.today_close);
            if (d.today_open) return shortTime(d.today_open) + " onwards";
            return "";
        }

        function sizeBox(isMobile) {
            // On phones the tile needs to be wider than the search field so a
            // full doctor name can sit on one line. Because "Featured Doctors in
            // your City" sits only ~150px below the search field, a tall floating
            // dropdown would collide with it, so we turn the panel into a
            // near-fullscreen overlay: from just under the input down to a small
            // margin above the bottom edge, with the results scrolling inside.
            if (!isMobile) {
                box.style.width = "";
                box.style.left = "";
                box.style.right = "";
                box.style.top = "";
                box.style.bottom = "";
                box.style.position = "";
                box.style.maxHeight = "";
                box.style.borderRadius = "";
                return;
            }
            var margin = 12;
            var r = wrap.getBoundingClientRect();
            box.style.position = "fixed";
            box.style.top = (r.bottom + 6) + "px";
            box.style.left = margin + "px";
            box.style.right = margin + "px";
            box.style.bottom = margin + "px";
            box.style.maxHeight = "none";
            box.style.width = "";
            box.style.borderRadius = "18px";
        }

        function render() {
            box.innerHTML = "";
            if (!items.length) { closeBox(); return; }
            var isMobile = window.matchMedia("(max-width: 768px)").matches;
            sizeBox(isMobile);
            items.forEach(function (it, i) {
                var el = document.createElement("div");
                el.className = "ac-item";
                if (isMobile && it.type === "doctor") {
                    el.className = "ac-item ac-item-doctor";
                    var media = document.createElement("div");
                    media.className = "ac-doc-media";
                    var img = document.createElement("img");
                    img.className = "ac-doc-img";
                    img.alt = it.name;
                    img.loading = "lazy";
                    img.src = it.image || "/static/img/no-image.jpeg";
                    img.addEventListener("error", function () { this.src = "/static/img/no-image.jpeg"; });
                    media.appendChild(img);
                    var rate = document.createElement("span");
                    rate.className = "ac-doc-rating";
                    rate.innerHTML = '<svg viewBox="0 0 24 24" width="10" height="10" fill="currentColor" aria-hidden="true"><path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg><span></span>';
                    rate.querySelector("span").textContent = it.rating ? Number(it.rating).toFixed(1) : "\u2014";
                    media.appendChild(rate);
                    var feeEl = document.createElement("span");
                    feeEl.className = "ac-doc-fee";
                    feeEl.textContent = (it.fee && it.fee > 0) ? ("Rs " + it.fee) : "On request";
                    var body = document.createElement("div");
                    body.className = "ac-doc-body";
                    var namerow = document.createElement("div");
                    namerow.className = "ac-doc-namerow";
                    var dn = document.createElement("div");
                    dn.className = "ac-doc-name";
                    dn.textContent = it.name;
                    namerow.appendChild(dn);
                    body.appendChild(namerow);
                    if (it.urdu_name) {
                        var urduRow = document.createElement("div");
                        urduRow.className = "ac-doc-urdurow";
                        var du = document.createElement("div");
                        du.className = "ac-doc-urdu";
                        du.textContent = it.urdu_name;
                        urduRow.appendChild(du);
                        urduRow.appendChild(feeEl);
                        body.appendChild(urduRow);
                    } else {
                        namerow.appendChild(feeEl);
                    }
                    var actions = document.createElement("div");
                    actions.className = "ac-doc-actions";
                    var clinicBtn = document.createElement("button");
                    clinicBtn.type = "button";
                    clinicBtn.className = "ac-doc-btn ac-doc-btn-clinic";
                    clinicBtn.textContent = "Clinic Check-up";
                    var onlineBtn = document.createElement("button");
                    onlineBtn.type = "button";
                    onlineBtn.className = "ac-doc-btn ac-doc-btn-online";
                    onlineBtn.textContent = "Online Check-up";
                    function bookWith(visit) {
                        return function (ev) {
                            ev.preventDefault();
                            ev.stopPropagation();
                            closeBox();
                            if (window.openBooking) window.openBooking(it.id, visit);
                            else window.location.href = it.url;
                        };
                    }
                    clinicBtn.addEventListener("click", bookWith("Clinic Visit"));
                    onlineBtn.addEventListener("click", bookWith("Online Check-up"));
                    actions.appendChild(clinicBtn);
                    actions.appendChild(onlineBtn);
                    body.appendChild(actions);
                    var foot = document.createElement("div");
                    foot.className = "ac-doc-foot";
                    var spec = document.createElement("span");
                    spec.className = "ac-doc-spec";
                    spec.textContent = it.specialty || "";
                    var city = document.createElement("span");
                    city.className = "ac-doc-city";
                    city.textContent = it.city || "";
                    foot.appendChild(spec);
                    foot.appendChild(city);
                    var timing = timingText(it);
                    if (timing) {
                        var tm = document.createElement("span");
                        tm.className = "ac-doc-timing";
                        tm.innerHTML = '<svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg><span></span>';
                        tm.querySelector("span").textContent = timing;
                        foot.appendChild(tm);
                    }
                    var top = document.createElement("div");
                    top.className = "ac-doc-top";
                    top.appendChild(media);
                    top.appendChild(body);
                    el.appendChild(top);
                    el.appendChild(foot);
                } else {
                    var tag = document.createElement("span");
                    tag.className = "ac-type ac-type-" + it.type;
                    tag.textContent = it.type[0].toUpperCase() + it.type.slice(1);
                    var name = document.createElement("span");
                    name.className = "ac-name";
                    name.textContent = it.name;
                    var sub = document.createElement("span");
                    sub.className = "ac-sub";
                    sub.textContent = it.sub || "";
                    el.appendChild(tag);
                    el.appendChild(name);
                    if (it.sub) el.appendChild(document.createElement("br"));
                    if (it.sub) el.appendChild(sub);
                }
                el.dataset.i = i;
                el.addEventListener("click", function () { window.location.href = items[this.dataset.i].url; });
                box.appendChild(el);
            });
            box.style.display = "block";
            if (isMobile) getScrim().style.display = "block";
        }

        function fetchSuggestions() {
            var q = input.value.trim();
            if (q.length < 2) { closeBox(); return; }
            fetch("/api/search?q=" + encodeURIComponent(q))
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (input.value.trim() !== q) return;
                    items = data.results;
                    render();
                })
                .catch(function () { closeBox(); });
        }

        input.addEventListener("input", function () {
            clearTimeout(timer);
            timer = setTimeout(fetchSuggestions, 180);
        });
        input.addEventListener("focus", function () { if (input.value.trim().length >= 2) fetchSuggestions(); });
        document.addEventListener("click", function (e) {
            if (!wrap.contains(e.target)) closeBox();
        });
        window.addEventListener("resize", function () {
            if (box.style.display === "block") sizeBox(window.matchMedia("(max-width: 768px)").matches);
        });
        input.addEventListener("keydown", function (e) {
            var el = box.querySelector("[data-i='0']");
            if (e.key === "Escape") { closeBox(); input.blur(); return; }
            if (e.key === "ArrowDown" && el) { e.preventDefault(); el.scrollIntoView({ block: "nearest" }); }
            if (e.key === "Enter") {
                if (box.style.display !== "none" && items.length === 1) {
                    e.preventDefault();
                    window.location.href = items[0].url;
                }
            }
        });
    }

    function init() {
        var inputs = document.querySelectorAll(".hero-search input, .filter-bar input[type='text']");
        for (var i = 0; i < inputs.length; i++) initAutocomplete(inputs[i]);
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
})();