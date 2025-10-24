Harika bir fikir. Metni markdown formatının avantajlarını (tablolar, kod blokları, vurgular ve emojiler) daha iyi kullanarak görsel olarak daha çekici ve okunabilir hale getirelim.

***

# 🌊 AUV için Mikrodenetleyici & Sistem Tasarım Rehberi (Teknofest Odaklı) 🤖

> **Kısa Özet:** Genelde en iyi mimari şudur:
> 1.  **Gerçek-Zaman Kontrolcü:** `STM32` veya `Teensy` gibi küçük, güvenilir bir MCU (Arduino değil).
> 2.  **Yüksek Seviye İşlemci:** `Raspberry Pi CM4` veya `NVIDIA Jetson` gibi bir SBC.
>
> Bu ayrım, hem enerji verimliliği hem de sistem güvenilirliği açısından en pratik çözümdür. *(Kaynak: ResearchGate+2, Raspberry Pi+2)*

***

## 1) Yarış ve Çevre Gereksinimleri: Neler Kritik? 💧

* **Güvenilirlik & Sızdırmazlık:** Elektronik ve su asla dost değildir. Hata kabul edilmez. Elektrik/güç koruması, sigortalar, *potting* (elektronik dolgu) ve *bulkhead* konnektörler (ıslak-bağlantı olmasa bile) şarttır. *(Kaynak: RoboNation)*
* **Gerçek-Zaman Motor Kontrolü:** PID döngüleri, ESC kontrolü ve itici (thruster) sürüşü için düşük gecikmeli, deterministik (öngörülebilir) I/O gerekir.
* **Sensör Entegrasyonu:** `IMU`, derinlik (basınç) sensörü, `DVL`/`USB-L` (varsa), magnetometre ve sonar. Güvenilir bir `IMU` seçimi kritiktir. *(Kaynak: auvnitrkl.github.io)*
* **Görüş & Algılama (Vision):** Kameralı görevler (nesne tespiti, optik akış) yüksek işlem gücü ve muhtemelen `GPU`/`NPU` gerektirir. SBC burada devreye girer. *(Kaynak: Raspberry Pi)*
* **Enerji & Termal Yönetim:** Batarya yönetimi (BMS), güç dağılımı ve özellikle `Jetson` gibi güçlü SBC'lerde ortaya çıkan ısı yükünün yönetilmesi gerekir. *(Kaynak: ResearchGate)*

## 2) Önerilen Mimari (En Yaygın ve Kanıtlanmış Yaklaşım) 🏗️

Sistemi **üç ana katmana** ayırın:

1.  **Düşük Seviye Kontrol Kartı (MCU Tabanlı):**
    * **Görevleri:** Motor sürüşü (`ESC` PWM/FOC), acil durum durdurma (fail-safe), `IMU` okuma, derinlik sabitleme (PID).
    * **Örnek:** `STM32` veya `Teensy`.
2.  **Yüksek Seviye İşlem Kartı (SBC Tabanlı):**
    * **Görevleri:** Navigasyon, görüntü işleme (OpenCV/YOLO), görev planlama, SLAM/Makine Öğrenmesi (ML).
    * **Örnek:** `Raspberry Pi CM4` veya `Jetson Orin`.
3.  **Güç Dağıtım Kartı (PDB):**
    * **Görevleri:** BMS (Batarya Yönetimi), sigortalar, tüm bileşenlere temiz ve regüle edilmiş güç sağlama.

Bu modüler yaklaşım, birçok başarılı üniversite takımı tarafından kullanılmaktadır. *(Kaynak: GitHub+1)*

## 3) Mikrodenetleyici ve Kontrolcü Seçenekleri ⚙️

İşte düşük seviyeli (gerçek-zamanlı) kontrol kartı için popüler seçeneklerin bir karşılaştırması:

| Seçenek | Çekirdek (Örnek) | Neden Kullanılır? | Artıları ✅ | Eksileri ❌ |
| :--- | :--- | :--- | :--- | :--- |
| **STM32 (F4/F7/H7)** | Cortex-M4 / M7 / M7+ | **Endüstri Standardı.** Yüksek performans, bol I/O, donanımsal timer/DMA. Gerçek-zamanlı kontrol (PID, filtreleme) için ideal. | Deterministik, stabil, geniş ekosistem (CubeMX, HAL), `F4`'ten `H7`'ye geniş performans skalası. | Gömülü Linux/Görüntü işleme için yetersiz. C/C++ uzmanlığı gerektirebilir. |
| **Teensy 4.1** | Cortex-M7 (600 MHz) | **Hızlı Prototipleme.** Arduino uyumlu ama *çok* daha güçlü (600+ MHz). Hızlı I/O ve DSP yetenekleri. | Geliştirmesi kolay (Arduino IDE), yüksek saat hızı, kompakt boyut. | Endüstriyel paketleme ve çevre birimi çeşitliliği STM32 kadar geniş değil. |
| **Arduino (AVR)** | ATmega328 (Uno) | **Sadece Öğrenme/Prototip.** Öğrenmesi en kolay platform. | Çok basit, devasa topluluk ve dokümantasyon. | Çok sınırlı işlem gücü/RAM. Teknofest seviyesi bir AUV'nin ana kontrolcüsü olamaz. |
| **ESP32** | Tensilica (Çift Çekirdek) | **Yüzey İletişimi.** Wi-Fi/Bluetooth entegrasyonu. | Uygun maliyetli, kablosuz haberleşme. | **Su altında KULLANILMAZ** (RF çalışmaz). Gerçek-zamanlı görevlerde STM32 kadar stabil değildir. |

**Parça Tavsiyesi (Low-Level):** `STM32H7` serisi (örn. `STM32H743`) — yüksek MHz, FPU ve DMA yetenekleri ile en zorlu kontrol görevleri için ideal.

## 4) Yüksek Seviye İşlem (SBC / Edge GPU) — Görüntü İşleme & ML için 👁️💻

* **Raspberry Pi Compute Module 4 (`CM4`):**
    * **Ne zaman?** Orta seviye görüntü işleme (`OpenCV`), `ROS` node'ları ve genel görev yönetimi için.
    * **Avantajı:** Düşük güç tüketimi, devasa topluluk, küçük form faktörü. *(Kaynak: Raspberry Pi+1)*
* **NVIDIA Jetson (Nano / Orin / Xavier):**
    * **Ne zaman?** Gerçek-zamanlı derin öğrenme (YOLO, NN inference) gerekiyorsa.
    * **Avantajı:** CUDA çekirdekleri (`GPU`/`NPU`) sayesinde benzersiz ML performansı.
    * **Dezavantajı:** Yüksek güç tüketimi ve ciddi ısı yönetimi gerektirir.

**Tavsiye Mimari:** `STM32H7` (Kontrol) + `Raspberry Pi CM4` (Orta Seviye Görevler) VEYA `NVIDIA Jetson Orin` (Ağır ML Görevleri). *(Kaynak: auvnitrkl.github.io+1)*

## 5) Haberleşme Protokolleri & I/O 📡

* **CAN bus:** Güvenilir ve gürültüye dayanıklı. Birden fazla kontrol kartı veya akıllı sensör (örn. motor sürücüler) varsa tavsiye edilir.
* **UART / RS485:** Basit sensörler (örn. DVL, Sonar) ve modemler için yaygın kullanılır.
* **SPI / I2C:** `IMU`, barometre gibi kart üstü yakın sensörler için. (Dikkat: `I2C` uzun hatlarda sorun çıkarabilir veya çakışma riski taşır).
* **Ethernet (Tether):** Yüzey iletişimi, yüksek hızlı telemetri ve video akışı için en iyi seçenek.

## 6) Sensörler & Çevre Birimleri (Özet) 🧭

* **IMU:** Aracın duruş (AHRS) tahmini için en kritik sensör. Filtreleme (Kalman/UKF) gereklidir. Kaliteli bir IMU (örn. `VectorNav VN-100` veya üst seviye Bosch/Invensense) hayat kurtarır.
* **Pressure/Depth Sensor:** Gerçek derinlik ölçümü için (örn. `MS5837`).
* **DVL / USBL (Varsa):** Yere göre hız veya mutlak konum bilgisi sağlar. Navigasyon isabetini katbekat artırır.
* **Kamera + LED:** Görüntü tabanlı görevler için. Sızdırmazlık ve kasaya sabitlenme (kalibrasyon) kritiktir.
* **Sonar:** Bulanık veya karanlık sularda navigasyon ve engelden kaçınma için hayati önem taşır.

## 7) Dayanıklılık & Test Önerileri (Yarış Kazandıran İpuçları) 🛡️

* **Mühendislik Gerçeği:** Birçok takım, yarıştan günler önce su sızıntısı veya güç kartı arızası yüzünden elenir. Elektrik panosunu ayrı, iyi izole edilmiş ve sigortalı tasarlayın. *(Kaynak: RoboNation)*
* **Yedeklilik (Redundancy):** Kritik sensörlerde (örn. ikinci bir IMU) yedekleme yapmak iyi bir stratejidir.
* **Simülasyon:** Kodunuzu suya atmadan önce `ROS` / `Gazebo` ortamında test edin. Görev senaryolarını simüle edin.
* **Loglama:** Her şeyi loglayın! Tüm sensör verilerini, motor komutlarını ve güç tüketimini detaylı kaydedin. Hata ayıklarken bu loglar paha biçilmezdir.
* **Sızdırmazlık Testi:** Montaj bittikten sonra aracı *basınçlı tankta* veya en azından *derin bir havuzda* saatlerce bekleterek test edin.

## 8) Özet — Hangi Mikrodenetleyiciyi Seçmelisiniz? (Net Öneri) 🎯

| Görev | Önerilen Çip | Neden? |
| :--- | :--- | :--- |
| **Low-Level (Kontrol)** | `STM32H743` | Gerçek-zaman garantisi, endüstriyel güvenilirlik, güçlü çevre birimleri. *(ResearchGate)* |
| **Prototip (Hızlı Devre)** | `Teensy 4.1` | Güçlü M7 çekirdek, kolay Arduino ortamı. *(RoboNation)* |
| **High-Level (Görüntü/ML)**| `RPi CM4` / `Jetson Orin` | Linux, `ROS`, `OpenCV` ve `GPU` hızlandırma. *(Raspberry Pi+1)* |

## 9) Hızlı Parça Listesi (Başlangıç) 🛒

* `STM32H743` Geliştirme Kartı (veya buna dayalı özel bir PCB)
* `Raspberry Pi Compute Module 4` + Taşıyıcı Kart (veya `NVIDIA Jetson Orin NX`)
* Yüksek kaliteli `IMU` (örn. VectorNav, Xsens, veya en azından `BNO085`)
* Derinlik Sensörü (örn. `MS5837-30BA`)
* ESC / Thruster Sürücü Kartı (Motor gücüne göre seçilmeli)
* Su geçirmez *Bulkhead* Konnektörler
* Güç Dağıtım Kartı (PDB) için sigortalar, regülatörler ve `BMS`.

## 10) Kısa Yol Haritası (8 Haftalık Sprint Önerisi) 🗓️🏁

1.  **Hafta 1–2:** Elektrik şeması + Güç Dağıtım Kartı (PDB) tasarımı ve montajı (BMS, sigortalar).
2.  **Hafta 3–4:** Düşük seviye kontrolcü (`STM32`/`Teensy`) kurulumu + `IMU`/Derinlik sensörü entegrasyonu ve filtreleme.
3.  **Hafta 5:** Yüksek seviye SBC (`CM4`/`Jetson`) kurulumu + `ROS`/`OpenCV` temel hattının (pipeline) çalıştırılması (kamera, telemetri).
4.  **Hafta 6:** Motor/ESC entegrasyonu + PID ayarlarının yapılması (tezgah testi).
5.  **Hafta 7:** Tam entegrasyon testi + Yüzey su testleri (kova/küçük havuz).
6.  **Hafta 8:** Yarış ortamına benzer bir yerde (deniz/göl) tam görev testi, sızdırmazlık doğrulaması.

***

## Okuma Listesi / Önemli Referanslar 📚

* **Teknofest:** İnsansız Su Altı Sistemleri Yarışması — Şartname ve kurallar. *(teknofest.org)*
* **Team Tiburon (AUV Takımı):** `STM32` + `Jetson` kombinasyonu üzerine tecrübeler, IMU'nun önemi. *(auvnitrkl.github.io)*
* **Akademik Çalışma:** `STM32` tabanlı su altı kontrol kartı tasarımı. *(ResearchGate+1)*
* **Raspberry Pi:** ASV/AUV uygulamalarında `CM4` kullanım örnekleri. *(Raspberry Pi)*
* **McGill Robotics (AUV Takımı):** Teknik Rapor (TDR) — Yaşadıkları gerçek dünya arızaları (güç kartı sorunları, sızıntılar) ve çıkardıkları dersler. *(RoboNation)*

***

> ## 💡 Son Söz — Pratik Tavsiye (Takım Sohbeti Modu)
>
> * Eğer takımınızın ağır görsel görevleri varsa (örn. karmaşık nesne tespiti) doğrudan `Jetson` düşünün. Yoksa, optimize edilmiş bir `OpenCV` ile `CM4` hem yeterli olacak hem de çok daha az güç tüketecektir.
> * İlk AUV'niz için *aşırı karmaşık* tek bir PCB tasarlamayın. **Modüler olun!** Arıza tespiti ve hata ayıklaması çok daha kolay olur.
> * Ve en önemlisi: **Yarıştan önce en az 3 tam su testi yapın.** Gerçek su, size simülasyonun öğretemeyeceği her şeyi öğretecektir.