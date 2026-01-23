"""
LPDP CTRL+F API Server
"""

import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(env_path)

# Create Flask app
app = Flask(__name__)
CORS(app)

# Import blueprints
from search import search_bp
from analyze_resume import analyze_bp

app.register_blueprint(search_bp, url_prefix='/api')
app.register_blueprint(analyze_bp, url_prefix='/api')

@app.route('/')
def index():
    return jsonify({
        'name': 'LPDP CTRL+F API',
        'version': '1.0.0'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

# Serve PDF files
@app.route('/download/<filename>')
def download_pdf(filename):
    pdf_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'source')
    return send_from_directory(pdf_dir, filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.getenv('PORT_API', 8001))
    print(f"LPDP CTRL+F API running on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
