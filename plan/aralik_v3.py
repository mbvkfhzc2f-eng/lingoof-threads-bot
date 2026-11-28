#!/usr/bin/env python3
"""Aralık planını Threads'te daha çok erişim, sohbet ve indirme için yeniden düzenler (28 Kasım 2026).

Neden: 179 gönderinin verisi (insights.md) zayıf serilerin (11:00 Günün Kelimesi, 13:00 anket ve öğle testleri) ve
ana metinde link olan gönderilerin çok az görüldüğünü gösterdi (link: medyan 9 görüntülenme, metin: 24, görsel: 44).
Threads'te sıralamayı en çok yanıtlar ve sohbet belirliyor; link içeren gönderiler daha az etkileşim aldığı için geri
kalıyor (Meta 2025 ortasından beri linki bilerek cezalandırmadığını söylüyor). Bu yüzden:

- 11:00 Günün Kelimesi ve 13:00 anket/öğle testi/hata avı/sen olsan serileri kalkar.
- 13:00: her gün Goof 2.0 (build 140) videosu; ana metin kendi başına da öğretir, cevap çoğu zaman spoiler'da saklı.
- Salı, perşembe, cumartesi 11:00: V3 carousel (Instagram'daki stüdyo çıktıları; yapay zekâ aracı yok).
- Haftanın özetleri eski kart yerine V3 kartla ya da carousel'la gider; eski Goof'lu ve yapay zekâ görselleri çıkar.
- Link ana metinde hiç yok; günde en fazla bir gönderinin ilk yorumunda, önizleme kartıyla.
- "Yaptıysan yorumlara ✅" gibi düşük emekli yorum istekleri gerçek sorularla değişir; "5 dakika" vaadi geçmez.

Kullanım: python3 plan/aralik_v3.py  (posts.json'u yerinde günceller; paylaşılmış gönderilere dokunmaz)
"""
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IG_POSTS = Path('/home/claude/lingoof-instagram-bot/posts.json')       # carousel görsel açıklamaları için (varsa)
START = '2026-11-29'

posts = json.loads((ROOT / 'posts.json').read_text(encoding='utf-8'))
state = json.loads((ROOT / 'state.json').read_text(encoding='utf-8'))
done = set(state['posted']) | {str(n) for n in state['skipped']}
ig_alts = {}
if IG_POSTS.exists():
    for p in json.loads(IG_POSTS.read_text(encoding='utf-8')):
        if p.get('src_id') and p.get('alt_texts'):
            ig_alts[p['src_id']] = p['alt_texts']

CTA = {
    'prova': "Bu sahneyi LINGOOF'ta Goof'la sesli prova edebilirsin: Goof Talk AI'da sen konuşursun, Goof cevap verir 🎙️ Ücretsiz indir: {LINK}",
    'hata': "LINGOOF'ta hata yap, Goof nedenini Türkçe açıklasın. A1'den C1'e dersler, ilk dersler ücretsiz 💜 {LINK}",
    'sik': "Her şık için Türkçe açıklama ve Goof'la sesli prova: LINGOOF'u ücretsiz indir 👉 {LINK}",
    'yurt': "Erasmus+, Work & Travel ve iş görüşmesi yolları LINGOOF'ta: önce hazırlan, sonra Goof'la prova yap 💜 {LINK}",
}

# ---------- 13:00 Goof 2.0 videoları (Instagram'da paylaşıldıktan sonraki gün) ----------
# (tarih, id, konu, metin, spoiler'lar, cta türü, video açıklaması)
REELS = [
 ('2026-11-29', 'r01-pov-whatsup', 'İngilizce Konuşma',
  "Erasmus'ta ilk gün. Ev arkadaşın Emma kapıdan giriyor: “What's up?”\n\nÇoğumuzun refleksi: “I'm fine, thank you. And you?”\n\nAma “What's up?” nasılsın demek değil, “ne var ne yok” demek. Doğal cevap:\nNot much! Just unpacking. You?\n\nSana ilk “What's up?” dendiğinde ne demiştin? 😅",
  ['Not much! Just unpacking. You?'], 'yurt', "Goof'lu animasyon: Emma “What's up?” diyor; “I'm fine, thank you” yerine “Not much! Just unpacking. You?” öneriliyor."),
 ('2026-11-30', 'r02-nasil-kolaygelsin', 'İngilizce Konuşma',
  "“Kolay gelsin”i İngilizceye nasıl çevirirsin?\n\n“Let it come easy!” dersen kimse anlamaz 😄 İngilizcede tek karşılığı yok, duruma göre değişiyor:\n\nÇalışan bir arkadaşa: Don't work too hard!\nYeni işe başlayana: Good luck with it!\nZorlanan birine: Hang in there!\n\nBu hafta en çok hangisine ihtiyacın var?",
  [], None, "Goof'lu animasyon: “Kolay gelsin” için üç doğal İngilizce karşılık."),
 ('2026-12-01', 'r03-hata-agree', 'İngilizce',
  "Bu cümlede 1 hata var:\n“I am agree with you.”\n\nBulabildin mi? Önce doğrusunu yorumlara yaz, sonra kontrol et.\nDoğrusu: I agree with you. Agree zaten fiil, önüne am/is/are gelmez.\n\nTürkçedeki “katılıyorum” kalıbı yüzünden çok yapılıyor. Sen de böyle diyor muydun?",
  ['I agree with you. Agree zaten fiil, önüne am/is/are gelmez.'], 'hata', "Goof'lu animasyon: “I am agree” hatası düzeltilip “I agree with you” oluyor."),
 ('2026-12-02', 'r04-quiz-bored', 'İngilizce',
  "Dersten sonra arkadaşına yazıyorsun: “Çok sıkıldım.”\n\nA) I'm bored.\nB) I'm boring.\n\nHangisi? Cevap: A. “I'm boring” dersen “Ben sıkıcı biriyim” demiş olursun.\n\nKural kısa: -ed hisseden, -ing hissettiren. bored/boring, tired/tiring, interested/interesting. Bu hafta neye “so boring” dedin?",
  ["A. “I'm boring” dersen “Ben sıkıcı biriyim” demiş olursun."], None, "Goof'lu mini test: “I'm bored” mu “I'm boring” mi?"),
 ('2026-12-03', 'r05-urun-evening', 'İngilizce',
  "Uygulamadan bir sahne. Boşluğu doldur:\n“I relax ___ the evening.”\nin / at / on\n\nSeçtin mi? Cevap: in. Saatte at, günde on, günün bölümünde in: in the morning, in the evening. Ama at night!\n\nLINGOOF'ta yanlış şıkkı seçince Goof nedenini Türkçe açıklıyor. Hata yap, düzelt, devam et.",
  ['in. Saatte at, günde on, günün bölümünde in: in the morning, in the evening. Ama at night!'], 'sik', "LINGOOF uygulamasından sahne: yanlış şık seçilince Goof Türkçe açıklıyor."),
 ('2026-12-04', 'r06-vs-veda', 'İngilizce Konuşma',
  "Vedalaşırken Türk usulü vs native:\n\n“Görüşürüz” → We will see! ❌ See you! ✅\n“Kendine iyi bak” → Look at yourself! ❌ Take care! ✅\n“Sağ ol” → Be alive! ❌ Thanks! ✅\n\n“Look at yourself” dersen karşındaki aynaya bakmaya gider 😄 Hangisini daha önce duymuştun?",
  [], None, "Goof'lu animasyon: vedalaşmada kelimesi kelimesine çeviriler ve doğal karşılıkları."),
 ('2026-12-05', 'r07-pov-bill', 'Seyahat İngilizcesi',
  "Londra'da bir restorandasın. Garson soruyor: “Anything else?”\n\nHesabı isteyeceksin. “Give me the account” mı dersin?\n\nDoğal hali: No, thanks. Could we get the bill? Hesap account değil: İngiltere'de the bill, ABD'de the check.\n\nYurt dışındaki ilk restoran deneyimin nasıldı?",
  ["No, thanks. Could we get the bill? Hesap account değil: İngiltere'de the bill, ABD'de the check."], None, "Goof'lu sahne: garsona “Could we get the bill?” demek."),
 ('2026-12-06', 'r08-hata-mistake', 'İngilizce',
  "Hata yaparken hata yapma:\n“I did a mistake.”\n\nDoğrusu ne? Cevap: I made a mistake. Hata yapmak make a mistake, do değil.\n\nmake ile gidenler: make a decision, make friends, make a plan. Burada hata yapmak serbest: en son hangi İngilizce hatanı fark ettin? 💜",
  ['I made a mistake. Hata yapmak make a mistake, do değil.'], 'hata', "Goof'lu animasyon: “I did a mistake” düzeltilip “I made a mistake” oluyor."),
 ('2026-12-07', 'r09-nasil-gecmisolsun', 'İngilizce Konuşma',
  "“Geçmiş olsun” İngilizcede nasıl denir?\n\n“Let it be past!” değil 😄 Duruma göre:\nHasta birine: Get well soon!\nMesajla yazarken: Hope you feel better!\nKötü bir habere: Sorry to hear that!\n\nGrip mevsimindeyiz. Bu hafta kime “Get well soon!” yazman gerekti?",
  [], None, "Goof'lu animasyon: “Geçmiş olsun” için üç İngilizce karşılık."),
 ('2026-12-08', 'r10-pov-alright', 'İngilizce Konuşma',
  "İngiliz arkadaşın seni görünce soruyor: “You alright?”\n\nHasta mı görünüyorsun? Hayır, İngiltere'de bu sadece bir selam.\nDoğal cevap: Yeah, good thanks! You?\n\n“No, I'm not sick!” dersen ikiniz de şaşırırsınız 😄 Sen hangi selamı ilk duyduğunda yanlış anlamıştın?",
  [], 'prova', "Goof'lu sahne: “You alright?” bir selamdır, doğal cevabı “Yeah, good thanks! You?”"),
 ('2026-12-09', 'r11-quiz-salt', 'İngilizce',
  "Yemekte tuzu istiyorsun. Hangisi daha kibar?\n\nA) Give me the salt.\nB) Could you pass the salt?\n\nCevap: B. Emir kipi İngilizcede sert duyulur, ricada Could you…? kullanılır.\n\nTürkçede “Tuzu versene” gayet normal. Sence İngilizcede neden kaba kaçıyor?",
  ['B. Emir kipi İngilizcede sert duyulur, ricada Could you…? kullanılır.'], None, "Goof'lu mini test: hangisi daha kibar, “Give me the salt” mı “Could you pass the salt?” mı?"),
 ('2026-12-10', 'r12-hata-age', 'İngilizce',
  "Yaşını söylerken en sık yapılan hata:\n“I have 25 years old.”\n\nDoğrusu? Cevap: I am 25 years old. Ya da kısaca I'm 25. Yaş have ile değil be ile söylenir.\n\nTürkçedeki “25 yaşım var” mantığı bizi have'e itiyor. Sen kaç yaşında İngilizceye başlamıştın?",
  ["I am 25 years old. Ya da kısaca I'm 25. Yaş have ile değil be ile söylenir."], 'hata', "Goof'lu animasyon: “I have 25 years old” düzeltilip “I am 25 years old” oluyor."),
 ('2026-12-11', 'r13-vs-sasirma', 'İngilizce Konuşma',
  "Şaşırınca ne dersin?\n\n“Hadi ya!” → Come on ya! ❌ No way! ✅\n“Yok artık!” → No more! ❌ You're kidding! ✅\n“Aynen!” → Same same! ❌ Totally! ✅\n\nBizim favorimiz “No way!” 😄 Senin en çok kullandığın şaşırma kalıbı hangisi?",
  [], None, "Goof'lu animasyon: şaşırınca kullanılan Türkçe kalıplar ve doğal İngilizce karşılıkları."),
 ('2026-12-12', 'r14-nasil-elinesaglik', 'İngilizce Konuşma',
  "“Eline sağlık” nasıl denir?\n\n“Health to your hands!” dersen yemeği yapan ellerine bakar 😄 İngilizcede yemeği övmek yeter:\n\nYemeği yapana: This is delicious!\nİltifat ederken: You're a great cook!\nDavet edene: Thanks for dinner!\n\nSenin evde en çok “eline sağlık” denen yemek hangisi?",
  [], None, "Goof'lu animasyon: “Eline sağlık” için üç İngilizce karşılık."),
 ('2026-12-13', 'r15-pov-blessyou', 'İngilizce Konuşma',
  "Derste biri hapşırdı: “Achoo!”\n\nNe dersin? “Live long!” mı?\n\nCevap: Bless you! Çok yaşa'nın karşılığı bu. Hapşıran da Thanks! der.\n\nPeki sen “Çok yaşa”ya ne cevap verirsin: “Sen de gör” mü, “Hep beraber” mi? 😄",
  ["Bless you! Çok yaşa'nın karşılığı bu. Hapşıran da Thanks! der."], 'prova', "Goof'lu sahne: biri hapşırınca “Bless you!” denir."),
 ('2026-12-14', 'r16-urun-drinks', 'İngilizce',
  "Uygulamadan bir an. Boşluğu doldur:\n“She ___ coffee every morning.”\ndrink / drinks\n\nCevap: drinks. He, she, it ile geniş zamanda fiil -s alır.\n\nLINGOOF'ta buraya drink yazınca Goof “Az kaldı!” der ve nedenini Türkçe açıklar. Sen bu -s'i en çok nerede unutuyorsun?",
  ['drinks. He, she, it ile geniş zamanda fiil -s alır.'], 'hata', "LINGOOF uygulamasından sahne: “drink” yerine “drinks”; Goof “Az kaldı!” diyor."),
 ('2026-12-15', 'r17-hata-light', 'İngilizce',
  "Hava karardı, arkadaşına diyorsun:\n“Can you open the light?”\n\nDoğrusu? Cevap: Can you turn on the light? Işık ve cihazlarda turn on / turn off denir.\n\nTV, telefon, klima: hepsi turn on. Türkçedeki “ışığı aç” yüzünden çok yapılan bir hata. Sen de yapıyor muydun?",
  ['Can you turn on the light? Işık ve cihazlarda turn on / turn off denir.'], None, "Goof'lu animasyon: “open the light” düzeltilip “turn on the light” oluyor."),
 ('2026-12-16', 'r18-quiz-latte', 'İngilizce Konuşma',
  "Kafede sıradasın. Hangisi daha doğal?\n\nA) I want a latte.\nB) Can I get a latte?\n\nCevap: B. I want talepkâr duyulur; siparişte Can I get…? ya da I'd like… dersin.\n\nSenin kahve siparişin ne? İngilizce yaz, bakalım ☕",
  ["B. I want talepkâr duyulur; siparişte Can I get…? ya da I'd like… dersin."], None, "Goof'lu mini test: kafede “I want a latte” mı “Can I get a latte?” mı?"),
 ('2026-12-17', 'r19-nasil-afiyet', 'İngilizce Konuşma',
  "“Afiyet olsun” nasıl denir?\n\n“Be healthy!” değil 😄 Duruma göre:\nGarson ya da ev sahibi: Enjoy your meal!\nKısa ve samimi: Enjoy!\nYemeğe başlarken: Dig in!\n\n“Dig in” kelime anlamıyla “kaz!” ama sofrada “Haydi başlayın!” demek. Sen hangisini kullanırdın?",
  [], None, "Goof'lu animasyon: “Afiyet olsun” için üç İngilizce karşılık."),
 ('2026-12-18', 'r20-hata-explain', 'İngilizce',
  "3 saniyede hatayı bul:\n“Can you explain me this?”\n\nCevap: Can you explain this to me? Explain kişiyi to ile alır.\n\nAynı tuzak say'de de var: say me değil, tell me ya da say to me. Bu hatayı derste en son kim yaptı? 🙋",
  ['Can you explain this to me? Explain kişiyi to ile alır.'], 'hata', "Goof'lu animasyon: “explain me” düzeltilip “explain this to me” oluyor."),
 ('2026-12-19', 'r21-pov-meeting', 'İş İngilizcesi',
  "Toplantıda müdürün soruyor: “Does that make sense?” Ama hiçbir şey anlamadın.\n\n“Repeat please!” mı dersin? Emir gibi duyulur.\nKibar hali: Sorry, could you go over that again?\n\nAnlamadığını söylemek zor gelir ama doğru cümleyle hiç garip değil. Sen anlamayınca sorar mısın, yoksa kafa mı sallarsın? 😅",
  [], 'prova', "Goof'lu sahne: toplantıda anlamayınca “Sorry, could you go over that again?” demek."),
 ('2026-12-20', 'r22-vs-telefon', 'İngilizce Konuşma',
  "Telefonda Türk usulü vs native:\n\nAçarken: Yes, please? ❌ Hello? ✅\nKim arıyor?: Who are you? ❌ Who's calling, please? ✅\nKapatırken: Okay okay, bye bye bye! ❌ Talk soon. Bye! ✅\n\nSonuncusu bizde çok yaygın 😄 İngilizce telefonda en çok neyde zorlanıyorsun?",
  [], None, "Goof'lu animasyon: telefonda Türk usulü cümleler ve doğal İngilizce karşılıkları."),
 ('2026-12-21', 'r23-nasil-kusura', 'İngilizce Konuşma',
  "“Kusura bakma” nasıl denir?\n\n“Don't look at the fault!” değil 😄\nKüçük bir aksilikte: Sorry about that!\nArkadaşlar arasında: My bad!\nResmî ortamda: I apologize.\n\n“My bad” favorimiz: kısa, samimi, suçu üstüne alıyor. En son neye “my bad” demen gerekirdi?",
  [], None, "Goof'lu animasyon: “Kusura bakma” için üç İngilizce karşılık."),
 ('2026-12-22', 'r24-hata-works', 'İngilizce',
  "Bu hatayı neredeyse herkes yapar:\n“She work in a bank.”\n\nCevap: She works in a bank. He, she, it ile geniş zamanda fiile -s gelir.\n\nKonuşurken bu -s'i unutmak çok normal. Kulağın alışsın diye üç kez sesli söyle. Sen en çok hangi kuralı unutuyorsun?",
  ['She works in a bank. He, she, it ile geniş zamanda fiile -s gelir.'], 'hata', "Goof'lu animasyon: “She work” düzeltilip “She works” oluyor."),
 ('2026-12-23', 'r25-quiz-discuss', 'İngilizce',
  "Hangisi doğru?\n\nA) We discussed it.\nB) We discussed about it.\n\nCevap: A. Discuss zaten “hakkında konuşmak” demek, about almaz: discuss the plan.\n\nAma talk about ve have a discussion about doğru. Sen bugüne kadar hangisini kullanıyordun?",
  ['A. Discuss zaten “hakkında konuşmak” demek, about almaz: discuss the plan.'], None, "Goof'lu mini test: “discussed it” mi “discussed about it” mi?"),
 ('2026-12-24', 'r26-pov-exam', 'İngilizce Konuşma',
  "Arkadaşın mesaj attı: “I passed my exam!!”\n\n“Congratulations. You are very successful.” yazmak üzeresin. Yanlış değil ama resmî bir yazı gibi duruyor.\n\nSohbette daha sıcak: No way! Well done, you!\n\nBu dönem geçmek istediğin sınav hangisi? YDS, YÖKDİL, IELTS...",
  [], 'prova', "Goof'lu sahne: sınavı geçen arkadaşa “No way! Well done, you!” demek."),
 ('2026-12-25', 'r27-hata-people', 'İngilizce',
  "Bu hatayı fark et:\n“People is very friendly here.”\n\nCevap: People are very friendly here. People çoğuldur, is değil are alır.\n\nTekili person: one person, two people. Yurt dışında insanların en çok neyi seni şaşırttı?",
  ['People are very friendly here. People çoğuldur, is değil are alır.'], None, "Goof'lu animasyon: “People is” düzeltilip “People are” oluyor."),
 ('2026-12-26', 'r28-nasil-hayirli', 'İngilizce Konuşma',
  "“Hayırlı olsun” nasıl denir?\n\n“Let it be charity!” değil 😄\nYeni ev, iş, araba: Congrats!\nYeni eve taşınana: Enjoy your new place!\nYeni bir başlangıca: All the best!\n\n2026'da sana kim “hayırlı olsun” dedi? Yeni iş mi, yeni ev mi?",
  [], 'yurt', "Goof'lu animasyon: “Hayırlı olsun” için üç İngilizce karşılık."),
 ('2026-12-27', 'r29-vs-nezaket', 'İngilizce Konuşma',
  "Nezaket: Türk usulü vs native\n\n“Rica ederim” → I request! ❌ You're welcome! ✅\n“Bol şans” → Plenty luck! ❌ Good luck! ✅\n“Boş ver” → Give empty! ❌ Never mind! ✅\n\n“Give empty” hayatımızın cümlesi olabilir 😄 Bunlardan hangisini daha önce duydun?",
  [], None, "Goof'lu animasyon: nezaket kalıplarında kelimesi kelimesine çeviriler ve doğruları."),
 ('2026-12-28', 'r30-urun-waiting', 'Seyahat İngilizcesi',
  "Uygulamadan bir sahne. Boşluğu doldur:\n“I'm waiting ___ the bus.”\nto / for / at\n\nCevap: for. Birini ya da bir şeyi beklerken wait for denir.\n\nLINGOOF'ta her hatanın Türkçe açıklaması var; seyahat ve yurt dışı yolları da hazır. Yanlış seçmek serbest, Goof düzeltir.",
  ['for. Birini ya da bir şeyi beklerken wait for denir.'], 'sik', "LINGOOF uygulamasından sahne: “waiting to” yerine “waiting for”; Goof Türkçe açıklıyor."),
 ('2026-12-29', 'r31-hata-depends', 'İngilizce',
  "Sen de böyle diyor musun?\n“It depends of the weather.”\n\nCevap: It depends on the weather. Depend her zaman on ile kullanılır.\n\n“Duruma göre” demek istediğinde kısaca: It depends! Yılbaşı planın belli mi, yoksa “it depends” mi? 😄",
  ['It depends on the weather. Depend her zaman on ile kullanılır.'], None, "Goof'lu animasyon: “depends of” düzeltilip “depends on” oluyor."),
 ('2026-12-30', 'r32-pov-bakarim', 'İngilizce Konuşma',
  "Ev arkadaşın soruyor: “Are you coming tonight?”\n\nTürkçede “Bakarım” dersin. İngilizcede “I will look” dersen neye bakacağını sorarlar.\n\nDoğal hali: Maybe! I'll see how I feel.\n\nYılbaşı davetlerine en çok verdiğin cevap ne: “Kesin gelirim” mi, “bakarım” mı? 😄",
  ["Maybe! I'll see how I feel."], 'prova', "Goof'lu sahne: “Bakarım” için “Maybe! I'll see how I feel.”"),
]

# ---------- 11:00 V3 carousel'lar (salı, perşembe, cumartesi) ----------
CAROUSELS = [
 ('2026-12-01', 'c04-yalanci', 'İngilizce',
  "Bu 5 kelime sandığın anlamda değil: sympathetic, agenda, actually...\n\nTürkçeye benziyorlar ama anlamları başka. Sympathetic “sempatik” değil, “anlayışlı” demek.\n\nDoğruları kaydırmalı kartlarda. Sen hangisini yanlış biliyordun?"),
 ('2026-12-03', 'c02-erasmus', 'İngilizce Konuşma',
  "Erasmus'ta ilk hafta: bu 5 cümle seni kurtarır.\n\nKampüste, yurtta, kafede ilk günden lazım olacak cümleler ve gelecek cevaplar kartlarda.\n\nErasmus'a giden ya da gidecek biri var mı çevrende? Ona gönder, ilk hafta işine yarar."),
 ('2026-12-05', 'c03-havalimani', 'Seyahat İngilizcesi',
  "Havalimanında bu 5 cümle yeter ✈️\n\nCheck-in'den kapıya kadar gerçek cümleler ve gelecek cevaplar kartlarda. Küçük not: biniş kapısı gate, door değil.\n\nKaydet, bir sonraki yolculukta lazım olur. Sen en son nereye uçtun?"),
 ('2026-12-08', 'c06-otel', 'Seyahat İngilizcesi',
  "Otelde bu 5 cümle yeter: girişten çıkışa, kibar ve doğal 🛎️\n\nRezervasyon, kahvaltı saati, Wi-Fi şifresi, bozuk klima... Hepsi kartlarda, gelecek cevaplarıyla.\n\nOtelde en çok neyi sormakta zorlanıyorsun?"),
 ('2026-12-10', 'c07-phrasal', 'İngilizce',
  "Her gün duyacağın 5 phrasal verb: figure out, run out of, look forward to, put off ve bir tane daha.\n\nDizilerde, işte, sohbette. Örnek cümleleri ve kısa ipuçları kartlarda.\n\nSen en çok hangisini duyuyorsun?"),
 ('2026-12-12', 'c12-restoran', 'Seyahat İngilizcesi',
  "Restoranda bu 5 cümle yeter: masa iste, sipariş ver, hesabı öde 🍝\n\nSiparişte I want yerine Can I get…? Alerjin varsa nasıl sorarsın? Hepsi kartlarda.\n\nYurt dışında yediğin en güzel yemek neydi?"),
 ('2026-12-15', 'c09-telefon', 'İngilizce Konuşma',
  "Telefonda panik yapma: 5 kalıp 📞\n\nTelefonda “I am Ece” değil “This is Ece” denir. Ses kesilince ne dersin? Sonra aramak istersen? Kartlarda.\n\nİngilizce telefon görüşmesi seni de geriyor mu?"),
 ('2026-12-17', 'c11-ulasim', 'Seyahat İngilizcesi',
  "Otobüste, trende: 5 kurtarıcı cümle 🚆\n\nBilet al, yolunu sor, aktarma yap. Gidiş-dönüş İngiltere'de return, ABD'de round trip.\n\nYurt dışında toplu taşımada hiç kayboldun mu?"),
 ('2026-12-19', 'c10-doktor', 'Seyahat İngilizcesi',
  "Yurt dışında hastalanırsan 5 cümle: belirtini anlat, ilacını sor.\n\nKaydet, umarız hiç lazım olmaz 🤞 Ama Erasmus'a ya da Work & Travel'a gideceksen cebinde dursun.\n\nKartlarda en çok hangisi işine yarar?"),
 ('2026-12-22', 'c01-inonat', 'İngilizce',
  "in, on, at: bir kere öğren, bitsin 🗓️\n\nSaatte at, günde on, ay ve yılda in. Gece mi? at night. Örnekler ve sonunda mini test kartlarda.\n\nMesaj yazarken en çok hangisinde duraksıyorsun?"),
 ('2026-12-24', 'c08-hatalar', 'İngilizce',
  "Türklerin en sık yaptığı 5 İngilizce hata, doğrusu ve kısa nedeniyle tek yerde.\n\nI am agree, I have 25 years old... Tanıdık geldi mi? Kaydet, bir daha düşmezsin.\n\nSen hangisini yapıyordun?"),
 ('2026-12-26', 'c13-yeniyilmesaj', 'İngilizce',
  "Yeni yıl mesajını İngilizce yaz: arkadaşa, hocaya, iş yerine hazır kalıplar 🎉\n\nKaydet, 31 Aralık gecesi lazım olacak.\n\nBu yıl kaç kişiye İngilizce mesaj atacaksın?"),
 ('2026-12-29', 'c14-hedef', 'İngilizce',
  "2027 hedefini İngilizce söyle: 5 kalıp, kendi hedefinle doldur.\n\nThis year, I'm going to... Kararlı plan için going to.\n\nKendi hedefini yorumlara İngilizce yaz. Goof'unki ilk yorumda 💜"),
]
CAROUSEL_REPLY = {
 'c14-hedef': "Goof'un hedefi hazır 💜\n“This year, I'm going to make more mistakes, out loud!”\n= Bu yıl daha çok hata yapacağım, hem de sesli!\nÇünkü hata yapmadan konuşma gelişmiyor.",
}


def find(n):
    return next(p for p in posts if p['n'] == n)


def cut_cta(post, cta_start):
    """Ana metindeki LINGOOF çağrısını ({LINK} dahil) çıkarır ve döndürür."""
    i = post['text'].index(cta_start)
    cta = post['text'][i:].strip()
    post['text'] = post['text'][:i].rstrip()
    return cta


def edit(n, old, new):
    p = find(n)
    for field in ('text', 'reply'):
        if p.get(field) and old in p[field]:
            p[field] = p[field].replace(old, new)
            return
    sys.exit(f'#{n}: metin bulunamadı: {old[:40]}')


def main():
    global posts
    if any(p['n'] >= 400 for p in posts):
        sys.exit('Plan zaten güncellenmiş (#400+ var).')
    removed = []
    keep = []
    for p in posts:
        upcoming = str(p['n']) not in done and p['date'] >= START
        if upcoming and (p['series'] == 'Günün Kelimesi' or p['time'] == '13:00'):
            removed.append(p['n'])
            continue
        keep.append(p)
    posts = keep

    # eski görünümlü ve yapay zekâ görselleri: çıkar ya da V3 kartla değiştir
    v3 = {165: ('v3/th-is.jpg', "LINGOOF özet kartı, Goof 2.0 ile: iş İngilizcesi için 6 kalıp. Tell me about yourself, I hope you're doing well, by Friday, Sorry to interrupt but, I'll get back to you, Thanks for your time."),
          221: ('v3/th-deyim.jpg', "LINGOOF özet kartı, Goof 2.0 ile: 7 İngilizce deyim ve Türkçe karşılıkları: break the ice, raining cats and dogs, spill the beans, when pigs fly, the ball is in your court, not my cup of tea, better late than never."),
          249: ('v3/th-dizi.jpg', "LINGOOF özet kartı, Goof 2.0 ile: dizi ve internet İngilizcesi, 7 ifade: I'm on my way, Never mind, No way, No spoilers please, binge-watch, That's a red flag, I can't wait."),
          277: ('v3/th-gramer.jpg', "LINGOOF özet kartı, Goof 2.0 ile: 7 kısa gramer kuralı: present perfect, used to, will ve going to, a ve an, at on in, many ve much, I'd like."),
          289: ('v3/th-yil.jpg', "LINGOOF yılın özeti kartı, Goof 2.0 ile: 2026'nın 9 cümlesi ve Türkçeleri.")}
    for p in posts:
        if str(p['n']) in done or p['date'] < START:
            continue
        if p['n'] in v3:
            p['img'], p['alt'] = v3[p['n']]
        elif p.get('img'):
            p.pop('img'), p.pop('alt', None)
    # 6 Aralık küçük konuşma özeti: Instagram'daki V3 small talk carousel'ı
    p193 = find(193)
    p193.pop('img', None), p193.pop('alt', None)
    p193['carousel'] = [f'medya:v3/c05-smalltalk/{i:02d}.jpg' for i in range(1, 11)]
    p193['alts'] = ig_alts.get('c05-smalltalk', [])
    p193['text'] = ("Small talk haftasının özeti ☕ Sohbeti tıkanmadan sürdürmek için 5 soru, doğal cevapları ve sonunda mini bir test.\n\n"
                    "Kaydet 🔖 Asansörde, kahve sırasında, toplantı başlamadan önce lazım olur.\n\n"
                    "Small talk'ta en çok nerede tıkanıyorsun: açarken mi, sürdürürken mi?")

    # düşük emekli yorum istekleri yerine gerçek sorular
    edit(165, "Bu haftanın sesli görevini yaptıysan yorumlara ✅ bırak 💜", "Bu hafta en çok hangisi işine yaradı? Numarasını yaz 💜")
    edit(221, "Bu haftanın sesli görevini yaptıysan yorumlara ✅ bırak 💜", "Hangisini ilk kullanacaksın? Numarasını yaz 💜")
    edit(249, "Bu haftanın sesli görevini yaptıysan yorumlara ✅ bırak 💜", "Hangisini en çok duyuyorsun? Numarasını yaz 💜")
    edit(277, "Bu haftanın sesli görevini yaptıysan yorumlara ✅ bırak 💜", "En çok hangisinde takılıyordun? Numarasını yaz 💜")
    edit(169, "Yaptığın gün yorumlara ✅", "Sen sohbeti en çok hangisiyle açarsın?")
    edit(197, "Yaptığın gün yorumlara ✅ Aklına", "Aklına")
    edit(225, "Haftanın sesli görevi 🎬 Öğlenki anketin devamı: Dizi", "Haftanın sesli görevi 🎬 Dizi")
    edit(225, "Yaptığın gün yorumlara ✅ Bu akşam", "Bu akşam")
    edit(253, "Yaptığın gün yorumlara ✅", "İlk cümleni yorumlara yaz: “I've been to...”")
    # "5 dakika" vaadi yok
    edit(188, "Günde 5 dakika yeter. Mükemmel olmasın", "Kısa olsun ama her gün olsun. Mükemmel olmasın")
    edit(281, "Her gün aynı saatte, 5 dakika, sesli İngilizce. Az mı? Bir yılda 30 saati geçer.",
         "Her gün aynı saatte, 10 dakika, sesli İngilizce. Az mı? Bir yılda 60 saati geçer.")
    edit(281, "Senin 5 dakikan hangi saatte?", "Senin 10 dakikan hangi saatte?")
    edit(281, "LINGOOF'ta ana ekrandaki “Günün yolu” birkaç adım, birkaç dakika sürüyor.",
         "LINGOOF'ta ana ekrandaki “Günün yolu” seni adım adım götürüyor.")
    edit(280, "Beş dakika bile olsa, söz!", "Kısa da olsa, söz!")
    edit(277, "Her gün birkaç dakika yeter: LINGOOF'ta", "Her güne küçük bir adım: LINGOOF'ta")

    # link ana metinden çıkar; ilk yoruma taşınacak adaylar
    moved = {}
    for n, start in [(168, 'Yazdıktan sonra bir de sesli söyle'), (174, 'Hava muhabbetinden sonra sıra kahvede'),
                     (196, 'Yüksek sesle denemek istersen'), (202, 'Deyimi bir de sesli söyle.'),
                     (230, 'Tonu sesli denemek için'), (236, 'Sesli pratik için LINGOOF'),
                     (252, 'sonra bir de sesli söyle.'), (258, 'Bu tür ikilileri adım adım')]:
        moved[n] = cut_cta(find(n), start)
    find(252)['text'] = find(252)['text'].rstrip(', ') + '.'
    for n, fix in [(168, "Yazdıktan sonra bir de sesli söyle: LINGOOF'ta Goof Talk AI'da mikrofona dokun, Goof seni dinliyor 💜 {LINK}"),
                   (252, "Cevabını bir de sesli söyle: LINGOOF'ta Goof'la konuştukça dilin alışır 💜 {LINK}")]:
        moved[n] = fix

    # 31 Aralık kapanış: Goof 2.0 "İyi seneler" videosu, link ilk yorumda
    k = find(293)
    k['text'] = ("Ekimde “Merhaba, ben Goof!” diye başlamıştık. Yeni yıla üç saat kaldı 💜\n\n"
                 "Bu gece lazım olacak üç cümle:\nGece yarısı: Happy New Year!\nMesajla: All the best in 2027!\n"
                 "Kadeh kaldırırken: Here's to a great year!\n\n"
                 "Burada okuyan, yazan, İngilizce cümle kurmayı deneyen herkese kocaman teşekkürler. 2027'de görüşmek üzere!")
    k['video'] = 'medya:v3/r33-nasil-iyiseneler.mp4'
    k['fallback_img'] = 'medya:v3/r33-nasil-iyiseneler.jpg'
    k['alt'] = "Goof'lu animasyon: “İyi seneler” için üç İngilizce karşılık."
    moved[293] = "2027'nin ilk İngilizce cümlesi sesli olsun: LINGOOF'ta Goof'la sesli prova et, ilk dersler ücretsiz 🎙️ {LINK}"

    new = []
    for i, (d, rid, topic, text, spoiler, cta, alt) in enumerate(REELS):
        new.append({'n': 400 + i, 'date': d, 'time': '13:00', 'series': 'Goof Videosu', 'topic': topic, 'text': text,
                    'video': f'medya:v3/{rid}.mp4', 'fallback_img': f'medya:v3/{rid}.jpg', 'alt': alt,
                    **({'spoiler': spoiler} if spoiler else {}), 'src': rid, 'cta': cta})
    new.append({'n': 433, 'date': '2026-12-31', 'time': '13:00', 'series': 'Goof Kartları', 'topic': 'İngilizce',
                'text': ("Bu yıl burada en çok konuştuğumuz 5 kalıp, tek yerde:\n\nWhat's up? · Can I get a latte? · Could we get the bill? · "
                         "I'll see how I feel. · Take care!\n\nKaydet, 2027'de lazım olacak. Senin 2026'da öğrendiğin en kullanışlı cümle hangisi?"),
                'carousel': [f'medya:v3/c15-yilozeti/{i:02d}.jpg' for i in range(1, 11)], 'alts': ig_alts.get('c15-yilozeti', []),
                'src': 'c15-yilozeti', 'cta': None})
    for i, (d, cid, topic, text) in enumerate(CAROUSELS):
        new.append({'n': 450 + i, 'date': d, 'time': '11:00', 'series': 'Goof Kartları', 'topic': topic, 'text': text,
                    'carousel': [f'medya:v3/{cid}/{j:02d}.jpg' for j in range(1, 11)], 'alts': ig_alts.get(cid, []),
                    'src': cid, 'cta': 'yurt' if cid in ('c02-erasmus', 'c10-doktor') else None,
                    **({'reply': CAROUSEL_REPLY[cid]} if cid in CAROUSEL_REPLY else {})})

    # günde en fazla bir link: önce mevcut ilk yorumlardaki link, sonra taşınan çağrı, sonra video/carousel çağrısı
    by_day = defaultdict(list)
    for p in posts + new:
        if str(p['n']) not in done and p['date'] >= START:
            by_day[p['date']].append(p)
    links = {}
    for d, items in sorted(by_day.items()):
        has = [p for p in items if '{LINK}' in (p.get('reply') or '')]
        for p in has[1:]:                                   # aynı gün ikinci link: çağrı kalır, link çıkar
            p['reply'] = p['reply'].replace('\n{LINK}', '').replace(' {LINK}', '').replace('{LINK}', '').rstrip()
        if has:
            links[d] = has[0]['n']
            continue
        cand = [p for p in items if p['n'] in moved]
        if cand:
            p = cand[0]
            p['reply'] = (p['reply'] + '\n\n' + moved[p['n']]) if p.get('reply') else moved[p['n']]
            links[d] = p['n']
            continue
        cand = [p for p in items if p.get('cta')]
        if cand:
            p = cand[0]
            body = CTA[p['cta']]
            p['reply'] = (p['reply'] + '\n\n' + body) if p.get('reply') else body
            links[d] = p['n']
    for p in new:
        p.pop('cta', None)

    posts = sorted(posts + new, key=lambda p: (p['date'], p['time'], p['n']))
    (ROOT / 'posts.json').write_text(json.dumps(posts, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'Kaldırılan: {len(removed)} gönderi · eklenen: {len(new)} · link içeren gün: {len(links)}')
    for d in sorted(by_day):
        print(d, 'link →', links.get(d, '-'), '|', ' '.join(f"{p['time']}:{p['n']}" for p in sorted(by_day[d], key=lambda x: x['time'])))


if __name__ == '__main__':
    main()
