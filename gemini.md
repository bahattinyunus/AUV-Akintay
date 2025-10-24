

# 🤖 AUV Mikrodenetleyici Rehberi: Teknofest için Zirveye Oynayan Seçimler

Merhaba\! Bir AUV yaparken sorulması gereken ilk soru "Hangi mikrodenetleyiciyi seçmeliyim?" değil, "**Hangi GÖREVLER için hangi işlemciyi seçmeliyim?**" olmalıdır.

Neden mi? Çünkü modern ve *güvenilir* bir AUV'de **asla tek bir işlemci bulunmaz.** Görevler o kadar farklıdır ki (refleks gibi hızlı motor kontrolü vs. görmek gibi karmaşık yapay zeka), tek bir işlemci bu iki işi de verimli yapamaz.

Başarılı takımların sırrı **"Böl ve Fethet"** mimarisidir.

Bu mimariyi insan vücudu gibi düşün:

1.  **Omurilik (Gerçek-Zamanlı Kontrolcü - MCU):** Refleksler, denge, nefes alma. Anlık tepki verir, gecikme kabul etmez, asla "çökmez".
2.  **Beyin (Yüksek Seviye İşlemci - SBC):** Görme, düşünme, karar verme. Güçlüdür ama "düşünürken" anlık gecikmeler yaşayabilir veya bir uygulama çökebilir.

Senin AUV'n de aynen böyle olmalı.

-----

## 1\. Mimari: "Omurilik" (MCU) + "Beyin" (SBC)

Bu mimaride iki işlemci birbiriyle (genellikle `UART` veya `CAN Bus` üzerinden) konuşur.

| Bileşen | Görevi | Örnek Donanım |
| :--- | :--- | :--- |
| **Omurilik (Low-Level)** | 💧 **Kritik Görevler:** Motor sürme (PID), Denge (IMU okuma), Derinlik (Basınç sensörü), Güç yönetimi, *Fail-Safe* (bağlantı koparsa yüzeye çık). | `STM32 (F4/F7/H7)` <br> `Teensy 4.1` |
| **Beyin (High-Level)** | 🧠 **Karmaşık Görevler:** Görüntü işleme (OpenCV), Nesne tespiti (YOLO/AI), Görev planlama, Navigasyon (ROS), Yüzeyle haberleşme. | `Raspberry Pi (CM4/Pi 4/Pi 5)` <br> `NVIDIA Jetson (Nano/Orin)` |

**Neden bu ayrım şart?**
Eğer "Beyin" (Raspberry Pi) üzerindeki `Linux` işletim sistemi veya `Python` kodunuz bir anlığına donarsa veya çökerse, "Omurilik" (STM32) bunu fark eder ve *Fail-Safe* prosedürünü işleterek aracı batmaktan kurtarır. Eğer tüm kontrolü Pi'ye verirseniz, en küçük bir yazılım hatası görevinizin (ve aracınızın) sonu olur.

-----

## 2\. "Omurilik" (MCU) Adayları: Gerçek Zamanlı Kontrolcüler

Senin asıl "mikrodenetleyici" dediğin parça burası. Görevi: **Asla Hata Yapma.**

### 🥇 Altın Standart: STM32 Serisi (Örn: F4, F7, H7)

Bu, endüstrinin ve tecrübeli Teknofest takımlarının tercihidir.

  * **Artıları ✅:**
      * **Güvenilirlik (Determinizm):** Görevleri *tam olarak* istenen zamanda yapar. Gecikme (latency) minimumdur.
      * **Güçlü Çevre Birimleri:** Donanımsal `Timer`'lar (motor PWM'leri için mükemmel), `CAN Bus` (gürültüye dayanıklı iletişim), `DMA` (işlemciyi yormadan veri aktarımı).
      * **Ekosistem:** STM32CubeMX gibi profesyonel araçlarla kod üretimi çok kolaydır.
  * **Eksileri ❌:**
      * **Öğrenme Eğrisi:** `Arduino`'ya göre daha karmaşıktır. C/C++ ve donanım bilgisi (register'lar, HAL kütüphaneleri) gerektirir.
  * **Gemini'nin Net Yorumu:** Eğer takımınızda gömülü sistemlere hakim biri varsa veya öğrenmeye vakit ayıracaksanız, **kesinlikle `STM32` kullanın.** `STM32F4` serisi (örn. F407) başlamak için harikadır.

### 🥈 Hızlı ve Güçlü: Teensy 4.0 / 4.1

Özellikle ABD'deki RoboSub yarışmalarında çok popüler olan, "hobi" ile "profesyonellik" arasındaki mükemmel köprüdür.

  * **Artıları ✅:**
      * **Hız:** 600 MHz Cortex-M7 çekirdeği ile *inanılmaz* hızlıdır. Çoğu `STM32F4`'ten daha güçlüdür.
      * **Kullanım Kolaylığı:** `Arduino IDE` veya `PlatformIO` ile programlanabilir. Arduino kütüphanelerinin çoğunu kullanır.
      * **Kompakt:** Çok küçük ve güçlü I/O pinlerine sahiptir.
  * **Eksileri ❌:**
      * `STM32` kadar "endüstriyel" bir ekosistemi ve donanımsal çeşitliliği yoktur.
  * **Gemini'nin Net Yorumu:** Eğer `C++` biliyorsunuz ama `STM32`'nin karmaşıklığından çekiniyorsanız ve *hızlıca* güçlü bir prototip yapmak istiyorsanız, **`Teensy 4.1` mükemmel bir seçimdir.**

### 🥉 Kaçınmanız Gerekenler (Ana Kontrolcü Olarak)

  * **Arduino (Uno/Nano - ATmega328):**
      * **Neden Uzak Durmalı?** 8-bit, 16 MHz işlemci. Yetersiz RAM. Aynı anda 6 motoru PID ile kontrol edip, IMU'dan veri okuyup, Beyin ile haberleşmeye gücü **yetmez.** Teknofest seviyesi için bir oyuncaktır. Sadece basit bir LED sürücü vb. alt görevler için kullanılabilir.
  * **ESP32:**
      * **Neden Yanlış Araç?** `ESP32`'nin ana gücü `Wi-Fi` ve `Bluetooth`'tur. Bu iki özellik de **suyun altında ÇALIŞMAZ.** Gerçek zamanlı işletim sistemi (RTOS) desteği olsa da, `STM32` veya `Teensy` kadar deterministik ve güvenilir değildir. Sadece *yüzey istasyonunuz* için mantıklıdır.

-----

## 3\. "Beyin" (SBC) Adayları: Görüntü İşleme ve Planlama

Burası `ROS`, `Python`, `OpenCV` ve `YOLO`'nun çalıştığı yerdir.

### 🥇 Standart Seçim: Raspberry Pi (Pi 4 / Pi 5 / CM4)

Takımların %80'i için en mantıklı seçimdir.

  * **Artıları ✅:**
      * **Ekosistem:** Devasa topluluk desteği. `ROS`, `OpenCV` kurulumu çok kolaydır.
      * **Güç Tüketimi:** `Jetson`'a göre çok daha az güç tüketir (batarya ömrü\!).
      * **Yeterli Güç:** `Pi 4` veya `Pi 5`, temel renk tespiti, kontur bulma, `Aruco` marker okuma gibi birçok Teknofest görevini rahatlıkla yapar.
  * **Eksileri ❌:**
      * `GPU`'su yoktur. Gerçek zamanlı, yüksek çözünürlüklü `YOLO` (yapay zeka) modellerini çalıştırmakta zorlanır.
  * **Gemini'nin Net Yorumu:** Eğer göreviniz "kırmızı şamandırayı bul", "turuncu halkadan geç" gibi temel `OpenCV` görevleriyse, **`Raspberry Pi 4` fazlasıyla yeterlidir** ve bataryanızı sömürmez.

### 🥈 Güçlü Seçim: NVIDIA Jetson (Nano / Orin Nano)

Eğer görevleriniz "denizaltı enkazını *tanı*", "belirli bir balık türünü *tespit et*" gibi karmaşık yapay zeka (ML/AI) modelleri gerektiriyorsa, `Jetson` şarttır.

  * **Artıları ✅:**
      * **GPU (CUDA Çekirdekleri):** Paralel işlem gücü sayesinde `YOLO` gibi derin öğrenme modellerini *gerçek zamanlı* (yüksek FPS) çalıştırabilir.
  * **Eksileri ❌:**
      * **Güç & Isı:** Canavar gibi güç çeker. Batarya planlamanızı ve ısı yönetiminizi (aktif soğutma) çok iyi yapmanız gerekir.
      * **Karmaşıklık:** Kurulumu ve yönetimi Pi'ye göre daha zordur.
  * **Gemini'nin Net Yorumu:** Sadece *gerçekten* `GPU` hızlandırmalı yapay zekaya ihtiyacınız varsa `Jetson`'a yönelin. Aksi halde Pi ile başlayın.

-----

## 4\. Özet: Hangi Kombinasyonu Seçmelisiniz?

İşte Teknofest için 3 farklı "paket" önerisi:

| Paket Adı | "Omurilik" (MCU) | "Beyin" (SBC) | Hangi Takımlar İçin? |
| :--- | :--- | :--- | :--- |
| **🏆 Profesyonel Paket**<br>(Tavsiyem) | **STM32H7** veya **F7** | **NVIDIA Jetson Orin** | Tecrübeli, iddialı, `C++` ve `YOLO`'ya hakim takımlar. |
| **⚡ Çevik Paket**<br>(Fiyat/Performans) | **Teensy 4.1** | **Raspberry Pi 4 / 5** | Hızlı prototip yapmak isteyen, `Arduino` tecrübesi olan, temel `OpenCV` görevleri olan takımlar. |
| **🎓 Güvenli Başlangıç** | **STM32F407** | **Raspberry Pi 4** | `STM32` öğrenmek isteyen, `Python`/`OpenCV` ile görevleri yapacak, dengeli ve güvenilir bir sistem arayan takımlar. |

-----

## 5\. Gemini'nin Altın Değerinde Ekstra Tavsiyeleri

1.  **Haberleşme Protokolü:** "Beyin" (Pi) ile "Omurilik" (STM32) arasında `CAN Bus` kullanmayı hedefleyin. `UART`'tan çok daha güvenilirdir, özellikle motor gürültüsünün olduğu bir ortamda veri bozulmasını engeller.
2.  **En Önemli Kural (Fail-Safe):** Omurilik (MCU) kodunuzun en başında şu olmalı: "Eğer 1 saniye boyunca Beyin'den (SBC) 'ben hayattayım' mesajı (heartbeat) almazsam, motorları durdur ve yüzeye çık." Bu kural sizi yarışmada kurtaracak olan kuraldır.
3.  **Güç (Power):** En iyi işlemci bile kötü bir güç dağıtım kartıyla (PDB) çalışmaz. Motorların çektiği akım ile işlemcilerin kullandığı hassas 5V/3.3V hattını çok iyi ayırın (regülatörler, filtreleme).
4.  **Sızdırmazlık \> Kod:** Ve unutmayın... **En iyi yazılım, ıslak bir mikrodenetleyicide çalışmaz.** Önce sızdırmazlığı garantileyin.

