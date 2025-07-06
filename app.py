from flask import Flask, request, send_file, render_template_string
from werkzeug.utils import secure_filename
import sqlite3
import os
from io import BytesIO
from datetime import datetime, timedelta
import uuid
import hashlib

app = Flask(__name__)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('files.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS files (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    user_password_hash TEXT NOT NULL,
                    access_code TEXT NOT NULL,
                    content BLOB NOT NULL,
                    upload_time TIMESTAMP NOT NULL
                )''')
    conn.commit()
    conn.close()

init_db()

# HTML template with Tailwind CSS
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>File Share & Upload</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center">
    <div class="container mx-auto p-6 bg-white rounded-lg shadow-lg max-w-2xl">
        <h1 class="text-3xl font-bold text-center text-gray-800 mb-6">File Share & Upload</h1>
        <form method="post" enctype="multipart/form-data" action="/upload" class="mb-6">
            <div class="flex flex-col space-y-4">
                <input type="password" name="password" placeholder="Set a password" required class="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                <input type="file" name="file" required class="file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100">
                <button type="submit" class="bg-blue-500 text-white py-2 px-4 rounded-lg hover:bg-blue-600 transition">Upload File</button>
            </div>
        </form>
        <form method="post" action="/" class="mb-6">
            <div class="flex flex-col space-y-4">
                <input type="password" name="password" placeholder="Enter password to view files" required class="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                <button type="submit" class="bg-blue-500 text-white py-2 px-4 rounded-lg hover:bg-blue-600 transition">View Files</button>
            </div>
        </form>
        {% if message %}
            <p class="{% if error %}text-red-500{% else %}text-green-500{% endif %} text-center mb-4">{{ message }}</p>
        {% endif %}
        {% if files %}
            <h2 class="text-2xl font-semibold text-gray-700 mb-4">Your Files</h2>
            <div class="space-y-4">
                {% for file in files %}
                    <div class="flex justify-between items-center p-4 bg-gray-50 rounded-lg shadow">
                        <div>
                            <span class="text-blue-500">{{ file[1] }}</span>
                            <p class="text-sm text-gray-500">Uploaded: {{ file[5] }}</p>
                            <p class="text-sm text-gray-500">Access Code: {{ file[3] }}</p>
                        </div>
                        <form action="/download/{{ file[0] }}" method="post" class="flex space-x-2">
                            <input type="hidden" name="password" value="{{ password }}">
                            <input type="text" name="access_code" placeholder="Enter access code" class="border rounded-lg px-2 py-1 text-sm" required>
                            <button type="submit" class="bg-blue-500 text-white px-3 py-1 rounded-lg hover:bg-blue-600 transition">Download</button>
                        </form>
                    </div>
                {% endfor %}
            </div>
        {% endif %}
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    files = []
    password = None
    message = None
    error = False
    
    if request.method == 'POST':
        password = request.form.get('password')
        if not password:
            return render_template_string(HTML_TEMPLATE, message="Password is required", error=True)
        
        # Hash the password
        user_password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Fetch user's files
        conn = sqlite3.connect('files.db')
        c = conn.cursor()
        # Clean up expired files
        expiration_time = datetime.utcnow() - timedelta(hours=1)
        c.execute("DELETE FROM files WHERE upload_time < ?", (expiration_time,))
        conn.commit()
        
        c.execute("SELECT id, filename, user_password_hash, access_code, content, upload_time FROM files WHERE user_password_hash = ?", (user_password_hash,))
        files = c.fetchall()
        conn.close()
        
        if not files:
            message = "No files found for this password or incorrect password"
            error = True
    
    return render_template_string(HTML_TEMPLATE, files=files, password=password, message=message, error=error)

@app.route('/upload', methods=['POST'])
def upload_file():
    password = request.form.get('password')
    if not password:
        return render_template_string(HTML_TEMPLATE, message="Password is required", error=True)
    
    user_password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if 'file' not in request.files:
        conn = sqlite3.connect('files.db')
        c = conn.cursor()
        c.execute("SELECT id, filename, user_password_hash, access_code, content, upload_time FROM files WHERE user_password_hash = ?", (user_password_hash,))
        files = c.fetchall()
        conn.close()
        return render_template_string(HTML_TEMPLATE, files=files, password=password, message="No file selected", error=True)
    
    file = request.files['file']
    if file.filename == '':
        conn = sqlite3.connect('files.db')
        c = conn.cursor()
        c.execute("SELECT id, filename, user_password_hash, access_code, content, upload_time FROM files WHERE user_password_hash = ?", (user_password_hash,))
        files = c.fetchall()
        conn.close()
        return render_template_string(HTML_TEMPLATE, files=files, password=password, message="No file selected", error=True)
    
    if file:
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        access_code = hashlib.md5((filename + str(datetime.utcnow())).encode()).hexdigest()[:8]
        file_content = file.read()
        upload_time = datetime.utcnow()
        
        conn = sqlite3.connect('files.db')
        c = conn.cursor()
        c.execute("INSERT INTO files (id, filename, user_password_hash, access_code, content, upload_time) VALUES (?, ?, ?, ?, ?, ?)",
                 (file_id, filename, user_password_hash, access_code, file_content, upload_time))
        conn.commit()
        c.execute("SELECT id, filename, user_password_hash, access_code, content, upload_time FROM files WHERE user_password_hash = ?", (user_password_hash,))
        files = c.fetchall()
        conn.close()
        
        return render_template_string(HTML_TEMPLATE, files=files, password=password, message=f"File {filename} uploaded successfully. Access code: {access_code}")

@app.route('/download/<file_id>', methods=['POST'])
def download_file(file_id):
    password = request.form.get('password')
    if not password:
        return render_template_string(HTML_TEMPLATE, message="Password is required", error=True)
    
    user_password_hash = hashlib.sha256(password.encode()).hexdigest()
    provided_code = request.form.get('access_code')
    
    conn = sqlite3.connect('files.db')
    c = conn.cursor()
    c.execute("SELECT id, filename, user_password_hash, access_code, content, upload_time FROM files WHERE user_password_hash = ?", (user_password_hash,))
    files = c.fetchall()
    
    c.execute("SELECT filename, access_code, content FROM files WHERE id = ? AND user_password_hash = ?", (file_id, user_password_hash))
    file_data = c.fetchone()
    conn.close()
    
    if not file_data:
        return render_template_string(HTML_TEMPLATE, files=files, password=password, message="File not found or you don't have access", error=True)
    
    filename, access_code, content = file_data
    if provided_code != access_code:
        return render_template_string(HTML_TEMPLATE, files=files, password=password, message="Invalid access code", error=True)
    
    return send_file(
        BytesIO(content),
        download_name=filename,
        as_attachment=True
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))