## AKINTAY — ROV Yazılım Deposu (Özet, Durum, Plan)

### Proje özeti

AKINTAY, Deneyap/ESP32 tabanlı 8 ESC’li bir ROV platformu için geliştirilen kontrol ve algılama yazılımlarından oluşur. Depoda;

- **Deneyap/ESP32** ile manuel sürüş miksajı (8 motor),
- **IMU (LSM6DSL)** ile temel düzey yatay dengeleme (PID denemesi),
- **Görüntü işleme** ile yön komutu üretimi (çizgi takibi vb.),
- **Raspberry Pi kamera** modülü için seri komutla foto/video kaydı,

gibi bileşenler yer alır. Geçen sezon araç batırılamadığı için tam sistem testi yapılmamıştır; mevcut kodlar deneme/örnek niteliğindedir ve tek bir ana uygulamada birleşmemiştir.

---

### Depo yapısı (yüksek seviye)

```
Teknofest-Akintay/
├─ deneyap/
│  ├─ AKINTAY_Main_Firmware.ino                                   # Birleşik ana firmware (Mod: Manuel/Vision/Stab)
│  ├─ manuel/
│  │  ├─ Manuel_Yazilim_esp32_8motor_joystick_kontrol.ino         # 8 ESC manuel miksaj + joystick
│  │  ├─ deneyap_modlar_manuel-joystick-kontrol-robotu-esp32.ino   # Modülerleştirilmiş sürüm (mod1/mod2)
│  │  └─ serial_cam_operator/
│  │     ├─ serial_cam_operator.py                                 # RPi üzerinde PHOTO/VIDEO komutlarını işler
│  │     ├─ deneyap_joycam_controller.ino                          # (README’de referanslı; depoda boş/eksik)
│  │     └─ README_AKINTAY.md                                      # Kamera kontrol alt projesi dökümanı
│  ├─ PID_Kontrol_pid_dengeleme_imu_servo_esp32.ino                # IMU tabanlı roll/pitch PID denemesi
│  ├─ hız_yon_mesafe/
│  │  └─ hız_yon_mesafe_hesaplama(deneyapKodu).ino                 # Potansiyometre ile hız/yön örneği
│  └─ haberleşme/
│     ├─ Haberlesme_Deneyap_Kodu_ultrasonik-mesafe-sensoru-okuma   # Ultrasonik mesafe sensörü seri çıktı örneği
│     └─ Haberlesme_Python_Kodu_ultrasonik-mesafe-sensoru-okuma    # Python tarafı okuma örneği
├─ görüntü işleme/
│  ├─ vision_control.py                                            # Vision → ESP32 protokol (CMD:F/L/R; SPEED:x)
│  ├─ çizgitakip_goruntu-ile-kontrol-edilen-rov.py                 # Vision → ESP32: F/L/R komutları
│  ├─ cizgi_takip_ve_manuelsurus_rpi.py                            # RPi GPIO ile 2 ESC doğrudan sürüm örneği
│  └─ (tarih klasörleri + demo betikleri)
├─ kayip_hazine/                                                   # Ayrı proje/denemeler (Arduino + Python)
├─ shape_model_final*.keras / *.h5                                 # Görsel sınıflandırma/model denemeleri
└─ README.md
```

---

### Mevcut durum — güçlü yanlar ve boşluklar

- **Manuel 8’li miksaj hazır**: `Manuel_Yazilim_esp32_8motor_joystick_kontrol.ino` joystick A0–A3’ten okuyup 1000–2000 µs aralığında 8 ESC’e dağıtıyor. Limitler (`mindeger=1060`, `maxdeger=1940`) tanımlı. Motor tersine çevirme için şartlı yapı örneği bulunuyor.
- **IMU PID denemesi mevcut**: `PID_Kontrol_pid_dengeleme_imu_servo_esp32.ino` ile LSM6DSL verisinden gyro integrasyonu yapılarak roll/pitch düzeltmesi uygulanmış (temel PID, drift kompanzasyonu sınırlı).
- **Görüntü işleme hattı**: Çizgi/renk temelli yön tahmini yapıp ESP32’ye seri üzerinden basit komutlar (F/L/R) gönderen Python betiği var.
- **RPi kamera kontrolü**: `serial_cam_operator.py` `PHOTO`/`VIDEO` komutlarıyla foto/video yakalama ve mp4’e dönüştürme akışını sağlıyor.

Boşluklar / entegrasyon eksikleri:

- **Tek bir ana uygulama yok**: Manuel sürüş, vision komut köprüsü, IMU stabilize ve RPi kamera komutlaşması ayrı ayrı dosyalarda; bir araya getirilmemiş.
- **RPi ↔ ESP32 komut protokolü yarım**: RPi tarafı `PHOTO/VIDEO` bekliyor; Deneyap’ta bu komutları gönderen (buton tetikli) örnek .ino dosyası dökümanda geçiyor ancak depoda uygulanmış, bütünleşik bir sürüm yok.
- **Vision’dan 8 motor miksere geçiş**: Vision komutlarını (F/L/R veya hız vektörü) mevcut 8’li miksajla güvenli şekilde birleştiren kontrol katmanı eksik.
- **Derinlik/başınç sensörü yok**: Otomatik derinlik tutma ve su-altı görevleri için gerekli sensör ve kontrol döngüsü hazır değil.
- **Güvenlik**: ESC arming, failsafe (komut kesilirse 1500 µs), hız sınırlandırma ve kuru test modları kodda standartlaştırılmamış.

---

### Önerilen sade entegrasyon mimarisi

1) **ESP32 tek firmware** (modlu yapı):
- Modlar: Manuel / Vision / Stabilize (IMU destekli). Seri üzerinden mod değiştirme ve hız ölçeklemesi.
- Seri protokol: Basit ve genişletilebilir yapı; örn. `CMD:F;SPEED:60` veya `VEL:surge,sway,heave,yaw`.
- Motor mikseri: Mevcut 8’li miksaj korunur; joystick/vision girdileri ile güvenli kaynaştırma, ölü-bölge ve limitler parametrik.

2) **Vision katmanı**:
- `çizgitakip_goruntu-ile-kontrol-edilen-rov.py` sadeleştirilip port/baud/speed parametreleri CLI argümanlarıyla verilir. Protokol satırı net: `b"CMD:F;SPEED:60\n"` gibi.

3) **RPi kamera**:
- `serial_cam_operator.py` korunur. ESP32 firmware’i butonlardan `PHOTO`/`VIDEO` yazıp RPi’den geri bildirim (`*_OK`) loglar.

4) **Güvenlik ve test**:
- ESC arming ve `1500 µs` failsafe.
- Kuru test modu: ESC’e sinyal yazmadan yalnızca seri çıktıyla doğrulama.
- Filtreleme: Girişlerde düşük geçiren filtre, joystick ölü-bölge, hız tavanı.

5) **IMU stabilize**:
- Complementary filter (gyro + accel) ile açı kestirimi iyileştirilir.
- Stabilize modu, sürüş komutuna küçük düzeltme (mix-in) uygular; tek başına agresif kontrol yapmaz.

---

### Hızlı başlarken (mevcut durumda)

- **Birleşik firmware (ESP32)**
  - `deneyap/AKINTAY_Main_Firmware.ino` dosyasını yükle (115200 baud).
  - Açılış modu: MANUAL. Mod değiştirme için seri hatta komut gönder:
    - `MODE:MANUAL` | `MODE:VISION` | `MODE:STAB`
  - Vision komut protokolü örnekleri:
    - `CMD:F;SPEED:60` (İleri, hız %60)
    - `CMD:L;SPEED:40` (Sola)
    - `CMD:R;SPEED:40` (Sağa)
  - Failsafe: Son komuttan 800 ms sonra zaman aşımı → duruş (1500 µs).
  - D9 → `PHOTO`, D0 → `VIDEO` komutlarını seri hatta yazar (RPi için).

- **Manuel sürüş (kuru test)**
  - `Manuel_Yazilim_esp32_8motor_joystick_kontrol.ino` yüklenir.
  - ESC takılı değilken seri monitörde X1/Y1/X2/Y2 ve M1..M8 değerleri doğrulanır.
  - ESC takılırsa önce düşük hız sınırlarıyla emniyetli deneme yapılır.

- **Vision → ESP32**
  - Önerilen: `görüntü işleme/vision_control.py` kullanın:
    - Örnek: `python vision_control.py --port COM3 --baud 115200 --speed 60 --show`
  - Alternatif: `çizgitakip_goruntu-ile-kontrol-edilen-rov.py` (eski basit F/L/R gönderen sürüm).

- **RPi kamera**
  - Raspberry Pi’de `serial_cam_operator.py` çalıştırılır. ESP32’den `PHOTO`/`VIDEO` komutları geldiğinde kayıt yapılır.

---

### Yol haritası (kısa)

- [x] ESP32 ana firmware’i tek dosyada modlu hale getirme (Manuel + Vision + Stabilize + RPi komutları)
- [x] Vision betiğini parametreli/protokol uyumlu yapma
- [ ] Failsafe, arming ve kuru test modlarını standartlaştırma
- [ ] IMU açı kestirimi için complementary filter ekleme
- [ ] Derinlik sensörü entegrasyonu (gelecek sprint)

---

### Yapılan değişiklikler (bu commit)

- **Yeni**: `deneyap/AKINTAY_Main_Firmware.ino` (mod: Manuel/Vision/Stab, failsafe, RPi komutları)
- **Yeni**: `görüntü işleme/vision_control.py` (argümanlı, `CMD:…;SPEED:…` protokolü)
- **Güncellendi**: README — yapı, kullanım, protokol ve yol haritası genişletildi.

> Not: Firmware ve vision betiği eklendi; istenirse derinlik sensörü ve IMU füzyonu bir sonraki adımda entegre edilir.

---

### İletişim

- Geliştirici: Bahattin Yunus Çetin
- Proje: AKINTAY — Akıllı Kontrollü İnteraktif Tabanlı Aygıt Yönetimi


