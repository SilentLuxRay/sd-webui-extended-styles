// Extended Styles - client-side handling of the "Thumbnail size" slider.
// Everything here: applies the size, remembers it in localStorage, updates live.
// It does not go through the server, so it never conflicts with Forge's ui-config.

(function () {
    var KEY = 'extendedStyles_gallerySize';
    var TABS = {
        t2i: { gid: 'extended_styles_gallery_t2i', sid: 'es_size_slider_t2i' },
        i2i: { gid: 'extended_styles_gallery_i2i', sid: 'es_size_slider_i2i' }
    };
    var applying = false;

    function getSize() {
        var v = parseInt(localStorage.getItem(KEY), 10);
        return (v >= 50 && v <= 200) ? v : 150;
    }
    function saveSize(v) {
        localStorage.setItem(KEY, v);
    }
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
    function init() {
        var v = getSize();
        Object.keys(TABS).forEach(function (k) {
            var t = TABS[k];
            applyCss(t.gid, v);
            setSliderDisplay(t.sid, v);
            hookSlider(t.sid, t.gid);
            hideNumberBox(t.sid);
        });
    }

    if (typeof onUiLoaded === 'function') {
        onUiLoaded(function () { init(); setTimeout(init, 800); });
    }
})();
