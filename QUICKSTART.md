## AKINTAY — Quick Start

Bu kısa rehber, projeyi hızlıca çalıştırmak isteyenler için temel adımları içerir. Daha ayrıntılı kurulum ve geliştirme rehberleri README ve docs klasöründe bulunur.

Önkoşullar
- Python 3.8+ (önerilen 3.10+)
- pip
- Windows: COM port, Linux/RPi: /dev/ttyUSB0 veya ttyAMA0 vb.
- (RPi kamera kullanımı için) ffmpeg ve Picamera2 kurulu olmalı

1) Sanal ortam ve bağımlılıklar

PowerShell (Windows) örnek:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r requirements.txt
```

Linux / macOS / RPi:

```bash
python3 -m venv .venv; source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

2) Hızlı test: 2D simülatör

Simülatörü çalıştırmak için (kök dizinde):

PowerShell:
```powershell
python .\sim\rov2d.py --keyboard --trail --obstacles --telemetry
```

Alternatif olarak GUI:
```powershell
python .\sim\sim_gui.py
```

3) Vision -> komut gönderme (kamera bağlıysa)

SERİ (ESP32 için):
```powershell
python .\görüntü işleme\vision_control.py --port COM3 --baud 115200 --speed 60 --show
```

UDP (sim ile):
```powershell
python .\görüntü işleme\vision_control.py --udp --udp_host 127.0.0.1 --udp_port 5005 --show
```

4) Joystick teleop (PC üzerindeki oyun kolu ile ESP32'ye veya sim'e komut gönderir)

```powershell
python .\teleop\joystick_teleop.py --port COM3 --baud 115200 --mode VEL
```

Not: Windows üzerinde doğru COM port'u `Device Manager`'dan kontrol edin. RPi üzerinde seri port genelde `/dev/ttyUSB0` veya `/dev/serial0` olur.

5) RPi kamera operatörü (Raspberry Pi üzerinde çalıştırın)

```bash
# RPi üzerinde
python3 serial_cam_operator.py
```

Bu betik ESP32'den gelen `PHOTO` ve `VIDEO` satırlarını bekler. ffmpeg kurulu değilse video dönüşümü başarısız olacaktır.

6) Arduino / ESP32 yükleme

- `deneyap/AKINTAY_Main_Firmware.ino` veya `deneyap/manuel/Manuel_Yazilim_esp32_8motor_joystick_kontrol.ino` dosyalarını Arduino IDE veya PlatformIO ile ESP32'ye yükleyin. Baud genelde 115200 veya firmware içinde belirtilen değerdir.

7) Docker / Gazebo (opsiyonel, ITU sim)

PowerShell ile docker image oluşturma ve çalıştırma (daha ayrıntılı bilgi `docs/itu_gazebo_setup.md` içinde):

```powershell
.\scripts\itu_sim_docker_build.ps1
.\scripts\itu_sim_docker_run.ps1
```

Ek Notlar ve Hızlı Sorun Giderme
- Seri bağlantı başarısızsa: doğru port, kablo (USB-serial) ve baud'ı kontrol edin.
- Kamera açılmazsa: başka uygulama tarafından kullanılıyor olabilir veya Picamera2/raspberrypi-firmware eksiktir.
- RPi'de ffmpeg yüklü değilse video işlemleri başarısız olur: `sudo apt install ffmpeg`.

İleri adımlar önerisi
- README içinde önerilen güvenlik (arming/failsafe) ve `QUICK START` adımlarını uygulayıp test edin.
- İsterseniz ben otomatik test (komut parse unit testi) ve kısa CI workflow örneği ekleyebilirim.
