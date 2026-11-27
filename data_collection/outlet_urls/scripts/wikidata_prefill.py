#!/usr/bin/env python3
"""Milestone 1 of outlet_domains_plan.md: look up every DNR outlet (2016-2026) in Wikidata.

For each distinct outlet_id the script searches Wikidata for the printed brand names, restricted to items of the
outlet's country (P17 country or P495 country of origin), keeps candidates that are instances of a media class
(newspaper, broadcaster, news website, ...), and records the best one with its official website (P856).

Nothing is written to outlets_<year>.csv. The result is one row per outlet in
    data_collection/outlet_urls/wikidata_candidates.csv
which milestone 2 (agent search) uses as a candidate and as an independent check.

Usage:
    python3 wikidata_prefill.py [--only CHE,SWE] [--cache DIR] [--contact URL-or-email]

Standard library only. `--cache DIR` stores API responses so that a re-run does not query Wikidata again.

Rate limits (mediawiki.org/wiki/Wikimedia_APIs/Rate_limits, 2026): clients whose User-Agent carries no contact
information get 10 requests per minute, clients with a contact (URL or email) 200 per minute. Without `--contact`
the script therefore runs at 9 requests per minute (the full registry takes several hours); with it at 180.
"""
import argparse, csv, difflib, glob, hashlib, json, os, re, sys, time, unicodedata
import threading
import urllib.error, urllib.parse, urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUTLET_DIR = os.path.dirname(HERE)
OUT = os.path.join(OUTLET_DIR, 'wikidata_candidates.csv')
YEARS = range(2016, 2027)
API = 'https://www.wikidata.org/w/api.php'
UA = 'outlet-domain-prefill/0.1 (academic research script)'
LANGS = 'en|de|fr|it|es|pt|nl|sv|nb|da|fi|pl|cs|sk|hu|ro|bg|hr|sr|el|tr'

# id suffixes that denote generic categories ("local newspaper"), not single outlets: no lookup
GENERIC = {'local_newspaper', 'local_radio', 'local_tv', 'regional_tv', 'regional_radio', 'commercial_radio', 'public_radio',
           'city_paper', 'free_city_paper', 'local_weekly', 'foreign_tv', 'foreign_newspaper', 'other_npo_tv_programmes',
           'other_commercial_tv', 'german_public_tv', 'german_commercial_tv', 'french_public_tv', 'french_commercial_tv',
           'belgian_tv', 'german_tv', 'broadcasters_papers_from_outside_sweden', 'regional_news_sites', 'fagblade',
           'foreign_media', 'commercial_tv', 'private_broadcasters', 'private_radio', 'private_tv', 'regional_media',
           'stadtanzeiger', 'free_newspaper', 'tv2_regional', 'other_digital_born', 'other_tv_stations', 'counter_media',
           'other_french_sites', 'national_magazine', 'state_public_tv_radio', 'irish_tabloids', 'other_tv',
           'tg1_tg2_tg3_tg4_tg5'}
MEDIA = re.compile(r'newspaper|news|televis|\btv\b|radio|broadcast|magazine|periodical|website|media|press|channel|'
                   r'portal|tabloid|station|publisher|publication|program|journal|blog|network|web service', re.I)
FIELDS = ['outlet_id', 'country', 'brand', 'first_year', 'last_year', 'printed_domain', 'wikidata_qid', 'wd_label',
          'wd_description', 'wd_classes', 'wd_website', 'wd_domain', 'country_match', 'label_sim', 'n_candidates',
          'dissolved', 'domain_agrees']

CACHE = None
RPM = 9
_lock, _next = threading.Lock(), [0.0]


def throttle():
    with _lock:
        wait = _next[0] - time.time()
        _next[0] = max(_next[0], time.time()) + 60.0 / RPM
    if wait > 0: time.sleep(wait)


def get(url, params=None):
    """GET with on-disk cache and backoff; returns parsed JSON (or text for non-JSON)."""
    full = url + ('?' + urllib.parse.urlencode(params) if params else '')
    path = os.path.join(CACHE, hashlib.sha1(full.encode()).hexdigest()) if CACHE else None
    if path and os.path.exists(path):
        body = open(path, encoding='utf-8').read()
    else:
        for attempt in range(8):
            if 'wikidata.org/w/api.php' in url: throttle()
            try:
                req = urllib.request.Request(full, headers={'User-Agent': UA})
                body = urllib.request.urlopen(req, timeout=60).read().decode('utf-8')
                break
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                if attempt == 7: raise
                retry = getattr(e, 'headers', None) and e.headers.get('Retry-After')
                time.sleep(int(retry) + 1 if retry and retry.isdigit() else 5 * 2 ** attempt)
        if path:
            with open(path, 'w', encoding='utf-8') as f: f.write(body)
    return json.loads(body) if body[:1] in '{[' else body


# ------------------------------------------------------------------------------------------- registered domain
def load_psl():
    txt = get('https://publicsuffix.org/list/public_suffix_list.dat')
    icann = txt.split('// ===END ICANN DOMAINS===')[0]   # private suffixes (blogspot.com ...) are not registries
    return {l.strip() for l in icann.splitlines() if l.strip() and not l.startswith('//')}


def registered_domain(url, psl):
    host = urllib.parse.urlsplit(url if '//' in url else '//' + url).hostname or ''
    labels = host.lower().strip('.').split('.')
    for i in range(len(labels)):
        if '.'.join(labels[i:]) in psl or '*.' + '.'.join(labels[i + 1:]) in psl:
            return '.'.join(labels[max(i - 1, 0):])
    return '.'.join(labels[-2:])


# ------------------------------------------------------------------------------------------------- brand names
def norm(s):
    s = ''.join(c for c in unicodedata.normalize('NFKD', s.lower()) if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def variants(brands):
    """Search strings for one outlet, most specific first: printed names without bracketed additions, then without
    'online'/'website', then without 'news', then without a domain ending."""
    out = []
    def add(v):
        v = re.sub(r'\s+', ' ', v).strip(' -/,.')
        if len(v) > 1 and v.lower() not in [o.lower() for o in out]: out.append(v)
    base = [re.sub(r'\(.*?\)|\(.*$', ' ', b) for b in brands]
    for b in base: add(b)
    for b in base: add(re.sub(r'\b(online|website|websites|app|digital)\b', ' ', b, flags=re.I))
    for b in base: add(re.sub(r'\b(online|website|websites|app|digital|news|nyheter|nyheder|uutiset|noticias)\b', ' ', b, flags=re.I))
    for b in base: add(re.sub(r'\.(com|org|net|[a-z]{2}|co\.uk|com\.tr)\b', ' ', b.split('/')[0], flags=re.I))
    return out[:5]


# ---------------------------------------------------------------------------------------------------- Wikidata
def country_qids(isos):
    q = 'SELECT ?c ?iso WHERE { VALUES ?iso { %s } ?c wdt:P298 ?iso }' % ' '.join(f'"{i}"' for i in isos)
    r = get('https://query.wikidata.org/sparql', {'query': q, 'format': 'json'})
    out = {}
    for b in r['results']['bindings']:
        qid = b['c']['value'].rsplit('/', 1)[1]
        iso = b['iso']['value']
        if iso not in out or int(qid[1:]) < int(out[iso][1:]): out[iso] = qid
    return out


def search(text, cqid=None):
    q = text + (' haswbstatement:' + '|'.join(f'{p}={c}' for c in cqid.split('|') for p in ('P17', 'P495')) if cqid else '')
    r = get(API, {'action': 'query', 'list': 'search', 'srsearch': q, 'srnamespace': 0, 'srlimit': 5, 'format': 'json'})
    return [h['title'] for h in r.get('query', {}).get('search', [])]


def entities(qids, props='labels|aliases|descriptions|claims'):
    out = {}
    qids = list(qids)
    for i in range(0, len(qids), 50):
        r = get(API, {'action': 'wbgetentities', 'ids': '|'.join(qids[i:i + 50]), 'props': props, 'languages': LANGS,
                      'format': 'json'})
        out.update(r.get('entities', {}))
    return out


def claim_values(ent, prop):
    """Values of a property, preferred rank first, deprecated dropped."""
    cl = [c for c in ent.get('claims', {}).get(prop, []) if c.get('rank') != 'deprecated'
          and c['mainsnak'].get('snaktype') == 'value']
    cl.sort(key=lambda c: c.get('rank') != 'preferred')
    vals = []
    for c in cl:
        v = c['mainsnak']['datavalue']['value']
        vals.append(v.get('id') or v.get('time') if isinstance(v, dict) else v)
    return vals


CLASS_LABELS = {}


def class_labels(qids):
    need = [q for q in qids if q not in CLASS_LABELS]
    if need:
        for q, e in entities(need, props='labels').items():
            CLASS_LABELS[q] = e.get('labels', {}).get('en', {}).get('value', q)
    return [CLASS_LABELS.get(q, q) for q in qids]


def lookup(outlet, cqid, psl):
    vs = variants(outlet['brands'])

    def best_of(cands, local):
        best, ents = None, entities(cands) if cands else {}
        for rank, q in enumerate(cands):
            e = ents.get(q, {})
            classes = class_labels(claim_values(e, 'P31'))
            if not any(MEDIA.search(c) for c in classes): continue
            names = [l['value'] for l in e.get('labels', {}).values()] + [a['value'] for al in e.get('aliases', {}).values() for a in al]
            sim = max([difflib.SequenceMatcher(None, norm(v), norm(n)).ratio() for v in vs for n in names] or [0])
            sites = claim_values(e, 'P856')
            score = sim + (0.15 if sites else 0) - 0.01 * rank
            if best is None or score > best['score']:
                best = dict(score=score, qid=q, sim=sim, sites=sites, classes=classes, ent=e, local=local)
        return best

    cands = []
    for v in vs:
        for q in search(v, cqid):
            if q not in cands: cands.append(q)
    best = best_of(cands, 'yes')
    if best is None or best['sim'] < 0.7:   # foreign brands (CNN in Switzerland), items without country statements
        world = []
        for v in vs[:3]:
            for q in search(v):
                if q not in cands and q not in world: world.append(q)
        alt = best_of(world, 'no')
        cands += world
        if alt and (best is None or alt['sim'] > best['sim'] + 0.1): best = alt
    matched = best['local'] if best else ''
    row = dict(outlet_id=outlet['outlet_id'], country=outlet['country'], brand=outlet['brands'][0],
               first_year=outlet['first'], last_year=outlet['last'], printed_domain=outlet['printed'],
               n_candidates=len(cands), country_match=matched)
    if best:
        e = best['ent']
        dom = registered_domain(best['sites'][0], psl) if best['sites'] else ''
        diss = claim_values(e, 'P576')
        row.update(wikidata_qid=best['qid'], wd_label=(e.get('labels', {}).get('en') or next(iter(e.get('labels', {}).values()), {})).get('value', ''),
                   wd_description=e.get('descriptions', {}).get('en', {}).get('value', ''),
                   wd_classes='; '.join(best['classes']), wd_website=best['sites'][0] if best['sites'] else '',
                   wd_domain=dom, label_sim=f"{best['sim']:.2f}", dissolved=diss[0][1:5] if diss else '',
                   domain_agrees='' if not (dom and outlet['printed']) else ('yes' if dom == outlet['printed'] else 'no'))
    return row


def load_outlets(only):
    o = {}
    for y in YEARS:
        for r in csv.DictReader(open(os.path.join(OUTLET_DIR, f'outlets_{y}.csv'), encoding='utf-8')):
            if only and r['country'] not in only: continue
            if r['outlet_id'].split('_', 1)[1] in GENERIC: continue
            d = o.setdefault(r['outlet_id'], dict(outlet_id=r['outlet_id'], country=r['country'], b=Counter(), dom=Counter(), years=set()))
            d['b'][r['brand']] += 1; d['years'].add(y)
            if r['domain']: d['dom'][r['domain']] += 1
    for d in o.values():
        d['brands'] = [b for b, _ in d['b'].most_common()]
        d['printed'] = d['dom'].most_common(1)[0][0] if d['dom'] else ''
        d['first'], d['last'] = min(d['years']), max(d['years'])
    return list(o.values())


def main():
    global CACHE, RPM, UA
    ap = argparse.ArgumentParser()
    ap.add_argument('--only'); ap.add_argument('--cache'); ap.add_argument('--contact')
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()
    if a.contact:
        UA, RPM = f'outlet-domain-prefill/0.1 ({a.contact})', 180
    if a.cache:
        CACHE = a.cache; os.makedirs(CACHE, exist_ok=True)
    outlets = load_outlets(set(a.only.split(',')) if a.only else None)
    psl = load_psl()
    cq = country_qids(sorted({o['country'] for o in outlets}))
    missing = {o['country'] for o in outlets} - set(cq)
    if 'NLD' in cq: cq['NLD'] += '|Q55'   # ISO code sits on the Kingdom (Q29999); media items use Netherlands (Q55)
    print('country items:', ' '.join(f'{k}={v}' for k, v in sorted(cq.items())), file=sys.stderr)
    if missing: sys.exit(f'no Wikidata country item for {missing}')
    with ThreadPoolExecutor(3) as ex:
        rows = list(ex.map(lambda o: lookup(o, cq[o['country']], psl), outlets))
    rows.sort(key=lambda r: r['outlet_id'])
    with open(a.out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    n = len(rows)
    print(f"{n} outlets | item found: {sum(bool(r.get('wikidata_qid')) for r in rows)} | with website: "
          f"{sum(bool(r.get('wd_domain')) for r in rows)} | agrees with printed domain: "
          f"{sum(r.get('domain_agrees') == 'yes' for r in rows)} yes, {sum(r.get('domain_agrees') == 'no' for r in rows)} no -> {a.out}")


if __name__ == '__main__':
    main()
