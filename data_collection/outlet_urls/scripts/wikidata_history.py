#!/usr/bin/env python3
"""Earlier website domains of the Wikidata items found by wikidata_prefill.py.

Wikidata keeps almost no dates on official-website statements (P856), but two traces of older domains exist:
  1. the item itself: additional P856 values of normal or deprecated rank, sometimes with start/end qualifiers;
  2. the item's edit history: every edit that created or changed a P856 statement carries the URL in its edit
     summary, so the dates at which editors recorded each URL can be read from the revision list.

Edit dates say when an editor recorded a URL, not when the outlet moved, and a domain that was never entered in
Wikidata (e.g. b.dk for Berlingske) cannot be recovered this way.

Output: data_collection/outlet_urls/wikidata_domain_history.csv, one row per outlet x registered domain.

Usage:
    python3 wikidata_history.py [--cache DIR] [--contact URL-or-email]
"""
import argparse, csv, os, re, sys
from concurrent.futures import ThreadPoolExecutor

import wikidata_prefill as wp

OUT = os.path.join(wp.OUTLET_DIR, 'wikidata_domain_history.csv')
FIELDS = ['outlet_id', 'wikidata_qid', 'domain', 'is_selected', 'in_item', 'rank', 'start', 'end', 'first_edit',
          'last_edit', 'n_edits']
URL = re.compile(r'\[\[Property:P856(?:\|P856)?\]\]:\s*(\S+?)(?:,|\s|$)')


def revisions(qid, max_pages=20):
    params = {'action': 'query', 'prop': 'revisions', 'titles': qid, 'rvprop': 'timestamp|comment', 'rvlimit': 500,
              'format': 'json'}
    out = []
    for _ in range(max_pages):
        r = wp.get(wp.API, params)
        page = next(iter(r.get('query', {}).get('pages', {}).values()), {})
        out += page.get('revisions', [])
        if 'continue' not in r: break
        params = dict(params, rvcontinue=r['continue']['rvcontinue'])
    return out


def history(row, ent, psl):
    doms = {}
    def d(url):
        dom = wp.registered_domain(url, psl)
        return doms.setdefault(dom, dict(domain=dom, in_item='', rank='', start='', end='', edits=[])) if '.' in dom else None
    for c in ent.get('claims', {}).get('P856', []):
        if c['mainsnak'].get('snaktype') != 'value': continue
        x = d(c['mainsnak']['datavalue']['value'])
        if x is None: continue
        x['in_item'] = 'yes'
        x['rank'] = x['rank'] or c.get('rank', '')
        for prop, key in (('P580', 'start'), ('P582', 'end')):
            q = c.get('qualifiers', {}).get(prop, [])
            if q and q[0].get('snaktype') == 'value': x[key] = q[0]['datavalue']['value']['time'][1:5]
    for rev in revisions(row['wikidata_qid']):
        m = URL.search(rev.get('comment', ''))
        if m and (x := d(m.group(1))) is not None: x['edits'].append(rev['timestamp'][:10])
    return [dict(outlet_id=row['outlet_id'], wikidata_qid=row['wikidata_qid'], domain=x['domain'],
                 is_selected='yes' if x['domain'] == row['wd_domain'] else '', in_item=x['in_item'], rank=x['rank'],
                 start=x['start'], end=x['end'], first_edit=min(x['edits'], default=''),
                 last_edit=max(x['edits'], default=''), n_edits=len(x['edits'])) for x in doms.values()]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--cache'); ap.add_argument('--contact')
    a = ap.parse_args()
    if a.contact: wp.UA, wp.RPM = f'outlet-domain-prefill/0.1 ({a.contact})', 180
    if a.cache:
        wp.CACHE = a.cache; os.makedirs(a.cache, exist_ok=True)
    rows = [r for r in csv.DictReader(open(wp.OUT, encoding='utf-8')) if r['wikidata_qid']]
    psl = wp.load_psl()
    ents = wp.entities(sorted({r['wikidata_qid'] for r in rows}), props='claims')
    with ThreadPoolExecutor(3) as ex:
        out = [x for res in ex.map(lambda r: history(r, ents.get(r['wikidata_qid'], {}), psl), rows) for x in res]
    out.sort(key=lambda r: (r['outlet_id'], r['is_selected'] != 'yes', r['first_edit']))
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(out)
    multi = {r['outlet_id'] for r in out if r['is_selected'] != 'yes'}
    print(f"{len(rows)} items | {len(out)} outlet-domain rows | outlets with more than one domain: {len(multi)} -> {OUT}")


if __name__ == '__main__':
    main()
