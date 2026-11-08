/* ============================================================================
   assets/js/site.js: the small amount of interactivity on the site
   ----------------------------------------------------------------------------
   Plain JavaScript, no libraries. Each feature looks for its own data-*
   attributes and does nothing on pages that don't have them:

     1. Home carousel            [data-carousel]       (index.html)
     2. Alumni filter buttons    [data-alumni-tab]     (people.html)
     3. Publication search,      [data-pub-search], [data-pub-kind],
        type filter, Copy BibTeX [data-copy-bibtex]    (publications.html)

   All content is already in the page as HTML; if JavaScript is off, every
   photo, alumnus and publication is still visible.
   ========================================================================== */

(function () {
  'use strict';

  var ACCENT = '#5cc8ff';

  /* Style a round filter button as selected (accent fill) or not (outline).
     Matches the look of the buttons in the design mockups. */
  function setPressed(button, on) {
    button.setAttribute('aria-pressed', on ? 'true' : 'false');
    button.style.background = on ? ACCENT : 'transparent';
    button.style.color = on ? '#0a0e14' : '#e8edf2';
    button.style.borderColor = on ? ACCENT : '#36414f';
  }

  /* ---- 1. Home carousel ----------------------------------------------------
     Slides are stacked on top of each other; only the current one is opaque.
     Advances every 9 seconds unless the visitor prefers reduced motion.
     The dots below jump to a slide; the credit text follows the current slide. */
  function initCarousel(root) {
    var slides = root.querySelectorAll('.slide');
    var dots = root.querySelectorAll('[data-slide-dot]');
    var credit = root.querySelector('[data-slide-credit]');
    var current = 0;
    var timer = null;
    if (slides.length < 2) return;

    function show(n) {
      current = n;
      slides.forEach(function (s, k) {
        s.style.opacity = k === n ? '1' : '0';
        s.setAttribute('aria-hidden', k === n ? 'false' : 'true');
      });
      dots.forEach(function (d, k) {
        d.firstElementChild.style.background = k === n ? '#ffffff' : 'rgba(255,255,255,.4)';
      });
      if (credit) credit.textContent = slides[n].getAttribute('data-credit') || '';
    }

    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    function start() {
      if (reduce) return;
      clearInterval(timer);
      timer = setInterval(function () { show((current + 1) % slides.length); }, 9000);
    }

    dots.forEach(function (d) {
      d.addEventListener('click', function () {
        show(parseInt(d.getAttribute('data-slide-dot'), 10));
        start();                     // restart the 9 s clock after a manual choice
      });
    });
    start();
  }

  /* ---- 2. Alumni filter (People page) --------------------------------------
     Buttons: "All" plus one per level. Each level's table is wrapped in
     [data-alumni-group="<level>"]; we hide the ones not selected. */
  function initAlumni() {
    var tabs = document.querySelectorAll('[data-alumni-tab]');
    var groups = document.querySelectorAll('[data-alumni-group]');
    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        var level = tab.getAttribute('data-alumni-tab');
        tabs.forEach(function (t) { setPressed(t, t === tab); });
        groups.forEach(function (g) {
          g.classList.toggle('is-hidden', level !== 'All' && g.getAttribute('data-alumni-group') !== level);
        });
      });
    });
  }

  /* ---- 3. Publications: search, type filter, Copy BibTeX -------------------
     Each paper is a [data-pub] row with data-kind and data-year. A row is shown
     when it matches the selected type AND contains the search text (in its
     title, authors or citation). The year label is shown only on the first
     visible row of each year, as in the full list. */
  function initPublications() {
    var rows = Array.prototype.slice.call(document.querySelectorAll('[data-pub]'));
    if (!rows.length) return;
    var search = document.querySelector('[data-pub-search]');
    var kindButtons = document.querySelectorAll('[data-pub-kind]');
    var count = document.querySelector('[data-pub-count]');
    var kind = 'All';

    // Searchable text for each row, worked out once.
    // (title link + authors line + citation line; not the button labels)
    var text = rows.map(function (r) {
      var parts = r.querySelectorAll('[data-pub-text]');
      return Array.prototype.map.call(parts, function (p) { return p.textContent; }).join(' ').toLowerCase();
    });

    function update() {
      var q = (search ? search.value : '').trim().toLowerCase();
      var lastYear = null;
      var shown = 0;
      rows.forEach(function (r, i) {
        var ok = (kind === 'All' || r.getAttribute('data-kind') === kind) && (!q || text[i].indexOf(q) !== -1);
        r.classList.toggle('is-hidden', !ok);
        if (!ok) return;
        shown++;
        var y = r.getAttribute('data-year');
        r.querySelector('[data-pub-year]').textContent = y !== lastYear ? y : '';
        lastYear = y;
      });
      if (count) count.textContent = shown + ' of ' + rows.length + ' shown';
    }

    if (search) search.addEventListener('input', update);
    kindButtons.forEach(function (b) {
      b.addEventListener('click', function () {
        kind = b.getAttribute('data-pub-kind');
        kindButtons.forEach(function (o) { setPressed(o, o === b); });
        update();
      });
    });

    // Copy BibTeX: the raw entries are in <script id="pub-bibtex">, in row order.
    var bib = [];
    try { bib = JSON.parse(document.getElementById('pub-bibtex').textContent); } catch (e) {}
    rows.forEach(function (r) {
      var btn = r.querySelector('[data-copy-bibtex]');
      if (!btn) return;
      btn.addEventListener('click', function () {
        var entry = bib[parseInt(r.getAttribute('data-index'), 10)] || '';
        var done = function () {
          document.querySelectorAll('[data-copy-bibtex]').forEach(function (o) { o.textContent = 'Copy BibTeX'; });
          btn.textContent = 'Copied ✓';
        };
        if (navigator.clipboard) navigator.clipboard.writeText(entry).then(done, done);
        else done();
      });
    });
  }

  document.querySelectorAll('[data-carousel]').forEach(initCarousel);
  initAlumni();
  initPublications();
})();
