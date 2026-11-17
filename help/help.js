// База знаний Финдикатора: поиск, прогресс «Курса новичка», увеличение скриншотов
(function () {
  // ---------- Прогресс курса (хранится только в этом браузере) ----------
  var KEY = 'findikator-help-read';
  function getRead() {
    try { return JSON.parse(localStorage.getItem(KEY) || '[]'); } catch (e) { return []; }
  }
  function setRead(list) {
    try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (e) { /* приватный режим — просто не запоминаем */ }
  }
  function paint() {
    var read = getRead();
    document.querySelectorAll('[data-kurs]').forEach(function (card) {
      var all = [];
      try { all = JSON.parse(card.getAttribute('data-kurs')); } catch (e) {}
      var done = all.filter(function (u) { return read.indexOf(u) >= 0; }).length;
      var bar = card.querySelector('.kurs-bar i');
      if (bar) bar.style.width = (all.length ? Math.round(done * 100 / all.length) : 0) + '%';
      var p = card.querySelector('.kurs-p');
      if (p) p.textContent = done ? 'Пройдено ' + done + ' из ' + all.length : 'Пройдено 0 из ' + all.length + ' – начните с первой статьи';
      var go = card.querySelector('.kurs-go');
      if (go && done) go.textContent = done === all.length ? 'Курс пройден ✓' : 'Продолжить →';
    });
    document.querySelectorAll('.anum[data-url]').forEach(function (n) {
      n.classList.toggle('done', read.indexOf(n.getAttribute('data-url')) >= 0);
    });
    document.querySelectorAll('.kurs-read input').forEach(function (cb) {
      cb.checked = read.indexOf(cb.getAttribute('data-url')) >= 0;
    });
  }
  document.querySelectorAll('.kurs-read input').forEach(function (cb) {
    cb.addEventListener('change', function () {
      var read = getRead(), u = cb.getAttribute('data-url'), i = read.indexOf(u);
      if (cb.checked && i < 0) read.push(u);
      if (!cb.checked && i >= 0) read.splice(i, 1);
      setRead(read);
      paint();
    });
  });
  paint();

  // ---------- Текущая статья в боковом меню ----------
  document.querySelectorAll('.aside a').forEach(function (a) {
    if (a.getAttribute('href') === location.pathname) a.classList.add('cur');
  });

  // ---------- Поиск ----------
  var index = null, loading = null;
  function load() {
    if (index) return Promise.resolve(index);
    if (!loading) loading = fetch('/help/search.json').then(function (r) { return r.json(); })
      .then(function (d) { index = d; return d; }).catch(function () { index = []; return index; });
    return loading;
  }
  function norm(s) { return (s || '').toLowerCase().replace(/ё/g, 'е'); }
  // Русские окончания: ищем по основе слова («загрузить» → «загруз»)
  var STOP = ['как', 'что', 'где', 'это', 'для', 'при', 'или', 'если', 'почему', 'зачем', 'когда', 'можно', 'нужно', 'мне', 'мой', 'над', 'под', 'про', 'без', 'чем', 'так', 'уже', 'все', 'всё'];
  function qwords(q) { return norm(q).split(/[^a-zа-я0-9]+/).filter(function (w) { return w.length > 1 && STOP.indexOf(w) < 0; }).map(stem); }
  function stem(w) { return w.length > 5 ? w.slice(0, w.length - 2) : (w.length > 3 ? w.slice(0, w.length - 1) : w); }
  function escHtml(s) { return s.replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function search(q) {
    var words = qwords(q);
    if (!words.length) return [];
    var res = [];
    index.forEach(function (a) {
      var t = norm(a.t), l = norm(a.l), x = norm(a.x), score = 0, all = true;
      words.forEach(function (w) {
        var s = 0;
        if (t.indexOf(w) >= 0) s += 10;
        if (l.indexOf(w) >= 0) s += 4;
        if (x.indexOf(w) >= 0) s += 1 + Math.min(3, x.split(w).length - 2);
        if (!s) all = false;
        score += s;
      });
      if (score && all) res.push({ a: a, s: score });
    });
    res.sort(function (p, q2) { return q2.s - p.s; });
    return res.slice(0, 8).map(function (r) { return r.a; });
  }
  function snippet(a, words) {
    var x = a.x, nx = norm(x), pos = -1;
    words.some(function (w) { pos = nx.indexOf(w); return pos >= 0; });
    if (pos < 0) return escHtml(a.l || x.slice(0, 110));
    var from = Math.max(0, pos - 40);
    var s = (from ? '…' : '') + x.slice(from, pos + 90) + '…';
    var h = escHtml(s);
    words.forEach(function (w) {
      h = h.replace(new RegExp('(' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '[а-яёa-z]*)', 'gi'), '<mark>$1</mark>');
    });
    return h;
  }
  document.querySelectorAll('.hsearch').forEach(function (box) {
    var input = box.querySelector('.hq'), out = box.querySelector('.hres'), act = -1;
    function render() {
      var q = input.value.trim();
      if (q.length < 2) { out.hidden = true; return; }
      load().then(function () {
        var words = qwords(q);
        var found = search(q);
        act = -1;
        out.innerHTML = found.length ? found.map(function (a) {
          return '<a href="' + a.u + '"><b>' + escHtml(a.t) + '</b><small>' + escHtml(a.s) + ' · ' + snippet(a, words) + '</small></a>';
        }).join('') : '<div class="none">Ничего не нашлось. Попробуйте другое слово или напишите нам в Telegram.</div>';
        out.hidden = false;
      });
    }
    input.addEventListener('focus', function () { load(); if (input.value.trim().length > 1) render(); });
    input.addEventListener('input', render);
    input.addEventListener('keydown', function (e) {
      var links = out.querySelectorAll('a');
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        if (!links.length) return;
        e.preventDefault();
        act = (act + (e.key === 'ArrowDown' ? 1 : -1) + links.length) % links.length;
        links.forEach(function (l, i) { l.classList.toggle('act', i === act); });
      } else if (e.key === 'Enter') {
        var l = links[act >= 0 ? act : 0];
        if (l) location.href = l.getAttribute('href');
      } else if (e.key === 'Escape') {
        out.hidden = true; input.blur();
      }
    });
    document.addEventListener('click', function (e) { if (!box.contains(e.target)) out.hidden = true; });
  });

  // ---------- Увеличение скриншота по щелчку (вместе с цифрами) ----------
  var zoom = document.getElementById('zoom');
  document.querySelectorAll('.shot-in').forEach(function (s) {
    s.addEventListener('click', function () {
      zoom.innerHTML = '';
      var c = s.cloneNode(true);
      c.style.cursor = 'zoom-out';
      var wrap = document.createElement('div');
      wrap.appendChild(c);
      zoom.appendChild(wrap);
      zoom.hidden = false;
    });
  });
  if (zoom) {
    zoom.addEventListener('click', function () { zoom.hidden = true; });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') zoom.hidden = true; });
  }
})();
