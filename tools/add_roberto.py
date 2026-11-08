#!/usr/bin/env python3
"""Aggiunge il lottatore "roberto" alle pagine compilate (index.html e test/index.html).

Il bundle è minificato: lo script inserisce le voci di roberto subito dopo l'apertura di
ogni tabella per personaggio, cercando ancore testuali uniche. Fallisce se un'ancora manca
o compare più volte (es. dopo un aggiornamento da upstream che cambia la minificazione).
È idempotente: se roberto c'è già, non fa nulla.

Uso: python3 tools/add_roberto.py <commit_repo_asset> [file.html ...]
"""
import hashlib, json, re, sys, os

ASSET_OWNER = 'RobertoD91'
ID = 'roberto'
ROSTER = '{id:"roberto",name:"Roberto",accent:"#00B3A4"}'
GLB = os.path.join(os.path.dirname(__file__), '..', '..', 'monkeys-brawl-assets', 'roberto.glb')

# Aspetto procedurale (usato se il .glb non si carica o con ?proc=1): base Francesco, senza occhiali,
# barba piena, abito blu scuro con camicia bianca e cravatta rossa.
LOOKS = ('window.MB_LOOKS=window.MB_LOOKS||{},window.MB_LOOKS.roberto={look:{S:1,bw:1.06,bd:1.04,waist:1.02,belly:0,'
         'aT:1.02,lT:1,nk:1.06,hipW:1,skin:"#dca37e",hair:"#2a1d16",eye:"#5a3a22",brow:"#24170f",fw:1,fh:1.06,fd:1,'
         'taper:.1,hollow:0,jaw:.08,cheek:.04,chin:.04,nose:[1,1.1,1,-.13,0],lid:.12,browT:1.25,browA:.08,browY:0,'
         'mouth:"smirk",style:"francesco",beard:{line:[-.38,-.5,-.42,-.02],off:.008,chin:.03,col:"#2b1f17"},'
         'stash:{w:.34,r:.022,y:-.26,droop:.12,col:"#24170f"},stub:0},'
         'casual:{top:"jacket",jacket:"#1f2a44",lapel:"#1a2338",under:"openshirt",shirt:"#f4f4f2",'
         'pants:"#1f2a44",shoe:"#0f0f12",belt:"#141418",cuff:1}};')


def value_at(s, i):
    """Restituisce l'espressione JS che parte da s[i] fino alla virgola/chiusura di livello 0."""
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


def table_value(s, anchor, key='francesco', quoted=False):
    """Valore di `key` nella tabella che si apre alla fine di `anchor`."""
    start = s.index(anchor) + len(anchor)
    k = ('"%s":' if quoted else '%s:') % key
    # cerca la chiave a profondità 1 dentro la tabella
    d, j, q = 0, start, None
    while j < len(s):
        c = s[j]
        if q:
            if c == '\\':
                j += 2
                continue
            if c == q:
                q = None
        elif c in '"\'`' and not (d == 0 and s.startswith(k, j)):
            q = c
        elif c in '([{':
            d += 1
        elif c in ')]}':
            if d == 0:
                raise KeyError('%s non trovato dopo %r' % (key, anchor))
            d -= 1
        if d == 0 and s.startswith(k, j) and s[j - 1] in '{,':
            return value_at(s, j + len(k))
        j += 1
    raise KeyError(key)


def insert_after(s, anchor, text):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit('ancora trovata %d volte: %r' % (n, anchor))
    i = s.index(anchor) + len(anchor)
    return s[:i] + text + s[i:]


def patch(path, commit):
    s = open(path, encoding='utf-8').read()
    if 'id:"roberto"' in s:
        print(path, ': roberto già presente, niente da fare')
        return
    glb = open(GLB, 'rb').read()
    ver = hashlib.sha1(glb).hexdigest()[:10]

    # --- configurazione asset (riga MB_ASSET_*) ---
    s, n = re.subn(r'window\.MB_ASSET_CDN="https://cdn\.jsdelivr\.net/gh/[^/]+/monkeys-brawl-assets@[0-9a-f]+/"',
                   'window.MB_ASSET_CDN="https://cdn.jsdelivr.net/gh/%s/monkeys-brawl-assets@%s/"' % (ASSET_OWNER, commit), s)
    assert n == 1, 'MB_ASSET_CDN'
    s = insert_after(s, 'window.MB_ASSET_VER={', '"chars/%s":"%s",' % (ID, ver))
    s = insert_after(s, '"sizes":{', '"chars/%s":%d,' % (ID, len(glb)))
    fmap = table_value(s, '"map":{', quoted=True)
    s = insert_after(s, '"map":{', '"%s":%s,' % (ID, fmap))
    meta = {'hh': 0.7, 'ho': [0.0, 0.0, -0.046], 'h': 1.995, 'grip': [-0.005, 0.045, 0.013]}
    s = insert_after(s, '"chars":{', '"%s":%s,' % (ID, json.dumps(meta, separators=(',', ':'))))

    # --- aspetto procedurale e roster ---
    s = insert_after(s, 'window.HCG_ROSTER=[{id:"simone"', '')  # verifica unicità
    s = s.replace('{id:"ada",name:"Ada",accent:"#FF5FA2"}]', '{id:"ada",name:"Ada",accent:"#FF5FA2"},%s]' % ROSTER, 1)
    assert ROSTER in s, 'HCG_ROSTER'
    s = insert_after(s, '\nwindow.MB_LOOKS=window.MB_LOOKS||{},window.MB_LOOKS.ada=', '')  # verifica
    i = s.index('\nwindow.MB_LOOKS=window.MB_LOOKS||{},window.MB_LOOKS.ada=')
    i = s.index('\n', i + 1)
    s = s[:i] + '\n' + LOOKS + s[i:]

    # --- tabelle di gioco (riga principale) ---
    nt = table_value(s, 'return n},nt={')
    nt = nt.replace('name:"Schiaffoni"', 'name:"Ingegnere"')
    et = table_value(s, 'anim:i[0].anim},s||{}),Et={')
    vl = table_value(s, 'CSC:.2},Vl={')
    lc = table_value(s, 'LINGER:3},Lc={')
    dc = table_value(s, 'gaetano:[0,4.2]},Dc={')
    ea = table_value(s, 'window.MB_PARRY=Ta;const Ea={')
    hs = table_value(s, 'ada:.937},hs={')
    na = table_value(s, 'window.MB_FAT=fs;const Na={')
    adds = [
        ('Yt.forEach(e=>Z[e.id]=e);const ls={',
         'roberto:{tag:"Ingegnere",sp:["Debug a Raffica","sette schiaffi rapidissimi, l\'ultimo fa volare"],'
         'su:["Prompt Engineering","scatta in avanti, afferra l\'avversario, lo riempie di schiaffi e lo lancia con un PROMPT!"]},'),
        ('return n},nt={', 'roberto:%s,' % nt),
        ('window.MB_PARRY=Ta;const Ea={', 'roberto:%s,' % ea),
        ('ada:.937},hs={', 'roberto:%s,' % hs),
        ('window.MB_FAT=fs;const Na={', 'roberto:%s,' % na),
        ('!c.fired&&c.t>=i&&(c.fired=1,s(a,o,r,c))}}),Tt={', 'roberto:{sp:mn.francesco.sp,su:mn.francesco.su},'),
        ('anim:i[0].anim},s||{}),Et={', 'roberto:%s,' % et),
        ('to(e,i)}const ao={', 'roberto:["Ho chiesto all\'IA come batterti. Ha detto: schiaffi."],'),
        ('LINGER:3},Lc={', 'roberto:%s,' % lc),
        ('gaetano:[0,4.2]},Dc={', 'roberto:%s,' % dc),
        ('CSC:.2},Vl={', 'roberto:%s,' % vl),
        ('n.scrollWidth>n.clientWidth+1)&&n.remove()})}const xu={',
         'roberto:{pa:"non arretra",sp:"raffica di schiaffi",su:"presa e PROMPT!"},'),
    ]
    for anchor, text in adds:
        s = insert_after(s, anchor, text)
    open(path, 'w', encoding='utf-8').write(s)
    print(path, ': roberto aggiunto (glb v=%s, %d byte)' % (ver, len(glb)))


if __name__ == '__main__':
    commit = sys.argv[1]
    files = sys.argv[2:] or ['index.html', 'test/index.html']
    for f in files:
        patch(f, commit)
