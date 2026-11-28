#!/usr/bin/env python3
"""LINGOOF Threads istatistikleri.

Paylaşılan her gönderinin görüntülenme, beğeni, yorum, repost, alıntı ve paylaşım sayılarını Threads API'den çeker;
takipçi sayısını, profil görüntülenmelerini ve link tıklamalarını (App Store linki) günlük kaydeder. insights.json'a ham
veriyi, insights.md'ye seri, biçim (metin, görsel, video, carousel...), gün ve saat bazında özet raporu yazar. Böylece
neyin erişim, sohbet ve indirme getirdiği görülür ve plan buna göre ayarlanır.

Token'da `threads_manage_insights` izni yoksa hata vermez, uyarı yazıp çıkar (paylaşımlar etkilenmez).
Yalnızca Python standart kütüphanesi kullanılır.
"""
import os
import sys
from datetime import date, datetime, timedelta

from bot import ROOT, TZ, api, load, media_kind, save, slot_time

METRICS = ['views', 'likes', 'replies', 'reposts', 'quotes', 'shares']
ENGAGE = METRICS[1:]
PLAN_START = datetime(2026, 10, 18, tzinfo=TZ)
DAYS = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']


def value(item):
    if 'total_value' in item:
        return item['total_value'].get('value', 0)
    vals = item.get('values') or [{}]
    return vals[-1].get('value', 0)


def fetch(token, media_id):
    data = api('GET', f'{media_id}/insights', {'metric': ','.join(METRICS)}, token).get('data', [])
    got = {d['name']: value(d) for d in data}
    return {m: int(got.get(m, 0) or 0) for m in METRICS}


def warn(msg):
    print(f'::warning title=İstatistikler alınamadı::{msg}')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write(f'### İstatistikler alınamadı\n\n{msg}\n')


def rate(rows):
    views = sum(r['views'] for r in rows)
    eng = sum(r['eng'] for r in rows)
    return f'%{100 * eng / views:.1f}' if views else '–'


def median(xs):
    xs = sorted(xs)
    if not xs:
        return 0
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def table(groups, label, order=None):
    lines = [f'| {label} | Gönderi | Ort. görüntülenme | Medyan | Ort. beğeni | Ort. yorum | Etkileşim oranı |',
             '|---|---:|---:|---:|---:|---:|---:|']
    items = list(groups.items())
    if order:
        items.sort(key=lambda kv: order.index(kv[0]) if kv[0] in order else 99)
    else:
        items.sort(key=lambda kv: -sum(r['eng'] for r in kv[1]) / len(kv[1]))
    for name, rows in items:
        n = len(rows)
        lines.append(f'| {name} | {n} | {sum(r["views"] for r in rows) / n:.0f} | {median([r["views"] for r in rows]):.0f}'
                     f' | {sum(r["likes"] for r in rows) / n:.1f} | {sum(r["replies"] for r in rows) / n:.1f} | {rate(rows)} |')
    return '\n'.join(lines)


def week_compare(rows, followers, now):
    """Son 7 gün ile önceki 7 günü karşılaştırır (son 24 saatteki gönderiler henüz oturmadığı için hariç)."""
    end = now - timedelta(hours=24)
    cur = [r for r in rows if end - timedelta(days=7) < r['when'] <= end]
    prev = [r for r in rows if end - timedelta(days=14) < r['when'] <= end - timedelta(days=7)]

    def stats(rs):
        if not rs:
            return '–', '–', '–'
        return f'{sum(r["views"] for r in rs) / len(rs):.0f}', f'{median([r["views"] for r in rs]):.0f}', f'{sum(r["replies"] for r in rs) / len(rs):.2f}'

    fol = {f['date']: f['count'] for f in followers}
    def gain(a, b):
        x, y = fol.get(a.isoformat()), fol.get(b.isoformat())
        return f'{y - x:+d}' if x is not None and y is not None else '–'
    today = now.date()
    c, p = stats(cur), stats(prev)
    return '\n'.join([
        '| Dönem | Gönderi | Ort. görüntülenme | Medyan | Ort. yorum | Yeni takipçi |', '|---|---:|---:|---:|---:|---:|',
        f'| Son 7 gün | {len(cur)} | {c[0]} | {c[1]} | {c[2]} | {gain(today - timedelta(days=7), today)} |',
        f'| Önceki 7 gün | {len(prev)} | {p[0]} | {p[1]} | {p[2]} | {gain(today - timedelta(days=14), today - timedelta(days=7))} |'])


def clicks_section(data):
    c = data.get('clicks') or {}
    total = c.get('total') or {}
    if not total and not c.get('error'):
        return []
    out = ['## Link tıklamaları (App Store)', '']
    if c.get('error'):
        out += [f'Alınamadı: {c["error"]}', '']
        return out
    out += ['| Link | Tıklama (planın başından beri) |', '|---|---:|']
    for url, v in sorted(total.items(), key=lambda kv: -kv[1]):
        out.append(f'| {url} | {v} |')
    daily = c.get('daily') or []
    if len(daily) >= 2:
        last = daily[-1]['sum'] - daily[max(0, len(daily) - 8)]['sum']
        out += ['', f'Son 7 günde yaklaşık **{last}** tıklama (günlük toplamların farkı).']
    out.append('')
    return out


def profile_views_section(data, rows, now):
    pv = data.get('profile_views') or {}
    if not pv:
        return []
    days = sorted(pv.items())
    last7 = sum(v for d, v in days[-7:])
    prev7 = sum(v for d, v in days[-14:-7])
    start = (now - timedelta(days=7)).date().isoformat()
    own = sum(r['views'] for r in rows if r['date'] >= start)
    return ['## Hesap görüntülenmeleri', '',
            f'Son 7 gün: **{last7}** · önceki 7 gün: {prev7} · aynı 7 günde kendi gönderilerimizin görüntülenmesi: {own}', '',
            "Threads API'nin hesap düzeyindeki `views` metriği. Kendi gönderilerimizin toplamından çok yüksekse fark büyük "
            'olasılıkla başkalarının gönderilerine yazdığımız yanıtların görüntülenmesinden gelir (yanıt görevi).', '']


def report(rows, data, now):
    followers = data['followers']
    by_series, by_time, by_kind, by_day = {}, {}, {}, {}
    for r in rows:
        by_series.setdefault(r['series'], []).append(r)
        by_time.setdefault(r['time'], []).append(r)
        by_kind.setdefault(r['kind'], []).append(r)
        by_day.setdefault(DAYS[r['when'].weekday()], []).append(r)
    total_views = sum(r['views'] for r in rows)
    out = ['# LINGOOF Threads istatistikleri',
           f'Son güncelleme: {now:%d.%m.%Y %H:%M} (Türkiye saati) · {len(rows)} gönderi · '
           f'toplam {total_views:,} görüntülenme · etkileşim oranı {rate(rows)}'.replace(',', '.')]
    if followers:
        first, last = followers[0], followers[-1]
        out.append(f'Takipçi: **{last["count"]}** ({first["date"]} tarihinden beri {last["count"] - first["count"]:+d})')
    out += ['', 'Etkileşim = beğeni + yorum + repost + alıntı + paylaşım. Oran = etkileşim / görüntülenme. '
            'Yorum sayısına botun kendi ilk yorumu dahil değil. Son 24 saatte paylaşılanlar henüz oturmadığı için düşük görünebilir.',
            '', '## Son 7 gün', '', week_compare(rows, followers, now), '']
    out += clicks_section(data)
    out += profile_views_section(data, rows, now)
    out += ['## Biçime göre', '', table(by_kind, 'Biçim'), '',
            '## Seriye göre', '', table(by_series, 'Seri'), '',
            '## Saate göre', '', table(by_time, 'Saat'), '',
            '## Güne göre', '', table(by_day, 'Gün', DAYS), '',
            '## En çok görülen 10 gönderi', '', '| # | Tarih | Seri | Biçim | Görüntülenme | Beğeni | Yorum | Başlangıç |',
            '|---:|---|---|---|---:|---:|---:|---|']
    for r in sorted(rows, key=lambda r: -r['views'])[:10]:
        out.append(f'| {r["n"]} | {r["date"]} {r["time"]} | {r["series"]} | {r["kind"]} | {r["views"]} | {r["likes"]} | {r["replies"]}'
                   f' | {r["start"]} |')
    out += ['', '## En çok yorum alan 10 gönderi', '', '| # | Tarih | Seri | Biçim | Yorum | Görüntülenme | Başlangıç |',
            '|---:|---|---|---|---:|---:|---|']
    for r in sorted(rows, key=lambda r: (-r['replies'], -r['views']))[:10]:
        out.append(f'| {r["n"]} | {r["date"]} {r["time"]} | {r["series"]} | {r["kind"]} | {r["replies"]} | {r["views"]} | {r["start"]} |')
    return '\n'.join(out) + '\n'


def user_metrics(token, data, now):
    """Link tıklamaları (planın başından beri, link başına) ve son 30 günün günlük profil görüntülenmeleri."""
    since, until = int(PLAN_START.timestamp()), int(now.timestamp())
    try:
        res = api('GET', 'me/threads_insights', {'metric': 'clicks', 'since': since, 'until': until}, token).get('data', [])
        total = {}
        for item in res:
            for lv in item.get('link_total_values') or []:
                total[lv.get('link_url', '?')] = total.get(lv.get('link_url', '?'), 0) + int(lv.get('value', 0) or 0)
        c = {'total': total, 'fetched': now.isoformat(timespec='seconds')}
        daily = [d for d in (data.get('clicks') or {}).get('daily', []) if d['date'] != now.date().isoformat()]
        c['daily'] = (daily + [{'date': now.date().isoformat(), 'sum': sum(total.values())}])[-60:]
        data['clicks'] = c
        print(f'Link tıklamaları: {sum(total.values())}')
    except RuntimeError as e:
        data['clicks'] = {**(data.get('clicks') or {}), 'error': str(e)[:200]}
        print(f'Link tıklamaları alınamadı: {e}')
    try:
        res = api('GET', 'me/threads_insights', {'metric': 'views', 'since': int((now - timedelta(days=30)).timestamp()),
                                                 'until': until}, token).get('data', [])
        pv = dict(data.get('profile_views') or {})
        for item in res:
            for v in item.get('values') or []:
                when = v.get('end_time', '')[:10]
                if when:
                    pv[when] = int(v.get('value', 0) or 0)
        data['profile_views'] = dict(sorted(pv.items())[-90:])
    except RuntimeError as e:
        print(f'Profil görüntülenmeleri alınamadı: {e}')


def main():
    token = (os.environ.get('THREADS_TOKEN_LIVE') or os.environ.get('THREADS_TOKEN', '')).strip()
    if not token:
        sys.exit('THREADS_TOKEN tanımlı değil.')
    now = datetime.now(TZ)
    state = load('state.json', {'posted': {}})
    posts = {str(p['n']): p for p in load('posts.json')}
    data = load('insights.json', {'posts': {}, 'followers': []})

    first_id = next(iter(state['posted'].values()), {}).get('id')
    try:
        if first_id:
            fetch(token, first_id)
    except RuntimeError as e:
        warn('Token\'da `threads_manage_insights` izni yok gibi görünüyor. README\'deki “İstatistikler” bölümündeki '
             f'adımlarla izni ekleyip yeni token üret ve THREADS_TOKEN\'ı güncelle. Hata: {e}')
        return

    errors = 0
    for n, rec in state['posted'].items():
        try:
            m = fetch(token, rec['id'])
        except RuntimeError as e:
            errors += 1
            print(f'#{n}: {e}')
            continue
        if rec.get('reply_id') and m['replies']:        # botun kendi ilk yorumu etkileşim sayılmasın
            m['replies'] -= 1
        data['posts'][n] = {**m, 'at': rec['at'], 'fetched': now.isoformat(timespec='seconds')}

    try:
        res = api('GET', 'me/threads_insights', {'metric': 'followers_count'}, token).get('data', [])
        count = int(value(res[0])) if res else None
    except RuntimeError as e:
        print(f'Takipçi sayısı alınamadı: {e}')
        count = None
    if count is not None:
        today = now.date().isoformat()
        data['followers'] = [f for f in data['followers'] if f['date'] != today] + [{'date': today, 'count': count}]
    user_metrics(token, data, now)

    save('insights.json', data)
    rows = []
    for n, m in data['posts'].items():
        p = posts.get(n)
        if not p:
            continue
        start = p['text'].split('\n')[0][:40].replace('|', '/')
        kind = (state['posted'].get(n) or {}).get('kind') or media_kind(p)
        rows.append({**m, 'n': int(n), 'date': p['date'], 'time': p['time'], 'series': p['series'], 'start': start,
                     'kind': kind, 'when': slot_time(p), 'eng': sum(m[k] for k in ENGAGE)})
    rows.sort(key=lambda r: r['when'])
    md = report(rows, data, now)
    (ROOT / 'insights.md').write_text(md, encoding='utf-8')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write(md)
    print(f'{len(rows)} gönderinin istatistiği güncellendi' + (f', {errors} gönderi alınamadı' if errors else '') +
          (f'. Takipçi: {count}' if count is not None else ''))


if __name__ == '__main__':
    main()
