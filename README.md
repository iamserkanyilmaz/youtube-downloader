# M-YouTube Downloader

M-YouTube Downloader, YouTube videolarını kolayca indirmenizi sağlayan kullanıcı dostu bir araçtır. Özellikle gizli veya kısıtlı videolar için YouTube çerezlerinizi yönetebilir ve bu videoları da indirebilirsiniz.

## Özellikler

- YouTube videolarını farklı formatlarda indirme
- Çoklu video indirme desteği
- Gizli videolar için YouTube cookie desteği
- Sezgisel ve modern kullanıcı arayüzü
- macOS ve Windows için yerel uygulama olarak paketleme

## Gereksinimler

- Python 3.7 veya üzeri
- Flask
- yt-dlp
- İnternet bağlantısı

## Kurulum

### Kaynaktan Çalıştırma

1. Repoyu klonlayın:
   ```
   git clone https://github.com/your-username/m-youtube-downloader.git
   cd m-youtube-downloader
   ```

2. Gerekli paketleri yükleyin:
   ```
   pip install -r requirements.txt
   ```

3. Uygulamayı başlatın:
   ```
   python app.py
   ```

### Hazır Uygulama

- **Windows**: Sağlanan Windows yükleyicisini indirip çalıştırın
- **macOS**: DMG dosyasını indirin, açın ve Uygulamalar klasörüne sürükleyin

## Uygulama Olarak Paketleme

### macOS

1. Gerekli paketleri yükleyin:
   ```
   pip install pyinstaller
   ```

2. Paketleme betiğini çalıştırın:
   ```
   chmod +x build_macos.sh
   ./build_macos.sh
   ```

### Windows

1. Gerekli paketleri yükleyin:
   ```
   pip install pyinstaller
   ```

2. Paketleme betiğini çalıştırın:
   ```
   build_windows.bat
   ```

## Kullanım

1. Uygulamayı başlatın
2. YouTube video URL'sini girin
3. Formatı seçin ve indirin
4. Gizli videolar için, "Cookie Ayarları" bölümünden YouTube çerezlerinizi yükleyin

## Merzigo Sans Fontları

Bu uygulama, Merzigo Sans fontları kullanılarak tasarlanmıştır. Kullanım sırasında en iyi deneyimi elde etmek için, bu fontların yüklü olduğundan emin olun.

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakınız.

## İletişim

Herhangi bir soru veya geri bildirim için [e-posta adresiniz] adresine e-posta gönderebilirsiniz. 