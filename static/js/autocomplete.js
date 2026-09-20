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

        function render() {
            box.innerHTML = "";
            if (!items.length) { closeBox(); return; }
            items.forEach(function (it, i) {
                var el = document.createElement("div");
                el.className = "ac-item";
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