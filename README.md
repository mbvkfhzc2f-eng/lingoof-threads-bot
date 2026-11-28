# LINGOOF Threads botu

LINGOOF'un Threads planını kendi kendine paylaşır: **18 Ekim (açılış) – 31 Aralık 2026**. Gönderiler Türkiye saatiyle kendi tarih ve saatinde resmi Threads API ile atılır. Bilgisayarının açık olması gerekmez; bot GitHub'ın sunucularında ücretsiz çalışır.

**29 Kasım'dan itibaren günlük düzen** (28 Kasım'daki veri analizine göre yenilendi, ayrıntı: `plan/aralik_v3.py`):

| Saat | Ne | Neden |
|---|---|---|
| 09:00 | Günün cümlesi, deyim ya da gramer: gerçek hayattan bir sahne ve soru | Sabah en çok görülen saat |
| 11:00 (salı, perşembe, cumartesi) | V3 carousel: 5 cümle, mini test, özet | Kaydedilen içerik |
| 13:00 | Goof 2.0 videosu (build 140 görünümü); ana metin tek başına da öğretir, cevap çoğu zaman spoiler'da | Videolar ve görseller Threads'te metinden daha çok etkileşim alıyor |
| 18:00 | Gerçek hayat sahnesi, Goof soruyor, doğru mu yanlış mı, cuma modu, pazar hikâyesi | Sohbet açan sorular |
| 21:00 | Akşam notu, sesli görev, haftanın özeti (V3 kart) | Akşam etkileşimi en yüksek |

- **Link kuralı:** App Store linki ana gönderide hiç yok (linkli gönderiler medyan 9 görüntülenmede kalıyordu). Günde en fazla bir gönderinin **ilk yorumunda**, önizleme kartıyla durur. Tıklamalar `insights.md` › Link tıklamaları bölümünde görünür.
- **Görseller:** Yalnızca uygulamanın V3 tasarımı ve build 140'ın Goof 2.0 pozlarıyla stüdyoda üretilen görseller ve videolar kullanılır; yapay zekâ görsel/video aracı yok. Eski Goof'lu kartlar ve yapay zekâ fotoğrafları plandan çıkarıldı (dosyaları geçmiş gönderiler için `img/` klasöründe duruyor; plan denetimi yeniden kullanılmalarını engeller).
- **Medya dalı:** Videolar ve carousel görselleri depoyu şişirmesin diye ayrı `medya` dalında. Gönderiler onlara `medya:v3/...` diye başvurur.
- Aynı gönderi iki kez gitmez. Saati 4 saatten fazla geçen gönderi atlanır. 31 Aralık'tan sonra kendiliğinden durur.
- Bir biçim olmazsa gönderi kaybolmaz: video olmazsa kapak görseliyle, carousel olmazsa ilk görselle, o da olmazsa metin olarak gider. Spoiler kabul edilmezse cevap ilk yoruma taşınır. Anket oluşturulamazsa seçenekler metne yazılır.
- Token GH_PAT gerekmeden canlı kalır (aşağıda).
- Sohbetlere katılma: Claude'un günlük yanıt görevi dil öğrenmeyi konuşan gönderilere faydalı yanıtlar yazar (ayrıntılar aşağıda).

## Kurulum (bir kerelik, ~15 dakika)

### 1. GitHub deposu
Bu klasörü **herkese açık (public)** bir GitHub deposuna koy. Görsellerin Threads'e gidebilmesi için depo herkese açık olmalı. Depoda gizli bir bilgi yok, token ayrı ve şifreli saklanıyor.

### 2. Threads erişim token'ı
1. [developers.facebook.com](https://developers.facebook.com) › **My Apps** › **Create App**. Kullanım durumu olarak **Access the Threads API**'yi seç.
2. Uygulamanın panelinde **App roles › Roles › Add People › Threads Tester** yolunu izle ve LINGOOF'un Threads kullanıcı adını ekle.
3. Threads'te **Ayarlar › Hesap › Web sitesi izinleri › Davetler** bölümünden daveti kabul et.
4. Panele dön: **Use cases › Access the Threads API › Customize**. Burada `threads_basic`, `threads_content_publish` ve `threads_manage_insights` izinlerinin ekli olduğundan emin ol. Sonuncusu istatistik raporu içindir.
5. Aynı yerde **Settings** sekmesinin altındaki **Generate Access Token** düğmesine bas ve token'ı kopyala. Token `TH` ile başlar.

### 3. Token'ı depoya ekle
Deponun **Settings › Secrets and variables › Actions › New repository secret** bölümüne git. Adı `THREADS_TOKEN`, değeri kopyaladığın token olsun.

### Kontrol
**Actions** sekmesinde **Threads paylaşımı › Run workflow** düğmesine bas. "Deneme" işaretli kalsın. Kayıtta hesap adını ve sıradaki gönderiyi görürsen her şey hazır. İlk gerçek paylaşım bir sonraki paylaşım saatinde gider.

## Ayarlar
- `posts.json`: her gönderinin tarihi, saati, metni ve biçimi burada. `{LINK}` yazan yere App Store linki girer; link yalnızca `reply` (ilk yorum) içinde kullanılır.
  - `topic`: Threads konu etiketi (ör. "İngilizce", "İngilizce Konuşma"). Reddedilirse gönderi etiketsiz gider.
  - `reply`: gönderiden 45 saniye sonra altına eklenen ilk yorum (ipucu, cevap ya da linkli çağrı).
  - `video` + `fallback_img` + `alt`: Goof 2.0 videosu, video olmazsa kullanılacak kapak ve açıklama.
  - `carousel` + `alts`: 2–20 görsel ve her birinin açıklaması.
  - `img` / `alt`: tek görsel (`img/` klasöründen, ör. `v3/th-is.jpg`).
  - `spoiler`: metindeki cevabın birebir aynısı (liste). Threads'te üstü kapalı görünür, dokununca açılır. Spoiler'dan önce emoji olmamalı.
  - `poll`: 2–4 seçenekli anket (her seçenek en fazla 25 bayt).
- `config.json`: `app_store_url`, `media_base_url` (medya dalının adresi), `video_base_url` (videolar için farklı bir adres gerekirse), `grace_hours`, `reply_delay_seconds`.
- `plan/medya.json`: medya dalındaki dosyaların listesi; plan denetimi bununla karşılaştırır.
- Plan denetimi: `python3 bot.py --check` (metin uzunluğu, spoiler, medya, eski görsel, ana metinde link).
- **Deneme:** Actions › Threads paylaşımı › Run workflow, "Deneme" işaretli: sıradaki gönderi, plan denetimi ve önümüzdeki 3 günün medya adresleri.
- **Doğrula:** aynı yerde "Deneme"nin işaretini kaldırıp "Doğrula"yı işaretle: sıradaki medyalı gönderilerin (ya da yazdığın numaraların) konteynerleri Meta'da oluşturulur ama **yayımlanmaz**. Videonun, carousel'ın ve spoiler'ın kabul edilip edilmediğini gösterir.
- Durdurmak için: **Actions › Threads paylaşımı › ⋯ › Disable workflow**. Tekrar açınca o günün tarihinden devam eder.
- Bir çalışma hata verirse GitHub sana e-posta atar. Son hatanın metni `state.json` içindeki `last_error` alanında da durur. Aynı gönderi 3 kez hata verirse atlanır.

## İstatistikler
**Threads istatistikleri** iş akışı her sabah 07:27'de çalışır ve `insights.md`'yi günceller:
- Son 7 gün ile önceki 7 günün karşılaştırması (ortalama/medyan görüntülenme, yorum, yeni takipçi)
- **Link tıklamaları:** App Store linkine planın başından beri kaç kez tıklandığı (Threads API `clicks` metriği) ve son 7 gün
- **Hesap görüntülenmeleri:** hesap düzeyindeki görüntülenme; kendi gönderilerimizden çok yüksekse farkı büyük olasılıkla yanıtlarımız getiriyor
- Biçime (metin, görsel, video, carousel, anket, link), seriye, saate ve güne göre tablolar; en çok görülen ve en çok yorum alan 10 gönderi
- `insights.json`: ham veri, günlük takipçi, günlük tıklama toplamı

Bunun için token'da `threads_manage_insights` izni olmalı (var). İzin yoksa iş akışı yalnızca uyarı verir, paylaşımlar etkilenmez. Hemen denemek için: **Actions › Threads istatistikleri › Run workflow**.

## Sohbetlere katılma (yanıt sistemi)
LINGOOF hesabı, Threads'te dil öğrenmeyi konuşan insanların gönderilerine faydalı yanıtlar yazar. Amaç satış yapmak değil. İşe yarayan bir öneri, gönderiyi yazan kişiyi de okuyanları da profile getirir. Veriler bunun hesabın en büyük erişim kaynağı olduğunu gösteriyor: hesap düzeyindeki görüntülenme, kendi gönderilerimizin görüntülenmesinin birkaç katı.

**Şu an çalışan yol (tarayıcı):** Claude'un **LINGOOF Threads yanıtları** görevi her gün 11:34'te, bilgisayarındaki Claude masaüstü uygulamasının yerleşik tarayıcısında @lingoof.app oturumuyla çalışır: anahtar kelimelerle son Türkçe dil öğrenme gönderilerini bulur, günde en fazla 10 faydalı yanıt yazar ve yanıtlarımıza gelen cevapları yanıtlar. Bilgisayar kapalıysa o günün turu yapılmaz.

**Bekleyen iyileştirme:** görevi günde iki tura (11:34 ve 21:34) çıkaran, önce kendi gönderilerimize gelen yorumları yanıtlayan (İngilizce cümle yazanlara Türkçe açıklamalı nazik düzeltme dahil) ve yeni yanıtların yarısını popüler gönderilere yazan güncelleme hazır: `yanitlar/YANIT_GOREVI_V2.md`. Zamanlanmış görevi değiştirmek senin onayını gerektiriyor; Claude'a "LINGOOF Threads yanıt görevini V2'ye güncelle" yazman yeterli.

**API yolu (Meta onayı bekliyor):** Aşağıdaki sistem, Meta `threads_keyword_search` iznini onaylarsa tarayıcı olmadan bulutta çalışır.

- Claude'un **LINGOOF yanıt turu** görevi bir arama başlatır. `yanitlar/ayar.json` içindeki anahtar kelimelerle ("İngilizce kursu", "YDS", "dil öğrenmek"...) son 36 saatte paylaşılmış gönderiler bulunur.
- Claude adayları okur ve yalnızca gerçekten katkı sunabileceği gönderilere `yanitlar/YAZIM_REHBERI.md`'deki kurallara göre yanıt yazar. Reklam, hassas konu, konu dışı gönderiler ve çocuk yaşta görünen yazarların gönderileri geçilir.
- Yanıtlar 1–2,5 dakika arayla LINGOOF hesabından gider.
- Sınırlar: günde en fazla 10 yanıt ve aynı kişiye 14 günde en fazla bir yanıt. Yanıtlarda link, hashtag, @etiket ya da "indir" çağrısı olmaz. Bu kurallar kodda da denetlenir.
- Kayıtlar: yazılan yanıtlar `yanitlar/kararlar.json`, gönderilenler ve linkleri `yanitlar/gonderilen.json`, son aramanın özeti `yanitlar/durum.json` dosyasında durur. Başkalarının gönderi metinleri herkese açık bu depoda düz metin olarak durmasın diye `yanitlar/adaylar.enc.json` şifreli tutulur. Bu dosyayı yalnızca Claude'un görevi açabilir.

### Kurulum (bir kerelik)
Threads, bir uygulamanın başkalarının gönderilerini aramasına ve onlara yanıt vermesine ancak Meta'nın uygulama incelemesinden (App Review) sonra izin veriyor. Onay gelene kadar arama yalnızca LINGOOF'un kendi gönderilerini döndürür. Sistem bu sürede hiçbir şey göndermez ve Claude'un her turu "onay bekleniyor" diye biter.

1. [developers.facebook.com](https://developers.facebook.com) › uygulaman › **Use cases › Access the Threads API › Customize** bölümünde `threads_keyword_search` ve `threads_manage_replies` izinlerini ekle. Mevcut izinler kalsın.
2. Kurulumun 2. adımındaki gibi **yeni token üret** ve `THREADS_TOKEN` secret'ını güncelle.
3. **App Review › Permissions and Features** bölümünden `threads_keyword_search` ve `threads_manage_replies` için **Advanced Access** iste. Başvuru formuna yapıştırılacak açıklamalar `yanitlar/META_INCELEME.md` dosyasında. Meta işletme doğrulaması ya da ek bilgi isteyebilir.
4. Onay gelince başka bir şey yapmana gerek yok, bir sonraki turda yanıtlar kendiliğinden başlar. `yanitlar/durum.json` hâlâ "henüz onaylamamış" diyorsa token'ı bir kez daha üretip secret'ı güncelle.

### Ayarlar ve durdurma
- `yanitlar/ayar.json`: anahtar kelimeler, günlük sınır (`gunluk_limit`), aynı kişiye tekrar yanıt aralığı (`yazar_araligi_gun`) ve gönderiyi baştan eleyen kelimeler (`yasak_kelimeler`).
- Yanıtların tonu ve kuralları `yanitlar/YAZIM_REHBERI.md` dosyasında. Burada yapılan değişiklik bir sonraki turdan itibaren geçerli olur.
- Durdurmak için `yanitlar/ayar.json` içinde `"acik": false` yap ya da Claude uygulamasında **LINGOOF yanıt turu** görevini duraklat.
- Deneme: **Actions › Threads yanıt araması › Run workflow** ("Deneme" işaretli kalsın). Kayıtta aramanın bulduğu gönderiler ve hangisinin neden elendiği görünür. Hiçbir şey kaydedilmez.

## Kesin saat için dış tetikleyici (önerilir)
GitHub'ın kendi zamanlayıcısı garanti vermez. Yoğun günlerde çalıştırmaları saatlerce geciktirebilir ya da hiç başlatmayabilir; 19 Ekim'de 8 çalıştırmadan yalnızca 2'si başladı. Gönderilerin tam saatinde gitmesi için ücretsiz [cron-job.org](https://cron-job.org) botu tetikleyebilir:

1. **GitHub token'ı:** GitHub › Settings › Developer settings › Personal access tokens › **Fine-grained tokens** › **Generate new token**.
   - Repository access: **Only select repositories** › `lingoof-threads-bot`
   - Permissions › Repository permissions › **Actions: Read and write** (başka izin gerekmez)
   - Expiration: 1 Ocak 2027 ya da sonrası (plan 31 Aralık'ta bitiyor)
   - Token'ı kopyala, yalnızca bir kez gösterilir.
2. **cron-job.org:** ücretsiz hesap aç › **Create cronjob**.
   - URL: `https://api.github.com/repos/mbvkfhzc2f-eng/lingoof-threads-bot/actions/workflows/post.yml/dispatches`
   - Zamanlama (Custom): saatler **9, 11, 13, 18, 21**; dakikalar **1, 6, 31**; saat dilimi **Europe/Istanbul**. 6. dakika, 10 Kasım'daki 09:05 anma paylaşımı içindir; 31. dakika yedektir.
   - Gelişmiş ayarlarda istek yöntemi **POST**. Header olarak şunları ekle:
     - `Accept: application/vnd.github+json`
     - `Authorization: Bearer <kopyaladığın token>`
     - `X-GitHub-Api-Version: 2022-11-28`
   - İstek gövdesi (request body): `{"ref":"main","inputs":{"dry_run":"false"}}`
3. **Test run** yap; yanıt kodu **204** olmalı ve **Actions** sekmesinde yeni bir "Threads paylaşımı" çalışması görünmeli. O an paylaşılacak gönderi yoksa kayıtta "paylaşılacak bir şey yok" yazar, bu normal.

GitHub'ın 15 dakikalık yoklaması yedek olarak çalışmaya devam eder. İkisi aynı anda çalışsa bile bir gönderi iki kez gitmez.

## Token'ın canlı kalması (GH_PAT gerekmez)
Uzun ömürlü Threads token'ı 60 gün geçerli; her yenilemede Meta yeni bir token verir ve süre yeniden 60 gün olur. **Threads token yenileme** iş akışı üç günde bir yeni token'ı alır, `THREADS_TOKEN` secret'ından türetilen anahtarla şifreler (AES-256) ve GitHub Actions önbelleğine yazar (`token_store.py`). Paylaşım, istatistik ve yanıt iş akışları önce önbellekteki bu güncel token'ı açar; yoksa secret'ı kullanır. Önbellek depoda görünmez, anahtarsız açılamaz, token'lar günlükte hep maskelidir.

- İlk yenileme 28 Kasım'da yapıldı: token 59 gün geçerli ve her üç günde bir uzuyor. 17 Aralık'taki eski bitiş tarihi artık sorun değil.
- GH_PAT eklemen gerekmiyor. Eklersen secret da ayrıca güncellenir.
- Token bir gün tamamen geçersiz olursa (ör. şifre değişikliği, uygulama izni kaldırma) yenileme adımı hata verir ve GitHub e-posta atar; o zaman Kurulum › 2. adımla yeni token üretip `THREADS_TOKEN`'ı güncellemen yeterli.
