# Сборка базы знаний findikator.ru/help (вызывается из _build.py).
#   _src/help/razdely.txt      — разделы и статьи по порядку (см. комментарий в начале файла)
#   _src/help/<раздел>/<статья>.md — текст статьи (Markdown с небольшими дополнениями, см. ниже)
#   _src/help/layout.html      — общий шаблон страниц базы знаний
#   help/img/                  — скриншоты (лежат прямо на сайте)
# Результат: help/index.html, help/<раздел>/index.html, help/<раздел>/<статья>.html, help/search.json
#
# Дополнения к Markdown в статьях:
#   ---  … ---  в начале файла   — title, lead (подзаголовок), who (кому), time (время), related (раздел/статья, через запятую)
#   ![Подпись](файл.png "1@20,30 2@55,40 рамка@10,20,30,8")  — скриншот из help/img; цифры и рамки поверх
#        картинки: N@x,y — кружок с цифрой (x, y в % от ширины и высоты), рамка@x,y,ш,в — красная рамка
#   > 💡 текст   — «Полезно знать»;   > ⚠️ текст — «Частая ошибка»;   > текст — просто заметка
#   ??? Вопрос  … ???            — «Проверьте себя»: вопрос и ответ под спойлером
#   [текст](раздел/статья)       — ссылка на другую статью базы знаний
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
HSRC = os.path.join(ROOT, '_src', 'help')
OUT = os.path.join(ROOT, 'help')


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def plural(n, one, few, many):
    n10, n100 = n % 10, n % 100
    if n10 == 1 and n100 != 11:
        return one
    if 2 <= n10 <= 4 and not 12 <= n100 <= 14:
        return few
    return many


def esc(s):
    return html.escape(s, quote=True)


# ---------- разделы ----------

def load_sections():
    sections, cur = [], None
    for raw in read(os.path.join(HSRC, 'razdely.txt')).splitlines():
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        if raw.startswith('  -') or raw.startswith('\t-'):
            slug, title = [x.strip() for x in raw.strip()[1:].split('|', 1)]
            cur['items'].append({'slug': slug, 'title': title})
        else:
            slug, emoji, title, desc = [x.strip() for x in raw.split('|', 3)]
            cur = {'slug': slug, 'emoji': emoji, 'title': title, 'desc': desc, 'items': []}
            sections.append(cur)
    return sections


# ---------- Markdown статьи ----------

def front(text):
    meta = {}
    m = re.match(r'\s*---\s*\n(.*?)\n---\s*\n', text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                v = v.strip()
                if len(v) > 1 and v[0] == v[-1] and v[0] in '"\'':
                    v = v[1:-1]
                meta[k.strip()] = v
        text = text[m.end():]
    return meta, text


def art_url(ref):
    sec, slug = ref.strip().strip('/').split('/', 1)
    return '/help/%s/%s.html' % (sec, slug.replace('.html', ''))


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'^\[ \] ', '<span class="cb" aria-hidden="true"></span>', s)   # пункт чек-листа
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'`(.+?)`', r'<code>\1</code>', s)

    def link(m):
        text, href = m.group(1), m.group(2)
        if not re.match(r'^(https?:|mailto:|/|#)', href):
            href = art_url(href)
        ext = ' target="_blank" rel="noopener"' if href.startswith('http') else ''
        return '<a href="%s"%s>%s</a>' % (href, ext, text)
    s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', link, s)
    return s


IMG = os.path.join(ROOT, 'help', 'img')
# Черновик: на месте ещё не снятого скриншота показывать рамку «Скриншот NN готовится».
# Перед публикацией поставить False — тогда такие места просто пропускаются.
DRAFT = False
MISSING = []


def find_img(stem):
    """Скриншот по номеру: «02» → help/img/02.png (или .jpg, .webp)."""
    for ext in ('.png', '.jpg', '.jpeg', '.webp'):
        if os.path.exists(os.path.join(IMG, stem + ext)):
            return stem + ext
    return None


def figure(alt, src, marks):
    if '.' not in src and '/' not in src:              # номер скриншота без расширения
        found = find_img(src)
        if not found:
            MISSING.append(src)
            if not DRAFT:
                return ''
            return ('<figure class="shot missing"><div class="shot-ph"><b>📷 Скриншот %s готовится</b>%s</div></figure>'
                    % (esc(src), '<span>' + inline(alt) + '</span>' if alt else ''))
        src = found
    parts = []
    for tok in (marks or '').split():
        m = re.match(r'^(\d+)@([\d.]+),([\d.]+)$', tok)
        if m:
            parts.append('<span class="mk" style="left:%s%%;top:%s%%">%s</span>' % (m.group(2), m.group(3), m.group(1)))
            continue
        m = re.match(r'^рамка@([\d.]+),([\d.]+),([\d.]+),([\d.]+)$', tok)
        if m:
            parts.append('<span class="frame" style="left:%s%%;top:%s%%;width:%s%%;height:%s%%"></span>' % m.groups())
    src = src if src.startswith('/') or src.startswith('http') else '/help/img/' + src
    cap = '<figcaption>%s</figcaption>' % inline(alt) if alt else ''
    return ('<figure class="shot"><div class="shot-in"><img src="%s" alt="%s" loading="lazy">%s</div>%s</figure>'
            % (esc(src), esc(alt), ''.join(parts), cap))


def md(text):
    out, para, lst, quote, table = [], [], None, [], []
    lines = text.splitlines()

    def flush():
        nonlocal para, lst, quote, table
        if para:
            out.append('<p>' + inline(' '.join(para)) + '</p>')
            para = []
        if lst:
            tag, start, items = lst
            body = ''
            for first, subs in items:
                sub = ''
                if subs:
                    sub = '<ul>' + ''.join('<li>' + inline(x) + '</li>' for x in subs) + '</ul>'
                body += '<li>' + inline(first) + sub + '</li>'
            st = ' start="%d"' % start if tag == 'ol' and start != 1 else ''
            out.append('<%s%s>%s</%s>' % (tag, st, body, tag))
            lst = None
        if quote:
            txt = ' '.join(quote)
            cls, label = 'note', ''
            if txt.startswith('💡'):
                cls, label, txt = 'tip', 'Полезно знать', txt[1:].strip()
            elif txt.startswith('⚠️') or txt.startswith('⚠'):
                cls, label, txt = 'warn', 'Частая ошибка', txt.lstrip('⚠️').strip()
            head = '<div class="callout-h">%s</div>' % label if label else ''
            out.append('<div class="callout %s">%s<p>%s</p></div>' % (cls, head, inline(txt)))
            quote = []
        if table:
            rows = [r for r in table if not re.match(r'^\|[\s:|-]+\|$', r)]
            cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
            h = '<tr>' + ''.join('<th>' + inline(c) + '</th>' for c in cells[0]) + '</tr>'
            b = ''.join('<tr>' + ''.join('<td>' + inline(c) + '</td>' for c in r) + '</tr>' for r in cells[1:])
            out.append('<div class="table-scroll"><table class="htable">' + h + b + '</table></div>')
            table = []

    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        i += 1
        if not line.strip():
            flush()
            continue
        if line.startswith('???'):                       # «Проверьте себя»
            flush()
            q = line[3:].strip()
            ans = []
            while i < len(lines) and not lines[i].startswith('???'):
                ans.append(lines[i])
                i += 1
            i += 1
            out.append('<details class="quiz"><summary><span class="quiz-h">Проверьте себя</span>%s</summary>'
                       '<div class="quiz-a">%s</div></details>' % (inline(q), md('\n'.join(ans))))
            continue
        m = re.match(r'^!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)\s*$', line)
        if m:
            flush()
            out.append(figure(m.group(1), m.group(2), m.group(3)))
            continue
        if line.startswith('>'):
            if para or lst or table:
                flush()
            quote.append(line[1:].strip())
            continue
        if quote:
            flush()
        if line.startswith('|'):
            if para or lst:
                flush()
            table.append(line)
            continue
        m = re.match(r'^(#{2,4})\s+(.*)$', line)
        if m:
            flush()
            lvl = len(m.group(1))
            title = m.group(2)
            aid = ''
            if lvl == 2:
                aid = ' id="%s"' % re.sub(r'[^\w-]+', '-', title.lower()).strip('-')[:60]
            out.append('<h%d%s>%s</h%d>' % (lvl, aid, inline(title), lvl))
            continue
        if line.strip() == '---':
            flush()
            out.append('<hr>')
            continue
        m = re.match(r'^(\s*)(-|\d+\.)\s+(.*)$', line)
        if m:
            if len(m.group(1)) >= 2 and lst:
                lst[2][-1][1].append(m.group(3))
                continue
            tag = 'ol' if m.group(2)[0].isdigit() else 'ul'
            if para:
                flush()
            if lst and lst[0] != tag:
                flush()
            if not lst:
                lst = (tag, int(m.group(2)[:-1]) if tag == 'ol' else 1, [])
            lst[2].append([m.group(3), []])
            continue
        if lst and raw.startswith('  '):
            last = lst[2][-1]
            if last[1]:
                last[1][-1] += ' ' + line.strip()
            else:
                last[0] += ' ' + line.strip()
            continue
        if lst:
            flush()
        para.append(line.strip())
    flush()
    return '\n'.join(out)


def plain(h):
    t = re.sub(r'<[^>]+>', ' ', h)
    return re.sub(r'\s+', ' ', html.unescape(t)).strip()


# ---------- страницы ----------

def crumbs(*items):
    parts = ['<a href="/help/">База знаний</a>']
    for title, href in items:
        parts.append('<a href="%s">%s</a>' % (href, esc(title)) if href else '<span>%s</span>' % esc(title))
    return '<nav class="hcrumbs">' + '<i>›</i>'.join(parts) + '</nav>'


def build(layout_main_vars):
    """Собирает базу знаний. Возвращает список адресов для sitemap."""
    layout = read(os.path.join(HSRC, 'layout.html'))
    sections = load_sections()
    by_slug = {s['slug']: s for s in sections}
    articles = {}          # 'раздел/статья' -> dict
    for s in sections:
        if s['slug'] == 'kurs':
            continue
        for it in s['items']:
            path = os.path.join(HSRC, s['slug'], it['slug'] + '.md')
            ref = s['slug'] + '/' + it['slug']
            it['ref'] = ref
            it['url'] = art_url(ref)
            it['ready'] = os.path.exists(path)
            if it['ready']:
                meta, body = front(read(path))
                it['title'] = meta.get('title', it['title'])
                it['lead'] = meta.get('lead', '')
                it['meta'] = meta
                it['html'] = md(body)
            articles[ref] = it
    kurs = by_slug.get('kurs')
    if kurs:
        for it in kurs['items']:
            a = articles.get(it['slug'])
            it.update({'ref': it['slug'], 'url': art_url(it['slug']), 'ready': bool(a and a['ready'])})
            if a:
                it['title'] = a['title']
        kurs_refs = [it['ref'] for it in kurs['items']]
    else:
        kurs_refs = []

    urls, search = [], []

    def page(rel, title, desc, body, bodycls=''):
        url = '/help/' + (rel[:-len('index.html')] if rel.endswith('index.html') else rel)
        text = (layout.replace('{{content}}', body)
                .replace('{{title}}', esc(title))
                .replace('{{description}}', esc(desc))
                .replace('{{url}}', url)
                .replace('{{bodycls}}', bodycls)
                .replace('{{cssv}}', layout_main_vars['cssv']))
        write(os.path.join(OUT, rel), text)
        urls.append(url)

    def count_label(s):
        n = sum(1 for it in s['items'] if it.get('ready'))
        return '%d %s' % (n, plural(n, 'статья', 'статьи', 'статей')) if n else 'готовится'

    # --- главная ---
    tiles = []
    for s in sections:
        if s['slug'] == 'kurs':
            continue
        tiles.append('<a class="tile" href="/help/%s/"><span class="tile-e">%s</span><b>%s</b><span class="tile-d">%s</span>'
                     '<span class="tile-n">%s</span></a>' % (s['slug'], s['emoji'], esc(s['title']), esc(s['desc']), count_label(s)))
    kurs_card = ''
    if kurs:
        kurs_card = ('<a class="kurs-card" href="/help/kurs/" data-kurs="%s"><span class="kurs-e">%s</span><span class="kurs-t">'
                     '<b>%s</b><span>%s</span><span class="kurs-bar"><i></i></span><span class="kurs-p"></span></span>'
                     '<span class="kurs-go">Начать →</span></a>'
                     % (esc(json.dumps([art_url(r) for r in kurs_refs])), kurs['emoji'], esc(kurs['title']), esc(kurs['desc'])))
    body = ('<section class="hhero"><div class="hwrap"><h1>Здесь вы найдёте ответы на свои вопросы</h1>'
            '<p>Пошаговые инструкции со скриншотами: как загрузить данные из 1С, разнести операции по статьям, '
            'читать отчёты и вести платёжный календарь.</p>'
            '<div class="hsearch big"><input type="search" class="hq" placeholder="Например: как загрузить выписку" autocomplete="off">'
            '<div class="hres" hidden></div></div></div></section>'
            '<section class="hwrap hmain">%s<div class="tiles">%s</div></section>' % (kurs_card, ''.join(tiles)))
    page('index.html', 'База знаний – Финдикатор',
         'Пошаговые инструкции по работе в Финдикаторе: загрузка из 1С, разноска по статьям, отчёты, бюджет и платёжный календарь.',
         body, 'home')

    # --- разделы ---
    for s in sections:
        rows = []
        for n, it in enumerate(s['items'], 1):
            a = articles.get(it['ref']) if s['slug'] == 'kurs' else it
            lead = (a or {}).get('lead', '')
            num = '<span class="anum" data-url="%s">%d</span>' % (it['url'], n) if s['slug'] == 'kurs' else ''
            if it.get('ready'):
                rows.append('<a class="arow" href="%s">%s<span><b>%s</b><span>%s</span></span></a>'
                            % (it['url'], num, esc(it['title']), esc(lead)))
            else:
                rows.append('<div class="arow soon">%s<span><b>%s</b><span>Статья готовится</span></span></div>'
                            % (num, esc(it['title'])))
        extra = ''
        if s['slug'] == 'kurs':
            extra = ('<div class="kurs-card flat" data-kurs="%s"><span class="kurs-t"><span class="kurs-bar"><i></i></span>'
                     '<span class="kurs-p"></span></span></div>' % esc(json.dumps([art_url(r) for r in kurs_refs])))
        body = ('<section class="hwrap hmain">%s<h1 class="sec-h"><span>%s</span>%s</h1><p class="sec-d">%s</p>%s'
                '<div class="alist%s">%s</div></section>'
                % (crumbs((s['title'], None)), s['emoji'], esc(s['title']), esc(s['desc']), extra,
                   ' numbered' if s['slug'] == 'kurs' else '', ''.join(rows)))
        page(s['slug'] + '/index.html', '%s – База знаний Финдикатора' % s['title'], s['desc'], body)

    # --- статьи ---
    for s in sections:
        if s['slug'] == 'kurs':
            continue
        side = ''.join('<a href="%s" class="%s">%s</a>' % (it['url'], '' if it['ready'] else 'soon', esc(it['title']))
                       for it in s['items'])
        for it in s['items']:
            if not it['ready']:
                continue
            meta = it['meta']
            info = []
            if meta.get('who'):
                info.append('<span>👤 %s</span>' % esc(meta['who']))
            if meta.get('time'):
                info.append('<span>⏱ %s</span>' % esc(meta['time']))
            rel_html = ''
            rel = [r.strip() for r in meta.get('related', '').split(',') if r.strip()]
            rel_items = [articles[r] for r in rel if r in articles]
            if rel_items:
                rel_html = '<div class="related"><h3>Связанные статьи</h3>%s</div>' % ''.join(
                    '<a href="%s" class="%s">%s</a>' % (a['url'], '' if a['ready'] else 'soon', esc(a['title'])) for a in rel_items)
            kurs_html = ''
            if it['ref'] in kurs_refs:
                k = kurs_refs.index(it['ref'])
                nxt = articles.get(kurs_refs[k + 1]) if k + 1 < len(kurs_refs) else None
                nxt_html = ('<a class="kurs-next%s" href="%s">Дальше: %s →</a>'
                            % ('' if nxt['ready'] else ' soon', nxt['url'], esc(nxt['title']))) if nxt else \
                    '<span class="kurs-next done">Это последняя статья курса 🎉</span>'
                kurs_html = ('<div class="kurs-box"><div class="kurs-box-h">🎓 Курс новичка · статья %d из %d</div>'
                             '<label class="kurs-read"><input type="checkbox" data-url="%s"> Прочитано, всё понятно</label>%s</div>'
                             % (k + 1, len(kurs_refs), it['url'], nxt_html))
            help_html = ('<div class="ask">Не нашли ответ? Напишите нам на <a href="mailto:findikator@yandex.ru?subject=Вопрос по Финдикатору">почту</a> '
                         'или позвоните: <a href="tel:+79615450553">+7 961 545-05-53</a> – ответим и допишем статью.</div>')
            body = ('<section class="hwrap hmain"><div class="acols"><aside class="aside"><div class="aside-h">%s %s</div>%s</aside>'
                    '<article class="art">%s<h1>%s</h1>%s%s<div class="art-body">%s</div>%s%s%s</article></div></section>'
                    % (s['emoji'], esc(s['title']), side,
                       crumbs((s['title'], '/help/%s/' % s['slug']), (it['title'], None)),
                       esc(it['title']),
                       '<p class="art-lead">%s</p>' % esc(it['lead']) if it['lead'] else '',
                       '<div class="art-info">%s</div>' % ''.join(info) if info else '',
                       it['html'], kurs_html, rel_html, help_html))
            page('%s/%s.html' % (s['slug'], it['slug']), '%s – База знаний Финдикатора' % it['title'],
                 it['lead'] or s['desc'], body, 'article')
            search.append({'t': it['title'], 'l': it['lead'], 's': s['title'], 'u': it['url'],
                           'x': plain(it['html'])[:4000]})

    write(os.path.join(OUT, 'search.json'), json.dumps(search, ensure_ascii=False))
    print('  help: %d разделов, %d статей готово, скриншотов не хватает: %d' % (len(sections), len(search), len(set(MISSING))))
    return urls
