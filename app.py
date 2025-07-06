from flask import Flask, request, send_file, render_template_string
from werkzeug.utils import secure_filename
import os
from io import BytesIO
from datetime import datetime, timedelta

app = Flask(__name__)

# In-memory storage for files (use a database or filesystem for production)
files_storage = {}

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
                {% for file_id, file_info in files.items() %}
                    <div class="file-item">
                        <a href="/download/{{ file_id }}">{{ file_info['name'] }}</a>
                        <span>(Uploaded: {{ file_info['time'] }})</span>
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
    current_time = datetime.utcnow()
    expired = [fid for fid, finfo in files_storage.items() 
              if current_time - finfo['time'] > timedelta(hours=1)]
    for fid in expired:
        del files_storage[fid]
    
    return render_template_string(HTML_TEMPLATE, files=files_storage)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return render_template_string(HTML_TEMPLATE, files=files_storage, 
                                   message="No file selected", error=True)
    
    file = request.files['file']
    if file.filename == '':
        return render_template_string(HTML_TEMPLATE, files=files_storage, 
                                   message="No file selected", error=True)
    
    if file:
        filename = secure_filename(file.filename)
        file_id = str(hash(filename + str(datetime.utcnow())))
        file_content = file.read()
        files_storage[file_id] = {
            'name': filename,
            'content': file_content,
            'time': datetime.utcnow()
        }
        return render_template_string(HTML_TEMPLATE, files=files_storage, 
                                   message=f"File {filename} uploaded successfully")

@app.route('/download/<file_id>')
def download_file(file_id):
    if file_id not in files_storage:
        return render_template_string(HTML_TEMPLATE, files=files_storage, 
                                   message="File not found", error=True)
    
    file_info = files_storage[file_id]
    return send_file(
        BytesIO(file_info['content']),
        download_name=file_info['name'],
        as_attachment=True
    )

if __name__ == '__main__':
    app.run(debug=True)