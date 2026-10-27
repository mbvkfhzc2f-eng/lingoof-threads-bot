#!/usr/bin/env python3
"""LINGOOF Threads istatistikleri.

Paylaşılan her gönderinin görüntülenme, beğeni, yorum, repost, alıntı ve paylaşım sayılarını Threads API'den çeker,
takipçi sayısını günlük kaydeder; insights.json'a ham veriyi, insights.md'ye seri ve saat bazında özet raporu yazar.
Böylece hangi serinin (anket, Hata Avı, Günün Kelimesi...) daha çok etkileşim aldığı görülür ve plan buna göre ayarlanır.

Token'da `threads_manage_insights` izni yoksa hata vermez, uyarı yazıp çıkar (paylaşımlar etkilenmez).
Yalnızca Python standart kütüphanesi kullanılır.
"""
import os
import sys
from datetime import datetime

from bot import ROOT, TZ, api, load, save, slot_time

METRICS = ['views', 'likes', 'replies', 'reposts', 'quotes', 'shares']
ENGAGE = METRICS[1:]


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


def table(groups, label):
    lines = [f'| {label} | Gönderi | Ort. görüntülenme | Ort. beğeni | Ort. yorum | Etkileşim oranı |',
             '|---|---:|---:|---:|---:|---:|']
    order = sorted(groups.items(), key=lambda kv: -sum(r['eng'] for r in kv[1]) / len(kv[1]))
    for name, rows in order:
        n = len(rows)
        lines.append(f'| {name} | {n} | {sum(r["views"] for r in rows) / n:.0f} | {sum(r["likes"] for r in rows) / n:.1f}'
                     f' | {sum(r["replies"] for r in rows) / n:.1f} | {rate(rows)} |')
    return '\n'.join(lines)


def report(rows, followers, now):
    by_series, by_time = {}, {}
    for r in rows:
        by_series.setdefault(r['series'], []).append(r)
        by_time.setdefault(r['time'], []).append(r)
    total_views = sum(r['views'] for r in rows)
    out = [f'# LINGOOF Threads istatistikleri',
           f'Son güncelleme: {now:%d.%m.%Y %H:%M} (Türkiye saati) · {len(rows)} gönderi · '
           f'toplam {total_views:,} görüntülenme · etkileşim oranı {rate(rows)}'.replace(',', '.')]
    if followers:
        first, last = followers[0], followers[-1]
        out.append(f'Takipçi: **{last["count"]}** ({first["date"]} tarihinden beri {last["count"] - first["count"]:+d})')
    out += ['', 'Etkileşim = beğeni + yorum + repost + alıntı + paylaşım. Oran = etkileşim / görüntülenme. '
            'Yorum sayısına botun kendi ilk yorumu dahil değil. Tablolar gönderi başına ortalama etkileşime göre sıralı. Son 24 saatte paylaşılanlar henüz oturmadığı için düşük görünebilir.',
            '', '## Seriye göre', '', table(by_series, 'Seri'), '', '## Saate göre', '', table(by_time, 'Saat'), '',
            '## En çok etkileşim alan 10 gönderi', '', '| # | Tarih | Seri | Görüntülenme | Beğeni | Yorum | Başlangıç |',
            '|---:|---|---|---:|---:|---:|---|']
    for r in sorted(rows, key=lambda r: -r['eng'])[:10]:
        out.append(f'| {r["n"]} | {r["date"]} {r["time"]} | {r["series"]} | {r["views"]} | {r["likes"]} | {r["replies"]}'
                   f' | {r["start"]} |')
    return '\n'.join(out) + '\n'


def main():
    token = os.environ.get('THREADS_TOKEN', '').strip()
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

    save('insights.json', data)
    rows = []
    for n, m in data['posts'].items():
        p = posts.get(n)
        if not p:
            continue
        start = p['text'].split('\n')[0][:40].replace('|', '/')
        rows.append({**m, 'n': int(n), 'date': p['date'], 'time': p['time'], 'series': p['series'], 'start': start,
                     'eng': sum(m[k] for k in ENGAGE)})
    rows.sort(key=lambda r: slot_time(posts[str(r['n'])]))
    md = report(rows, data['followers'], now)
    (ROOT / 'insights.md').write_text(md, encoding='utf-8')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write(md)
    print(f'{len(rows)} gönderinin istatistiği güncellendi' + (f', {errors} gönderi alınamadı' if errors else '') +
          (f'. Takipçi: {count}' if count is not None else ''))


if __name__ == '__main__':
    main()
