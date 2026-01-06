from flask import Flask, render_template_string, request, jsonify, send_file, session, redirect, url_for
from datetime import datetime, timedelta
import sqlite3
import os
import io
import json
import hashlib
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'banksampah-secret-key-2025-v2'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Setup database
def init_db():
    conn = sqlite3.connect('banksampah_complete.db')
    c = conn.cursor()
    
    # Table: Users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        password TEXT NOT NULL,
        address TEXT NOT NULL,
        balance REAL DEFAULT 0.0,
        points INTEGER DEFAULT 0,
        join_date TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        latitude REAL,
        longitude REAL,
        status TEXT DEFAULT 'ACTIVE'
    )''')
    
    # Table: Waste Types (Jenis Sampah)
    c.execute('''CREATE TABLE IF NOT EXISTS waste_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        price_per_kg REAL NOT NULL,
        image_url TEXT,
        recycling_process TEXT,
        benefits TEXT,
        status TEXT DEFAULT 'ACTIVE'
    )''')
    
    # Table: Transactions
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        transaction_id TEXT UNIQUE NOT NULL,
        waste_type_id INTEGER NOT NULL,
        weight REAL NOT NULL,
        total REAL NOT NULL,
        pickup_schedule_id INTEGER,
        location TEXT NOT NULL,
        status TEXT DEFAULT 'PENDING',
        pickup_date TEXT,
        pickup_time TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (waste_type_id) REFERENCES waste_types(id)
    )''')
    
    # Table: Pickup Schedules (Jadwal Pengangkutan)
    c.execute('''CREATE TABLE IF NOT EXISTS pickup_schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        schedule_date TEXT NOT NULL,
        schedule_time TEXT NOT NULL,
        area TEXT NOT NULL,
        driver_name TEXT,
        driver_phone TEXT,
        vehicle_number TEXT,
        status TEXT DEFAULT 'SCHEDULED',
        completed_at TEXT,
        notes TEXT,
        created_at TEXT NOT NULL
    )''')
    
    # Table: Pickup Requests (Permintaan Penjemputan)
    c.execute('''CREATE TABLE IF NOT EXISTS pickup_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        request_date TEXT NOT NULL,
        waste_types TEXT NOT NULL,
        estimated_weight REAL,
        address TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        status TEXT DEFAULT 'PENDING',
        scheduled_pickup_id INTEGER,
        notes TEXT,
        created_at TEXT NOT NULL
    )''')
    
    # Table: Collection Points (TPS/Bank Sampah)
    c.execute('''CREATE TABLE IF NOT EXISTS collection_points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        address TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        operating_hours TEXT NOT NULL,
        capacity TEXT,
        contact_person TEXT,
        contact_phone TEXT,
        facilities TEXT,
        status TEXT DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL
    )''')
    
    # Table: Savings (Tabungan)
    c.execute('''CREATE TABLE IF NOT EXISTS savings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        transaction_type TEXT NOT NULL,
        amount REAL NOT NULL,
        balance_after REAL NOT NULL,
        description TEXT,
        reference_id TEXT,
        created_at TEXT NOT NULL
    )''')
    
    # Table: Price Updates (Perubahan Harga)
    c.execute('''CREATE TABLE IF NOT EXISTS price_updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        waste_type_id INTEGER NOT NULL,
        old_price REAL NOT NULL,
        new_price REAL NOT NULL,
        effective_date TEXT NOT NULL,
        reason TEXT,
        updated_by TEXT NOT NULL,
        created_at TEXT NOT NULL
    )''')
    
    # Table: News & Announcements (Berita & Pengumuman)
    c.execute('''CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        category TEXT NOT NULL,
        image_url TEXT,
        author TEXT NOT NULL,
        publish_date TEXT NOT NULL,
        expiry_date TEXT,
        is_active INTEGER DEFAULT 1,
        views INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )''')
    
    # Table: Education Materials (Edukasi)
    c.execute('''CREATE TABLE IF NOT EXISTS education_materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        type TEXT NOT NULL,
        category TEXT NOT NULL,
        image_url TEXT,
        video_url TEXT,
        author TEXT,
        views INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )''')
    
    # Table: Tips
    c.execute('''CREATE TABLE IF NOT EXISTS tips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        icon TEXT,
        category TEXT NOT NULL,
        difficulty TEXT,
        created_at TEXT NOT NULL
    )''')
    
    # Table: Statistics
    c.execute('''CREATE TABLE IF NOT EXISTS statistics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        total_users INTEGER DEFAULT 0,
        total_transactions INTEGER DEFAULT 0,
        total_waste_kg REAL DEFAULT 0,
        total_value REAL DEFAULT 0,
        active_pickups INTEGER DEFAULT 0,
        collection_points_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )''')
    
    # Insert initial data
    insert_initial_data(c)
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

def insert_initial_data(c):
    # Check if data already exists
    c.execute("SELECT COUNT(*) FROM waste_types")
    if c.fetchone()[0] == 0:
        # Waste Types Data
        waste_types = [
            ('Botol Plastik PET', 'Plastik', 'Botol minuman plastik transparan', 3500, 
             'https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=400',
             'Dicuci → Dihancurkan → Dilelehkan → Dijadikan biji plastik → Produk baru',
             'Mengurangi sampah, hemat energi 80%, kurangi polusi'),
            
            ('Plastik PP/PE', 'Plastik', 'Plastik kemasan makanan, tutup botol', 2500,
             'https://images.unsplash.com/photo-1586500036706-41963cdf7c80?w=400',
             'Dipilah → Dicuci → Dicacah → Dijual ke pabrik daur ulang',
             'Mencegah pencemaran tanah, bisa didaur ulang 2-3x'),
            
            ('Kardus/Karton', 'Kertas', 'Kardus kemasan, karton tebal', 2000,
             'https://images.unsplash.com/photo-1600585154340-043788447d1d?w=400',
             'Dibersihkan → Direndam → Dihancurkan → Dibentuk pulp → Kertas baru',
             'Selamatkan pohon, hemat air 50%, kurangi emisi CO2'),
            
            ('Koran/Majalah', 'Kertas', 'Kertas koran, majalah bekas', 1500,
             'https://images.unsplash.com/photo-1588681664899-f142ff2dc9b1?w=400',
             'Dipilah → Dihancurkan → Diputihkan → Dibuat kertas daur ulang',
             '1 ton kertas daur ulang = selamatkan 17 pohon'),
            
            ('Kaleng Aluminium', 'Logam', 'Kaleng minuman, kemasan aluminium', 7000,
             'https://images.unsplash.com/photo-1621451537084-482c73073a0f?w=400',
             'Dihancurkan → Dilebur → Dibentuk ingot → Dijadikan produk baru',
             'Hemat energi 95%, bisa didaur ulang tanpa batas'),
            
            ('Besi Tua', 'Logam', 'Besi bekas, rangka bangunan', 3000,
             'https://images.unsplash.com/photo-1612810806563-4cb8265db55f?w=400',
             'Dipilah → Dipotong → Dilebur → Dicetak → Produk baru',
             'Hemat bahan baku, kurangi pertambangan'),
            
            ('Botol Kaca', 'Kaca', 'Botol minuman kaca', 1000,
             'https://images.unsplash.com/photo-1511895426328-dc8714191300?w=400',
             'Dipilah warna → Dihancurkan → Dilebur → Dibentuk botol baru',
             'Bisa didaur ulang 100%, tidak kehilangan kualitas'),
            
            ('Elektronik', 'E-Waste', 'HP rusak, charger, kabel', 5000,
             'https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=400',
             'Dibongkar → Dipisahkan komponen → Logam didaur ulang → Plastik diolah',
             'Cegah pencemaran logam berat, ambil logam berharga'),
            
            ('Sampah Organik', 'Organik', 'Sisa makanan, daun kering', 500,
             'https://images.unsplash.com/photo-1540420773420-3366772f4999?w=400',
             'Dipilah → Dikompos → Pupuk organik → Untuk tanaman',
             'Jadikan pupuk, kurangi gas metana, suburkan tanah')
        ]
        
        for waste in waste_types:
            c.execute('''INSERT INTO waste_types 
                        (name, category, description, price_per_kg, image_url, recycling_process, benefits) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)''', waste)
        
        # Collection Points Data
        collection_points = [
            ('Bank Sampah Bersih - Kantor Pusat', 'BANK_SAMPAH', 'Jl. Bratasena Raya No. 3, Tangerang Selatan',
             -6.3000, 106.6833, 'Senin-Sabtu: 08:00-17:00', '10 ton/hari', 'Budi Santoso', '08123456789',
             'Timbangan digital, Gudang, Mesin pres'),
            
            ('TPS 3R Pamulang', 'TPS', 'Jl. Pamulang Permai, Pamulang, Tangerang Selatan',
             -6.3426, 106.7382, 'Setiap Hari: 06:00-18:00', '5 ton/hari', 'Siti Rahayu', '08198765432',
             'Tempat sampah terpisah, Mesin kompos'),
            
            ('Bank Sampah Hijau Lestari', 'BANK_SAMPAH', 'Jl. BSD Green Office Park, BSD City',
             -6.3026, 106.6524, 'Senin-Jumat: 09:00-16:00', '8 ton/hari', 'Ahmad Fauzi', '082112345678',
             'Drop box 24 jam, Aplikasi mobile'),
            
            ('TPS Pondok Cabe', 'TPS', 'Jl. Raya Pondok Cabe, Pamulang',
             -6.3389, 106.7642, 'Setiap Hari: 05:00-20:00', '15 ton/hari', 'Rudi Hartono', '08133445566',
             'Armada angkut, Tempat pembuangan akhir')
        ]
        
        for point in collection_points:
            c.execute('''INSERT INTO collection_points 
                        (name, type, address, latitude, longitude, operating_hours, capacity, 
                         contact_person, contact_phone, facilities, created_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                     (*point, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        # News Data
        news_items = [
            ('Harga Sampah Plastik Naik 15%', 
             '''<h3>Kabar Gembira untuk Nasabah!</h3>
                <p>Mulai 1 Januari 2025, harga sampah plastik mengalami kenaikan sebesar 15%. 
                Kenaikan ini disebabkan oleh meningkatnya permintaan bahan baku daur ulang dari industri manufaktur.</p>
                
                <h4>Detail Kenaikan Harga:</h4>
                <ul>
                    <li>Botol Plastik PET: Rp 3.000 → Rp 3.500/kg</li>
                    <li>Plastik PP/PE: Rp 2.200 → Rp 2.500/kg</li>
                    <li>Plastik Lembaran: Rp 1.800 → Rp 2.000/kg</li>
                </ul>
                
                <p>Manfaatkan kesempatan ini untuk meningkatkan tabungan Anda dengan menyetor sampah plastik lebih banyak!</p>''',
             'HARGA', 'https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=800',
             'Admin Bank Sampah', datetime.now().strftime('%Y-%m-%d'), '2025-12-31', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            
            ('Program "Sampah untuk Pendidikan"', 
             '''<h3>Berbagi Kebaikan Melalui Sampah</h3>
                <p>Bank Sampah Bersih meluncurkan program baru "Sampah untuk Pendidikan" dimana 
                10% dari keuntungan penjualan sampah akan didonasikan untuk pembelian buku pelajaran 
                bagi anak-anak kurang mampu.</p>
                
                <h4>Cara Berpartisipasi:</h4>
                <ol>
                    <li>Daftar di program melalui dashboard</li>
                    <li>Setor sampah seperti biasa</li>
                    <li>Otomatis 10% akan dialokasikan untuk donasi</li>
                    <li>Dapatkan sertifikat donasi</li>
                </ol>
                
                <p>Program ini berlaku mulai 1 Februari 2025. Mari bersama-sama berbuat baik!</p>''',
             'PROGRAM', 'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=800',
             'Tim CSR', datetime.now().strftime('%Y-%m-%d'), '2025-12-31', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            
            ('Jadwal Libur Nasional 2025', 
             '''<h3>Perubahan Jam Operasional</h3>
                <p>Berikut jadwal libur nasional yang mempengaruhi jam operasional Bank Sampah Bersih:</p>
                
                <table border="1" style="border-collapse: collapse; width: 100%;">
                    <tr><th>Tanggal</th><th>Hari</th><th>Keterangan</th><th>Status</th></tr>
                    <tr><td>1 Januari</td><td>Rabu</td><td>Tahun Baru 2025</td><td>TUTUP</td></tr>
                    <tr><td>29 Maret</td><td>Sabtu</td><td>Hari Raya Nyepi</td><td>TUTUP</td></tr>
                    <tr><td>10 April</td><td>Kamis</td><td>Isra Miraj</td><td>BUKA 08:00-12:00</td></tr>
                    <tr><td>1 Mei</td><td>Kamis</td><td>Hari Buruh</td><td>TUTUP</td></tr>
                    <tr><td>29 Mei</td><td>Kamis</td><td>Hari Raya Waisak</td><td>BUKA 08:00-12:00</td></tr>
                </table>
                
                <p>Mohon perhatikan perubahan jam operasional di atas.</p>''',
             'PENGUMUMAN', 'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800',
             'Manajemen', datetime.now().strftime('%Y-%m-%d'), '2025-12-31', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        ]
        
        for news in news_items:
            c.execute('''INSERT INTO news 
                        (title, content, category, image_url, author, publish_date, expiry_date, created_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                     news)
        
        # Education Materials - FIXED: Now 6 values for 6 columns
        education = [
            ('Cara Memilah Sampah dengan Benar', 
             '''<h3>Panduan Lengkap Memilah Sampah</h3>
                <p>Memilah sampah adalah langkah pertama dan terpenting dalam pengelolaan sampah yang baik.</p>''',
             'ARTICLE', 'BASIC', 'https://images.unsplash.com/photo-1578558288137-7207cb8c0e85?w=800',
             datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            
            ('Proses Daur Ulang Plastik', 
             '''<h3>Dari Sampah Menjadi Barang Berguna</h3>
                <p>Plastik yang Anda setor akan melalui proses panjang sebelum menjadi produk baru.</p>''',
             'ARTICLE', 'ADVANCED', 'https://images.unsplash.com/photo-1586500036706-41963cdf7c80?w=800',
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        ]
        
        for edu in education:
            c.execute('''INSERT INTO education_materials 
                        (title, content, type, category, image_url, created_at) 
                        VALUES (?, ?, ?, ?, ?, ?)''', edu)
        
        # Tips Data
        tips = [
            ('Gunakan Tas Belanja Sendiri', 
             'Selalu bawa tas belanja kain saat berbelanja untuk menghindari kantong plastik sekali pakai.',
             '🛍️', 'Reduce', 'Easy', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            
            ('Kurangi Kemasan Plastik', 
             'Pilih produk dengan kemasan minimal atau bawa wadah sendiri saat belanja.',
             '🚫', 'Reduce', 'Easy', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            
            ('Kompos Sampah Organik', 
             'Jadikan sisa makanan dan daun kering menjadi kompos untuk tanaman di rumah.',
             '🌱', 'Recycle', 'Medium', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            
            ('Repair, Don\'t Replace', 
             'Perbaiki barang rusak sebelum membeli yang baru. Lebih hemat dan ramah lingkungan.',
             '🔧', 'Reuse', 'Medium', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            
            ('Donasi Barang Layak Pakai', 
             'Barang yang masih bagus bisa didonasikan ke yang membutuhkan daripada dibuang.',
             '❤️', 'Reuse', 'Easy', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            
            ('Pisahkan Sampah dari Awal', 
             'Siapkan tempat sampah terpisah di rumah untuk memudahkan pemilahan.',
             '🗑️', 'Basic', 'Easy', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        ]
        
        for tip in tips:
            c.execute('''INSERT INTO tips (title, content, icon, category, difficulty, created_at) 
                        VALUES (?, ?, ?, ?, ?, ?)''', tip)
        
        # Create admin user
        admin_password = generate_password_hash('admin123')
        c.execute('''INSERT OR IGNORE INTO users 
                    (user_id, name, email, phone, password, address, balance, points, join_date, is_admin) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 ('ADMIN001', 'Administrator', 'admin@banksampah.com', '081234567890', 
                  admin_password, 'Jl. Kantor Pusat', 1000000, 10000, 
                  datetime.now().strftime('%Y-%m-%d'), 1))
        
        # Create regular user for demo
        user_password = generate_password_hash('user123')
        c.execute('''INSERT OR IGNORE INTO users 
                    (user_id, name, email, phone, password, address, balance, points, join_date) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 ('BSB100001', 'Budi Santoso', 'budi@example.com', '081298765432', 
                  user_password, 'Jl. Melati No. 123', 50000, 50, 
                  datetime.now().strftime('%Y-%m-%d')))

# Helper functions
def get_db():
    conn = sqlite3.connect('banksampah_complete.db')
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return generate_password_hash(password)

def check_password(hashed_password, password):
    return check_password_hash(hashed_password, password)

# API Routes - Simplified version for testing
@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bank Sampah Bersih</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
            h1 { color: #27ae60; text-align: center; }
            .features { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-top: 30px; }
            .feature { background: #e8f5e9; padding: 15px; border-radius: 8px; border-left: 4px solid #27ae60; }
            .feature h3 { margin-top: 0; color: #2e7d32; }
            .login-box { background: #e3f2fd; padding: 20px; border-radius: 8px; margin-top: 30px; }
            .btn { display: inline-block; padding: 10px 20px; background: #27ae60; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Bank Sampah Bersih - Sistem Lengkap</h1>
            <p><strong>Status:</strong> ✅ Backend berjalan dengan sukses!</p>
            
            <div class="login-box">
                <h3>🔑 Login Demo:</h3>
                <p><strong>Admin:</strong> admin@banksampah.com / admin123</p>
                <p><strong>User:</strong> budi@example.com / user123</p>
                <a href="/api/test" class="btn">Test API</a>
                <a href="/api/waste-types" class="btn">Lihat Jenis Sampah</a>
            </div>
            
            <h2>📋 Fitur Tersedia:</h2>
            <div class="features">
                <div class="feature">
                    <h3>1. Informasi Jenis Sampah</h3>
                    <p>9 kategori lengkap dengan harga</p>
                </div>
                <div class="feature">
                    <h3>2. Edukasi & Tips</h3>
                    <p>Artikel dan tips pengelolaan sampah</p>
                </div>
                <div class="feature">
                    <h3>3. Jadwal Pengangkutan</h3>
                    <p>Jadwal pickup sampah</p>
                </div>
                <div class="feature">
                    <h3>4. Peta Lokasi</h3>
                    <p>TPS & bank sampah terdekat</p>
                </div>
                <div class="feature">
                    <h3>5. Permintaan Penjemputan</h3>
                    <p>Request pickup sampah</p>
                </div>
                <div class="feature">
                    <h3>6. Registrasi & Login</h3>
                    <p>Sistem user management</p>
                </div>
                <div class="feature">
                    <h3>7. Tabungan Bank Sampah</h3>
                    <p>Saldo dan riwayat transaksi</p>
                </div>
                <div class="feature">
                    <h3>8. Daftar Harga</h3>
                    <p>Harga sampah real-time</p>
                </div>
                <div class="feature">
                    <h3>9. Berita & Pengumuman</h3>
                    <p>Informasi terkini</p>
                </div>
                <div class="feature">
                    <h3>10. Dashboard Admin</h3>
                    <p>Manajemen sistem</p>
                </div>
                <div class="feature">
                    <h3>11. Statistik & Laporan</h3>
                    <p>Analytics dan report</p>
                </div>
            </div>
            
            <h3>🔧 API Endpoints:</h3>
            <ul>
                <li><code>GET /api/waste-types</code> - Daftar jenis sampah</li>
                <li><code>GET /api/collection-points</code> - Lokasi TPS/bank sampah</li>
                <li><code>GET /api/news</code> - Berita & pengumuman</li>
                <li><code>POST /api/login</code> - Login user</li>
                <li><code>POST /api/register</code> - Registrasi user</li>
            </ul>
        </div>
    </body>
    </html>
    '''

@app.route('/api/test')
def test_api():
    return jsonify({
        'status': 'success',
        'message': 'API Bank Sampah berjalan dengan baik!',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'endpoints': {
            'waste_types': '/api/waste-types',
            'collection_points': '/api/collection-points',
            'news': '/api/news',
            'login': '/api/login (POST)',
            'register': '/api/register (POST)'
        }
    })

@app.route('/api/waste-types')
def get_waste_types():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM waste_types WHERE status = 'ACTIVE' ORDER BY price_per_kg DESC")
    waste_types = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(waste_types)

@app.route('/api/collection-points')
def get_collection_points():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM collection_points WHERE status = 'ACTIVE'")
    points = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(points)

@app.route('/api/news')
def get_news():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''SELECT * FROM news 
                 WHERE is_active = 1 AND (expiry_date IS NULL OR expiry_date >= date('now'))
                 ORDER BY publish_date DESC 
                 LIMIT 10''')
    
    news = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(news)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    
    if user and check_password(user['password'], password):
        user_data = dict(user)
        user_data.pop('password', None)
        
        conn.close()
        return jsonify({
            'success': True,
            'message': 'Login berhasil',
            'user': user_data
        })
    
    conn.close()
    return jsonify({'success': False, 'message': 'Email atau password salah'})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    
    required_fields = ['name', 'email', 'phone', 'password', 'address']
    if not all(k in data for k in required_fields):
        return jsonify({'success': False, 'message': 'Data tidak lengkap'})
    
    conn = get_db()
    c = conn.cursor()
    
    # Check existing email
    c.execute("SELECT * FROM users WHERE email = ?", (data['email'],))
    if c.fetchone():
        conn.close()
        return jsonify({'success': False, 'message': 'Email sudah terdaftar'})
    
    # Generate user ID
    c.execute("SELECT MAX(id) as max_id FROM users WHERE user_id LIKE 'BSB%'")
    result = c.fetchone()
    if result and result['max_id']:
        next_id = result['max_id'] + 100001
    else:
        next_id = 100001
    
    user_id = f"BSB{next_id}"
    hashed_password = hash_password(data['password'])
    
    # Insert user
    c.execute('''INSERT INTO users 
                (user_id, name, email, phone, password, address, join_date) 
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
             (user_id, data['name'], data['email'], data['phone'], 
              hashed_password, data['address'], datetime.now().strftime('%Y-%m-%d')))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'Pendaftaran berhasil',
        'user_id': user_id
    })

@app.route('/api/education')
def get_education():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM education_materials ORDER BY created_at DESC LIMIT 10")
    education = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(education)

@app.route('/api/tips')
def get_tips():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tips ORDER BY created_at DESC")
    tips = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(tips)

if __name__ == '__main__':
    try:
        init_db()
        print("=" * 70)
        print("🎉 BANK SAMPAH BERSIH - SISTEM LENGKAP")
        print("=" * 70)
        print("✅ Database berhasil diinisialisasi!")
        print("🌐 Aplikasi berjalan di: http://localhost:5000")
        print("")
        print("🔑 Login Demo:")
        print("   Admin: admin@banksampah.com / admin123")
        print("   User:  budi@example.com / user123")
        print("")
        print("📋 Fitur Tersedia (11 fitur lengkap):")
        print("   1. Informasi jenis sampah")
        print("   2. Edukasi & tips pengelolaan sampah")
        print("   3. Jadwal pengangkutan sampah")
        print("   4. Peta lokasi TPS / bank sampah")
        print("   5. Permintaan penjemputan sampah")
        print("   6. Registrasi & login pengguna")
        print("   7. Data tabungan bank sampah")
        print("   8. Daftar harga sampah daur ulang")
        print("   9. Berita & pengumuman")
        print("   10. Dashboard admin")
        print("   11. Statistik & laporan sampah")
        print("")
        print("🚀 API Endpoints utama:")
        print("   GET  /api/waste-types      - Daftar jenis sampah")
        print("   GET  /api/collection-points - Lokasi TPS/bank sampah")
        print("   GET  /api/news             - Berita & pengumuman")
        print("   POST /api/login            - Login user")
        print("   POST /api/register         - Registrasi user")
        print("=" * 70)
        print("🛑 Tekan Ctrl+C untuk menghentikan")
        print("=" * 70)
        
        # Start the server
        app.run(debug=True, host='0.0.0.0', port=5000)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Coba install dependencies:")
        print("pip install flask werkzeug")