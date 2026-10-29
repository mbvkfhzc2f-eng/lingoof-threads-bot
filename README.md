# LINGOOF Threads botu

LINGOOF'un Threads planını kendi kendine paylaşır: **18 Ekim (açılış) – 31 Aralık 2026**, her gün **09:00, 11:00, 13:00, 18:00 ve 21:00**'da (Türkiye saati; 11:00 "Günün Kelimesi" 28 Ekim'de başlıyor) o saate düşen gönderi resmi Threads API ile atılır. Bilgisayarının açık olması gerekmez; bot GitHub'ın sunucularında ücretsiz çalışır.

- 358 gönderi: metinler, anketler, görselli gönderiler, özel günler (29 Ekim, 10 Kasım, Öğretmenler Günü, yılbaşı...) ve yanıtlar
- Her 7 gönderiden birinde App Store linki: `https://apps.apple.com/tr/app/lingoof/id6816741034`
- Aynı gönderi iki kez gitmez. Saati 4 saatten fazla geçen gönderi atlanır, plan takvimdeki tarihlerden şaşmaz. Bot geç kurulsa bile hesabın ilk gönderisi tanışma gönderisi olur. 31 Aralık'tan sonra kendiliğinden durur.
- GitHub botu her 15 dakikada bir yoklar; saati gelmiş gönderi varsa paylaşılır. GitHub'ın zamanlayıcısı garanti vermediği için dakikası dakikasına paylaşım için aşağıdaki **dış tetikleyici** önerilir.
- Bir anket oluşturulamazsa gönderi kaybolmaz: seçenekler metne yazılıp gönderi yine paylaşılır.
- Token üç günde bir otomatik yenilenir.
- Sohbetlere katılma: dil öğrenmeyi konuşan gönderilere günde en fazla 10 faydalı yanıt. Meta onayı gerekiyor, ayrıntılar aşağıda.

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
- `posts.json`: her gönderinin tarihi, saati ve metni burada. GitHub üzerinden düzenleyebilirsin; `{LINK}` yazan yere App Store linki girer.
  - `topic`: Threads konu etiketi (ör. "İngilizce", "İngilizce Öğren"). Gönderiyi o konunun akışında da gösterir. Etiket reddedilirse gönderi etiketsiz gider, hiçbir zaman takılmaz.
  - `poll`: 2–4 seçenekli anket (her seçenek en fazla 25 bayt). Anket oluşturulamazsa seçenekler metne yazılıp paylaşılır.
  - `img` / `alt`: `img/` klasöründeki görsel ve görme engelliler için açıklaması. `card_*.jpg` dosyaları kaydedilmeye uygun LINGOOF bilgi kartları.
- Durdurmak için: **Actions › Threads paylaşımı › ⋯ › Disable workflow**. Tekrar açınca o günün tarihinden devam eder.
- Bir çalışma hata verirse GitHub sana e-posta atar. Son hatanın metni `state.json` içindeki `last_error` alanında da durur. Aynı gönderi 3 kez hata verirse atlanır.

## İstatistikler
**Threads istatistikleri** iş akışı her sabah 07:27'de paylaşılan her gönderinin görüntülenme, beğeni, yorum, repost, alıntı ve paylaşım sayılarını ve takipçi sayısını çeker:
- `insights.md`: seriye ve saate göre ortalamalar, en çok etkileşim alan 10 gönderi. Hangi serinin işe yaradığını görüp planı buna göre ayarlamak için.
- `insights.json`: ham veri ve günlük takipçi sayısı.

Bunun için token'da `threads_manage_insights` izni olmalı: 2. adımın 4. maddesindeki gibi izni ekle, 5. maddedeki gibi **yeni token üret** ve `THREADS_TOKEN` secret'ını yeni token'la güncelle. İzin yoksa iş akışı yalnızca uyarı verir, paylaşımlar etkilenmez. Hemen denemek için: **Actions › Threads istatistikleri › Run workflow**.

## Sohbetlere katılma (yanıt sistemi)
LINGOOF hesabı, Threads'te dil öğrenmeyi konuşan insanların gönderilerine faydalı yanıtlar yazar. Amaç satış yapmak değil. İşe yarayan bir öneri, gönderiyi yazan kişiyi de okuyanları da profile getirir.

- Günde 4 kez (10:37, 13:37, 15:37 ve 21:37) Claude'un **LINGOOF yanıt turu** görevi bir arama başlatır. `yanitlar/ayar.json` içindeki anahtar kelimelerle ("İngilizce kursu", "YDS", "dil öğrenmek"...) son 36 saatte paylaşılmış gönderiler bulunur.
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
   - Zamanlama (Custom): saatler **9, 13, 18, 21**; dakikalar **1, 6, 31**; saat dilimi **Europe/Istanbul**. 6. dakika, 10 Kasım'daki 09:05 anma paylaşımı içindir; 31. dakika yedektir.
   - Gelişmiş ayarlarda istek yöntemi **POST**. Header olarak şunları ekle:
     - `Accept: application/vnd.github+json`
     - `Authorization: Bearer <kopyaladığın token>`
     - `X-GitHub-Api-Version: 2022-11-28`
   - İstek gövdesi (request body): `{"ref":"main","inputs":{"dry_run":"false"}}`
3. **Test run** yap; yanıt kodu **204** olmalı ve **Actions** sekmesinde yeni bir "Threads paylaşımı" çalışması görünmeli. O an paylaşılacak gönderi yoksa kayıtta "paylaşılacak bir şey yok" yazar, bu normal.

GitHub'ın 15 dakikalık yoklaması yedek olarak çalışmaya devam eder. İkisi aynı anda çalışsa bile bir gönderi iki kez gitmez.

## Gerekli: GH_PAT (token'ın aralık sonuna kadar geçerli kalması için)
Threads token'ı 18 Ekim'de alındı ve yaklaşık 17 Aralık'ta sona erer. Plan 31 Aralık'a kadar sürdüğü için token'ın yenilenmesi gerekiyor. Meta her yenilemede yeni bir token veriyor ve botun bunu `THREADS_TOKEN` olarak kaydedebilmesi için GitHub'da bir izin token'ı lazım:

1. GitHub › Settings › Developer settings › Personal access tokens › **Fine-grained tokens** › **Generate new token**
   - Repository access: **Only select repositories** › `lingoof-threads-bot`
   - Permissions › Repository permissions › **Secrets: Read and write** (başka izin gerekmez)
   - Expiration: 1 Ocak 2027 ya da sonrası
2. Oluşan token'ı kopyala ve deponun **Settings › Secrets and variables › Actions › New repository secret** bölümüne `GH_PAT` adıyla ekle.

Bundan sonra token üç günde bir kendiliğinden yenilenir. GH_PAT eklenene kadar yenileme adımı Actions'ta yalnızca uyarı gösterir. 1 Aralık'tan itibaren hata verip e-posta gönderir ki token sona ermeden fark edilsin. GH_PAT eklemek istemezsen 1 Aralık civarında 2. adımdaki gibi yeni bir Threads token'ı üretip `THREADS_TOKEN`'ı güncellemen de yeterli.
