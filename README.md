# LINGOOF Threads medyası

Bu dal yalnızca Threads gönderilerinde kullanılan Goof 2.0 (V3 görünüm) videolarını ve carousel görsellerini tutar.
Ana daldaki bot bunlara `medya:` önekiyle başvurur (`config.json › media_base_url`). Dosyalar build 140'ın Goof
pozlarıyla stüdyoda üretildi; yapay zekâ görsel/video aracı kullanılmadı. Ana dalı küçük tutmak için ayrı dalda.

- `v3/<id>.mp4`: dikey video (1080×1920, H.264, AAC)
- `v3/<id>.jpg`: videonun kapağı (video olmazsa yedek görsel)
- `v3/<id>/01.jpg…10.jpg`: carousel görselleri (1080×1350)
