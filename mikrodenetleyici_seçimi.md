AUV için Mikrodenetleyici & Sistem Tasarım Rehberi (Teknofest odaklı) 🌊🤖
Kısa özet: Genelde iyi çalışan mimari = küçük, güvenilir gerçek-zaman kontrolcü (STM32/Teensy vs Arduino) + yüksek işlem gücü gereken görevler için SBC (Raspberry Pi CM4 / NVIDIA Jetson). Bu ayrım hem enerji hem de güvenilirlik bakımından pratik. (ResearchGate+2, Raspberry Pi+2)

1) Yarış/çevre gereksinimleri — neler önemli? 💧
Güvenilirlik & su sızdırmazlığı: Elektronik suyla barışık değil; hata kabul etmez. Elektrik / güç koruma, sigortalar, potting ve uygun konnektörler (wet-mate değilse en azında bulkhead) şart. (RoboNation)

Gerçek-zaman motor kontrolü: PID/ESC kontrolü, thruster sürüşü; düşük gecikmeli, deterministik I/O gerekiyor.

Sensör entegrasyonu: IMU, derinlik (pressure) sensörü, DVL/USB-L (varsa), magnetometre, sonar/sonar-like sensors. IMU'yu güvenilir almak kritik. (auvnitrkl.github.io)

Görüş / algılama: Kameralı görev varsa yüksek işlem gücü ve GPU / NPU isteyebilirsiniz (nesne algılama, stereo/optical flow). SBC burada devreye girer. (Raspberry Pi)

Enerji/termal: Batarya yönetimi, güç dağılımı, ısı yükü (özellikle SBC/Jetson’larda). (ResearchGate)

2) Mimari önerisi (en yaygın, denenmiş yaklaşım) 🏗️
Elektronik katmanları ayırın:

Low-level control board (gerçek zamanlı, MCU tabanlı): motor sürücüleri, ESC PWM/FOC, fail-safe, IMU okuması, derinlik kontrolü.

High-level compute (SBC): navigasyon, görüntü işleme, planlama, SLAM/ML.

Güç & dağıtım: BMS, sigortalar, yarı-izole regülatörler.

Bu ayrım, birçok yarışma/üniversite takımı tarafından kullanılıyor. (GitHub+1)

3) Düşünülecek mikrodenetleyici / kontrolcü seçenekleri ⚙️
(Artıları/Eksileri)

A) STM32 (Cortex-M serileri — F4 / F7 / H7) — Endüstri tercihi
Neden? Yüksek performanslı, çok sayıda I/O, donanım timer/ADC/DMA, CAN/USART/SPI güçlü. Pek çok AUV kontrol kartı STM32 tabanlı tasarlanmış. Özellikle gerçek-zaman kontrol, IMU filtreleme, PID için ideal. (ResearchGate+1)

Artılar: Deterministik, stabil, STM ekosistemi (HAL, LL, CubeMX), geniş seçim (F4→H7).

Eksiler: Gömülü Linux/vision işleri için yetersiz; geliştirme C/C++ uzmanlığı gerekebilir.

Parça tavsiyesi: STM32H7 serisi (ör. STM32H743) — yüksek MHz, FPU ve DMA yetenekleri.

B) Teensy 4.1 (NXP i.MX RT1062, Cortex-M7) — Hızlı prototip, yüksek MHz
Neden? Arduino compatible ama çok daha güçlü (600 MHz kadar). Hızlı I/O, güçlü DSP yetenekleri. Küçük takımlarda düşük seviye kontrolcü olarak popüler. (RoboNation)

Artılar: Kolay geliştirme, yüksek performans, az yer kaplar.

Eksiler: Endüstriyel paketlemeler kadar geniş çevre birimi desteği olmayabilir.

C) Arduino (AVR) — ATmega / Uno gibi — Başlangıç için kolay ama sınırlı
Artılar: Çok öğrenmesi kolay, bol dokümantasyon.

Eksiler: Sınırlı işlem/g/ram; gerçek-zaman karmaşık filtreler/çok sensör okumaları için yetersiz. Teknofest seviye AUV için genelde düşük seviye prototip aşamasında kullanılır. (richardelectronics.com)

D) ESP32 — Wi-Fi/BT entegre, fakat su altı için dikkat
Artılar: Uygun maliyet, kablosuz özellikler (yüzey iletişimi için faydalı).

Eksiler: Gerçek-zaman kritik görevlerde stabilite sorunları; Wi-Fi su altına işlemez — dolayısıyla ESP32 sadece yüzey/telemetri cihazlarında mantıklı. (AUV içinde düşük tercih.) (socketxp.com)

4) Yüksek seviyede işlem (SBC / Edge GPU) — görüntü & ML için 👁️💻
Raspberry Pi Compute Module 4 (CM4): Küçük, güçlü, geniş topluluk. Görüntü işleme, ROS, OpenCV için yeterli; düşük güç tüketimi. Birçok deniz/arazi aracı CM4 kullanıyor. (Raspberry Pi+1)

NVIDIA Jetson (Nano / Orin / Xavier / TX2 eski): Eğer gerçek-zaman derin öğrenme (YOLO/NN inference) gerekiyorsa Jetson serisi GPU/NPU avantajı sunar. Ancak enerji & ısı yönetimi dikkate alınmalı. Takımlar Jetson + STM32 kombinasyonunu tercih ediyor. (auvnitrkl.github.io+1)

Tavsiye mimari: STM32/Teensy (low-level) + Raspberry Pi CM4 (orta-seviye görüntü) veya Jetson (daha ağır ML).

5) Haberleşme protokolleri & I/O 📡
CAN bus: Güçlü ve güvenilir; birden fazla kontrol kartı varsa tavsiye edilir.

UART/RS485: Basit sensörler ve modemler için.

SPI/I2C: IMU, barometer vb. için sık kullanılır (I2C dikkat, I2C hattı boot/çakışma riski).

Ethernet: Yüzey iletişimi/telemetri için iyi.

Bu altyapı, modüler ve hata toleranslı bir sistem kurmanıza yardımcı olur. (RoboNation)

6) Sensörler & çevre birimleri (kısa) 🧭
IMU: Yüksek kaliteli — AHRS için filtreleme gerekir (Kalman/UKF). Takımlar için çok kritik. (auvnitrkl.github.io)

Pressure/Depth sensor: Gerçek derinlik ölçümü.

DVL / USBL (varsa): gerçek konum elde etmek için — çok daha isabetli navigasyon.

Kamera + LED: Görüntü tabanlı görevler için; kameranın kasaya sabitlenmesi ve sızdırmazlık kritik.

Sonar: Görüşün olmadığı koşullarda hayati.

7) Dayanıklılık & test önerileri (yarış kazandırır) 🛡️
Mühendislik gerçeği: Birçok takım son hafta su sızıntısı/power board arızası yüzünden elendi. Elektrik panosunu ayrı, iyi izole edilmiş, sigortalı tasarla. Testlerini gerçek su koşulunda yap; sızdırmazlık testlerini şiddetle öneririm. (RoboNation)

Redundancy: Kritik sensörlerde yedekleme (örn. ikinci IMU) iyi bir fikir.

Simülasyon & yazılım testleri: ROS / Gazebo ile prosedürleri ve görev senaryolarını simüle et.

Loglama: Tüm sensörleri ve güç hattını detaylı logla; hata yaşandığında kök sebebi bulmak kolaylaşır.

8) Özet — Hangi mikrodenetleyiciyi seçmelisiniz? (Net öneri) 🎯
Mükemmel dengeli seçim (önerim):

Low-level flight/control board: STM32H7 (ör. STM32H743) — gerçek-zaman kontrol, güvenilir, takımların tercih ettiği endüstriyel sınıf. (ResearchGate)

Prototip / hızlı devre: Teensy 4.1 — daha hızlı prototip, güçlü M7 çekirdek. (RoboNation)

High-level compute (vision/AI): Raspberry Pi Compute Module 4 (hafif ML/vision) veya NVIDIA Jetson (gerçek zamanlı derin öğrenme gerekiyorsa). (Raspberry Pi+1)

Neden bu kombinasyon? STM32/Teensy gerçek-zaman garantisi ve I/O gücü verir; CM4/Jetson görüntü ve planlama yükünü omuzlar. Takımlar (ör. üniversite AUV projeleri) bu ayrımı iyi sebeplerle kullanıyor. (GitHub+1)

9) Hızlı parça listesi (başlangıç) 🛒
STM32H743 development board (veya custom control board)

Teensy 4.1 (opsiyonel, prototip)

Raspberry Pi Compute Module 4 + CM4 carrier (NVMe / eMMC tercihi) veya NVIDIA Jetson Orin NX / Nano (görev ihtiyacına göre)

IMU (ör. VectorNav, VN-100 gibi kalite aralığına göre) veya yüksek kaliteli Bosch/Invensense IMU

Pressure (depth) sensor (MS5837 gibi başlangıç)

ESC / thruster driver board (motor gücüne göre)

Bulkhead konektörler, su geçirmez konnektörler, sigortalar, BMS

10) Kısa yol haritası — 8 haftalık sprint önerisi 🗓️🏁
Hafta 1–2: Elektrik şeması + güç dağıtımı (BMS, sigortalar)

Hafta 3–4: Low-level kontrolcü kurulumu (STM32/Teensy) + IMU/derinlik entegrasyonu

Hafta 5: SBC kur ve ROS/OpenCV temel pipeline (kamera, telemetri)

Hafta 6: Motor/ESC entegrasyonu + PID tuning (bench test)

Hafta 7: Entegre test + yüzey su testleri (kova/mini havuz)

Hafta 8: Deniz/yarış ortamında tam test, sızdırmazlık doğrulama

Kaynaklar / Okuma (önemli referanslar) 📚
Teknofest Unmanned Underwater Systems Competition — yarışma şartları & tarihçe. (teknofest.org)

Team Tiburon (üniversite AUV) — STM32 ile Jetson/TX2 kombinasyonu; takım deneyimleri ve IMU önemi. (auvnitrkl.github.io)

STM32 tabanlı su altı kontrol kartı tasarımı (akademik çalışma). (ResearchGate+1)

Raspberry Pi Compute Module 4 başarı hikayesi — ASV/AUV uygulamalarında CM4 kullanımı. (Raspberry Pi)

McGill Robotics AUV TDR — gerçek dünya arızaları ve dayanıklılık problemleri (güç board arızaları, sızıntılar). Öğrenilecek dersler. (RoboNation)

Son söz — pratik tavsiye (takım sohbeti modu) 💡🏆
Eğer takımın görsel görevleri varsa Jetson düşün; yoksa CM4 + optimize OpenCV yeterli ve daha az güç yiyor.

İlk AUV’in için aşırı karmaşık bir tek kart düşünme — modüler ol, hata ayıklamak kolay olsun.

Ve en önemlisi: yarıştan önce en az 3 tam su testi yap. Gerçek su, her şeyi öğretiyor. (Evet, su soğuk, ama AUV’ler daha soğuk kalırsa kalma şansı yok 😅.)