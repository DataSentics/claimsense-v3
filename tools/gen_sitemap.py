#!/usr/bin/env python3
"""Generate sitemap.xml for claimsense.app.

Single source of truth for the locale URL map. The hreflang annotations in each
page's <head> must agree with what this emits -- if you add or rename a page,
change PAGES here and re-run, then check the page's own <link rel="alternate">
tags still match.

Only locales listed in LIVE are emitted. A locale that is noindex'd or blocked
in robots.txt must NOT appear in the sitemap: listing a blocked URL contradicts
the block and produces coverage warnings in Search Console.

lastmod comes from git's last commit date for each file, so it stays honest.
Pages with uncommitted changes, or a file git doesn't know about, are emitted
without a lastmod rather than with a guessed one.

Usage:  python tools/gen_sitemap.py          # writes sitemap.xml
        python tools/gen_sitemap.py --check  # exit 1 if sitemap.xml is stale
"""

import io
import os
import subprocess
import sys

BASE = 'https://claimsense.app'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Locales included in the sitemap. Add 'fr' once the French pages lose their
# noindex meta and the Disallow: /fr/ line is removed from robots.txt.
LIVE = ('en', 'de')

# key -> {locale: url path}
PAGES = [
    ('home',           {'en': '/',                'de': '/de/',                   'fr': '/fr/'}),
    ('features',       {'en': '/features/',       'de': '/de/funktionen/',        'fr': '/fr/fonctionnalites/'}),
    ('architecture',   {'en': '/architecture/',   'de': '/de/architektur/',       'fr': '/fr/architecture/'}),
    ('use-cases',      {'en': '/use-cases/',      'de': '/de/anwendungsfaelle/',  'fr': '/fr/cas-d-usage/'}),
    ('implementation', {'en': '/implementation/', 'de': '/de/implementierung/',   'fr': '/fr/implementation/'}),
    ('our-story',      {'en': '/our-story/',      'de': '/de/unsere-geschichte/', 'fr': '/fr/notre-histoire/'}),
    ('pricing',        {'en': '/pricing/',        'de': '/de/preise/',            'fr': '/fr/tarifs/'}),
    ('partners',       {'en': '/partners/',       'de': '/de/partner/',           'fr': '/fr/partenaires/'}),
    ('business-case',  {'en': '/business-case/',  'de': '/de/business-case/',     'fr': '/fr/business-case/'}),
    ('faq',            {'en': '/faq/',            'de': '/de/faq/',               'fr': '/fr/faq/'}),
    ('help',           {'en': '/help/',           'de': '/de/hilfe/',             'fr': '/fr/aide/'}),
    ('careers',        {'en': '/careers/',        'de': '/de/karriere/',          'fr': '/fr/carrieres/'}),
    ('privacy',        {'en': '/privacy/',        'de': '/de/datenschutz/',       'fr': '/fr/confidentialite/'}),
    ('cookie-policy',  {'en': '/cookie-policy/',  'de': '/de/cookie-richtlinie/', 'fr': '/fr/politique-cookies/'}),
]

# x-default points at the English version.
XDEFAULT = 'en'


def rel_file(url_path):
    parts = [p for p in url_path.strip('/').split('/') if p]
    return '/'.join(parts + ['index.html'])


def git_lastmod(rel):
    """Last commit date (YYYY-MM-DD) for a file, or None.

    Returns None when the file has uncommitted changes -- a committed date
    would understate it and today's date would be a guess, so we omit the
    field entirely rather than publish something untrue.
    """
    try:
        dirty = subprocess.run(['git', 'status', '--porcelain', '--', rel],
                               cwd=ROOT, capture_output=True, text=True, timeout=20)
        if dirty.returncode == 0 and dirty.stdout.strip():
            return None
        out = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', rel],
                             cwd=ROOT, capture_output=True, text=True, timeout=20)
        if out.returncode == 0:
            d = out.stdout.strip()
            return d or None
    except Exception:
        pass
    return None


def build():
    missing, urls = [], []
    for key, locales in PAGES:
        live = [(lc, locales[lc]) for lc in LIVE if lc in locales]
        for lc, path in live:
            rel = rel_file(path)
            if not os.path.exists(os.path.join(ROOT, rel.replace('/', os.sep))):
                missing.append(rel)
                continue
            alts = ''.join(
                '\n    <xhtml:link rel="alternate" hreflang="%s" href="%s%s"/>' % (a, BASE, p)
                for a, p in live)
            if XDEFAULT in dict(live):
                alts += ('\n    <xhtml:link rel="alternate" hreflang="x-default" href="%s%s"/>'
                         % (BASE, dict(live)[XDEFAULT]))
            lm = git_lastmod(rel)
            urls.append('  <url>\n    <loc>%s%s</loc>%s%s\n  </url>'
                        % (BASE, path, alts,
                           ('\n    <lastmod>%s</lastmod>' % lm) if lm else ''))
    body = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + '\n'.join(urls) + '\n</urlset>\n')
    return body, len(urls), missing


def main():
    body, n, missing = build()
    out = os.path.join(ROOT, 'sitemap.xml')
    for m in missing:
        sys.stderr.write('WARNING: listed page not found on disk: %s\n' % m)
    if '--check' in sys.argv:
        cur = io.open(out, encoding='utf8').read() if os.path.exists(out) else ''
        if cur != body:
            sys.stderr.write('sitemap.xml is stale -- run: python tools/gen_sitemap.py\n')
            return 1
        print('sitemap.xml is up to date (%d URLs)' % n)
        return 0
    io.open(out, 'w', encoding='utf8', newline='').write(body)
    print('wrote sitemap.xml: %d URLs, locales=%s' % (n, ','.join(LIVE)))
    if 'fr' not in LIVE:
        print('note: French excluded -- add "fr" to LIVE when /fr/ goes live')
    return 0


if __name__ == '__main__':
    sys.exit(main())
