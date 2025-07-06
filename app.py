from flask import Flask, request, send_file, render_template_string, make_response
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
                    user_id TEXT NOT NULL,
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
                <input type="file" name="file" required class="file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100">
                <button type="submit" class="bg-blue-500 text-white py-2 px-4 rounded-lg hover:bg-blue-600 transition">Upload File</button>
            </div>
        </form>
        {% if message %}
            <p class="{% if error %}text-red-500{% else %}text-green-500{% endif %} text-center mb-4">{{ message }}</p>
        {% endif %}
        <h2 class="text-2xl font-semibold text-gray-700 mb-4">Your Uploaded Files</h2>
        <div class="space-y-4">
            {% if files %}
                {% for file in files %}
                    <div class="flex justify-between items-center p-4 bg-gray-50 rounded-lg shadow">
                        <div>
                            <a href="/download/{{ file[0] }}" class="text-blue-500 hover:underline">{{ file[1] }}</a>
                            <p class="text-sm text-gray-500">Uploaded: {{ file[5] }}</p>
                            <p class="text-sm text-gray-500">Access Code: {{ file[3] }}</p>
                        </div>
                        <form action="/download/{{ file[0] }}" method="post" class="flex space-x-2">
                            <input type="text" name="access_code" placeholder="Enter access code" class="border rounded-lg px-2 py-1 text-sm" required>
                            <button type="submit" class="bg-blue-500 text-white px-3 py-1 rounded-lg hover:bg-blue-600 transition">Download</button>
                        </form>
                    </div>
                {% endfor %}
            {% else %}
                <p class="text-gray-500 text-center">No files uploaded yet.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    # Get or set user_id cookie
    user_id = request.cookies.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
    
    # Clean up expired files (older than 1 hour)
    conn = sqlite3.connect('files.db')
    c = conn.cursor()
    expiration_time = datetime.utcnow() - timedelta(hours=1)
    c.execute("DELETE FROM files WHERE upload_time < ?", (expiration_time,))
    conn.commit()
    
    # Fetch user's files
    c.execute("SELECT id, filename, user_id, access_code, content, upload_time FROM files WHERE user_id = ?", (user_id,))
    files = c.fetchall()
    conn.close()
    
    resp = make_response(render_template_string(HTML_TEMPLATE, files=files))
    if not request.cookies.get('user_id'):
        resp.set_cookie('user_id', user_id, max_age=60*60*24*30)  # 30 days
    return resp

@app.route('/upload', methods=['POST'])
def upload_file():
    user_id = request.cookies.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
    
    if 'file' not in request.files:
        conn = sqlite3.connect('files.db')
        c = conn.cursor()
        c.execute("SELECT id, filename, user_id, access_code, content, upload_time FROM files WHERE user_id = ?", (user_id,))
        files = c.fetchall()
        conn.close()
        resp = make_response(render_template_string(HTML_TEMPLATE, files=files, message="No file selected", error=True))
        if not request.cookies.get('user_id'):
            resp.set_cookie('user_id', user_id, max_age=60*60*24*30)
        return resp
    
    file = request.files['file']
    if file.filename == '':
        conn = sqlite3.connect('files.db')
        c = conn.cursor()
        c.execute("SELECT id, filename, user_id, access_code, content, upload_time FROM files WHERE user_id = ?", (user_id,))
        files = c.fetchall()
        conn.close()
        resp = make_response(render_template_string(HTML_TEMPLATE, files=files, message="No file selected", error=True))
        if not request.cookies.get('user_id'):
            resp.set_cookie('user_id', user_id, max_age=60*60*24*30)
        return resp
    
    if file:
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        access_code = hashlib.md5((filename + str(datetime.utcnow())).encode()).hexdigest()[:8]  # 8-char access code
        file_content = file.read()
        upload_time = datetime.utcnow()
        
        conn = sqlite3.connect('files.db')
        c = conn.cursor()
        c.execute("INSERT INTO files (id, filename, user_id, access_code, content, upload_time) VALUES (?, ?, ?, ?, ?, ?)",
                 (file_id, filename, user_id, access_code, file_content, upload_time))
        conn.commit()
        c.execute("SELECT id, filename, user_id, access_code, content, upload_time FROM files WHERE user_id = ?", (user_id,))
        files = c.fetchall()
        conn.close()
        
        resp = make_response(render_template_string(HTML_TEMPLATE, files=files, message=f"File {filename} uploaded successfully. Access code: {access_code}"))
        if not request.cookies.get('user_id'):
            resp.set_cookie('user_id', user_id, max_age=60*60*24*30)
        return resp

@app.route('/download/<file_id>', methods=['GET', 'POST'])
def download_file(file_id):
    user_id = request.cookies.get('user_id')
    if not user_id:
        return render_template_string(HTML_TEMPLATE, files=[], message="User session expired. Please upload a file to start a new session.", error=True)
    
    conn = sqlite3.connect('files.db')
    c = conn.cursor()
    c.execute("SELECT id, filename, user_id, access_code, content, upload_time FROM files WHERE user_id = ?", (user_id,))
    files = c.fetchall()
    
    if request.method == 'POST':
        provided_code = request.form.get('access_code')
        c.execute("SELECT filename, access_code, content FROM files WHERE id = ? AND user_id = ?", (file_id, user_id))
        file_data = c.fetchone()
        conn.close()
        
        if not file_data:
            return render_template_string(HTML_TEMPLATE, files=files, message="File not found or you don't have access", error=True)
        
        filename, access_code, content = file_data
        if provided_code != access_code:
            return render_template_string(HTML_TEMPLATE, files=files, message="Invalid access code", error=True)
        
        return send_file(
            BytesIO(content),
            download_name=filename,
            as_attachment=True
        )
    
    c.execute("SELECT filename FROM files WHERE id = ? AND user_id = ?", (file_id, user_id))
    file_data = c.fetchone()
    conn.close()
    
    if not file_data:
        return render_template_string(HTML_TEMPLATE, files=files, message="File not found or you don't have access", error=True)
    
    return render_template_string(HTML_TEMPLATE, files=files)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))