// Extended Styles - client-side handling:
//   - "Thumbnail size" slider (size remembered in localStorage)
//   - NSFW filter: blurs the thumbnails of styles with "nsfw" in the name (on/off remembered)
// All client-side: does not go through the server, so it never conflicts with Forge's ui-config.

(function () {
    var KEY = 'extendedStyles_gallerySize';
    var BKEY = 'extendedStyles_blurNsfw';
    var TABS = {
        t2i: { gid: 'extended_styles_gallery_t2i', sid: 'es_size_slider_t2i', cb: 'es_nsfw_t2i' },
        i2i: { gid: 'extended_styles_gallery_i2i', sid: 'es_size_slider_i2i', cb: 'es_nsfw_i2i' }
    };
    var applying = false;

    // ---------------- thumbnail size ----------------
    function getSize() {
        var v = parseInt(localStorage.getItem(KEY), 10);
        return (v >= 50 && v <= 200) ? v : 150;
    }
    function saveSize(v) { localStorage.setItem(KEY, v); }
    function applyCss(gid, v) {
        var g = gradioApp().querySelector('#' + gid);
        if (!g) return;
        var st = g.querySelector('style.es-size');
        if (!st) { st = document.createElement('style'); st.className = 'es-size'; g.appendChild(st); }
        st.textContent = '#' + gid + ' .grid-container{grid-template-columns:repeat(auto-fill,' + v +
            'px)!important;grid-template-rows:none!important;grid-auto-rows:' + v + 'px!important;}';
    }
    function setSliderDisplay(sid, v) {
        var wrap = gradioApp().querySelector('#' + sid);
        if (!wrap) return;
        applying = true;
        wrap.querySelectorAll('input').forEach(function (inp) {
            inp.value = v;
            inp.dispatchEvent(new Event('input', { bubbles: true }));
        });
        applying = false;
    }
    function hookSlider(sid, gid) {
        var wrap = gradioApp().querySelector('#' + sid);
        if (!wrap || wrap.dataset.esHooked) return;
        wrap.dataset.esHooked = '1';
        wrap.addEventListener('input', function (e) {
            if (applying) return;
            var v = parseInt(e.target && e.target.value, 10);
            if (!(v >= 50 && v <= 200)) return;
            saveSize(v);
            applyCss(gid, v);
        });
    }
    function hideNumberBox(sid) {
        var wrap = gradioApp().querySelector('#' + sid);
        if (!wrap || wrap.querySelector('style.es-nonum')) return;
        var st = document.createElement('style');
        st.className = 'es-nonum';
        st.textContent = '#' + sid + ' input:not([type="range"]){display:none!important;}';
        wrap.appendChild(st);
    }

    // ---------------- NSFW filter ----------------
    function blurOn() { return localStorage.getItem(BKEY) === '1'; }
    function saveBlur(on) { localStorage.setItem(BKEY, on ? '1' : '0'); }
    function ensureBlurStyle(gid) {
        var g = gradioApp().querySelector('#' + gid);
        if (!g || g.querySelector('style.es-nsfw-css')) return;
        var st = document.createElement('style');
        st.className = 'es-nsfw-css';
        // blurred by default, sharp on hover
        st.textContent = '#' + gid + ' img.es-nsfw-blur{filter:blur(16px)!important;transition:filter .12s ease}' +
            '#' + gid + ' img.es-nsfw-blur:hover{filter:none!important}';
        g.appendChild(st);
    }
    function applyBlur(gid) {
        var g = gradioApp().querySelector('#' + gid);
        if (!g) return;
        var on = blurOn();
        g.querySelectorAll('img').forEach(function (img) {
            var alt = (img.getAttribute('alt') || '').toLowerCase();
            if (on && alt.indexOf('nsfw') !== -1) img.classList.add('es-nsfw-blur');
            else img.classList.remove('es-nsfw-blur');
        });
    }
    function hookNsfw(cbid, gid) {
        var wrap = gradioApp().querySelector('#' + cbid);
        if (wrap && !wrap.dataset.nsfwHooked) {
            wrap.dataset.nsfwHooked = '1';
            var inp = wrap.querySelector('input[type="checkbox"]');
            if (inp) {
                inp.checked = blurOn();                 // initial state from localStorage
                inp.addEventListener('change', function () {
                    saveBlur(inp.checked);
                    applyBlur(gid);
                });
            }
        }
        ensureBlurStyle(gid);
        var g = gradioApp().querySelector('#' + gid);
        if (g && !g.dataset.nsfwObs) {
            g.dataset.nsfwObs = '1';                    // re-apply when the gallery changes
            new MutationObserver(function () { applyBlur(gid); })
                .observe(g, { childList: true, subtree: true });
        }
        applyBlur(gid);
    }

    // ---------------- start ----------------
    function init() {
        var v = getSize();
        Object.keys(TABS).forEach(function (k) {
            var t = TABS[k];
            applyCss(t.gid, v);
            setSliderDisplay(t.sid, v);
            hookSlider(t.sid, t.gid);
            hideNumberBox(t.sid);
            hookNsfw(t.cb, t.gid);
        });
    }

    if (typeof onUiLoaded === 'function') {
        onUiLoaded(function () { init(); setTimeout(init, 800); });
    }
})();
