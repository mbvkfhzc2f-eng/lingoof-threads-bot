#!/usr/bin/env python3
"""Threads token'ını GH_PAT gerekmeden canlı tutar.

Uzun ömürlü Threads token'ı 60 gün geçerlidir; her yenilemede Meta yeni bir token verir ve süre yeniden 60 gün olur.
GitHub secret'ını iş akışının içinden güncellemek GH_PAT ister. GH_PAT yoksa yeni token, THREADS_TOKEN secret'ından
türetilen anahtarla AES-256 ile şifrelenir ve GitHub Actions önbelleğine (.thtok/tok.enc) yazılır. Önbellek depoda
görünmez, yalnızca bu deponun iş akışları erişir; anahtar olmadan şifresi çözülemez. Token'lar hiçbir zaman günlüğe
yazılmaz (::add-mask::).

  python3 token_store.py load      önbellekteki geçerli token'ı sonraki adımlara THREADS_TOKEN_LIVE olarak verir
  python3 token_store.py refresh   token'ı yeniler; yenisi önbelleğe (GH_PAT varsa secret'a da) yazılır
Yalnızca Python standart kütüphanesi ve openssl kullanılır.
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

STORE = Path('.thtok/tok.enc')
API = 'https://graph.threads.net'


def secret():
    k = os.environ.get('THREADS_TOKEN', '').strip()
    if not k:
        print('THREADS_TOKEN secret tanımlı değil.')
        sys.exit(0)
    return k


def mask(value):
    print(f'::add-mask::{value}', flush=True)


def openssl(args, data, key):
    env = dict(os.environ, THK=key)
    r = subprocess.run(['openssl', 'enc', '-aes-256-cbc', '-pbkdf2', '-iter', '200000', '-md', 'sha256'] + args
                       + ['-pass', 'env:THK'], input=data, capture_output=True, env=env)
    return r.returncode == 0, r.stdout


def get(path, params):
    url = f'{API}/{path}?{urllib.parse.urlencode(params)}'
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read()).get('error', {}).get('message', '')
        except Exception:
            msg = ''
        return {'_error': f'HTTP {e.code} {msg}'[:200]}
    except Exception as e:
        return {'_error': type(e).__name__}


def valid(tok):
    d = get('v1.0/me', {'fields': 'id,username', 'access_token': tok})
    return '_error' not in d and bool(d.get('id'))


def stored():
    """Önbellekteki token (çözülebilir ve biçimi doğruysa)."""
    if not STORE.exists():
        return None
    ok, raw = openssl(['-d', '-in', str(STORE)], None, secret())
    if not ok:
        return None
    tok = raw.decode('utf-8', 'ignore').strip()
    if len(tok) < 50 or not tok.isalnum():
        return None
    return tok


def output(key, value):
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f'{key}={value}\n')


def load():
    tok = stored()
    if not tok:
        print("Önbellekte yenilenmiş token yok; THREADS_TOKEN secret'ı kullanılacak.")
        return 0
    mask(tok)
    if not valid(tok):
        print("Önbellekteki token geçersiz; THREADS_TOKEN secret'ı kullanılacak.")
        return 0
    with open(os.environ['GITHUB_ENV'], 'a') as f:
        f.write(f'THREADS_TOKEN_LIVE={tok}\n')
    print('Güncel token önbellekten alındı.')
    return 0


def refresh():
    base = secret()
    cur = stored() or base
    src = 'önbellek' if cur != base else 'secret'
    mask(cur)
    d = get('refresh_access_token', {'grant_type': 'th_refresh_token', 'access_token': cur})
    new = (d.get('access_token') or '').strip()
    if not new:
        if valid(cur):
            print(f'Token şimdilik yenilenmedi ama geçerli ({src}); bir sonraki çalışmada tekrar denenecek. {d.get("_error", "")}')
            return 0
        print(f"::error::Threads token'ı geçersiz ya da süresi dolmuş ({src}). README'deki 2. adımla yeni token üretip "
              "THREADS_TOKEN secret'ını güncelle.")
        return 1
    mask(new)
    days = int(d.get('expires_in', 0)) // 86400
    if new == cur:
        print(f'Token uzatıldı: {days} gün geçerli ({src}).')
        return 0
    if not valid(new):
        print('::error::Meta yeni bir token verdi ama doğrulanamadı; mevcut token kullanılmaya devam ediyor.')
        return 1
    STORE.parent.mkdir(exist_ok=True)
    ok, _ = openssl(['-salt', '-out', str(STORE)], new.encode(), base)
    if not ok:
        print('::error::Yeni token şifrelenemedi.')
        return 1
    output('saved', 'true')
    print(f'Yeni token şifrelenip önbelleğe yazıldı: {days} gün geçerli, her yenilemede tekrar uzar.')
    pat = os.environ.get('GH_PAT', '').strip()
    if pat:
        r = subprocess.run(['gh', 'secret', 'set', 'THREADS_TOKEN', '--repo', os.environ['REPO']], input=new.encode(),
                           capture_output=True, env=dict(os.environ, GH_TOKEN=pat))
        print('THREADS_TOKEN secret da güncellendi.' if r.returncode == 0 else '(Not) GH_PAT ile secret güncellenemedi; önbellek yeterli.')
    return 0


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'load':
        sys.exit(load())
    if cmd == 'refresh':
        sys.exit(refresh())
    sys.exit('kullanım: token_store.py load|refresh')
