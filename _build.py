# Сборка сайта on-fin.ru: страницы из _src/pages вставляются в общий шаблон _src/layout.html
# (шапка, меню, блок «Демонстрация», подвал) и сохраняются в корень сайта по тем же путям.
# Страница «Инструкция» собирается из файла «Инструкция по настройке и работе.md» в папке проекта.
# Запуск: python _build.py   (папки и файлы с «_» GitHub Pages не публикует)
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, '_src')
PAGES = os.path.join(SRC, 'pages')
INSTRUCTION_MD = os.path.join(os.path.dirname(ROOT), 'Инструкция по настройке и работе.md')
CSS_VERSION = '8'
SITE = 'https://on-fin.ru'


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def front(text):
    """Заголовок страницы в комментарии <!-- title: … / description: … --> в начале файла."""
    meta = {}
    m = re.match(r'\s*<!--(.*?)-->', text, re.S)
    if m:
        for line in m.group(1).strip().splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                meta[k.strip()] = v.strip()
        text = text[m.end():]
    return meta, text.strip() + '\n'


def inline_md(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'`(.+?)`', r'<code>\1</code>', s)
    return s


def md_to_html(md):
    """Простой перевод инструкции из Markdown: заголовки, списки, таблицы, абзацы, черта."""
    out, para, lst, table = [], [], None, []

    def flush():
        nonlocal para, lst, table
        if para:
            out.append('<p>' + inline_md(' '.join(para)) + '</p>')
            para = []
        if lst:
            tag, items = lst
            li = lambda it: '<li>' + inline_md(it[0]) + (
                '<ul>' + ''.join('<li>' + inline_md(x) + '</li>' for x in it[1]) + '</ul>' if it[1] else '') + '</li>'
            out.append('<%s>%s</%s>' % (tag, ''.join(li(i) for i in items), tag))
            lst = None
        if table:
            rows = [r for r in table if not re.match(r'^\|[\s:|-]+\|$', r)]
            cells = [[c.strip() for c in r.strip('|').split('|')] for r in rows]
            h = '<tr>' + ''.join('<th>' + inline_md(c) + '</th>' for c in cells[0]) + '</tr>'
            b = ''.join('<tr>' + ''.join('<td>' + inline_md(c) + '</td>' for c in r) + '</tr>' for r in cells[1:])
            out.append('<div class="table-scroll"><table class="doc-table">' + h + b + '</table></div>')
            table = []

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        if line.startswith('|'):
            if para or lst:
                flush()
            table.append(line)
            continue
        m = re.match(r'^(#{1,4})\s+(.*)$', line)
        if m:
            flush()
            level = max(2, min(len(m.group(1)), 4))   # ## → h2, ### → h3 (h1 — заголовок страницы)
            out.append('<h%d>%s</h%d>' % (level, inline_md(m.group(2)), level))
            continue
        if line.strip() == '---':
            flush()
            out.append('<hr>')
            continue
        m = re.match(r'^(\s*)(-|\d+\.)\s+(.*)$', line)
        if m:
            if len(m.group(1)) >= 2 and lst:          # вложенный пункт — внутрь предыдущего
                lst[1][-1][1].append(m.group(3))
                continue
            tag = 'ol' if m.group(2)[0].isdigit() else 'ul'
            if para:
                flush()
            if lst and lst[0] != tag:
                flush()
            if not lst:
                lst = (tag, [])
            lst[1].append([m.group(3), []])
            continue
        if lst and raw.startswith('  '):
            last = lst[1][-1]
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


def instruction_page():
    md = read(INSTRUCTION_MD)
    # Убираем заголовок файла и внутренний абзац про установку
    lines = md.splitlines()
    if lines and lines[0].startswith('# '):
        lines = lines[1:]
    md = '\n'.join(lines)
    md = re.sub(r'^Инструкция для клиента.*$', '', md, count=1, flags=re.M)
    body = md_to_html(md)
    return ({'title': 'Инструкция по настройке и работе – ФинУчет',
             'description': 'Как настроить ФинУчет и работать с ним каждый день: загрузка из 1С, справочник статей, правила разноски, отчёты, платёжный календарь, группа компаний, закрытие года.'},
            '<div class="page-head"><div class="wrap">\n'
            '<p class="crumbs"><a href="/">Главная</a> → Полезное</p>\n'
            '<h1>Инструкция по настройке и работе</h1>\n'
            '<p class="lead">Полная инструкция, которую получает каждый клиент: от первой настройки до закрытия года.</p>\n'
            '</div></div>\n<div class="wrap doc">\n' + body + '\n</div>\n')


def main():
    layout = read(os.path.join(SRC, 'layout.html'))
    pages = []
    for dirpath, _, files in os.walk(PAGES):
        for name in sorted(files):
            if name.endswith('.html'):
                rel = os.path.relpath(os.path.join(dirpath, name), PAGES).replace('\\', '/')
                meta, body = front(read(os.path.join(dirpath, name)))
                pages.append((rel, meta, body))
    pages.append(('poleznoe/instrukciya.html',) + instruction_page())

    urls = []
    for rel, meta, body in pages:
        url = '/' + (rel[:-len('index.html')] if rel.endswith('index.html') else rel)
        page = (layout.replace('{{content}}', body)
                .replace('{{title}}', html.escape(meta.get('title', 'ФинУчет')))
                .replace('{{description}}', html.escape(meta.get('description', '')))
                .replace('{{url}}', url)
                .replace('{{cssv}}', CSS_VERSION))
        write(os.path.join(ROOT, rel), page)
        if rel != '404.html':
            urls.append(url)
        print('  ' + rel)

    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += ['  <url><loc>%s%s</loc></url>' % (SITE, u) for u in sorted(urls)]
    sitemap += ['  <url><loc>%s/privacy.html</loc></url>' % SITE, '</urlset>', '']
    write(os.path.join(ROOT, 'sitemap.xml'), '\n'.join(sitemap))
    write(os.path.join(ROOT, 'robots.txt'), 'User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n' % SITE)
    print('Готово: %d страниц, sitemap.xml, robots.txt' % len(pages))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
