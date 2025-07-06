from flask import Flask, request, send_file, render_template_string
from werkzeug.utils import secure_filename
import sqlite3
import os
from io import BytesIO
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('files.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS files (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    content BLOB NOT NULL,
                    upload_time TIMESTAMP NOT NULL
                )''')
    conn.commit()
    conn.close()

init_db()

# HTML template for the web interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>File Share & Upload</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 800px; margin: auto; }
        .file-list { margin-top: 20px; }
        .file-item { margin: 10px 0; }
        .error { color: red; }
        .success { color: green; }
    </style>
</head>
<body>
    <div class="container">
        <h1>File Share & Upload</h1>
        <form method="post" enctype="multipart/form-data" action="/upload">
            <input type="file" name="file" required>
            <input type="submit" value="Upload File">
        </form>
        {% if message %}
            <p class="{% if error %}error{% else %}success{% endif %}">{{ message }}</p>
        {% endif %}
        <h2>Uploaded Files</h2>
        <div class="file-list">
            {% if files %}
                {% for file in files %}
                    <div class="file-item">
                        <a href="/download/{{ file[0] }}">{{ file[1] }}</a>
                        <span>(Uploaded: {{ file[3] }})</span>
                    </div>
                {% endfor %}
            {% else %}
                <p>No files uploaded yet.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    # Clean up expired files (older than 1 hour)
    conn = sqlite3.connect('files.db')
    c = conn.cursor()
    expiration_time = datetime.utcnow() - timedelta(hours=1)
    c.execute("DELETE FROM files WHERE upload_time < ?", (expiration_time,))
    conn.commit()
    
    # Fetch remaining files
    c.execute("SELECT id, filename, content, upload_time FROM files")
    files = c.fetchall()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        conn = sqlite3.connect('files.db')
        c = conn.cursor()
        c.execute("SELECT id, filename, content, upload_time FROM files")
        files = c.fetchall()
        conn.close()
        return render_template_string(HTML_TEMPLATE, files=files, 
                                   message="No file selected", error=True)
    
    file = request.files['file']
    if file.filename == '':
        conn = sqlite3.connect('files.db')
        c = conn.cursor()
        c.execute("SELECT id, filename, content, upload_time FROM files")
        files = c.fetchall()
        conn.close()
        return render_template_string(HTML_TEMPLATE, files=files, 
                                   message="No file selected", error=True)
    
    if file:
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        file_content = file.read()
        upload_time = datetime.utcnow()
        
        conn = sqlite3.connect('files.db')
        c = conn.cursor()
        c.execute("INSERT INTO files (id, filename, content, upload_time) VALUES (?, ?, ?, ?)",
                 (file_id, filename, file_content, upload_time))
        conn.commit()
        conn.close()
        
        c.execute("SELECT id, filename, content, upload_time FROM files")
        files = c.fetchall()
        conn.close()
        
        return render_template_string(HTML_TEMPLATE, files=files, 
                                   message=f"File {filename} uploaded successfully")

@app.route('/download/<file_id>')
def download_file(file_id):
    conn = sqlite3.connect('files.db')
    c = conn.cursor()
    c.execute("SELECT filename, content FROM files WHERE id = ?", (file_id,))
    file_data = c.fetchone()
    conn.close()
    
    if not file_data:
        conn = sqlite3.connect('files.db')
        c = conn.cursor()
        c.execute("SELECT id, filename, content, upload_time FROM files")
        files = c.fetchall()
        conn.close()
        return render_template_string(HTML_TEMPLATE, files=files, 
                                   message="File not found", error=True)
    
    filename, content = file_data
    return send_file(
        BytesIO(content),
        download_name=filename,
        as_attachment=True
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))