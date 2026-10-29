# Meta App Review başvurusu

Yanıt sisteminin çalışması için Meta'nın iki izne **Advanced Access** vermesi gerekiyor. Başvuruyu [developers.facebook.com](https://developers.facebook.com) › uygulaman › **App Review › Permissions and Features** bölümünden yapabilirsin. Formda her izin için "bu izni nasıl kullanacaksınız" sorusu çıkar. Aşağıdaki İngilizce metinleri olduğu gibi yapıştırabilirsin. Hepsi sistemin gerçekte yaptığını anlatıyor.

## threads_keyword_search

> LINGOOF is an English speaking-practice app for Turkish learners. We use keyword search to find recent public Threads posts in Turkish where people talk about learning English (for example "İngilizce kursu", "YDS" or "dil öğrenmek"), so that our official LINGOOF account can join those conversations with a helpful study tip. Searches run 4 times a day over a fixed list of about 12 keywords, fewer than 100 queries per day. Results are used only to choose which posts to reply to. We do not build profiles and we do not sell or share the data. Candidate posts are stored only in encrypted form and are replaced on every search. For posts we reply to, we keep the post ID, link and username (so that we never reply to the same person more than once every 14 days) together with our own reply.

## threads_manage_replies

> We use this permission to publish replies from our official LINGOOF account (reply_to_id) under public posts found with keyword search, and under our own posts as part of our daily content schedule. Every reply is written for that specific post and contains no links, hashtags or mentions. We publish at most 10 such replies per day and at most one reply per person every 14 days.

## Ekran kaydı
Meta bir ekran kaydı isterse kısa bir video yeterli olur:

1. Meta panelinde uygulamanın izinler sayfasını göster.
2. GitHub'da **Actions › Threads yanıt araması › Run workflow** çalıştır ("Deneme" işaretli kalsın). Çalışmanın kaydında arama sonuçları görünür. Onaydan önce sonuçlar yalnızca LINGOOF'un kendi gönderileridir, bu da izni gösterir.
3. Threads'te LINGOOF'un kendi gönderilerinden birinin altındaki yanıtı göster (paylaşım botu her gün bu şekilde yanıt ekliyor).
