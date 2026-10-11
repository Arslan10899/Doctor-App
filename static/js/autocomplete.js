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

        function closeBox() { box.style.display = "none"; box.innerHTML = ""; items = []; }

        function sizeBox(isMobile) {
            // On phones the tile needs to be wider than the search field so a
            // full doctor name can sit on one line; anchor it to the viewport
            // with a small margin instead of the input's own width.
            if (!isMobile) {
                box.style.width = "";
                box.style.left = "";
                box.style.right = "";
                return;
            }
            var margin = 12;
            var r = wrap.getBoundingClientRect();
            box.style.width = (window.innerWidth - margin * 2) + "px";
            box.style.left = (margin - r.left) + "px";
            box.style.right = "auto";
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
                    var img = document.createElement("img");
                    img.className = "ac-doc-img";
                    img.alt = it.name;
                    img.loading = "lazy";
                    img.src = it.image || "/static/img/no-image.jpeg";
                    img.addEventListener("error", function () { this.src = "/static/img/no-image.jpeg"; });
                    var body = document.createElement("div");
                    body.className = "ac-doc-body";
                    var dn = document.createElement("div");
                    dn.className = "ac-doc-name";
                    dn.textContent = it.name;
                    body.appendChild(dn);
                    if (it.urdu_name) {
                        var du = document.createElement("div");
                        du.className = "ac-doc-urdu";
                        du.textContent = it.urdu_name;
                        body.appendChild(du);
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
                    body.appendChild(foot);
                    el.appendChild(img);
                    el.appendChild(body);
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