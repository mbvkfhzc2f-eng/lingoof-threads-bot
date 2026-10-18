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


def main():
    cfg = load('config.json', {})
    state = load('state.json', {'posted': {}, 'skipped': []})
    posts = load('posts.json')
    dry = os.environ.get('DRY_RUN', '').strip().lower() in ('1', 'true', 'yes')
    token = os.environ.get('THREADS_TOKEN', '').strip()
    now = datetime.now(TZ)

    if not token:
        sys.exit('THREADS_TOKEN tanımlı değil: GitHub > Settings > Secrets and variables > Actions altına ekle.')
    me = api('GET', 'me', {'fields': 'id,username'}, token)
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
              f'{" · anket" if nxt.get("poll") else ""}{" · görsel" if nxt.get("img") else ""}{" · yanıtlı" if nxt.get("reply") else ""}\n')
        print(fill(nxt['text'], cfg))
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
        raise RuntimeError(f'#{post["n"]} Threads sınırını aşıyor ({threads_len(text)} > {LIMIT})')
    params = {'media_type': 'TEXT', 'text': text}
    if post.get('poll'):
        params['poll_attachment'] = json.dumps({k: v for k, v in zip(('option_a', 'option_b', 'option_c', 'option_d'), post['poll'])}, ensure_ascii=False)
    elif post.get('img') and image_base(cfg):
        params.update(media_type='IMAGE', image_url=image_base(cfg) + post['img'])
    elif '{LINK}' in post['text'] and cfg.get('app_store_url'):
        params['link_attachment'] = cfg['app_store_url']

    try:
        post_id = publish(token, params)
    except RuntimeError as e:
        if params.get('media_type') != 'IMAGE':
            raise
        print(f'Görsel yüklenemedi, metin olarak paylaşılıyor: {e}')
        post_id = publish(token, {'media_type': 'TEXT', 'text': text})
    state['posted'][str(post['n'])] = {'id': post_id, 'at': now.isoformat(timespec='seconds')}
    save('state.json', state)                          # yanıt başarısız olsa bile ana paylaşım tekrar gitmesin
    print(f"Paylaşıldı: #{post['n']} ({post['date']} {post['time']}) → {post_id}")

    if post.get('reply'):
        time.sleep(int(cfg.get('reply_delay_seconds', 45)))
        reply_id = publish(token, {'media_type': 'TEXT', 'text': fill(post['reply'], cfg), 'reply_to_id': post_id})
        state['posted'][str(post['n'])]['reply_id'] = reply_id
        save('state.json', state)
        print(f'Yanıt eklendi → {reply_id}')


if __name__ == '__main__':
    main()
