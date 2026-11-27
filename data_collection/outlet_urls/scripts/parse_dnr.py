"""DO NOT RUN — kept for documentation only.

This is the parser used for the first, automatic transcription of the DNR "top brands" charts (October 2026).
Its output was turned into outlets_<year>.csv by build scripts that have since been removed, and the CSVs were
then checked against the reports and corrected by hand (PR #3, November 2026). The CSVs are the authoritative
version; nothing regenerates them. References below to build_csv_all.py and overrides_all.py are to removed files.
The 2016 report was parsed with a separate script that is no longer in the repo.

Original description:

Generic geometric parser for the "TOP BRANDS" charts of the Reuters Digital News Reports 2013-2026.

Usage:  python3 parse_dnr.py <year> [--scratch DIR] [--pdf PATH] [--only CCC,CCC]

For every market page listed in PAGES[year] it runs
    pdftohtml -xml -i -f P -l P <pdf> <scratch>/<year>/xml_P
(if not already present).  pdftohtml splits text into elements by font, so brand labels, bar numbers and
chart headers come out as separate elements with coordinates.  The parser pairs brand labels (right-aligned
to the chart axis) with the numbers printed next to the bars and writes
<scratch>/<year>/parsed_<year>.json  ->  {ISO3: [ {list_type, submarket, brand, pct, use3, page, note}, ... ]}

Chart conventions handled
  * 2013:  "Top online brands" / "Top offline brands" figures (one page per country), numbers printed as "52%".
  * 2014:  "ONLINE" / "OFFLINE" charts, numbers printed as "28%".
  * 2015:  "ONLINE" / "TV, RADIO AND PRINT"; the PDF text layer contains every word twice (second copy
           shifted ~63pt to the right) -> de-duplicated.
  * 2017-2025: two numbers per bar in the text layer: the visible label (weekly use) and a hidden label
           (= weekly use minus "3 days per week or more", i.e. the length of the light bar segment; verified
           by measuring bar lengths in the rendered page).  We store use3 = weekly - hidden.
  * 2020:  one page per country without column headers -> pseudo headers from HEADLESS.
  * 2026:  only one number per bar (weekly use for news).
  * Language sub-markets (Belgium, Switzerland, Canada): header suffixes such as "(FLEMISH SPEAKING)",
           "FLANDERS", "(GERMAN)" -> submarket "flemish-speaking", "german-speaking", ...
  * "ALSO" boxes next to the online chart -> rows with a note.
  * Inset boxes between the two charts ("BBC TV News: 52%", "VRT (Public broadcaster) 67%") -> rows with a
    note where the pattern is simple; other candidates are printed to stderr and added by hand in build_csv_all.py.
  * Hidden design-template annotations in the 2024-2026 PDFs ("Axis Line on both layers:", "90% CMYK Black",
    "Tisa Sans Pro Medium", ...) are dropped via JUNK.
"""
import re, html, sys, json, os, subprocess, statistics

# ---------------------------------------------------------------- page maps (PDF page index, 1-based)
PAGES = {
 2012: {'GBR':27},   # DNR 2012: UK only (figure 1.2f + online table on PDF page 16); rows are entered by hand in overrides_all.MANUAL
 2013: {'GBR':56,'USA':58,'FRA':59,'DEU':60},
 2014: {'USA':21,'GBR':23,'DEU':25,'FRA':27,'DNK':29,'FIN':31,'ESP':33,'ITA':35},
 2015: {'USA':23,'GBR':25,'DEU':27,'FRA':29,'ESP':31,'ITA':33,'IRL':35,'DNK':37,'FIN':39},
 2017: {'GBR':55,'AUT':57,'BEL':59,'HRV':61,'CZE':63,'DNK':65,'FIN':67,'FRA':69,'DEU':71,'GRC':73,'HUN':75,'IRL':77,
        'ITA':79,'NLD':81,'NOR':83,'POL':85,'PRT':87,'ROU':89,'SVK':91,'ESP':93,'SWE':95,'CHE':97,'TUR':99,'USA':103,
        'CAN':109,'MEX':113},
 2018: {'GBR':63,'AUT':65,'BEL':67,'BGR':69,'HRV':71,'CZE':73,'DNK':75,'FIN':77,'FRA':79,'DEU':81,'GRC':83,'HUN':85,
        'IRL':87,'ITA':89,'NLD':91,'NOR':93,'POL':95,'PRT':97,'ROU':99,'SVK':101,'ESP':103,'SWE':105,'CHE':107,'TUR':109,
        'USA':113,'CAN':119,'MEX':123},
 2019: {'GBR':69,'AUT':71,'BEL':73,'BGR':75,'HRV':77,'CZE':79,'DNK':81,'FIN':83,'FRA':85,'DEU':87,'GRC':89,'HUN':91,
        'IRL':93,'ITA':95,'NLD':97,'NOR':99,'POL':101,'PRT':103,'ROU':105,'SVK':107,'ESP':109,'SWE':111,'CHE':113,'TUR':115,
        'USA':119,'CAN':125,'MEX':129},
 2020: {'GBR':62,'AUT':63,'BEL':64,'BGR':65,'HRV':66,'CZE':67,'DNK':68,'FIN':69,'FRA':70,'DEU':71,'GRC':72,'HUN':73,
        'IRL':74,'ITA':75,'NLD':76,'NOR':77,'POL':78,'PRT':79,'ROU':80,'SVK':81,'ESP':82,'SWE':83,'CHE':84,'TUR':85,
        'USA':88,'CAN':91,'MEX':93},
 2021: {'GBR':63,'AUT':65,'BEL':67,'BGR':69,'HRV':71,'CZE':73,'DNK':75,'FIN':77,'FRA':79,'DEU':81,'GRC':83,'HUN':85,
        'IRL':87,'ITA':89,'NLD':91,'NOR':93,'POL':95,'PRT':97,'ROU':99,'SVK':101,'ESP':103,'SWE':105,'CHE':107,'TUR':109,
        'USA':113,'CAN':119,'MEX':125},
 2022: {'GBR':63,'AUT':65,'BEL':67,'BGR':69,'HRV':71,'CZE':73,'DNK':75,'FIN':77,'FRA':79,'DEU':81,'GRC':83,'HUN':85,
        'IRL':87,'ITA':89,'NLD':91,'NOR':93,'POL':95,'PRT':97,'ROU':99,'SVK':101,'ESP':103,'SWE':105,'CHE':107,'TUR':109,
        'USA':113,'CAN':119,'MEX':125},
 2023: {'GBR':59,'AUT':61,'BEL':63,'BGR':65,'HRV':67,'CZE':69,'DNK':71,'FIN':73,'FRA':75,'DEU':77,'GRC':79,'HUN':81,
        'IRL':83,'ITA':85,'NLD':87,'NOR':89,'POL':91,'PRT':93,'ROU':95,'SVK':97,'ESP':99,'SWE':101,'CHE':103,'TUR':105,
        'USA':109,'CAN':115,'MEX':121},
 2024: {'GBR':65,'AUT':67,'BEL':69,'BGR':71,'HRV':73,'CZE':75,'DNK':77,'FIN':79,'FRA':81,'DEU':83,'GRC':85,'HUN':87,
        'IRL':89,'ITA':91,'NLD':93,'NOR':95,'POL':97,'PRT':99,'ROU':101,'SVK':103,'ESP':105,'SWE':107,'CHE':109,'TUR':111,
        'USA':115,'CAN':121,'MEX':127},
 2025: {'GBR':67,'AUT':69,'BEL':71,'BGR':73,'HRV':75,'CZE':77,'DNK':79,'FIN':81,'FRA':83,'DEU':85,'GRC':87,'HUN':89,
        'IRL':91,'ITA':93,'NLD':95,'NOR':97,'POL':99,'PRT':101,'ROU':103,'SRB':105,'SVK':107,'ESP':109,'SWE':111,'CHE':113,
        'TUR':115,'USA':119,'CAN':125,'MEX':131},
 2026: {'GBR':74,'AUT':76,'BEL':78,'BGR':80,'HRV':82,'CZE':84,'DNK':86,'FIN':88,'FRA':90,'DEU':92,'GRC':94,'HUN':96,
        'IRL':98,'ITA':100,'NLD':102,'NOR':104,'POL':106,'PRT':108,'ROU':110,'SRB':112,'SVK':114,'ESP':116,'SWE':118,
        'CHE':120,'TUR':122,'USA':126,'CAN':132,'MEX':138},
}
# printed page number = PDF index + offset
PAGE_OFFSET = {2012:-2, 2013:-2, 2026:-3}
# years whose charts carry a hidden second label (= weekly - 3days)
TWO_NUMBERS = {2017,2018,2019,2020,2021,2022,2023,2024,2025}
# 2020 pages without column headers: pseudo headers (x0, x1, y) for offline/online
HEADLESS = {2020: [dict(x0=275.0,x1=406.0,y=125.0,lt='offline',sub='',t='(pseudo) TV, RADIO AND PRINT'),
                   dict(x0=443.0,x1=516.0,y=125.0,lt='online',sub='',t='(pseudo) ONLINE')]}
SUBMAP = {'flanders':'flemish-speaking','flemish':'flemish-speaking','wallonia':'french-speaking','french':'french-speaking',
          'german':'german-speaking','english':'english-speaking','italian':'italian-speaking'}
STOP = ('CHANGING','DIFFERENT TYPES','SOURCES OF NEWS','DEVICES FOR NEWS','USE AN','AUDIENCE MAP','BRAND ATTRIBUTES',
        'DIGITAL REACH','CROSS PLATFORM','TOP SOCIAL','Q5','Q8A/B','BASE','OVERALL TRUST','PUBLIC OPINION')
STOP_EXACT = ('MEDIA','TRUST','CROSS','TRADITIONAL','CHANGING MEDIA')
JUNK = {'Axis Line on both layers:','0.5pt stroke weight','Rounded ends','90% CMYK Black','90% CMYK','Black','Text:','Numbers:',
        'German Text:','Tisa Sans Pro Medium','Tisa Sans Pro Light','Tisa Sans Pro','Tisa Sans','Light','Medium','Tisa Sans Pro TV Light',
        '6pt w/ -20 tracking','Part','90% CMYK Part'}
ZOOM = 1.5   # pdftohtml default zoom: xml units = pt * 1.5

def is_stop(t):
    u = t.upper()
    return u in STOP_EXACT or any(u == s or u.startswith(s + ' ') or u.startswith(s + ':') for s in STOP)

def load_elements(path):
    s = open(path, encoding='utf-8', errors='replace').read()
    els = []
    for m in re.finditer(r'<text top="(-?\d+)" left="(-?\d+)" width="(\d+)" height="(\d+)" font="(\d+)">(.*?)</text>', s, re.S):
        top, left, w, h, font, body = m.groups()
        t = html.unescape(re.sub(r'<[^>]+>', '', body)).replace('\xa0', ' ').replace('\x08', '').strip()
        t = re.sub(r'\s+', ' ', t)
        if not t or t in JUNK: continue
        x0, y0 = int(left)/ZOOM, int(top)/ZOOM
        els.append(dict(x0=x0, y0=y0, x1=x0+int(w)/ZOOM, y1=y0+int(h)/ZOOM, t=t, font=int(font)))
    return els

def dedup_shadow(els, shift=63.0):
    """2015: every text element exists twice (second copy shifted +shift in x). Drop the right-hand copies."""
    drop = set()
    for w in els:
        for v in els:
            if v is w or v['t'] != w['t']: continue
            if abs(v['y0']-w['y0']) < 1.5 and shift-3 < v['x0']-w['x0'] < shift+3: drop.add(id(v))
    return [e for e in els if id(e) not in drop]

def cy(o): return (o['y0']+o['y1'])/2

HEAD_RE = re.compile(r'^(TV, RADIO,? AND PRINT|OFFLINE|ONLINE|Top (?:online|offline|oﬄine) brands)\b(.*)$')
def find_headers(els):
    heads = []
    for e in els:
        m = HEAD_RE.match(e['t'])
        if not m: continue
        kw, rest = m.group(1), m.group(2).strip()
        lt = 'online' if kw.upper().startswith('ONLINE') or 'online' in kw else 'offline'
        x1 = e['x1']
        if not rest:   # qualifier may be a separate element to the right on the same baseline
            q = [f for f in els if f is not e and abs(cy(f)-cy(e)) < 5 and -2 < f['x0']-e['x1'] < 12 and not HEAD_RE.match(f['t'])]
            if q:
                q = min(q, key=lambda f: f['x0']); rest = q['t'].strip()
        rest = re.sub(r'[()*]', ' ', rest).replace('SPEAKING', '').replace('speaking', '').replace('-', ' ').strip().lower()
        if rest and rest not in SUBMAP: continue      # "ONLINE NEWS" etc. are not chart headers
        heads.append(dict(x0=e['x0'], x1=x1, y=cy(e), lt=lt, sub=SUBMAP.get(rest, ''), t=e['t'] + (' ' + rest if rest else '')))
    return heads

ISNUM = re.compile(r'^\d{1,3}%?$')
def numval(t): return int(t.rstrip('%'))

def parse_page(year, path, pct_suffix=False):
    els = load_elements(path)
    if year == 2015: els = dedup_shadow(els)
    heads = find_headers(els)
    if year in HEADLESS:   # 2020: the left-column heading "WEEKLY REACH OFFLINE AND ONLINE" is split into elements
        heads = [h for h in heads if h['x0'] > 150]
        if not heads: heads = [dict(h) for h in HEADLESS[year]]
    if not heads:
        print(f'!! no chart headers found in {path}', file=sys.stderr); return []
    heads.sort(key=lambda h: (h['y'], h['x0']))
    rows_h = []
    for h in heads:
        if rows_h and abs(rows_h[-1][0]['y'] - h['y']) < 8: rows_h[-1].append(h)
        else: rows_h.append([h])
    page_bottom = max(e['y1'] for e in els)
    numeric_ok = lambda t: ISNUM.fullmatch(t) is not None and (pct_suffix or not t.endswith('%')) and 0 < numval(t) <= 100
    out = []
    for ri, hrow in enumerate(rows_h):
        y_top = max(h['y'] for h in hrow) + 4
        y_end = rows_h[ri+1][0]['y'] - 2 if ri+1 < len(rows_h) else page_bottom
        for e in els:
            if y_top + 20 < e['y0'] < y_end and e['x0'] > 150 and is_stop(e['t']): y_end = e['y0'] - 2
        blk = [e for e in els if y_top < cy(e) < y_end]
        used = set()
        # ---- ALSO boxes
        also_rows = []
        for e in blk:
            if e['t'] not in ('ALSO', 'Also'): continue
            used.add(id(e))
            ax, ay = e['x0'], e['y1']
            for m in blk:
                if ay - 1 < m['y0'] < ay + 90 and ax - 4 < m['x0'] < ax + 6 and id(m) not in used:
                    roww = [w for w in blk if abs(cy(w)-cy(m)) < 3 and ax - 4 <= w['x0'] < ax + 110]
                    txt = ' '.join(w['t'] for w in sorted(roww, key=lambda w: w['x0']))
                    mm = re.fullmatch(r'(.+?)\s*:?\s*(\d+)%', txt)
                    if mm:
                        also_rows.append(dict(brand=mm.group(1).strip(), pct=int(mm.group(2)), y=cy(m), x=ax))
                        for w in roww: used.add(id(w))
        # ---- label clusters (right edge of label elements)
        cand = [(e['x1'], e) for e in blk if not numeric_ok(e['t']) and id(e) not in used]
        cand.sort(key=lambda c: c[0])
        clusters = []
        for x1, e in cand:
            if clusters and abs(clusters[-1]['x'] - x1) < 3.0:
                clusters[-1]['els'].append(e); clusters[-1]['xs'].append(x1); clusters[-1]['x'] = statistics.median(clusters[-1]['xs'])
            else: clusters.append(dict(x=x1, xs=[x1], els=[e]))
        clusters = [c for c in clusters if len(c['els']) >= 3]
        allnums = [e for e in blk if numeric_ok(e['t']) and id(e) not in used]
        axes = []
        for c in clusters:
            ax = c['x']
            hits = sum(1 for e in c['els'] if any(ax + 1 < n['x0'] < ax + 150 and abs(cy(n)-cy(e)) < 7 for n in allnums))
            if hits < max(2, 0.5 * len(c['els'])): continue
            def dist(h):   # distance between the axis and the header keyword's span
                if h['x0'] - 5 <= ax <= h['x1'] + 5: return 0
                return min(abs(ax - h['x0']), abs(ax - h['x1']))
            h = min(hrow, key=dist)
            axes.append(dict(x=ax, head=h, n=len(c['els'])))
        best = {}
        for a in axes:
            k = id(a['head'])
            if k not in best or a['n'] > best[k]['n']: best[k] = a
        axes = sorted(best.values(), key=lambda a: a['x'])
        if len(axes) < len(hrow):
            print(f'!! {path}: found {len(axes)} axes for {len(hrow)} headers {[h["t"] for h in hrow]}', file=sys.stderr)
        for ai, a in enumerate(axes):
            ax, h = a['x'], a['head']
            x_hi = ax + 200
            if ai + 1 < len(axes): x_hi = min(x_hi, axes[ai+1]['x'] - 60)
            nums = sorted([e for e in allnums if ax + 1 < e['x0'] < x_hi and id(e) not in used], key=cy)
            nrows = []
            for e in nums:
                if nrows and abs(cy(e) - nrows[-1]['y']) < 3.5: nrows[-1]['nums'].append(e)
                else: nrows.append(dict(y=cy(e), nums=[e]))
            labels = sorted([e for e in blk if not numeric_ok(e['t']) and id(e) not in used and abs(e['x1'] - ax) <= 3.0 and e['x0'] > ax - 260], key=cy)
            if len(nrows) >= 3:   # stop after an abnormal gap (other charts further down)
                gaps = [nrows[i+1]['y'] - nrows[i]['y'] for i in range(len(nrows)-1)]
                med = statistics.median(gaps)
                for i, g in enumerate(gaps):
                    if g > 2.6 * med: nrows = nrows[:i+1]; break
            rows = []
            for nr in nrows:
                near = sorted([l for l in labels if abs(cy(l) - nr['y']) < 6.5], key=cy)
                if not near: continue
                brand = ' '.join(l['t'] for l in near)
                for l in near: labels.remove(l)
                nw = sorted(nr['nums'], key=lambda w: w['x0'])
                note = ''
                if len(nw) > 2 and year in TWO_NUMBERS:
                    print(f'!! {path} {h["lt"]} {brand}: dropping extra number labels {[w["t"] for w in nw[2:]]}', file=sys.stderr)
                    nw = nw[:2]
                vals = sorted({numval(w['t']) for w in nw}, reverse=True)
                pct, use3 = vals[0], None
                if year in TWO_NUMBERS and len(vals) == 2: use3 = pct - vals[1]
                elif len(vals) > 1:
                    note = f'number labels in text layer: {vals}'
                    print(f'!! {path} {h["lt"]} {brand}: numbers {vals}', file=sys.stderr)
                rows.append(dict(list_type=h['lt'], submarket=h['sub'], brand=brand, pct=pct, use3=use3, note=note, y=nr['y']))
                for w in nr['nums']: used.add(id(w))
                for l in near: used.add(id(l))
            leftover = [l['t'] for l in labels if any(abs(cy(l) - r['y']) < 14 for r in rows)]
            if leftover: print(f'!! {path} {h["lt"]} {h["sub"]}: unpaired label lines {leftover}', file=sys.stderr)
            out.extend(rows)
        on = [h for h in hrow if h['lt'] == 'online']
        for r in also_rows:
            # the box belongs to the chart whose axis lies left of it
            left = [a for a in axes if a['x'] < r['x']]
            h = left[-1]['head'] if left else (on[0] if on else hrow[0])
            out.append(dict(list_type=h['lt'], submarket=h['sub'], brand=r['brand'], pct=r['pct'], use3=None,
                            note=f"listed in 'ALSO' box next to the {'online' if h['lt']=='online' else 'TV/radio/print'} chart", y=r['y']))
        # ---- inset boxes between the two charts
        if len(axes) >= 2:
            lo, hi = axes[0]['x'] + 15, axes[-1]['x'] - 30
            off = [h for h in hrow if h['lt'] == 'offline']
            for e in blk:
                if id(e) in used or not (lo < e['x0'] < hi) or not re.search(r'\d+%', e['t']): continue
                roww = sorted([w for w in blk if abs(cy(w)-cy(e)) < 4 and lo < w['x0'] < hi + 40 and id(w) not in used], key=lambda w: w['x0'])
                txt = ' '.join(w['t'] for w in roww)
                mm = re.fullmatch(r'([A-Za-zÀ-ž][^%]*?)\s*:?\s*(\d+)%', txt)
                if mm and len(mm.group(1).split()) <= 5:
                    out.append(dict(list_type='offline', submarket=off[0]['sub'] if off else '', brand=mm.group(1).strip(), pct=int(mm.group(2)),
                                    use3=None, note='inset box next to the TV/radio/print chart', y=cy(e)))
                    for w in roww: used.add(id(w))
                else:
                    print(f'?? inset candidate {path}: {txt!r} (x0={e["x0"]:.0f}, y={e["y0"]:.0f})', file=sys.stderr)
    return out

def main():
    year = int(sys.argv[1])
    scratch = sys.argv[sys.argv.index('--scratch')+1] if '--scratch' in sys.argv else '.'
    pdf = sys.argv[sys.argv.index('--pdf')+1] if '--pdf' in sys.argv else f'data_collection/DNRs/Digital-News-Report-{year}.pdf'
    only = sys.argv[sys.argv.index('--only')+1].split(',') if '--only' in sys.argv else None
    d = os.path.join(scratch, str(year)); os.makedirs(d, exist_ok=True)
    res = {}
    for c, p in PAGES[year].items():
        if only and c not in only: continue
        xml = os.path.join(d, f'xml_{p}.xml')
        if not os.path.exists(xml):
            subprocess.run(['pdftohtml', '-xml', '-i', '-f', str(p), '-l', str(p), pdf, xml[:-4]], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        rows = parse_page(year, xml, pct_suffix=(year <= 2014))
        for r in rows: r['page'] = p + PAGE_OFFSET.get(year, 0); r.pop('y', None)
        res[c] = rows
        print(f'=== {c} p{p}: {len(rows)} rows')
        for r in rows:
            u = '' if r['use3'] is None else f'(3d+ {r["use3"]})'
            print(f"  {r['list_type']:8s} {r['submarket']:16s} {r['pct']:3d} {u:9s} {r['brand']}  {r['note']}")
    if not only:
        json.dump(res, open(os.path.join(d, f'parsed_{year}.json'), 'w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
