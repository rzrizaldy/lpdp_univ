"""
Vercel Serverless Function for LPDP CTRL+F API
"""

import os
import sys
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api'))

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Import handlers
try:
    from analyze_resume import analyze_bp
    app.register_blueprint(analyze_bp, url_prefix='/api')
except Exception as e:
    print(f"Error importing analyze_resume: {e}")

@app.route('/api')
@app.route('/api/')
def api_index():
    return jsonify({
        'name': 'LPDP CTRL+F API',
        'version': '1.0.0',
        'endpoints': ['/api/analyze', '/api/search']
    })

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy'})

# Search endpoint (simple version)
@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    return jsonify({'query': query, 'results': []})

# For Vercel
def handler(request):
    return app(request)

# Export for Vercel
app = app
