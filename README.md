# LINGOOF Threads botu

LINGOOF'un Threads planını kendi kendine paylaşır: **18 Ekim (açılış) – 31 Aralık 2026**, her gün **09:00, 13:00, 18:00 ve 21:00**'da (Türkiye saati) o saate düşen gönderi resmi Threads API ile atılır. Bilgisayarının açık olması gerekmez; bot GitHub'ın sunucularında ücretsiz çalışır.

- 295 gönderi: metinler, anketler, görselli gönderiler, özel günler (29 Ekim, 10 Kasım, Öğretmenler Günü, yılbaşı...) ve yanıtlar
- Her 7 gönderiden birinde App Store linki: `https://apps.apple.com/tr/app/lingoof/id6816741034`
- Aynı gönderi iki kez gitmez. Saati 3 saatten fazla geçen gönderi atlanır, plan takvimdeki tarihlerden şaşmaz. Bot geç kurulsa bile hesabın ilk gönderisi tanışma gönderisi olur. 31 Aralık'tan sonra kendiliğinden durur.
- GitHub botu her 15 dakikada bir yoklar; saati gelmiş gönderi varsa paylaşılır. GitHub'ın zamanlayıcısı garanti vermediği için dakikası dakikasına paylaşım için aşağıdaki **dış tetikleyici** önerilir.
- Bir anket oluşturulamazsa gönderi kaybolmaz: seçenekler metne yazılıp gönderi yine paylaşılır.
- Token üç günde bir otomatik yenilenir.

## Kurulum (bir kerelik, ~15 dakika)

### 1. GitHub deposu
Bu klasörü **herkese açık (public)** bir GitHub deposuna koy. Görsellerin Threads'e gidebilmesi için depo herkese açık olmalı. Depoda gizli bir bilgi yok, token ayrı ve şifreli saklanıyor.

### 2. Threads erişim token'ı
1. [developers.facebook.com](https://developers.facebook.com) › **My Apps** › **Create App**. Kullanım durumu olarak **Access the Threads API**'yi seç.
2. Uygulamanın panelinde **App roles › Roles › Add People › Threads Tester** yolunu izle ve LINGOOF'un Threads kullanıcı adını ekle.
3. Threads'te **Ayarlar › Hesap › Web sitesi izinleri › Davetler** bölümünden daveti kabul et.
4. Panele dön: **Use cases › Access the Threads API › Customize**. Burada `threads_basic` ve `threads_content_publish` izinlerinin ekli olduğundan emin ol.
5. Aynı yerde **Settings** sekmesinin altındaki **Generate Access Token** düğmesine bas ve token'ı kopyala. Token `TH` ile başlar.

### 3. Token'ı depoya ekle
Deponun **Settings › Secrets and variables › Actions › New repository secret** bölümüne git. Adı `THREADS_TOKEN`, değeri kopyaladığın token olsun.

### Kontrol
**Actions** sekmesinde **Threads paylaşımı › Run workflow** düğmesine bas. "Deneme" işaretli kalsın. Kayıtta hesap adını ve sıradaki gönderiyi görürsen her şey hazır. İlk gerçek paylaşım bir sonraki paylaşım saatinde gider.

## Ayarlar
- `posts.json`: her gönderinin tarihi, saati ve metni burada. GitHub üzerinden düzenleyebilirsin; `{LINK}` yazan yere App Store linki girer.
- Durdurmak için: **Actions › Threads paylaşımı › ⋯ › Disable workflow**. Tekrar açınca o günün tarihinden devam eder.
- Bir çalışma hata verirse GitHub sana e-posta atar. Son hatanın metni `state.json` içindeki `last_error` alanında da durur. Aynı gönderi 3 kez hata verirse atlanır.

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

## İsteğe bağlı: GH_PAT
Meta yenilemede aynı token'ın süresini uzatır. Yeni bir token verirse botun onu kendisi kaydedebilmesi için GitHub'da sadece bu depoya yetkili bir token oluştur. GitHub › Settings › Developer settings › Fine-grained tokens yolunu izle, izin olarak Secrets: Read and write ver. Bunu `GH_PAT` adıyla secret olarak ekle. Eklemezsen ve token değişirse bot sana hata e-postası gönderir.
