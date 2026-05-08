import os
import string
import random
import qrcode
import io
import base64
import urllib.parse
from flask import Flask, request, jsonify, redirect, render_template_string
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

if 'RDS_HOSTNAME' in os.environ:
    username = os.environ.get('RDS_USERNAME')
    password = os.environ.get('RDS_PASSWORD')
    hostname = os.environ.get('RDS_HOSTNAME')
    port = os.environ.get('RDS_PORT')
    dbname = os.environ.get('RDS_DB_NAME')
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{username}:{password}@{hostname}:{port}/{dbname}"
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///lokal.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
with app.app_context():
    db.create_all()

class URLMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.String(2048), nullable=False)
    short_code = db.Column(db.String(50), unique=True, nullable=False)
    stat_code = db.Column(db.String(50), unique=True, nullable=False) 
    clicks = db.Column(db.Integer, default=0)

def generate_random_string(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

GLOBAL_CSS = """
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --color-1: #1E104E; 
            --color-2: #452E5A; 
            --color-3: #FF653F; 
            --color-4: #FFC85C; 
            
            --bg-color: #f4f7f6;
            --card-bg: #ffffff;
            --text-main: #333333;
            --border-color: #dee2e6;
        }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background-color: var(--bg-color); 
            color: var(--text-main); 
            margin: 0; 
            padding: 40px 20px; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            min-height: 80vh; 
        }
        .card { 
            background: var(--card-bg); 
            padding: 40px; 
            border-radius: 12px; 
            box-shadow: 0 8px 24px rgba(30, 16, 78, 0.1); 
            width: 100%; 
            max-width: 550px; 
            text-align: center; 
        }
        .card-left { text-align: left; }
        h2 { color: var(--color-1); margin-top: 0; font-weight: 700; }
        
        input[type="url"], input[type="text"] { 
            width: 100%; 
            padding: 12px; 
            margin-bottom: 20px; 
            border: 2px solid var(--border-color); 
            border-radius: 6px; 
            box-sizing: border-box;
            font-size: 1em;
            transition: border-color 0.3s;
        }
        input:focus { outline: none; border-color: var(--color-1); }
        
        .btn { 
            display: inline-block;
            width: 100%;
            padding: 12px 20px; 
            cursor: pointer; 
            background-color: var(--color-1); 
            color: white; 
            border: none; 
            border-radius: 6px; 
            font-weight: 600; 
            font-size: 1em;
            transition: all 0.2s; 
            text-decoration: none;
            box-sizing: border-box;
        }
        .btn:hover { background-color: var(--color-2); }
        
        .btn-outline {
            background-color: transparent;
            color: var(--color-2);
            border: 2px solid var(--color-2);
            margin-top: 20px;
        }
        .btn-outline:hover { background-color: var(--color-2); color: white; }
        
        .section-label { font-weight: 600; margin-bottom: 8px; font-size: 0.95em; color: var(--color-1); }
        .info-text { font-size: 0.85em; color: #666; margin-top: 5px; }
        hr { border: 0; border-top: 1px solid var(--border-color); margin: 30px 0; }

        .input-group {
            display: flex;
            align-items: stretch;
            margin-bottom: 5px;
        }
        .input-group .alert-box {
            flex: 1;
            background: #f8f9fa;
            padding: 12px;
            border: 2px solid var(--border-color);
            border-right: none;
            border-top-left-radius: 6px;
            border-bottom-left-radius: 6px;
            color: var(--color-1);
            font-weight: 600;
            overflow-x: auto;
            white-space: nowrap;
            display: flex;
            align-items: center;
        }
        .input-group .btn-copy {
            width: auto;
            margin: 0;
            border-top-left-radius: 0;
            border-bottom-left-radius: 0;
            background-color: var(--color-3); 
            border: 2px solid var(--color-3);
            padding: 0 20px;
        }
        .input-group .btn-copy:hover {
            background-color: #e55a38;
            border-color: #e55a38;
        }
        .input-group .btn-copy-alt {
            background-color: var(--color-2); 
            border-color: var(--color-2);
        }
        .input-group .btn-copy-alt:hover {
            background-color: var(--color-1);
            border-color: var(--color-1);
        }
        
        .error-alert {
            background-color: rgba(255, 101, 63, 0.1);
            color: var(--color-3);
            border: 1px solid var(--color-3);
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-weight: 600;
            text-align: left;
        }
    </style>
"""


@app.route('/', methods=['GET'])
def index():
    error_msg = request.args.get('error')
    error_html = ""
    if error_msg:
        error_html = f"""
        <div class="error-alert">
            <i class="fa-solid fa-triangle-exclamation"></i> {error_msg}
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>URL Shortener</title>
        {GLOBAL_CSS}
    </head>
    <body>
        <div class="card">
            <h2><i class="fa-solid fa-link" style="color: var(--color-3);"></i> URL Shortener</h2>
            
            {error_html}

            <form action="/shorten" method="POST">
                <div style="text-align: left;">
                    <label class="section-label">URL Asli</label>
                    <input type="url" name="url" placeholder="https://contoh.com/halaman-panjang" required>
                    
                    <label class="section-label">Short URL Kustom (Opsional)</label>
                    <input type="text" name="custom_code" placeholder="Misal: shorturl">
                </div>
                <button type="submit" class="btn"><i class="fa-solid fa-compress"></i> Buat Short URL</button>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route('/stats/<stat_code>', methods=['GET'])
def link_stats(stat_code):
    mapping = URLMapping.query.filter_by(stat_code=stat_code).first()
    if not mapping:
        return "<h2 style='text-align:center; color:red; margin-top:50px;'><i class='fa-solid fa-circle-exclamation'></i> Data tidak ditemukan (404)</h2>", 404

    short_url = request.host_url + mapping.short_code

    img = qrcode.make(short_url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Analitik Short URL</title>
        {GLOBAL_CSS}
    </head>
    <body>
        <div class="card">
            <h2><i class="fa-solid fa-chart-line" style="color: var(--color-3);"></i> Analitik Short URL</h2>
            
            <div style="text-align: left; margin-top: 20px;">
                <div class="section-label">URL Asli:</div>
                <a href="{mapping.original_url}" target="_blank" style="word-break: break-all; color: var(--color-2);">{mapping.original_url}</a>
                
                <div class="section-label" style="margin-top: 15px;">Short URL:</div>
                <a href="{request.host_url + mapping.short_code}" target="_blank" style="color: var(--color-2);">{request.host_url + mapping.short_code}</a>
            </div>
            
            <div style="text-align: center; margin-top: 30px; margin-bottom: 30px;">
                <div class="section-label">Kode QR Short URL</div>
                <img src="data:image/png;base64,{qr_base64}" width="140" style="border: 2px solid var(--color-2); padding: 5px; border-radius: 8px; background: white;">
            </div>

            <div style="background: linear-gradient(135deg, var(--color-3), var(--color-4)); color: white; padding: 30px; border-radius: 10px; margin: 30px 0; box-shadow: 0 4px 15px rgba(255, 101, 63, 0.3);">
                <div style="font-size: 1.1em; font-weight: 600; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);">Total Kunjungan</div>
                <div style="font-size: 4em; font-weight: bold; margin: 10px 0; line-height: 1; text-shadow: 2px 2px 4px rgba(0,0,0,0.2);">{mapping.clicks}</div>
                <div style="font-size: 0.9em; font-weight: 600; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);">kali diakses</div>
            </div>

            <a href="/" class="btn btn-outline"><i class="fa-solid fa-arrow-left"></i> Kembali ke Beranda</a>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "success", "message": "Aplikasi berjalan dengan normal"}), 200


@app.route('/shorten', methods=['POST'])
def shorten_url():
    original_url = request.form.get('url')
    custom_code = request.form.get('custom_code')
    
    if not original_url: 
        error_msg = urllib.parse.quote("URL tidak boleh kosong!")
        return redirect(f"/?error={error_msg}")

    if custom_code:
        custom_code = custom_code.strip().replace(" ", "-")
        if URLMapping.query.filter_by(short_code=custom_code).first():
            error_msg = urllib.parse.quote(f"Kode kustom '{custom_code}' sudah terpakai. Silakan gunakan kode lain.")
            return redirect(f"/?error={error_msg}")
        short_code = custom_code
    else:
        short_code = generate_random_string(6)

    stat_code = generate_random_string(10)

    while URLMapping.query.filter_by(stat_code=stat_code).first():
        stat_code = generate_random_string(10)

    new_mapping = URLMapping(original_url=original_url, short_code=short_code, stat_code=stat_code)
    db.session.add(new_mapping)
    db.session.commit()

    short_url = request.host_url + short_code
    stats_url = request.host_url + 'stats/' + stat_code

    img = qrcode.make(short_url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    result_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Short URL Berhasil Dibuat</title>
        {GLOBAL_CSS}
    </head>
    <body>
        <div class="card card-left">
            <h2 style="color: var(--color-1); text-align: center;"><i class="fa-solid fa-circle-check" style="color: var(--color-4);"></i> Berhasil Dibuat</h2>
            <p style="text-align: center; font-size: 0.9em; color: var(--color-1); background-color: rgba(255, 200, 92, 0.2); padding: 10px; border-radius: 6px; border: 1px solid var(--color-4);">
                <i class="fa-solid"></i> <strong>Penting:</strong>Simpan kedua URL di bawah ini.
            </p>
            
            <div style="margin-bottom: 25px; margin-top: 25px;">
                <div class="section-label"><i class="fa-solid fa-share-nodes"></i> URL Publik</div>
                <div class="input-group">
                    <div class="alert-box" id="shortUrl">{short_url}</div>
                    <button class="btn btn-copy" onclick="copyLink('shortUrl')" title="Salin URL"><i class="fa-solid fa-copy"></i> Salin</button>
                </div>
            </div>

            <div style="margin-bottom: 25px;">
                <div class="section-label"><i class="fa-solid fa-lock"></i> URL Analitik</div>
                <div class="input-group">
                    <div class="alert-box" id="statsUrl" style="background-color: #e2e3e5;">{stats_url}</div>
                    <button class="btn btn-copy btn-copy-alt" onclick="copyLink('statsUrl')" title="Salin URL Analitik"><i class="fa-solid fa-copy"></i> Salin</button>
                </div>
                <div class="info-text">Gunakan URL ini untuk melihat jumlah kunjungan.</div>
            </div>

            <div style="text-align: center; margin-top: 30px;">
                <div class="section-label">Kode QR Short URL</div>
                <img src="data:image/png;base64,{qr_base64}" width="160" style="border: 2px solid var(--color-2); padding: 5px; border-radius: 8px; background: white;">
            </div>

            <hr>
            <div style="text-align: center;">
                <a href="/" class="btn btn-outline" style="margin-top: 0; width: 100%;"><i class="fa-solid fa-arrow-left"></i> Kembali ke Beranda</a>
            </div>
        </div>

        <script>
            function copyLink(elementId) {{
                var text = document.getElementById(elementId).innerText;

                if (navigator.clipboard && window.isSecureContext) {{
                    navigator.clipboard.writeText(text).then(function() {{
                        alert("URL berhasil disalin ke papan klip!");
                    }}).catch(function() {{
                        alert("Gagal menyalin. Silakan blok teks dan salin manual.");
                    }});
                }} else {{
                    var textArea = document.createElement("textarea");
                    textArea.value = text;
                    
                    textArea.style.position = "fixed";
                    textArea.style.opacity = "0";
                    document.body.appendChild(textArea);
                    
                    textArea.select();
                    try {{
                        var successful = document.execCommand('copy');
                        if (successful) {{
                            alert("URL berhasil disalin ke papan klip!");
                        }} else {{
                            alert("Gagal menyalin. Silakan blok teks dan salin manual.");
                        }}
                    }} catch (err) {{
                        alert("Browser Anda tidak mendukung fitur ini.");
                    }}
                    document.body.removeChild(textArea);
                }}
            }}
        </script>
    </body>
    </html>
    """
    return render_template_string(result_html)


@app.route('/initdb')
def init_db():
    try:
        db.create_all()
        return "<h3 style='color: green;'>Sukses: Tabel database berhasil dibuat di AWS RDS MySQL!</h3><br><a href='/'>Kembali ke Beranda</a>"
    except Exception as e:
        return f"<h3 style='color: red;'>Gagal membuat tabel:</h3><p>{str(e)}</p>"
    
@app.route('/<short_code>', methods=['GET'])
def redirect_to_url(short_code):
    mapping = URLMapping.query.filter_by(short_code=short_code).first()
    if mapping:
        mapping.clicks += 1
        db.session.commit()
        return redirect(mapping.original_url)
    return "URL tidak ditemukan (404)", 404


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)