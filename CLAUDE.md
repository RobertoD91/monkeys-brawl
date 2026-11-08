# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Lingua e branch

- Parla con l'utente **in italiano** (anche commenti e testi del gioco sono in italiano).
- Lavora direttamente su **`main`** (niente branch di feature, salvo richiesta esplicita).

## Cos'è questo repo

**Monkey Brawl League**: picchiaduro 3D (three.js) nel browser per una lega di fantacalcio. Modalità: contro il PC, in due, online, Royal, torneo, "Compito in classe" (quiz). È una PWA (`manifest.webmanifest`, orientamento landscape) servita come sito statico (GitHub Pages, `.nojekyll`).

**Questo repo contiene solo l'output compilato, non i sorgenti.** I commit ("Monkey Brawl League: pagina del gioco" / "pagina di prova") sono deploy automatici fatti dal repo upstream di Francesco De Nittis (`Fraffo96`), di cui questo è un fork. I riferimenti a `src/*.js` (es. `src/vsui.js`) e `tools/build_*.py` nei commenti indicano file che **qui non esistono**. Non ci sono package.json, build, lint né test automatici in questo repo.

Repo collegati:
- `../monkeys-brawl-assets` (`RobertoD91/monkeys-brawl-assets`): modelli `.glb`, musica `.mp3`, `sfx_samples.js`, `three.min.js`. Anch'esso solo artefatti, nessun codice da costruire.
- Backend: Cloudflare Worker `monkeys-brawl.francesco-denittis.workers.dev` (prod) / `monkeys-brawl-test.…` (test). Non è in nessuno dei due repo.

## Struttura dei file

- `index.html` (~900 KB, ~650 righe con righe lunghissime): tutto il gioco. CSS inline, markup delle schermate (`<section class="screen" id="…">`), sprite SVG e poi una sequenza di `<script>` minificati e concatenati (IIFE). **Non leggerlo con `Read` per intero né fare `cat`/`grep` senza limitare l'output**: usa `grep -o '.\{80\}PATTERN.\{120\}'` o `awk` su singole righe.
- `pg_art.js` (`window.MB_PG_ART`, ritratti dei lottatori) e `ui_art.js` (`window.MB_UI_ART`, immagini fumetti/K.O.): data URI webp generati da script upstream ("non modificare a mano"), caricati in ritardo.
- `exam.js`: `window.MB_EXAM_Q`, domande della modalità "Compito in classe", caricato su richiesta.
- `test/`: copia completa del sito = **pagina di prova (staging)**. Differisce dalla root solo per: host del Worker `monkeys-brawl-test`, badge "TEST" al posto del beacon Cloudflare Insights. Una modifica fatta in `index.html` va replicata in `test/index.html` (e viceversa) mantenendo queste differenze; gli altri file sono identici.

## Architettura runtime (in `index.html`)

Comunicazione tra moduli tramite globali su `window`:
- **Config di deploy** (righe ~217–221): `MB_WS_HOST` (Worker per online/lobby), `MB_ASSET_CDN` (jsDelivr su `Fraffo96/monkeys-brawl-assets@<commit>` fissato), `MB_ASSET_BASE` (fallback `…workers.dev/assets/`), `MB_ASSET_VER` (hash per cache-busting `?v=`), `MB_ASSET_META` (per personaggio: misure, altezza `h`, `grip`, `sizes`), `MB_MUSIC` (src CDN + `alt` Worker), liste di file lazy (`MB_EXAM_FILES`, ecc. come coppie [locale, Worker]).
- **Caricamento asset**: ogni asset prova prima il CDN jsDelivr e in caso di errore ripiega sul Worker (anche `three.min.js` via `onerror`). I personaggi sono caricati da `MB_GLB` come `chars/<id>.glb` + variante opzionale `chars/<id>_fix.glb`; le animazioni condivise stanno in `anim/library` (= `library.glb`, clip indicizzate per nome). Aggiornare un asset a mano significa: commit nel repo asset, poi aggiornare il commit fissato in `MB_ASSET_CDN` (anche in `three.min.js`, `MB_MUSIC`, `sfx_samples`) e l'hash in `MB_ASSET_VER`, in entrambe le pagine (di norma lo fa il deploy upstream).
- **Contenuti dichiarativi**: `MB_LOOKS.<id>` (proporzioni/colori del fighter), `HCG_ROSTER` (elenco lottatori, id/nome/accento), `HCG_STAGES.push({id,name,sub,build})` (arene; quelle "dipinte" usano `MB_PAINTED` con panorama e pavimento jpg e un `seed` deterministico).
- **Online**: WebSocket `wss://<MB_WS_HOST>/lobby` e `/ws/<stanza>`; nome e uid in `localStorage` (`mb_name`, `mb_uid`).
- **Hook per test automatici**: con `navigator.webdriver` (Playwright) il gioco cambia comportamento: online/lobby disattivato salvo `?lobby`, caricamento in background disattivato salvo `?bg=1`, presentazioni/replay saltati salvo `window.__pres`/`window.__replay`. Altri flag di debug: `window.__perf`, `__ai`, `__auto`, `__hcg`, `__bgLog`, `__netlog`, `__noCombo`, `MB_NOPRES`.

## Provare il gioco in locale

Serve un server HTTP (gli script online e alcuni loader si disattivano con `file://`):

```bash
python3 -m http.server 8000
```

Poi `http://localhost:8000/` (prod) o `http://localhost:8000/test/` (prova). Gli asset arrivano comunque da CDN/Worker remoti, quindi serve rete. Per verifiche automatiche usa Playwright headless (preinstallato) controllando gli errori in console; ricorda che sotto webdriver alcune parti sono disattivate (vedi sopra).

## Modifiche proprie di questo fork

- **Lottatori del fork** (`roberto`, `andrea`) definiti in `FIGHTERS` dentro `tools/add_fighter.py`; si applicano con `python3 tools/add_fighter.py <commit_repo_asset> <id> [<id> ...]`. Lo script copia le voci di un lottatore "modello" in tutte le tabelle per personaggio del bundle (roster, `MB_LOOKS`, statistiche `nt`, combo `Et`, speciali `Tt`, frasi `ao`, provocazioni `Vl`, descrizioni `ls`/`xu`, `Ea`/`hs`/`Na`/`Lc`/`Dc`, `MB_ASSET_META` con `hh`/`ho`/`h` letti dal `.glb`, `MB_ASSET_VER`), con eventuali sostituzioni di testo, e punta `MB_ASSET_CDN` a `RobertoD91/monkeys-brawl-assets@<commit>`. È idempotente e fallisce se un'ancora non si trova più. Dopo un aggiornamento da upstream (che sovrascrive `index.html`/`test/index.html`) va rilanciato con tutti gli id; se fallisce, riallinea le ancore in `TABLES`. Il `.glb` deve già essere nel repo asset al commit indicato.
- Speciali/super dei lottatori del fork riusano i set "storici" in `mn` che nessun lottatore attuale usa (`mn.francesco` per roberto, `mn.giacomo` per andrea).
- Ritratti/teste HUD dei lottatori del fork in `pg_art.js` (`MB_PG_ART`, `MB_PG_META`, `MB_HUD_HEAD`), generati da `characters/tools/build_art.py` nel repo asset; il `?v=` di `pg_art.js` nelle due pagine è aggiornato all'hash del file.
- Un nuovo lottatore deve comparire in **tutte** quelle tabelle: se manca da `Et` il gioco scrive "mancano combo", se manca da `MB_LOOKS`/`ye` `buildFighterModel` lo tratta come sconosciuto. Non riusare super che trasformano il modello (`fn(e,t,"fat"…)` ecc.): caricano il `.glb` di un altro personaggio.
- La pipeline dei personaggi è in `../monkeys-brawl-assets/characters/tools/` (`build_glb.sh <id>`: articolazioni automatiche, rig, ottimizzazione); i sorgenti di ogni personaggio in `characters/<id>/`. Le foto di partenza (`ref/`) e i file intermedi che le contengono vanno nel repo **privato** `RobertoD91/brawl` (`characters/<id>/ref/`), mai nei due repo pubblici.
- Le Space Hugging Face usate (FLUX.1 Kontext dev, Hunyuan3D 2.1) girano su ZeroGPU: la quota gratuita giornaliera basta per circa un personaggio (Hunyuan con texture chiede 270 s).

## Pipeline personaggi 3D (dal brief upstream)

Per creare/modificare personaggi si segue il brief di Fraffo96 (https://gist.github.com/Fraffo96/88142dc00eb05afd5be5141da5ca62b5). Punti chiave:
- Un `.glb` per personaggio con mesh+texture, scheletro con nomi ossa **Mixamo** (`mixamorig:Hips`, …), stessa rest pose, scala e orientamento di tutti gli altri; animazioni in un'unica libreria condivisa (`library.glb`), tagli annotati in `cuts.json`.
- Flusso: sheet 2D (fronte/lato/retro in A-pose, sfondo bianco) → **checkpoint: approvazione utente** → mesh con Hunyuan3D 2.1 (Hugging Face, `gradio_client`) → Blender headless (pulizia, armatura Mixamo, pesi) → render di 8 pose di prova → **checkpoint: revisione utente** → animazioni Mixamo (FBX Binary, Without Skin, 30 fps, nessuna keyframe reduction) → integrazione three.js (`GLTFLoader`, `AnimationMixer`, `crossFadeTo` 0.1–0.2 s, `AnimationUtils.subclip`) → arte 2D (ritratto, icona, emblema barra vita, wallpaper).
- Le animazioni sono solo estetiche: non devono toccare il bilanciamento. A parità di seed, i match simulati headless devono dare risultati identici dopo una modifica solo visiva.
- Regole: non modificare personaggi già approvati; nessun servizio a pagamento senza approvazione esplicita; token/chiavi solo in `.env`; ogni step salva il suo output in una cartella dedicata (`characters/<id>/{ref,sheet,mesh,rig,out,art}`); a fine personaggio, breve riepilogo di cosa è stato fatto, dove sono i file e cosa resta da rivedere.
