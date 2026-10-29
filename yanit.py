#!/usr/bin/env python3
"""LINGOOF Threads yanıt sistemi: dil öğrenme sohbetlerine LINGOOF hesabından katılır.

Akış (README › Sohbetlere katılma):
  1. Claude'un zamanlanmış görevi yanitlar/.ara dosyasını push eder. "Threads yanıt araması" iş akışı `bul` komutunu
     çalıştırır: anahtar kelimelerle son gönderileri arar, eler, kalan adayları Claude'un açık anahtarıyla şifreleyip
     yanitlar/adaylar.enc.json'a, aramanın özetini yanitlar/durum.json'a yazar. Başkalarının gönderi metinleri herkese
     açık depoda düz metin olarak durmaz.
  2. Claude `adaylar` ile listeyi çözer, yanitlar/YAZIM_REHBERI.md'ye göre yanıtları yazar, `ekle` ile denetleyip
     yanitlar/kararlar.json'a kaydeder ve push eder. "Threads yanıt gönderimi" iş akışı `gonder` komutunu çalıştırır:
     yanıtları günlük sınır içinde, birkaç dakika arayla paylaşır ve sonucu yanitlar/gonderilen.json'a yazar.

Komutlar:
  python3 yanit.py bul
  python3 yanit.py gonder
  python3 yanit.py adaylar --anahtar OZEL_ANAHTAR.pem
  python3 yanit.py ekle KARARLAR.json --anahtar OZEL_ANAHTAR.pem

Ortam değişkenleri: THREADS_TOKEN; DENEME=true ise bul/gonder hiçbir şey kaydetmez ve göndermez, yalnızca gösterir.
Yalnızca Python standart kütüphanesi ve openssl komutu kullanılır.
"""
import argparse
import base64
import json
import os
import random
import re
import secrets
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bot import ROOT, TZ, api, publish, report_error, threads_len

DIR = ROOT / 'yanitlar'
AYAR = DIR / 'ayar.json'
ISTEK = DIR / '.ara'
DURUM = DIR / 'durum.json'
ADAYLAR = DIR / 'adaylar.enc.json'
KARARLAR = DIR / 'kararlar.json'
GONDERILEN = DIR / 'gonderilen.json'
ACIK_ANAHTAR = DIR / 'claude_acik_anahtar.pem'

ALANLAR = 'id,text,media_type,permalink,timestamp,username,has_replies,is_quote_post,is_reply'
VARSAYILAN = {
    'acik': True,
    'anahtar_kelimeler': [],
    'limit_yeni': 25,             # her kelime için en yeni gönderiler (RECENT)
    'limit_populer': 10,          # her kelime için öne çıkan gönderiler (TOP)
    'en_eski_saat': 36,           # bundan eski gönderiler aday olmaz
    'en_fazla_aday': 30,
    'en_kisa_metin': 25,
    'yasak_kelimeler': [],
    'gunluk_limit': 10,
    'tur_basina_yanit': 3,        # Claude'un bir turda yazabileceği en fazla yanıt
    'tur_basina_gonderim': 4,     # gönderim iş akışının bir çalışmada atabileceği en fazla yanıt
    'yazar_araligi_gun': 14,      # aynı kişiye en erken bu kadar gün sonra tekrar yanıt
    'bekleme_saniye': [60, 150],  # iki yanıt arası bekleme (saniye, rastgele)
    'en_kisa_yanit': 80,
    'en_fazla_emoji': 2,
}
LINK = re.compile(r'https?://|www\.|\b[\w-]+\.(com|net|org|io|app|co|me|ly|gl|tr)\b', re.I)
CAGRI = re.compile(r'app ?store|play ?store|google play|\bindir(in|iniz)?\b|profilimiz|\bdm\b')
OAEP = ['-pkeyopt', 'rsa_padding_mode:oaep', '-pkeyopt', 'rsa_oaep_md:sha256']
AES = ['-aes-256-cbc', '-pbkdf2', '-iter', '100000', '-a', '-A', '-pass', 'env:YANIT_PAROLA']


# ---------- yardımcılar ----------

def oku(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return default


def yaz(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def ayarlar():
    return {**VARSAYILAN, **oku(AYAR, {})}


def env_dogru(ad):
    return os.environ.get(ad, '').strip().lower() in ('1', 'true', 'yes')


def simdi():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def zaman(s):
    """Threads (2026-10-29T08:07:01+0000) ya da bizim (…Z) zaman damgası → datetime; okunamazsa None."""
    if not s:
        return None
    s = str(s).strip().replace('Z', '+00:00')
    if re.search(r'[+-]\d{4}$', s):
        s = s[:-2] + ':' + s[-2:]
    try:
        z = datetime.fromisoformat(s)
    except ValueError:
        return None
    return z if z.tzinfo else z.replace(tzinfo=timezone.utc)


def kucuk(s):
    """Türkçeye uygun küçük harf: I → ı, İ → i."""
    return (s or '').replace('I', 'ı').replace('İ', 'i').lower()


def emoji_sayisi(s):
    return sum(1 for ch in s if unicodedata.category(ch) == 'So' and ord(ch) >= 0x2190)


def metin_sorunu(metin, ayar):
    """Yanıt metni kurallara uymuyorsa nedenini döndürür (Claude düzeltsin diye), uyuyorsa None."""
    if not metin:
        return 'yanıt boş'
    n = threads_len(metin)
    if n > 500:
        return f'çok uzun ({n} > 500, Threads sınırı)'
    if len(metin) < ayar['en_kisa_yanit']:
        return f'çok kısa ({len(metin)} karakter, en az {ayar["en_kisa_yanit"]})'
    if LINK.search(metin):
        return 'link içeremez'
    if '@' in metin:
        return '@ ile kimse etiketlenemez'
    if '#' in metin:
        return 'hashtag içeremez'
    if '{' in metin or '}' in metin:
        return 'şablon işareti ({ }) içeremez'
    if '—' in metin:
        return 'uzun tire (—) yerine doğal noktalama kullan'
    if CAGRI.search(kucuk(metin)):
        return 'indirme, mağaza, DM ya da profil çağrısı içeremez'
    if emoji_sayisi(metin) > ayar['en_fazla_emoji']:
        return f'en fazla {ayar["en_fazla_emoji"]} emoji'
    return None


def hata_kodu(e):
    m = re.search(r'"code"\s*:\s*(\d+)', str(e))
    return int(m.group(1)) if m else None


def genel_hata(e):
    """Token, izin ya da hız sınırı hatası: tek bir gönderiye değil tüm çalışmaya ait, devam etmenin anlamı yok."""
    k = hata_kodu(e)
    return k in (4, 10, 17, 32, 190, 613) or (k is not None and 200 <= k <= 299)


# ---------- şifreleme (openssl: RSA-OAEP ile sarılmış tek kullanımlık AES anahtarı) ----------

def _openssl(args, veri, parola=None):
    env = dict(os.environ)
    if parola is not None:
        env['YANIT_PAROLA'] = parola
    r = subprocess.run(['openssl', *args], input=veri, capture_output=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(f'openssl {args[0]} başarısız: {r.stderr.decode(errors="replace").strip()[:300]}')
    return r.stdout


def sifrele(veri):
    parola = secrets.token_hex(32)
    govde = _openssl(['enc', '-salt', *AES], veri, parola).decode().strip()
    anahtar = _openssl(['pkeyutl', '-encrypt', '-pubin', '-inkey', str(ACIK_ANAHTAR), *OAEP], parola.encode())
    return {'anahtar': base64.b64encode(anahtar).decode(), 'veri': govde}


def coz(paket, ozel_anahtar):
    parola = _openssl(['pkeyutl', '-decrypt', '-inkey', str(ozel_anahtar), *OAEP],
                      base64.b64decode(paket['anahtar'])).decode()
    return _openssl(['enc', '-d', *AES], (paket['veri'] + '\n').encode(), parola)


def aday_listesi(ozel_anahtar):
    paket = oku(ADAYLAR, {})
    if not paket.get('veri'):
        return []
    return json.loads(coz(paket, ozel_anahtar))


# ---------- kayıtlar, kota ----------

def gonderildi(kayit):
    return kayit.get('durum') == 'gonderildi'


def bekliyor(pid, karar, gonderilen):
    """Karar 'yanıtla' ama yanıt henüz gitmedi ve vazgeçilmedi."""
    if karar.get('karar') != 'yanitla':
        return False
    k = gonderilen.get(pid)
    return k is None or k.get('durum') == 'hata'


def eskimis(karar, ayar, an):
    """Hedef gönderi o kadar eski ki yanıt artık tuhaf kaçar (arama penceresi + 12 saat)."""
    z = zaman(karar.get('gonderi_zamani'))
    return z is not None and an - z > timedelta(hours=ayar['en_eski_saat'] + 12)


def yakin_yazarlar(ayar, kararlar, gonderilen, an, bekleyenler_dahil=True):
    """Son `yazar_araligi_gun` günde yanıt verdiğimiz (ve istenirse yanıtı sırada bekleyen) kişiler, küçük harfle."""
    sinir = an - timedelta(days=ayar['yazar_araligi_gun'])
    adlar = {kucuk(k.get('kullanici')) for k in gonderilen.values()
             if gonderildi(k) and (zaman(k.get('zaman')) or sinir) > sinir}
    if bekleyenler_dahil:
        adlar |= {kucuk(k.get('kullanici')) for pid, k in kararlar.items() if bekliyor(pid, k, gonderilen)}
    return adlar - {''}


def kota(ayar, kararlar, gonderilen, an):
    bugun = an.astimezone(TZ).date()
    giden = sum(1 for k in gonderilen.values()
                if gonderildi(k) and zaman(k.get('zaman')) and zaman(k['zaman']).astimezone(TZ).date() == bugun)
    bekleyen = sum(1 for pid, k in kararlar.items() if bekliyor(pid, k, gonderilen) and not eskimis(k, ayar, an))
    kalan = max(0, min(ayar['tur_basina_yanit'], ayar['gunluk_limit'] - giden - bekleyen))
    return {'bugun_gonderilen': giden, 'bekleyen': bekleyen, 'gunluk_limit': ayar['gunluk_limit'], 'kalan': kalan}


def gonderilen_kaydi():
    kayit = oku(GONDERILEN, {})
    kayit.setdefault('yanitlar', {})
    return kayit


# ---------- bul (GitHub Actions) ----------

def elenme_nedeni(m, ayar, en_eski, kararlar, gonderilen, yakin):
    pid = str(m.get('id') or '')
    metin = (m.get('text') or '').strip()
    z = zaman(m.get('timestamp'))
    if not pid:
        return 'kimlik yok'
    if pid in kararlar or pid in gonderilen:
        return 'daha önce değerlendirildi'
    if m.get('is_reply'):
        return 'başka bir gönderiye yanıt'
    if len(metin) < ayar['en_kisa_metin']:
        return 'metin çok kısa'
    if z is None or z < en_eski:
        return 'eski'
    if LINK.search(metin):
        return 'link içeriyor'
    k = kucuk(metin)
    if any(kucuk(w) in k for w in ayar['yasak_kelimeler']):
        return 'yasaklı kelime'
    if kucuk(m.get('username')) in yakin:
        return 'bu kişiye yakın zamanda yanıt verildi'
    return None


def _bul(ayar, deneme, an, durum):
    if not ayar['acik']:
        durum['not'] = 'Yanıt sistemi kapalı (yanitlar/ayar.json › "acik": false).'
        return []
    token = os.environ.get('THREADS_TOKEN', '').strip()
    if not token:
        durum['hata'] = 'THREADS_TOKEN tanımlı değil.'
        return []
    ben = kucuk(api('GET', 'me', {'fields': 'id,username'}, token).get('username'))
    kararlar = oku(KARARLAR, {})
    gonderilen = gonderilen_kaydi()['yanitlar']
    yakin = yakin_yazarlar(ayar, kararlar, gonderilen, an)
    en_eski = an - timedelta(hours=ayar['en_eski_saat'])
    sorgular = [(k, t, n) for k in ayar['anahtar_kelimeler']
                for t, n in (('RECENT', ayar['limit_yeni']), ('TOP', ayar['limit_populer'])) if n]
    bulunan, hatalar = {}, []

    for kelime, tur, limit in sorgular:
        try:
            sonuc = api('GET', 'keyword_search', {'q': kelime, 'search_type': tur, 'fields': ALANLAR,
                                                  'since': int(en_eski.timestamp()), 'limit': limit}, token)
        except RuntimeError as e:
            hatalar.append(f'"{kelime}" ({tur}): {e}')
            if not durum['sorgu'] or genel_hata(e) or len(hatalar) >= 3:
                break                                   # ilk sorgu ya da izin/token hatası: kalanlar da başarısız olur
            continue
        durum['sorgu'] += 1
        for m in sonuc.get('data', []):
            durum['sonuc'] += 1
            ad = m.get('username') or ''
            kendi = kucuk(ad) == ben
            neden = 'LINGOOF\'un kendi gönderisi' if kendi else elenme_nedeni(m, ayar, en_eski, kararlar, gonderilen, yakin)
            durum['kendi_gonderisi'] += kendi
            if deneme:
                ozet = (m.get('text') or '').replace('\n', ' ')[:110]
                print(f'[{tur} · {kelime}] @{ad} · {m.get("timestamp", "")[:16]} · {neden or "ADAY"} · {ozet}')
            if neden:
                continue
            a = bulunan.get(str(m['id']))
            if a:
                if kelime not in a['kelimeler']:
                    a['kelimeler'].append(kelime)
                continue
            z = zaman(m.get('timestamp'))
            bulunan[str(m['id'])] = {
                'id': str(m['id']), 'kullanici': ad, 'metin': (m.get('text') or '').strip()[:700],
                'link': m.get('permalink'), 'zaman': iso(z), 'kac_saat_once': round((an - z).total_seconds() / 3600, 1),
                'yanitlari_var': bool(m.get('has_replies')), 'alinti': bool(m.get('is_quote_post')),
                'tur': m.get('media_type'), 'kelimeler': [kelime],
            }

    secilen, yazarlar = [], set()
    for a in sorted(bulunan.values(), key=lambda a: a['zaman'], reverse=True):
        if kucuk(a['kullanici']) not in yazarlar:      # bir kişiden yalnızca en yeni gönderisi
            yazarlar.add(kucuk(a['kullanici']))
            secilen.append(a)
    secilen = secilen[:ayar['en_fazla_aday']]

    if hatalar:
        durum['hata'] = f'{len(hatalar)} sorgu başarısız. İlki: {hatalar[0]}'[:600]
    if not durum['sorgu'] and hatalar:
        durum['not'] = ('Anahtar kelime araması çalışmadı. Token\'da threads_keyword_search izni yoksa '
                        'README › Sohbetlere katılma adımlarını uygula.')
    elif durum['sonuc'] and durum['sonuc'] == durum['kendi_gonderisi']:
        durum['not'] = ('Arama yalnızca LINGOOF\'un kendi gönderilerini döndürdü: Meta threads_keyword_search iznini '
                        'henüz onaylamamış. Onay gelene kadar başkalarının gönderilerine yanıt verilemez.')
    elif not durum['sonuc'] and durum['sorgu']:
        durum['not'] = ('Aramada hiç sonuç çıkmadı. İzin henüz onaylanmadıysa arama yalnızca LINGOOF\'un kendi '
                        'gönderilerine bakar.')
    return secilen


def bul():
    ayar = ayarlar()
    deneme = env_dogru('DENEME')
    an = simdi()
    durum = {'istek': ISTEK.read_text(encoding='utf-8').strip() if ISTEK.exists() else '',
             'son_arama': iso(an), 'sorgu': 0, 'sonuc': 0, 'kendi_gonderisi': 0, 'aday': 0, 'hata': None, 'not': None}
    adaylar = []
    try:
        adaylar = _bul(ayar, deneme, an, durum)
    except Exception as e:                              # durum.json her koşulda yazılsın: Claude'un turu beklemede kalmasın
        durum['hata'] = f'{type(e).__name__}: {e}'[:600]
    durum['aday'] = len(adaylar)
    print(f'{durum["sorgu"]} sorgu · {durum["sonuc"]} sonuç ({durum["kendi_gonderisi"]} LINGOOF\'un kendi) · '
          f'{durum["aday"]} aday')
    if durum['not']:
        print(f'Not: {durum["not"]}')
    if durum['hata']:
        print(f'::warning title=Yanıt araması::{durum["hata"]}')
    if deneme:
        print('(Deneme) Hiçbir şey kaydedilmedi.')
        return
    paket = {'istek': durum['istek'], 'olusturuldu': durum['son_arama'], 'adet': len(adaylar)}
    try:
        paket.update(sifrele(json.dumps(adaylar, ensure_ascii=False).encode()))
    except Exception as e:
        paket['adet'] = durum['aday'] = 0
        durum['hata'] = f'Adaylar şifrelenemedi: {e}'[:600]
        print(f'::warning title=Yanıt araması::{durum["hata"]}')
    yaz(ADAYLAR, paket)
    yaz(DURUM, durum)


# ---------- adaylar / ekle (Claude) ----------

def son_yanitlar(kararlar, n=8):
    yanitlar = sorted((k for k in kararlar.values() if k.get('karar') == 'yanitla'), key=lambda k: k.get('zaman', ''))
    return [k['yanit'] for k in yanitlar[-n:]]


def guncel_adaylar(ozel_anahtar, ayar, kararlar, gonderilen, an):
    yakin = yakin_yazarlar(ayar, kararlar, gonderilen, an)
    return [a for a in aday_listesi(ozel_anahtar)
            if a['id'] not in kararlar and a['id'] not in gonderilen and kucuk(a['kullanici']) not in yakin]


def adaylar_komutu(ozel_anahtar):
    ayar, an = ayarlar(), simdi()
    kararlar, gonderilen = oku(KARARLAR, {}), gonderilen_kaydi()['yanitlar']
    durum = oku(DURUM, {})
    liste = guncel_adaylar(ozel_anahtar, ayar, kararlar, gonderilen, an)
    k = kota(ayar, kararlar, gonderilen, an)
    if not liste:
        ozet = durum.get('not') or durum.get('hata') or 'Yanıt verilecek yeni gönderi yok.'
    elif not k['kalan']:
        ozet = f'Günlük yanıt sınırı ({ayar["gunluk_limit"]}) doldu.'
    else:
        ozet = f'{len(liste)} aday gönderi; bu turda en fazla {k["kalan"]} yanıt yazılabilir.'
    print(json.dumps({'devam': bool(liste and k['kalan']), 'ozet': ozet, 'durum': durum, 'kota': k,
                      'son_yanitlarimiz': son_yanitlar(kararlar), 'adaylar': liste}, ensure_ascii=False, indent=1))


def ekle_komutu(dosya, ozel_anahtar):
    ayar, an = ayarlar(), simdi()
    kararlar, gonderilen = oku(KARARLAR, {}), gonderilen_kaydi()['yanitlar']
    adaylar = {a['id']: a for a in guncel_adaylar(ozel_anahtar, ayar, kararlar, gonderilen, an)}
    girdi = json.loads(Path(dosya).read_text(encoding='utf-8'))
    if not isinstance(girdi, list):
        sys.exit('Kararlar bir JSON dizisi olmalı: [{"id": "...", "karar": "yanitla", "yanit": "..."}, ...]')

    sorunlar, yeni, yazarlar, uygulama = [], {}, set(), 0
    for i, k in enumerate(girdi, 1):
        pid, karar = str(k.get('id', '')), k.get('karar')
        a = adaylar.get(pid)
        if not a:
            sorunlar.append(f'{i}. kayıt: {pid} bu turun adayları arasında yok')
        elif pid in yeni:
            sorunlar.append(f'{i}. kayıt: {pid} iki kez yazılmış')
        elif karar == 'gec':
            yeni[pid] = {'karar': 'gec', 'zaman': iso(an)}
        elif karar != 'yanitla':
            sorunlar.append(f'{i}. kayıt: karar "yanitla" ya da "gec" olmalı')
        else:
            metin = (k.get('yanit') or '').strip()
            sorun = metin_sorunu(metin, ayar)
            if sorun:
                sorunlar.append(f'@{a["kullanici"]} yanıtı: {sorun}')
                continue
            if kucuk(a['kullanici']) in yazarlar:
                sorunlar.append(f'@{a["kullanici"]}: aynı kişiye bir turda tek yanıt')
                continue
            yazarlar.add(kucuk(a['kullanici']))
            uygulama += bool(re.search(r'lingoof|goof', kucuk(metin)))
            yeni[pid] = {'karar': 'yanitla', 'kullanici': a['kullanici'], 'link': a.get('link'),
                         'gonderi_zamani': a.get('zaman'), 'yanit': metin, 'zaman': iso(an)}

    yanit_sayisi = sum(1 for k in yeni.values() if k['karar'] == 'yanitla')
    kalan = kota(ayar, kararlar, gonderilen, an)['kalan']
    if yanit_sayisi > kalan:
        sorunlar.append(f'{yanit_sayisi} yanıt yazılmış ama bu turda en fazla {kalan} yanıt gidebilir')
    if uygulama > 1:
        sorunlar.append('bir turda en fazla 1 yanıtta LINGOOF ya da Goof anılabilir')
    if sorunlar:
        print('Kaydedilmedi. Düzeltilmesi gerekenler:\n- ' + '\n- '.join(sorunlar))
        sys.exit(2)

    for pid in adaylar:                                 # hakkında karar yazılmayan adaylar geçilmiş sayılır
        yeni.setdefault(pid, {'karar': 'gec', 'zaman': iso(an)})
    kararlar.update(yeni)
    sinir = iso(an - timedelta(days=7))                 # eski "geç" kayıtlarına gerek yok; yanıtlar kalıcı kayıttır
    kararlar = {p: k for p, k in kararlar.items() if k.get('karar') == 'yanitla' or k.get('zaman', '') >= sinir}
    yaz(KARARLAR, kararlar)
    print(f'Kaydedildi: {yanit_sayisi} yanıt, {len(yeni) - yanit_sayisi} geçildi.')


# ---------- gonder (GitHub Actions) ----------

def ozet_yaz(satirlar):
    yol = os.environ.get('GITHUB_STEP_SUMMARY')
    if yol and satirlar:
        with open(yol, 'a', encoding='utf-8') as f:
            f.write('### Yanıt gönderimi\n\n' + '\n'.join(satirlar) + '\n')


def gonder():
    ayar = ayarlar()
    deneme = env_dogru('DENEME')
    if not ayar['acik']:
        print('Yanıt sistemi kapalı (yanitlar/ayar.json › "acik": false).')
        return
    an = simdi()
    kayit = gonderilen_kaydi()
    gonderilen = kayit['yanitlar']
    kararlar = oku(KARARLAR, {})
    sira = sorted(((p, k) for p, k in kararlar.items() if bekliyor(p, k, gonderilen)), key=lambda x: x[1].get('zaman', ''))
    if not sira:
        print('Gönderilecek yanıt yok.')
        return
    token = os.environ.get('THREADS_TOKEN', '').strip()
    if not token and not deneme:
        report_error('THREADS_TOKEN tanımlı değil.')
        sys.exit(1)

    hak = min(ayar['tur_basina_gonderim'], ayar['gunluk_limit'] - kota(ayar, kararlar, gonderilen, an)['bugun_gonderilen'])
    yakin = yakin_yazarlar(ayar, kararlar, gonderilen, an, bekleyenler_dahil=False)
    giden, satirlar, genel = 0, [], None

    def kaydet():
        if not deneme:
            kayit['son_calisma'] = {'zaman': iso(simdi()), 'gonderilen': giden}
            yaz(GONDERILEN, kayit)

    for pid, k in sira:
        ad = k.get('kullanici', '')
        iptal = metin_sorunu(k.get('yanit', ''), ayar)
        if not iptal and kucuk(ad) in yakin:
            iptal = f'@{ad} kişisine son {ayar["yazar_araligi_gun"]} günde zaten yanıt verildi'
        if not iptal and eskimis(k, ayar, an):
            iptal = 'gönderi artık çok eski'
        if iptal:
            print(f'Vazgeçildi: @{ad} ({iptal})')
            if not deneme:
                gonderilen[pid] = {'kullanici': ad, 'durum': 'iptal', 'neden': iptal, 'zaman': iso(simdi())}
            continue
        if giden >= hak:
            print('Bu çalışmanın ya da günün sınırı doldu; kalan yanıtlar bir sonraki gönderimde.')
            break
        if deneme:
            print(f'(Deneme) @{ad} ← {k["yanit"]}')
            giden += 1
            continue
        if giden:
            time.sleep(random.randint(*ayar['bekleme_saniye']))
        try:
            yanit_id = publish(token, {'media_type': 'TEXT', 'text': k['yanit'], 'reply_to_id': pid})
        except RuntimeError as e:
            print(f'::warning title=Yanıt gönderilemedi::@{ad}: {e}')
            sayac = gonderilen.get(pid, {}).get('deneme', 0)
            if genel_hata(e):                           # token/izin/hız sınırı: gönderinin suçu değil, sonra yine denensin
                gonderilen[pid] = {'kullanici': ad, 'durum': 'hata', 'deneme': sayac, 'neden': str(e)[:400],
                                   'zaman': iso(simdi())}
                genel = e
                break
            sayac += 1                                  # gönderiye özgü hata (silinmiş, yanıtlara kapalı...): bir kez daha denenir
            gonderilen[pid] = {'kullanici': ad, 'durum': 'hata' if sayac < 2 else 'iptal', 'deneme': sayac,
                               'neden': str(e)[:400], 'zaman': iso(simdi())}
            kaydet()
            continue
        try:
            link = api('GET', yanit_id, {'fields': 'permalink'}, token).get('permalink')
        except RuntimeError:
            link = None
        gonderilen[pid] = {'kullanici': ad, 'durum': 'gonderildi', 'yanit_id': yanit_id, 'yanit_link': link,
                           'link': k.get('link'), 'zaman': iso(simdi())}
        yakin.add(kucuk(ad))
        giden += 1
        kaydet()                                         # her yanıttan sonra: çalışma yarıda kesilse de aynı yanıt iki kez gitmez
        print(f'Gönderildi → @{ad}: {link or yanit_id}')
        satirlar.append(f'- @{ad}: {link or yanit_id}')

    kaydet()
    ozet_yaz(satirlar)
    if genel:
        report_error(f'Yanıt gönderimi durdu (token ya da izin sorunu): {genel}')
        sys.exit(1)


def main():
    p = argparse.ArgumentParser(description='LINGOOF Threads yanıt sistemi')
    alt = p.add_subparsers(dest='komut', required=True)
    alt.add_parser('bul')
    alt.add_parser('gonder')
    a = alt.add_parser('adaylar')
    a.add_argument('--anahtar', required=True)
    e = alt.add_parser('ekle')
    e.add_argument('dosya')
    e.add_argument('--anahtar', required=True)
    args = p.parse_args()
    if args.komut == 'bul':
        bul()
    elif args.komut == 'gonder':
        gonder()
    elif args.komut == 'adaylar':
        adaylar_komutu(args.anahtar)
    else:
        ekle_komutu(args.dosya, args.anahtar)


if __name__ == '__main__':
    main()
