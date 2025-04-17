from flask import Flask, render_template, request, session, redirect, url_for, send_file, jsonify, flash, \
    send_from_directory
import subprocess
import os
import tempfile
import shutil
import re
import json
import uuid
import time
from datetime import datetime
from pathlib import Path
import threading
import sys
from yt_dlp import YoutubeDL

# PyInstaller ile paketlendiğinde kaynak dizin tespiti
def resource_path(relative_path):
    """ Kaynak dosyalarının yolunu PyInstaller paketlenmiş uygulamada veya normal çalışma modunda döndürür """
    try:
        # PyInstaller oluşturur bir geçici klasör ve paths _MEIPASS'a çözümler
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# Flask uygulama başlatma
template_folder = resource_path('templates')
static_folder = resource_path('static')
app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
app.secret_key = 'youtube_downloader_secret_key'  # Güvenli bir anahtar oluşturun

# Cookies dosya yolunu belirleme
base_dir = os.path.expanduser("~")
config_dir = os.path.join(base_dir, '.m-youtube-downloader')
cookies_path = os.path.join(config_dir, 'cookies.txt')

# Kaynak dizinini oluşturma
os.makedirs(config_dir, exist_ok=True)

# Video listesi için saklaama
video_list = []
# İndirme geçmişi için saklama
download_history = []


def get_video_list():
    global video_list
    return video_list


def save_video_list(new_list):
    global video_list
    video_list = new_list


def get_download_history():
    global download_history
    return download_history


def add_to_download_history(video_info, format_id, download_path):
    global download_history
    download_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history_item = {
        'id': str(len(download_history) + 1),
        'title': video_info['title'],
        'channel': video_info['channel'],
        'duration': video_info['duration'],
        'upload_date': video_info['upload_date'],
        'thumbnail': video_info['thumbnail'],
        'format_id': format_id,
        'download_path': download_path,
        'download_time': download_time,
        'url': video_info.get('url', '')  # URL bilgisini ekle
    }
    download_history.append(history_item)
    return history_item


# İndirme klasörünü platform bağımsız olarak tespit et
def get_download_directory():
    """Platform bağımsız olarak standart indirme klasörünü belirler"""
    try:
        # Önce platform standarlarına göre indirme klasörünü belirlemeye çalış
        if os.name == 'nt':  # Windows
            try:
                import winreg
                # Windows kayıt defterinden indirme klasörünü al
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                    r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders') as key:
                    download_dir = winreg.QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')[0]
            except:
                # winreg başarısız olursa standart yöntemi dene
                download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        else:  # macOS ve Linux
            download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')

        # Klasörün gerçekten var olduğundan emin ol
        if not os.path.exists(download_dir):
            download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)
    except Exception as e:
        # Herhangi bir sorun olursa kullanıcının ev dizinindeki Downloads klasörünü kullan
        print(f"İndirme klasörü tespitinde hata: {str(e)}")
        download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

    # Alt klasör oluştur
    final_dir = os.path.join(download_dir, 'M-YouTube Downloads')
    os.makedirs(final_dir, exist_ok=True)
    return final_dir


@app.route('/', methods=['GET', 'POST'])
def index():
    error = request.args.get('error', None)
    message = request.args.get('message', None)
    active_tab = request.args.get('active_tab', 'singleVideo')
    url = ""
    formats = None
    video_info = None
    cookies_exists = os.path.exists(cookies_path)

    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        if not url:
            error = "Lütfen bir YouTube video URL'si girin."
        else:
            try:
                # Video bilgilerini çek (senin daha önce dönüştürdüğümüz get_video_info fonksiyonu kullanılabilir)
                video_info = get_video_info(url)

                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'skip_download': True,
                    'forcejson': True
                }

                if cookies_exists:
                    ydl_opts['cookiefile'] = cookies_path

                # Format listesini al
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    formats = []
                    for fmt in info.get('formats', []):
                        format_id = fmt.get('format_id')
                        ext = fmt.get('ext')
                        resolution = fmt.get('resolution') or fmt.get('height') or 'N/A'
                        description = fmt.get('format_note') or fmt.get('format')
                        label = f"{resolution} ({ext})"
                        formats.append((format_id, label, description))

            except Exception as e:
                error = f"Video bilgileri alınamadı: {str(e)}"

    return render_template('index.html',
                           url=url,
                           formats=formats,
                           video_info=video_info,
                           video_list=get_video_list(),
                           download_history=get_download_history(),
                           error=error,
                           message=message,
                           cookies_set=cookies_exists,
                           active_tab=active_tab)


def get_video_info(url):
    try:
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'forcejson': True,
        }

        if os.path.exists(cookies_path):
            ydl_opts['cookiefile'] = cookies_path

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        title = info.get('title', 'Bilinmiyor')
        channel = info.get('uploader', 'Bilinmiyor')
        duration_seconds = info.get('duration', 0)

        # Süreyi biçimlendir
        try:
            duration_seconds = int(duration_seconds)
            minutes, seconds = divmod(duration_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            if hours > 0:
                duration = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                duration = f"{minutes}:{seconds:02d}"
        except:
            duration = "Bilinmiyor"

        # Yükleme tarihini biçimlendir
        upload_date = info.get('upload_date', '')
        try:
            if len(upload_date) == 8:
                year = upload_date[:4]
                month = upload_date[4:6]
                day = upload_date[6:8]
                upload_date = f"{day}.{month}.{year}"
        except:
            upload_date = "Bilinmiyor"

        thumbnail = info.get('thumbnail', '')

        return {
            'title': title,
            'channel': channel,
            'duration': duration,
            'upload_date': upload_date,
            'thumbnail': thumbnail,
            'url': url
        }

    except Exception as e:
        print(f"Error in get_video_info: {str(e)}")
        return None


@app.route('/download', methods=['POST'])
def download_video():
    url = request.form['url']
    format_id = request.form['format_id']

    try:
        download_dir = get_download_directory()

        ydl_opts = {
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }

        # Ses ve videoyu birleştirme gerekiyorsa
        merge_needed_ids = ['137', '299', '298', '266', '264', '138', '22', '136', '135', '134', '133', '160']
        if format_id in merge_needed_ids:
            ydl_opts.update({
                'format': f'{format_id}+bestaudio/best',
                'merge_output_format': 'mp4'
            })
        else:
            ydl_opts.update({
                'format': format_id
            })

        if os.path.exists(cookies_path):
            ydl_opts['cookiefile'] = cookies_path

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Başarılı ise video bilgilerini al
        video_info = get_video_info(url)

        # İndirme geçmişine ekle
        add_to_download_history(video_info, format_id, download_dir)

        return redirect(
            url_for('index', message=f"'{video_info['title']}' videosu başarıyla {download_dir} konumuna indirildi!",
                    url=url))

    except Exception as e:
        return redirect(url_for('index', error=f"İndirme sırasında hata oluştu: {str(e)}", url=url))


@app.route('/add-multiple', methods=['POST'])
def add_multiple_videos():
    urls_text = request.form.get('urls', '')
    urls = [url.strip() for url in urls_text.split('\n') if url.strip()]

    if not urls:
        return redirect(url_for('index', error="Lütfen en az bir video URL'si girin.", active_tab="multipleVideos"))

    count = 0
    for url in urls:
        try:
            video_info = get_video_info(url)
            if video_info:
                # Tüm formatları al
                formats = get_all_formats(url)
                video_data = {
                    'id': str(len(get_video_list()) + 1),
                    'url': url,
                    'title': video_info['title'],
                    'channel': video_info['channel'],
                    'duration': video_info['duration'],
                    'thumbnail': video_info['thumbnail'],
                    'formats': formats,
                    'selected_format': None  # Kullanıcı seçimi için
                }
                current_list = get_video_list()
                current_list.append(video_data)
                save_video_list(current_list)
                count += 1
        except Exception as e:
            print(f"Error adding video {url}: {str(e)}")

    if count > 0:
        return redirect(url_for('index', message=f"{count} video başarıyla eklendi.", active_tab="multipleVideos"))
    else:
        return redirect(url_for('index', error="Hiçbir video eklenemedi. Lütfen geçerli YouTube URL'leri girin.",
                                active_tab="multipleVideos"))


def get_all_formats(url):
    """Bir video için tüm formatları döndürür (yt-dlp modülü ile)"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'forcejson': True
        }

        if os.path.exists(cookies_path):
            ydl_opts['cookiefile'] = cookies_path

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        for fmt in info.get('formats', []):
            format_id = fmt.get('format_id')
            ext = fmt.get('ext')
            resolution = fmt.get('resolution') or fmt.get('height') or 'N/A'
            description = fmt.get('format_note') or fmt.get('format') or ''
            acodec = fmt.get('acodec')

            # Format etiketini oluştur
            label = f"{resolution} ({ext})"

            # Ses bilgisi
            has_audio = acodec != 'none'

            # Açıklamayı zenginleştir
            if has_audio:
                description = f"{description} (Sesli)"
            else:
                description = f"{description} (Sessiz)"

            formats.append({
                'id': format_id,
                'label': label,
                'description': description.strip(),
                'ext': ext,
                'resolution': resolution,
                'has_audio': has_audio
            })

        return formats

    except Exception as e:
        print(f"Error in get_all_formats: {str(e)}")
        return []


@app.route('/download-all', methods=['POST'])
def download_all_videos():
    video_list = get_video_list()
    if not video_list:
        return redirect(url_for('index', error="İndirilecek video bulunamadı."))

    download_dir = get_download_directory()
    success_count = 0
    error_count = 0

    merge_needed_ids = ['137', '299', '298', '266', '264', '138', '22', '136', '135', '134', '133', '160']

    for video in video_list:
        try:
            url = video['url']
            format_id = video.get('selected_format')

            if not format_id:
                format_id = get_best_format(url)  # Bu fonksiyon da modül versiyona göre uyarlanmalı gerekiyorsa

            ydl_opts = {
                'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True
            }

            if format_id in merge_needed_ids:
                ydl_opts.update({
                    'format': f'{format_id}+bestaudio/best',
                    'merge_output_format': 'mp4'
                })
            else:
                ydl_opts['format'] = format_id

            if os.path.exists(cookies_path):
                ydl_opts['cookiefile'] = cookies_path

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Başarılı indirme sonrası geçmişe ekle
            video_info = get_video_info(url)
            add_to_download_history(video_info, format_id, download_dir)
            success_count += 1

        except Exception as e:
            error_count += 1
            print(f"Error downloading {url}: {str(e)}")

    # Listeyi temizle
    save_video_list([])

    if success_count > 0:
        message = f"{success_count} video başarıyla indirildi."
        if error_count > 0:
            message += f" {error_count} video indirilemedi."
        return redirect(url_for('index', message=message))
    else:
        return redirect(url_for('index', error=f"Hiçbir video indirilemedi. {error_count} hata oluştu."))


@app.route('/update-format', methods=['POST'])
def update_format():
    """Seçilen video için format güncellemesi yapar"""
    video_id = request.form.get('video_id')
    format_id = request.form.get('format_id')

    if not video_id or not format_id:
        return jsonify({'success': False, 'error': 'Video ID ve format ID gerekli.'})

    video_list = get_video_list()
    for video in video_list:
        if video['id'] == video_id:
            video['selected_format'] = format_id
            save_video_list(video_list)
            return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Video bulunamadı.'})


@app.route('/remove-video', methods=['POST'])
def remove_video():
    video_id = request.form.get('video_id')

    video_list = get_video_list()
    video_list = [v for v in video_list if v['id'] != video_id]
    save_video_list(video_list)

    return redirect(url_for('index', message="Video listeden kaldırıldı."))


@app.route('/cookies', methods=['GET', 'POST'])
def manage_cookies():
    message = None
    error = None
    cookies_exists = os.path.exists(cookies_path)

    if request.method == 'POST':
        if request.form.get('_method') == 'DELETE' or request.path == '/clear-cookies':
            # Cookie'leri temizle
            if os.path.exists(cookies_path):
                try:
                    os.remove(cookies_path)
                    message = "Cookie dosyası başarıyla silindi!"
                except Exception as e:
                    error = f"Cookie dosyası silinirken hata oluştu: {str(e)}"
            cookies_exists = False
        elif 'cookie_file' in request.files:
            # Cookie dosyasını yükle
            file = request.files['cookie_file']
            if file.filename == '':
                error = "Dosya seçilmedi!"
            elif not file.filename.endswith('.txt'):
                error = "Sadece .txt uzantılı dosyalar kabul edilir!"
            else:
                try:
                    # Dizini oluştur (varsa sorun değil)
                    os.makedirs(os.path.dirname(cookies_path), exist_ok=True)

                    # Cookie dosyasını kaydet
                    file.save(cookies_path)
                    message = "Cookie dosyası başarıyla yüklendi!"
                    cookies_exists = True
                except Exception as e:
                    error = f"Cookie dosyası yüklenirken hata oluştu: {str(e)}"

    return render_template('cookies.html',
                           cookies_set=cookies_exists,
                           message=message,
                           error=error)


@app.route('/upload-cookies', methods=['POST'])
def upload_cookies():
    if 'cookie_file' not in request.files:
        return redirect(url_for('manage_cookies'))

    file = request.files['cookie_file']
    if file.filename == '':
        flash('Dosya seçilmedi!')
        return redirect(url_for('manage_cookies'))

    if not file.filename.endswith('.txt'):
        flash('Sadece .txt uzantılı dosyalar kabul edilir!')
        return redirect(url_for('manage_cookies'))

    try:
        # Dizini oluştur (varsa sorun değil)
        os.makedirs(os.path.dirname(cookies_path), exist_ok=True)

        # Cookie dosyasını kaydet
        file.save(cookies_path)
        return redirect(url_for('manage_cookies', message="Cookie dosyası başarıyla yüklendi!"))
    except Exception as e:
        return redirect(url_for('manage_cookies', error=f"Cookie dosyası yüklenirken hata oluştu: {str(e)}"))


@app.route('/clear-cookies', methods=['POST'])
def clear_cookies():
    if os.path.exists(cookies_path):
        try:
            os.remove(cookies_path)
            return redirect(url_for('manage_cookies', message="Cookie dosyası silindi!"))
        except Exception as e:
            return redirect(url_for('manage_cookies', error=f"Cookie dosyası silinirken hata oluştu: {str(e)}"))
    return redirect(url_for('manage_cookies'))


@app.route('/static/img/logo.svg')
def serve_logo():
    return send_file('static/img/logo.svg', mimetype='image/svg+xml')


@app.route('/static/img/hello.gif')
def serve_hello_gif():
    return send_file(resource_path('static/img/hello.gif'), mimetype='image/gif')


@app.route('/goodbye')
def goodbye():
    # Kapanış sayfasını göster
    return render_template('goodbye.html')


@app.route('/shutdown', methods=['POST'])
def shutdown():
    # Sunucuyu kapatma işlemini başlat
    def shutdown_server():
        time.sleep(1)  # Yanıtın döndürülmesi için kısa bir bekleme
        os._exit(0)  # Uygulamayı zorla kapat

    # Arka planda çalışacak bir iş parçacığı başlat
    thread = threading.Thread(target=shutdown_server)
    thread.daemon = True
    thread.start()

    return jsonify({"success": True, "message": "Sunucu kapatılıyor..."})


@app.route('/history')
def view_history():
    return render_template('history.html',
                           download_history=get_download_history(),
                           cookies_set=os.path.exists(cookies_path))


@app.route('/export-history')
def export_history():
    history = get_download_history()

    # Geçici bir dosya oluştur
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
    temp_file_path = temp_file.name

    with open(temp_file_path, 'w', encoding='utf-8') as f:
        f.write("M-YouTube Downloader - İndirme Geçmişi\n")
        f.write("=" * 50 + "\n\n")

        for item in history:
            f.write(f"Başlık: {item['title']}\n")
            f.write(f"Kanal: {item['channel']}\n")
            f.write(f"Süre: {item['duration']}\n")
            f.write(f"Yükleme Tarihi: {item['upload_date']}\n")
            f.write(f"İndirme Tarihi: {item['download_time']}\n")
            f.write(f"İndirme Konumu: {item['download_path']}\n")
            f.write(f"URL: {item.get('url', '')}\n")  # URL bilgisini ekle
            f.write("-" * 50 + "\n\n")

    return send_file(temp_file_path,
                     as_attachment=True,
                     download_name="m-youtube-downloader-history.txt",
                     mimetype='text/plain')


@app.route('/clear-history', methods=['POST'])
def clear_history():
    global download_history
    download_history = []
    return redirect(url_for('view_history', message="İndirme geçmişi temizlendi."))


def get_best_format(url):
    """Bir video için en iyi formatı döndürür (video + ses)"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'forcejson': True
        }

        if os.path.exists(cookies_path):
            ydl_opts['cookiefile'] = cookies_path

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = info.get('formats', [])
        best_format = None

        # Önce hem video hem ses içeren formatları ara
        for fmt in formats:
            if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                best_format = fmt.get('format_id')
                break

        # Eğer video+ses formatı bulunamazsa, önce 1080p, sonra 720p, sonra herhangi bir video
        if not best_format:
            for fmt in formats:
                if '1080' in str(fmt.get('format_note', '')).lower() and fmt.get('vcodec') != 'none':
                    best_format = fmt.get('format_id')
                    break

        if not best_format:
            for fmt in formats:
                if '720' in str(fmt.get('format_note', '')).lower() and fmt.get('vcodec') != 'none':
                    best_format = fmt.get('format_id')
                    break

        if not best_format:
            for fmt in formats:
                if fmt.get('vcodec') != 'none' and fmt.get('acodec') == 'none':
                    best_format = fmt.get('format_id')
                    break

        return best_format

    except Exception as e:
        print(f"Error in get_best_format: {str(e)}")
        return None


if __name__ == '__main__':
    # Tarayıcıyı otomatik olarak aç
    import webbrowser

    port = 5000
    url = f"http://127.0.0.1:{port}"


    def open_browser():
        time.sleep(1.5)  # Sunucunun başlamasını bekle
        webbrowser.open(url)


    # Tarayıcıyı arka planda aç
    threading.Thread(target=open_browser).start()

    # Sunucuyu başlat
    app.run(debug=False, port=port)
