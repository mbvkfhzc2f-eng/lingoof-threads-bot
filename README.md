# LINGOOF Threads botu

LINGOOF'un Threads planını kendi kendine paylaşır: **18 Ekim (açılış) – 31 Aralık 2026**, her gün **09:00, 13:00, 18:00 ve 21:00**'da (Türkiye saati) o saate düşen gönderi resmi Threads API ile atılır. Bilgisayarının açık olması gerekmez; bot GitHub'ın sunucularında ücretsiz çalışır.

- 295 gönderi: metinler, anketler, görselli gönderiler, özel günler (29 Ekim, 10 Kasım, Öğretmenler Günü, yılbaşı...) ve yanıtlar
- Her 7 gönderiden birinde App Store linki: `https://apps.apple.com/tr/app/lingoof/id6816741034`
- Aynı gönderi iki kez gitmez. Saati 3 saatten fazla geçen gönderi atlanır, plan takvimdeki tarihlerden şaşmaz. Bot geç kurulsa bile hesabın ilk gönderisi tanışma gönderisi olur. 31 Aralık'tan sonra kendiliğinden durur.
- Token ayın 1'inde ve 15'inde otomatik yenilenir.

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
- Bir çalışma hata verirse GitHub sana e-posta atar.

## İsteğe bağlı: GH_PAT
Meta yenilemede aynı token'ın süresini uzatır. Yeni bir token verirse botun onu kendisi kaydedebilmesi için GitHub'da sadece bu depoya yetkili bir token oluştur. GitHub › Settings › Developer settings › Fine-grained tokens yolunu izle, izin olarak Secrets: Read and write ver. Bunu `GH_PAT` adıyla secret olarak ekle. Eklemezsen ve token değişirse bot sana hata e-postası gönderir.
