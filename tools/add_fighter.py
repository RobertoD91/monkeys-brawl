#!/usr/bin/env python3
"""Aggiunge lottatori del fork (roberto, andrea, ...) alle pagine compilate (index.html, test/index.html).

Il bundle è minificato: per ogni tabella per personaggio lo script copia il valore di un lottatore
"modello" (o usa un valore esplicito) e lo inserisce subito dopo l'apertura della tabella, trovata con
ancore testuali uniche. Fallisce se un'ancora manca o compare più volte (es. dopo un aggiornamento da
upstream che cambia la minificazione). Idempotente: un lottatore già presente non viene reinserito.

Uso: python3 tools/add_fighter.py <commit_repo_asset> <id> [<id> ...] [--refresh <id> ...]
     (aggiorna sempre MB_ASSET_CDN al commit indicato; i .glb vengono letti da ../monkeys-brawl-assets)
     --refresh: per lottatori già presenti il cui .glb è cambiato, aggiorna hash (MB_ASSET_VER),
     dimensione (sizes) e misure (MB_ASSET_META.chars) senza toccare il resto.
     --pages <file.html> ...: pagine da modificare (default: index.html e test/index.html di questo repo).

Lottatori privati: se esiste ../brawl/game/fighters_private.py (o $BRAWL_PRIVATE), le sue voci
FIGHTERS_PRIVATE si aggiungono a FIGHTERS. Quelle con local=True non passano da jsDelivr: il nome del
.glb finisce in MB_LOCAL_GLB e un piccolo hook su XMLHttpRequest reindirizza le loro richieste a
assets/chars/<id>.glb (il sito privato li serve da sé; il resto degli asset non cambia).
Non usarle mai sulle pagine del repo pubblico.
"""
import hashlib, json, os, re, struct, sys

ASSET_OWNER = 'RobertoD91'
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, '..', '..', 'monkeys-brawl-assets')
PAGES = [os.path.join(HERE, '..', 'index.html'), os.path.join(HERE, '..', 'test', 'index.html')]

FIGHTERS = {
    'roberto': dict(
        roster='{id:"roberto",name:"Roberto",accent:"#00B3A4"}',
        model='francesco',                      # da chi copiare le tabelle non specificate
        nt_replace={'name:"Schiaffoni"': 'name:"Ingegnere"'},
        Tt='{sp:mn.francesco.sp,su:mn.francesco.su}',
        ls='{tag:"Ingegnere",sp:["Debug a Raffica","sette schiaffi rapidissimi, l\'ultimo fa volare"],'
           'su:["Prompt Engineering","scatta in avanti, afferra l\'avversario, lo riempie di schiaffi e lo lancia con un PROMPT!"]}',
        xu='{pa:"non arretra",sp:"raffica di schiaffi",su:"presa e PROMPT!"}',
        ao='["Ho chiesto all\'IA come batterti. Ha detto: schiaffi."]',
        grip=[-0.005, 0.045, 0.013],
        looks='{look:{S:1,bw:1.06,bd:1.04,waist:1.02,belly:0,aT:1.02,lT:1,nk:1.06,hipW:1,skin:"#dca37e",hair:"#2a1d16",'
              'eye:"#5a3a22",brow:"#24170f",fw:1,fh:1.06,fd:1,taper:.1,hollow:0,jaw:.08,cheek:.04,chin:.04,'
              'nose:[1,1.1,1,-.13,0],lid:.12,browT:1.25,browA:.08,browY:0,mouth:"smirk",style:"francesco",'
              'beard:{line:[-.38,-.5,-.42,-.02],off:.008,chin:.03,col:"#2b1f17"},stash:{w:.34,r:.022,y:-.26,droop:.12,'
              'col:"#24170f"},stub:0},casual:{top:"jacket",jacket:"#1f2a44",lapel:"#1a2338",under:"openshirt",'
              'shirt:"#f4f4f2",pants:"#1f2a44",shoe:"#0f0f12",belt:"#141418",cuff:1}}',
    ),
    'andrea': dict(
        roster='{id:"andrea",name:"Andrea",accent:"#B388FF"}',
        model='petruzzellis',
        nt='jt("giacomo",{name:"Relatore",hp:104,spd:1.02,passive:"Botta e risposta: parare nell\'istante giusto '
           'stordisce chi attacca",bars:{pow:3,spd:3,res:3,rng:5}})',
        Et_replace={'"Uncino Vittoriano"': '"Domanda Scomoda"', '"Mulinello d\'Acciaio"': '"Slide Successiva"',
                    'GIUDICATO!': 'NEXT SLIDE!'},
        Tt='{sp:mn.giacomo.sp,su:mn.giacomo.su}',
        ls='{tag:"Relatore",sp:["Slide di Riserva","si ripara dietro le slide: scudo e un po\' di vita"],'
           'su:["Grafico a Barre","salta e fa spuntare da terra le barre di un istogramma intorno all\'avversario"]}',
        xu='{pa:"parata perfetta stordisce",sp:"scudo e cura",su:"istogramma dal pavimento"}',
        ao='["Prossima slide: tu al tappeto."]',
        grip=[-0.005, 0.05, 0.015],
        looks='{look:{S:1.02,bw:.9,bd:.9,waist:.86,belly:0,aT:.9,lT:.94,nk:.94,hipW:.9,skin:"#ecc4a4",hair:"#1f1712",'
              'eye:"#5b4330",brow:"#1f1712",fw:.94,fh:1.08,fd:.98,taper:.14,hollow:.02,jaw:0,cheek:.04,chin:.04,'
              'nose:[1,1.12,1,-.13,0],lid:.12,browT:1.1,browA:.1,browY:0,mouth:"grin",style:"francesco",'
              'beard:{line:[-.36,-.5,-.42,-.02],off:.009,chin:.035,col:"#241a14"},stash:{w:.34,r:.022,y:-.26,droop:.14,'
              'col:"#1f1712"},stub:0},casual:{top:"jacket",jacket:"#3a3d44",lapel:"#32353b",under:"openshirt",'
              'shirt:"#f4f4f2",pants:"#3a3d44",shoe:"#0f0f12",belt:"#141418",cuff:1}}',
    ),
}

# tabelle per personaggio nella riga principale: nome -> ancora (la tabella si apre alla fine dell'ancora)
_PRIV = os.environ.get('BRAWL_PRIVATE') or os.path.join(HERE, '..', '..', 'brawl', 'game', 'fighters_private.py')
if os.path.exists(_PRIV):
    import importlib.util
    _spec = importlib.util.spec_from_file_location('fighters_private', _PRIV)
    _mod = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_mod)
    FIGHTERS.update(_mod.FIGHTERS_PRIVATE)

TABLES = {
    'ls': 'Yt.forEach(e=>Z[e.id]=e);const ls={',
    'nt': 'return n},nt={',
    'Ea': 'window.MB_PARRY=Ta;const Ea={',
    'hs': 'ada:.937},hs={',
    'Na': 'window.MB_FAT=fs;const Na={',
    'Tt': '!c.fired&&c.t>=i&&(c.fired=1,s(a,o,r,c))}}),Tt={',
    'Et': 'anim:i[0].anim},s||{}),Et={',
    'ao': 'to(e,i)}const ao={',
    'Lc': 'LINGER:3},Lc={',
    'Dc': 'gaetano:[0,4.2]},Dc={',
    'Vl': 'CSC:.2},Vl={',
    'xu': 'n.scrollWidth>n.clientWidth+1)&&n.remove()})}const xu={',
}


def value_at(s, i):
    """Espressione JS che parte da s[i] fino alla virgola/chiusura di livello 0."""
    d, j, q = 0, i, None
    while j < len(s):
        c = s[j]
        if q:
            if c == '\\':
                j += 2
                continue
            if c == q:
                q = None
        elif c in '"\'`':
            q = c
        elif c in '([{':
            d += 1
        elif c in ')]}':
            if d == 0:
                break
            d -= 1
        elif c == ',' and d == 0:
            break
        j += 1
    return s[i:j]


def table_value(s, anchor, key, quoted=False):
    """Valore di `key` nella tabella che si apre alla fine di `anchor`."""
    start = s.index(anchor) + len(anchor)
    k = ('"%s":' if quoted else '%s:') % key
    d, j, q = 0, start, None
    while j < len(s):
        c = s[j]
        if d == 0 and q is None and s.startswith(k, j) and s[j - 1] in '{,':
            return value_at(s, j + len(k))
        if q:
            if c == '\\':
                j += 2
                continue
            if c == q:
                q = None
        elif c in '"\'`':
            q = c
        elif c in '([{':
            d += 1
        elif c in ')]}':
            if d == 0:
                raise KeyError('%s non trovato dopo %r' % (key, anchor))
            d -= 1
        j += 1
    raise KeyError(key)


def insert_after(s, anchor, text):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit('ancora trovata %d volte: %r' % (n, anchor))
    i = s.index(anchor) + len(anchor)
    return s[:i] + text + s[i:]


def glb_meta(path):
    """hh/ho dai fianchi, h dall'ingombro della mesh (POSITION min/max con la trasformazione del nodo)."""
    b = open(path, 'rb').read()
    n = struct.unpack('<I', b[12:16])[0]
    g = json.loads(b[20:20 + n])
    hips = next(x for x in g['nodes'] if x.get('name') == 'mixamorigHips')
    t = hips.get('translation', [0, 0, 0])
    node = next(x for x in g['nodes'] if 'mesh' in x)
    acc = g['accessors'][g['meshes'][node['mesh']]['primitives'][0]['attributes']['POSITION']]
    sc = node.get('scale', [1, 1, 1])[1]
    tr = node.get('translation', [0, 0, 0])[1]
    lo, hi = acc['min'][1], acc['max'][1]
    if acc.get('normalized'):
        lo, hi = max(lo, -1.0), min(hi, 1.0)
    h = (hi - lo) * sc
    return round(t[1], 4), [round(t[0], 4), 0.0, round(t[2], 4)], round(h, 4)


def glb_file(fid):
    return os.path.join(FIGHTERS[fid].get('glb_dir', ASSETS), fid + '.glb')


def add(s, fid, cfg):
    glb_path = glb_file(fid)
    if cfg.get('local'):            # servito dal sito stesso (assets/chars/<id>.glb), non da jsDelivr
        anchor = re.search(r"window\.MB_ASSET_BASE=window\.MB_ASSET_BASE\|\|'[^']*';", s).group(0)
        if 'window.MB_LOCAL_GLB=[' not in s:
            hook = ("window.MB_LOCAL_GLB=[];(function(){var o=XMLHttpRequest.prototype.open;"
                    "XMLHttpRequest.prototype.open=function(m,u){try{var f=String(u).split('?')[0].split('/').pop();"
                    "if(window.MB_LOCAL_GLB.indexOf(f)>=0&&String(u).indexOf('assets/chars/')!==0)"
                    "arguments[1]='assets/chars/'+f}catch(e){}return o.apply(this,arguments)}})();")
            s = s.replace(anchor, anchor + hook, 1)
        s = s.replace('window.MB_LOCAL_GLB=[', 'window.MB_LOCAL_GLB=["%s.glb",' % fid, 1)
    glb = open(glb_path, 'rb').read()
    ver = hashlib.sha1(glb).hexdigest()[:10]
    model = cfg['model']

    # --- configurazione asset ---
    s = insert_after(s, 'window.MB_ASSET_VER={', '"chars/%s":"%s",' % (fid, ver))
    s = insert_after(s, '"sizes":{', '"chars/%s":%d,' % (fid, len(glb)))
    s = insert_after(s, '"map":{', '"%s":%s,' % (fid, table_value(s, '"map":{', model, quoted=True)))
    hh, ho, h = glb_meta(glb_path)
    meta = {'hh': hh, 'ho': ho, 'h': h, 'grip': cfg['grip']}
    s = insert_after(s, '"chars":{', '"%s":%s,' % (fid, json.dumps(meta, separators=(',', ':'))))

    # --- roster e aspetto procedurale ---
    i = s.index('window.HCG_ROSTER=[{id:"simone"') + len('window.HCG_ROSTER=')
    arr = value_at(s, i)
    assert arr.startswith('[') and arr.endswith(']'), 'HCG_ROSTER'
    j = i + len(arr) - 1
    s = s[:j] + ',' + cfg['roster'] + s[j:]
    anchor = '\nwindow.MB_LOOKS=window.MB_LOOKS||{},window.MB_LOOKS.ada='
    assert s.count(anchor) == 1, 'MB_LOOKS.ada'
    i = s.index('\n', s.index(anchor) + 1)
    s = s[:i] + '\nwindow.MB_LOOKS=window.MB_LOOKS||{},window.MB_LOOKS.%s=%s;' % (fid, cfg['looks']) + s[i:]

    # --- tabelle di gioco ---
    if 'scale' in cfg:                      # scala del modello GLB (come vito: xn={vito:1.08})
        s = insert_after(s, ',xn={', '%s:%s,' % (fid, cfg['scale']))
    for name, anchor in TABLES.items():
        if name in cfg:
            v = cfg[name]
        elif name + '_parts' in cfg:        # es. Tt: sp da un lottatore, su da un altro, con testi sostituiti
            parts = []
            for prop, (src, repl) in cfg[name + '_parts'].items():
                pv = table_value(table_value(s, anchor, src), '{', prop)
                for a, b in repl.items():
                    assert a in pv, '%s.%s: %r non trovato' % (src, prop, a)
                    pv = pv.replace(a, b)
                parts.append('%s:%s' % (prop, pv))
            v = '{' + ','.join(parts) + '}'
        else:
            v = table_value(s, anchor, model)
            for a, b in cfg.get(name + '_replace', {}).items():
                assert a in v, '%s: %r non trovato nel valore di %s' % (name, a, model)
                v = v.replace(a, b)
        s = insert_after(s, anchor, '%s:%s,' % (fid, v))
    print('  + %s (glb v=%s, %d byte, hh=%s h=%s)' % (fid, ver, len(glb), hh, h))
    return s


def refresh(s, fid):
    glb_path = glb_file(fid)
    glb = open(glb_path, 'rb').read()
    ver = hashlib.sha1(glb).hexdigest()[:10]
    hh, ho, h = glb_meta(glb_path)
    meta = {'hh': hh, 'ho': ho, 'h': h, 'grip': FIGHTERS[fid]['grip']}
    for pat, rep in [(r'"chars/%s":"[0-9a-f]+"' % fid, '"chars/%s":"%s"' % (fid, ver)),
                     (r'"chars/%s":\d+' % fid, '"chars/%s":%d' % (fid, len(glb))),
                     (r'"%s":\{"hh":[^}]*\}' % fid, '"%s":%s' % (fid, json.dumps(meta, separators=(',', ':'))))]:
        s, n = re.subn(pat, rep, s)
        assert n == 1, (fid, pat, n)
    print('  ~ %s aggiornato (glb v=%s, %d byte)' % (fid, ver, len(glb)))
    return s


def patch(path, commit, ids, refresh_ids=()):
    s = open(path, encoding='utf-8').read()
    s, n = re.subn(r'window\.MB_ASSET_CDN="https://cdn\.jsdelivr\.net/gh/[^/]+/monkeys-brawl-assets@[0-9a-f]+/"',
                   'window.MB_ASSET_CDN="https://cdn.jsdelivr.net/gh/%s/monkeys-brawl-assets@%s/"' % (ASSET_OWNER, commit), s)
    assert n == 1, 'MB_ASSET_CDN'
    print(path)
    for fid in ids:
        if 'id:"%s"' % fid in s:
            print('  = %s già presente' % fid)
            continue
        s = add(s, fid, FIGHTERS[fid])
    for fid in refresh_ids:
        s = refresh(s, fid)
    open(path, 'w', encoding='utf-8').write(s)


if __name__ == '__main__':
    args = sys.argv[1:]
    commit = args.pop(0)
    pages = PAGES
    if '--pages' in args:
        i = args.index('--pages'); pages = args[i + 1:]; args = args[:i]
    rid = args[args.index('--refresh') + 1:] if '--refresh' in args else []
    ids = args[:args.index('--refresh')] if '--refresh' in args else args
    for fid in ids + rid:
        if fid not in FIGHTERS:
            raise SystemExit('lottatore sconosciuto: ' + fid)
    for p in pages:
        if p in PAGES and any(FIGHTERS[f].get('local') for f in ids + rid):
            raise SystemExit('lottatori privati sulle pagine pubbliche: usa --pages')
        patch(p, commit, ids, rid)
