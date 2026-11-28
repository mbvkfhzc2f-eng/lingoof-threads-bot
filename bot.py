#!/usr/bin/env python3
"""LINGOOF Threads botu.

planı (posts.json) Türkiye saatiyle, her gönderinin kendi tarih ve saatinde resmi Threads API ile paylaşır:
metin, anket, görsel, video (Goof 2.0 videoları), carousel, spoiler'lı cevap ve paylaşımın altına ilk yorum.
App Store linki ana gönderiye değil ilk yoruma (önizleme kartıyla) konur. Hangi paylaşımın yapıldığı state.json'da
tutulur; aynı paylaşım iki kez gitmez, saati geçmiş paylaşımlar sonradan yığılmaz.

Ortam değişkenleri:
  THREADS_TOKEN       Threads uzun ömürlü erişim token'ı (GitHub secret)
  THREADS_TOKEN_LIVE  token_store.py'nin önbellekten açtığı yenilenmiş token (varsa önce bu kullanılır)
  DRY_RUN             "true" ise hiçbir şey paylaşmaz; token'ı, sıradaki paylaşımı ve planı denetleyip gösterir
  python3 bot.py --check   yalnızca planı denetler (token gerekmez)
Yalnızca Python standart kütüphanesi kullanılır.
"""
import json
import os
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
TZ = ZoneInfo('Europe/Istanbul')
API = 'https://graph.threads.net/v1.0'
LIMIT = 500                      # Threads metin sınırı; emojiler UTF-8 bayt uzunluğu kadar sayılır
POLL_MAX = 25                    # anket seçeneği: 1–25 karakter; Türkçe harfler bayt sayılabileceği için baytla ölçülür
MAX_TRIES = 3                    # aynı gönderi bu kadar kez hata verirse atlanır (her 15 dakikada boşuna denenmesin)


def load(name, default=None):
    path = ROOT / name
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def save(name, obj):
    (ROOT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def threads_len(text):
    n = 0
    for ch in text:
        if ord(ch) > 0xFFFF or (ord(ch) >= 0x2000 and unicodedata.category(ch) in ('So', 'Sk', 'Mn', 'Cf')):
            n += len(ch.encode('utf-8'))
        else:
            n += 1
    return n


def api(method, path, params, token):
    query = dict(params, access_token=token)
    body = urllib.parse.urlencode(query).encode()
    url = f'{API}/{path}'
    if method == 'GET':
        req = urllib.request.Request(f'{url}?{body.decode()}')
    else:
        req = urllib.request.Request(url, data=body, method='POST')
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors='replace')
            if e.code >= 500 and attempt < 2:          # Meta tarafında geçici hata: biraz bekleyip tekrar dene
                last = f'{e.code} {detail}'
                time.sleep(10 * (attempt + 1))
                continue
            raise RuntimeError(f'Threads API {e.code} ({path}): {detail}') from None
        except urllib.error.URLError as e:
            last = str(e)
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f'Threads API bağlantı hatası ({path}): {last}')


def wait_ready(token, container_id, timeout=120):
    """Konteyner hazır olana kadar bekler (görsellerde Meta dosyayı indirip işler)."""
    waited = 0
    while waited <= timeout:
        st = api('GET', container_id, {'fields': 'status,error_message'}, token)
        status = st.get('status')
        if status == 'FINISHED':
            return
        if status in ('ERROR', 'EXPIRED'):
            raise RuntimeError(f'Konteyner {status}: {st.get("error_message")}')
        time.sleep(5)
        waited += 5
    raise RuntimeError('Konteyner zamanında hazır olmadı')


def container(token, params, timeout=120):
    cid = api('POST', 'me/threads', params, token)['id']
    time.sleep(3)
    wait_ready(token, cid, timeout)
    return cid


def publish(token, params):
    timeout = 300 if params.get('media_type') in ('VIDEO', 'CAROUSEL') else 120
    cid = container(token, params, timeout)
    return api('POST', 'me/threads_publish', {'creation_id': cid}, token)['id']


EXTRAS = ('topic_tag', 'alt_text')               # erişimi artıran ama paylaşımı asla engellememesi gereken alanlar


def publish_main(token, params):
    """Ana gönderiyi paylaşır; konu etiketi ya da görsel açıklaması reddedilirse onlarsız bir kez daha dener."""
    try:
        return publish(token, params)
    except RuntimeError as e:
        extra = [k for k in EXTRAS if k in params]
        if not extra:
            raise
        print(f'{" / ".join(extra)} ile paylaşılamadı, onlarsız deneniyor: {e}')
        return publish(token, {k: v for k, v in params.items() if k not in extra})


def topic_of(post):
    """Threads konu etiketi: 1–50 karakter, nokta ve & içermez. Geçersizse etiket gönderilmez."""
    t = (post.get('topic') or '').strip()
    return t if t and len(t) <= 50 and '.' not in t and '&' not in t else None


def slot_time(post):
    d = date.fromisoformat(post['date'])
    hh, mm = (int(x) for x in post['time'].split(':'))
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=TZ)


def image_base(cfg):
    base = cfg.get('image_base_url') or 'auto'
    if base != 'auto':
        return base.rstrip('/') + '/'
    repo, ref = os.environ.get('GITHUB_REPOSITORY'), os.environ.get('GITHUB_REF_NAME', 'main')
    return f'https://raw.githubusercontent.com/{repo}/{ref}/img/' if repo else None


def fill(text, cfg):
    url = (cfg.get('app_store_url') or '').strip()
    return text.replace('{LINK}', url if url else 'App Store’da “LINGOOF” diye arat')


def poll_ok(opts):
    return 2 <= len(opts) <= 4 and all(o.strip() and len(o.encode('utf-8')) <= POLL_MAX for o in opts)


def poll_as_text(text, opts):
    """Anket oluşturulamazsa seçenekleri metne yazar; cevaplar yorumlarda toplanır."""
    lines = '\n'.join(f'{k}) {o}' for k, o in zip('ABCD', opts))
    full = f'{text}\n\n{lines}\n\nCevabını harfiyle yorumlara yaz 👇'
    return full if threads_len(full) <= LIMIT else f'{text}\n\n{lines}'



# ---------- medya, spoiler ve plan denetimi ----------

LEGACY_IMG = ('card_', '01_', '02_', '03_', '04_', '05_', '06_', '07_', '08_', '09_', '10_', '11_', '12_', '13_')


def resolve(ref, cfg):
    """Medya adresi: tam URL olduğu gibi; 'medya:v3/...' bu deponun medya dalı (Goof 2.0 videoları, carousel'lar);
    'ig:v2/...' Instagram botunun GitHub Pages medyası; diğerleri bu deponun img/ klasörü."""
    ref = (ref or '').strip()
    if ref.startswith(('http://', 'https://')):
        return ref
    if ref.startswith('medya:'):
        path = ref[6:].lstrip('/')
        repo = os.environ.get('GITHUB_REPOSITORY') or 'mbvkfhzc2f-eng/lingoof-threads-bot'
        base = cfg.get('media_base_url') or f'https://raw.githubusercontent.com/{repo}/medya/'
        if path.lower().endswith(('.mp4', '.mov')) and cfg.get('video_base_url'):
            base = cfg['video_base_url']
        return base.rstrip('/') + '/' + path
    if ref.startswith('ig:'):
        base = (cfg.get('ig_media_base_url') or '').rstrip('/')
        return f'{base}/{ref[3:].lstrip("/")}' if base else None
    base = image_base(cfg)
    return base + ref if base else None


def medya_manifest():
    m = load('plan/medya.json', None)
    return set(m) if m else None


def utf16_len(text):
    return len(text.encode('utf-16-le')) // 2


def spoiler_entities(text, parts):
    """Spoiler'lı bölümlerin konumları. Konum, öncesinde emoji yoksa karakter ve UTF-16 sayımında aynıdır;
    Meta'nın hangi birimi kullandığı belgelenmediği için plan denetimi spoiler'dan önce emoji olmasını engeller."""
    ents = []
    for part in parts or []:
        i = text.find(part)
        if i < 0 or not part.strip():
            raise ValueError(f'spoiler metinde yok: {part[:40]}')
        ents.append({'entity_type': 'SPOILER', 'offset': utf16_len(text[:i]), 'length': utf16_len(part)})
    return ents[:10]


def without_spoilers(text, parts):
    """Spoiler kabul edilmezse cevaplar ana metinden çıkarılır ve ilk yoruma taşınır."""
    for part in parts or []:
        text = text.replace(part, '(cevap ilk yorumda 👇)', 1)
    return text


def media_kind(post):
    if post.get('video'):
        return 'video'
    if post.get('carousel'):
        return 'carousel'
    if post.get('img'):
        return 'görsel'
    if post.get('poll'):
        return 'anket'
    if '{LINK}' in post.get('text', ''):
        return 'link'
    return 'metin'


def check_plan(posts, cfg, done=frozenset(), today=None):
    """Paylaşılmamış gönderileri denetler; sorun listesini döndürür."""
    problems = []
    seen = set()
    manifest = medya_manifest()
    for post in posts:
        n = post.get('n')
        if n in seen:
            problems.append(f'#{n}: aynı numara iki kez var')
        seen.add(n)
        if str(n) in done or (today and post['date'] < today):
            continue
        where = f'#{n} ({post["date"]} {post["time"]})'
        text = fill(post.get('text', ''), cfg)
        if threads_len(text) > LIMIT:
            problems.append(f'{where}: metin {threads_len(text)} > {LIMIT}')
        if post.get('reply') and threads_len(fill(post['reply'], cfg)) > LIMIT:
            problems.append(f'{where}: ilk yorum {threads_len(fill(post["reply"], cfg))} > {LIMIT}')
        for part in post.get('spoiler') or []:
            i = text.find(part)
            if i < 0:
                problems.append(f'{where}: spoiler metinde yok: {part[:30]}')
            elif utf16_len(text[:i]) != i:
                problems.append(f'{where}: spoiler\'dan önce emoji var (konum belirsizleşir)')
        if post.get('poll') and not poll_ok(post['poll']):
            problems.append(f'{where}: anket seçenekleri geçersiz')
        if post.get('carousel') and not 2 <= len(post['carousel']) <= 20:
            problems.append(f'{where}: carousel 2–20 öğe olmalı')
        for ref in [post.get('img'), post.get('video'), *(post.get('carousel') or [])]:
            if not ref:
                continue
            if ref.split('/')[-1].startswith(LEGACY_IMG):
                problems.append(f'{where}: eski görünümlü/eski görsel kullanılıyor: {ref}')
            if not ref.startswith(('http', 'ig:', 'medya:')) and not (ROOT / 'img' / ref).exists():
                problems.append(f'{where}: görsel dosyası yok: img/{ref}')
            if ref.startswith('medya:') and manifest is not None and ref[6:] not in manifest:
                problems.append(f'{where}: medya dalında yok: {ref}')
            if ref.startswith('ig:') and not cfg.get('ig_media_base_url'):
                problems.append(f'{where}: ig_media_base_url ayarı yok')
        if '{LINK}' in post.get('text', '') and not post.get('link_main'):
            problems.append(f'{where}: link ana metinde (ilk yoruma taşınmalı)')
        if topic_of(post) is None and post.get('topic'):
            problems.append(f'{where}: konu etiketi geçersiz')
    return problems


def head_ok(url):
    """Medya adresine ulaşılabiliyor mu (deneme çalıştırmasında)."""
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200, r.headers.get('Content-Type', '')
    except Exception as e:
        return False, str(e)[:80]


def build_params(post, cfg, text, base):
    """Ana gönderinin konteyner parametreleri (en zengin biçim). Geri dönüşler publish_post'ta."""
    poll = post.get('poll')
    params = {'media_type': 'TEXT', 'text': text, **base}
    if post.get('video') and resolve(post['video'], cfg):
        params.update(media_type='VIDEO', video_url=resolve(post['video'], cfg))
        if post.get('alt'):
            params['alt_text'] = post['alt'][:1000]
    elif post.get('carousel'):
        params.update(media_type='CAROUSEL')
    elif post.get('img') and resolve(post['img'], cfg):
        params.update(media_type='IMAGE', image_url=resolve(post['img'], cfg))
        if post.get('alt'):
            params['alt_text'] = post['alt'][:1000]
    elif poll and poll_ok(poll):
        params['poll_attachment'] = json.dumps({k: v for k, v in zip(('option_a', 'option_b', 'option_c', 'option_d'), poll)}, ensure_ascii=False)
    elif poll:
        print(f'Anket seçenekleri {POLL_MAX} baytı aşıyor; anket metin olarak paylaşılıyor.')
        params['text'] = poll_as_text(text, poll)
    elif '{LINK}' in post['text'] and cfg.get('app_store_url'):
        params['link_attachment'] = cfg['app_store_url']
    return params


def carousel_children(token, post, cfg):
    alts = post.get('alts') or []
    kids = []
    for i, ref in enumerate(post['carousel'][:20]):
        url = resolve(ref, cfg)
        kind = 'VIDEO' if url.lower().endswith(('.mp4', '.mov')) else 'IMAGE'
        item = {'media_type': kind, 'is_carousel_item': 'true', ('video_url' if kind == 'VIDEO' else 'image_url'): url}
        if i < len(alts) and alts[i]:
            item['alt_text'] = alts[i][:1000]
        try:
            kids.append(container(token, item, 300 if kind == 'VIDEO' else 120))
        except RuntimeError as e:
            if 'alt_text' not in item:
                raise
            print(f'Carousel {i + 1}. öğe açıklamasız deneniyor: {e}')
            item.pop('alt_text')
            kids.append(container(token, item, 300 if kind == 'VIDEO' else 120))
    return kids


def publish_post(token, post, cfg, text, base):
    """Ana gönderiyi en zengin biçimde paylaşır; olmazsa sırayla daha sade biçimlere düşer.
    Dönüş: (post_id, ilk yoruma eklenecek not ya da None)."""
    parts = post.get('spoiler') or []
    note = None
    params = build_params(post, cfg, text, base)
    if parts:
        try:
            params['text_entities'] = json.dumps(spoiler_entities(params['text'], parts), ensure_ascii=False)
        except ValueError as e:
            print(f'Spoiler atlandı: {e}')

    def attempt(prm):
        if prm.get('media_type') == 'CAROUSEL' and 'children' not in prm:
            prm = dict(prm, children=','.join(carousel_children(token, post, cfg)))
        return publish_main(token, prm)

    def without_entities(prm):
        nonlocal note
        if 'text_entities' not in prm:
            return prm
        note = 'Cevap: ' + ' / '.join(x.strip() for x in parts)
        out = {k: v for k, v in prm.items() if k != 'text_entities'}
        out['text'] = without_spoilers(prm['text'], parts)
        return out

    try:
        return attempt(params), note
    except RuntimeError as e:
        first = e
    print(f'İlk deneme olmadı ({params["media_type"]}): {first}')
    if 'text_entities' in params:                       # spoiler'ı kaldırıp aynı biçimde bir kez daha
        try:
            return attempt(without_entities(params)), note
        except RuntimeError as e:
            print(f'Spoiler\'sız da olmadı: {e}')
        params = without_entities(params)
    text_only = {'media_type': 'TEXT', 'text': params['text'], **base}
    if params['media_type'] == 'CAROUSEL' and post['carousel']:
        url = resolve(post['carousel'][0], cfg)
        if not url.lower().endswith(('.mp4', '.mov')):
            try:
                print('Carousel olmadı, ilk görselle tek görsel deneniyor.')
                return publish_main(token, dict(text_only, media_type='IMAGE', image_url=url)), note
            except RuntimeError as e:
                print(f'Tek görsel de olmadı: {e}')
    if params['media_type'] == 'VIDEO' and post.get('fallback_img'):
        try:
            print('Video olmadı, yedek görselle deneniyor.')
            return publish_main(token, dict(text_only, media_type='IMAGE', image_url=resolve(post['fallback_img'], cfg))), note
        except RuntimeError as e:
            print(f'Yedek görsel de olmadı: {e}')
    if 'poll_attachment' in params:
        text_only['text'] = poll_as_text(params['text'], post['poll'])
    if params['media_type'] == 'TEXT' and 'poll_attachment' not in params and 'link_attachment' not in params:
        raise first                                     # zaten düz metindi: gerçek bir hata
    print('Metin olarak paylaşılıyor.')
    return publish_main(token, text_only), note



def validate_containers(token, posts, pending, cfg, now):
    """Paylaşmadan doğrular: sıradaki medyalı gönderilerin konteynerlerini oluşturur, Meta'nın işleyip işlemediğine bakar.
    Konteynerler yayımlanmaz, 24 saatte kendiliğinden silinir. VALIDATE_N="400,401" ya da VALIDATE_COUNT=3."""
    only = {x.strip() for x in os.environ.get('VALIDATE_N', '').split(',') if x.strip()}
    count = int(os.environ.get('VALIDATE_COUNT', '3') or 3)
    if only:
        todo = [p for p in posts if str(p['n']) in only]
    else:
        todo = [p for p in pending if slot_time(p) > now and media_kind(p) in ('video', 'carousel', 'görsel')][:count]
    ok_all = True
    for post in todo:
        text = fill(post['text'], cfg)
        base = {'topic_tag': topic_of(post)} if topic_of(post) else {}
        params = build_params(post, cfg, text, base)
        if post.get('spoiler'):
            params['text_entities'] = json.dumps(spoiler_entities(params['text'], post['spoiler']), ensure_ascii=False)
        try:
            if params['media_type'] == 'CAROUSEL':
                params['children'] = ','.join(carousel_children(token, post, cfg))
            cid = container(token, params, 300 if params['media_type'] in ('VIDEO', 'CAROUSEL') else 120)
            print(f'✓ #{post["n"]} {media_kind(post)}{" + spoiler" if post.get("spoiler") else ""}: konteyner hazır ({cid}), yayımlanmadı.')
        except RuntimeError as e:
            ok_all = False
            print(f'✗ #{post["n"]} {media_kind(post)}: {e}')
    if not todo:
        print('Doğrulanacak medyalı gönderi yok.')
    if not ok_all:
        sys.exit(1)

def report_error(msg):
    """Hatayı GitHub Actions'ta görünür kılar: çalıştırma sayfasında kırmızı uyarı + adım özeti."""
    one = msg.replace('%', '%25').replace('\r', '').replace('\n', '%0A')
    print(f'::error title=Threads paylaşımı başarısız::{one}')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write(f'### Paylaşım başarısız\n\n```\n{msg}\n```\n')


def fail(state, now, n, err):
    """Hatayı state.json'a yazar (depoda görünsün), gerekirse gönderiyi atlar ve çalıştırmayı hata ile bitirir."""
    state['last_error'] = {'at': now.isoformat(timespec='seconds'), 'n': n, 'error': str(err)[:800]}
    if n is not None:
        tries = state.setdefault('failures', {})
        tries[str(n)] = tries.get(str(n), 0) + 1
        if tries[str(n)] >= MAX_TRIES and n not in state['skipped']:
            state['skipped'].append(n)
            print(f'#{n} {MAX_TRIES} kez hata verdi, atlanıyor.')
    save('state.json', state)
    report_error(f'#{n}: {err}' if n is not None else str(err))
    sys.exit(1)


def main():
    cfg = load('config.json', {})
    state = load('state.json', {'posted': {}, 'skipped': []})
    posts = load('posts.json')
    dry = os.environ.get('DRY_RUN', '').strip().lower() in ('1', 'true', 'yes')
    token = (os.environ.get('THREADS_TOKEN_LIVE') or os.environ.get('THREADS_TOKEN', '')).strip()
    now = datetime.now(TZ)

    if not token:
        sys.exit('THREADS_TOKEN tanımlı değil: GitHub > Settings > Secrets and variables > Actions altına ekle.')
    try:
        me = api('GET', 'me', {'fields': 'id,username'}, token)
    except RuntimeError as e:
        fail(state, now, None, f'Threads hesabına bağlanılamadı (token geçersiz ya da süresi dolmuş olabilir): {e}')
    print(f'Hesap: @{me.get("username")}  ·  Türkiye saati: {now:%d.%m.%Y %H:%M}')

    grace = timedelta(hours=float(cfg.get('grace_hours', 3)))
    done = set(state['posted']) | {str(n) for n in state['skipped']}
    pending = [p for p in posts if str(p['n']) not in done]
    due = [p for p in pending if slot_time(p) <= now]
    fresh = [p for p in due if now - slot_time(p) <= grace]
    stale = [p for p in due if p not in fresh]

    # Hesabın ilk gönderisi her zaman tanışma gönderisidir; bot planın başlangıcından sonra kurulsa bile önce o gider.
    # O saatin kendi gönderisi atlanmaz, 40 dakika sonraki yedek çalışmada paylaşılır.
    intro = posts[0]
    if not state['posted'] and intro in stale:
        stale.remove(intro)
        fresh = [intro]

    if os.environ.get('VALIDATE', '').strip().lower() in ('1', 'true', 'yes'):
        validate_containers(token, posts, pending, cfg, now)
        return

    if dry:
        nxt = fresh[-1] if fresh else next((p for p in pending if slot_time(p) > now), None)
        if not nxt:
            print('Plan tamamlanmış, paylaşılacak bir şey kalmadı.')
            return
        when = 'şimdi' if fresh else f'{slot_time(nxt):%d.%m.%Y %H:%M}'
        print(f'\n(Deneme) Sıradaki: #{nxt["n"]} · {when} · {media_kind(nxt)}'
              f'{" · spoiler" if nxt.get("spoiler") else ""}{" · ilk yorumlu" if nxt.get("reply") else ""}'
              f'{" · konu: " + topic_of(nxt) if topic_of(nxt) else ""}\n')
        print(fill(nxt['text'], cfg))
        if nxt.get('reply'):
            print('\n↳ ' + fill(nxt['reply'], cfg))
        problems = check_plan(posts, cfg, done, now.date().isoformat())
        print('\nPlan denetimi: ' + ('sorun yok.' if not problems else f'{len(problems)} sorun'))
        for x in problems[:40]:
            print('  - ' + x)
        soon = [q for q in pending if now <= slot_time(q) <= now + timedelta(days=int(os.environ.get('CHECK_DAYS', '3')))]
        refs = sorted({resolve(r, cfg) for q in soon for r in [q.get('img'), q.get('video'), q.get('fallback_img'), *(q.get('carousel') or [])] if r})
        for url in refs:
            ok, info = head_ok(url)
            print(f'  {"✓" if ok else "✗"} {url}  {info}')
        if stale:
            print(f'\n(Not) Tarihi geçmiş {len(stale)} gönderi ilk gerçek çalışmada atlanacak.')
        return

    for p in stale:                                    # saati çoktan geçmiş gönderiler: akışı doldurmamak için atla
        state['skipped'].append(p['n'])
        print(f'Atlandı: #{p["n"]} ({slot_time(p):%d.%m %H:%M} saati geçmiş)')
    if not fresh:
        save('state.json', state)
        nxt = next((p for p in pending if slot_time(p) > now and p not in stale), None)
        print('Şu an paylaşılacak bir şey yok.' + (f' Sıradaki: #{nxt["n"]} · {slot_time(nxt):%d.%m.%Y %H:%M}' if nxt else ' Plan tamamlandı.'))
        return
    for p in fresh[:-1]:                               # aynı anda birden çok gönderi düşerse yalnızca en yenisi gider
        state['skipped'].append(p['n'])
    post = fresh[-1]

    text = fill(post['text'], cfg)
    if threads_len(text) > LIMIT:
        fail(state, now, post['n'], f'metin Threads sınırını aşıyor ({threads_len(text)} > {LIMIT})')
    base = {'topic_tag': topic_of(post)} if topic_of(post) else {}
    try:
        post_id, note = publish_post(token, post, cfg, text, base)
    except RuntimeError as e:
        fail(state, now, post['n'], e)
    state['posted'][str(post['n'])] = {'id': post_id, 'at': now.isoformat(timespec='seconds'), 'kind': media_kind(post)}
    state.get('failures', {}).pop(str(post['n']), None)
    save('state.json', state)                          # yanıt başarısız olsa bile ana paylaşım tekrar gitmesin
    print(f"Paylaşıldı: #{post['n']} ({post['date']} {post['time']}, {media_kind(post)}) → {post_id}")

    reply = fill(post['reply'], cfg) if post.get('reply') else ''
    if note:                                           # spoiler kabul edilmediyse cevap ilk yoruma
        reply = f'{note}\n\n{reply}'.strip() if threads_len(f'{note}\n\n{reply}') <= LIMIT else note
    if reply:
        time.sleep(int(cfg.get('reply_delay_seconds', 45)))
        rp = {'media_type': 'TEXT', 'text': reply, 'reply_to_id': post_id}
        if '{LINK}' in (post.get('reply') or '') and cfg.get('app_store_url'):
            rp['link_attachment'] = cfg['app_store_url']   # link yalnızca ilk yorumda, önizleme kartıyla
        try:
            try:
                reply_id = publish(token, rp)
            except RuntimeError as e:
                if 'link_attachment' not in rp:
                    raise
                print(f'Link kartı eklenemedi, düz metin deneniyor: {e}')
                reply_id = publish(token, {k: v for k, v in rp.items() if k != 'link_attachment'})
        except RuntimeError as e:
            fail(state, now, None, f'#{post["n"]} paylaşıldı ama altına yanıt eklenemedi: {e}')
        state['posted'][str(post['n'])]['reply_id'] = reply_id
        save('state.json', state)
        print(f'İlk yorum eklendi → {reply_id}')

if __name__ == '__main__':
    if '--check' in sys.argv:
        _cfg = load('config.json', {})
        _state = load('state.json', {'posted': {}, 'skipped': []})
        _done = set(_state['posted']) | {str(n) for n in _state['skipped']}
        _probs = check_plan(load('posts.json'), _cfg, _done, datetime.now(TZ).date().isoformat())
        print('Plan denetimi: ' + ('sorun yok.' if not _probs else f'{len(_probs)} sorun'))
        for _x in _probs:
            print('  - ' + _x)
        sys.exit(1 if _probs else 0)
    main()
