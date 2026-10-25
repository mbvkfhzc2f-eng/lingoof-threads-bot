#!/usr/bin/env python3
"""LINGOOF Threads botu.

planı (posts.json) Türkiye saatiyle, her gönderinin kendi tarih ve saatinde resmi Threads API ile paylaşır:
metin, anket, görsel, App Store linki ve paylaşımın altına yanıt. Hangi paylaşımın yapıldığı state.json'da tutulur;
aynı paylaşım iki kez gitmez, saati geçmiş paylaşımlar sonradan yığılmaz.

Ortam değişkenleri:
  THREADS_TOKEN  Threads uzun ömürlü erişim token'ı (GitHub secret)
  DRY_RUN        "true" ise hiçbir şey paylaşmaz; token'ı ve sıradaki paylaşımı kontrol edip gösterir
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


def publish(token, params):
    cid = api('POST', 'me/threads', params, token)['id']
    time.sleep(3)
    wait_ready(token, cid)
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
    token = os.environ.get('THREADS_TOKEN', '').strip()
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

    if dry:
        nxt = fresh[-1] if fresh else next((p for p in pending if slot_time(p) > now), None)
        if not nxt:
            print('Plan tamamlanmış, paylaşılacak bir şey kalmadı.')
            return
        when = 'şimdi' if fresh else f'{slot_time(nxt):%d.%m.%Y %H:%M}'
        print(f'\n(Deneme) Sıradaki: #{nxt["n"]} · {when}'
              f'{" · anket" if nxt.get("poll") else ""}{" · görsel" if nxt.get("img") else ""}{" · yanıtlı" if nxt.get("reply") else ""}'
              f'{" · konu: " + topic_of(nxt) if topic_of(nxt) else ""}\n')
        print(fill(nxt['text'], cfg))
        bad = [p['n'] for p in pending if p.get('poll') and not poll_ok(p['poll'])]
        if bad:
            print(f'\n(Not) Seçenekleri {POLL_MAX} baytı aşan anketler metin olarak gidecek: {bad}')
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
    poll = post.get('poll')
    if threads_len(text) > LIMIT:
        fail(state, now, post['n'], f'metin Threads sınırını aşıyor ({threads_len(text)} > {LIMIT})')
    base = {'topic_tag': topic_of(post)} if topic_of(post) else {}
    params = {'media_type': 'TEXT', 'text': text, **base}
    if poll and poll_ok(poll):
        params['poll_attachment'] = json.dumps({k: v for k, v in zip(('option_a', 'option_b', 'option_c', 'option_d'), poll)}, ensure_ascii=False)
    elif poll:
        print(f'Anket seçenekleri {POLL_MAX} baytı aşıyor; anket metin olarak paylaşılıyor.')
        params['text'] = poll_as_text(text, poll)
    elif post.get('img') and image_base(cfg):
        params.update(media_type='IMAGE', image_url=image_base(cfg) + post['img'])
        if post.get('alt'):
            params['alt_text'] = post['alt'][:1000]
    elif '{LINK}' in post['text'] and cfg.get('app_store_url'):
        params['link_attachment'] = cfg['app_store_url']

    try:
        try:
            post_id = publish_main(token, params)
        except RuntimeError as e:
            if params.get('media_type') == 'IMAGE':
                print(f'Görsel yüklenemedi, metin olarak paylaşılıyor: {e}')
                post_id = publish_main(token, {'media_type': 'TEXT', 'text': text, **base})
            elif 'poll_attachment' in params:
                print(f'Anket oluşturulamadı, metin olarak paylaşılıyor: {e}')
                state['last_error'] = {'at': now.isoformat(timespec='seconds'), 'n': post['n'], 'error': f'anket: {e}'[:800]}
                post_id = publish_main(token, {'media_type': 'TEXT', 'text': poll_as_text(text, poll), **base})
            else:
                raise
    except RuntimeError as e:
        fail(state, now, post['n'], e)
    state['posted'][str(post['n'])] = {'id': post_id, 'at': now.isoformat(timespec='seconds')}
    state.get('failures', {}).pop(str(post['n']), None)
    save('state.json', state)                          # yanıt başarısız olsa bile ana paylaşım tekrar gitmesin
    print(f"Paylaşıldı: #{post['n']} ({post['date']} {post['time']}) → {post_id}")

    if post.get('reply'):
        time.sleep(int(cfg.get('reply_delay_seconds', 45)))
        try:
            reply_id = publish(token, {'media_type': 'TEXT', 'text': fill(post['reply'], cfg), 'reply_to_id': post_id})
        except RuntimeError as e:
            fail(state, now, None, f'#{post["n"]} paylaşıldı ama altına yanıt eklenemedi: {e}')
        state['posted'][str(post['n'])]['reply_id'] = reply_id
        save('state.json', state)
        print(f'Yanıt eklendi → {reply_id}')


if __name__ == '__main__':
    main()
