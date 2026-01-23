"""
Vercel Serverless Function for LPDP CTRL+F API
"""

import os
import json
from http.server import BaseHTTPRequestHandler

# OpenAI client
from openai import OpenAI

client = None
if os.getenv('OPENAI_API_KEY'):
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

SYSTEM_PROMPT = """Kamu adalah konsultan ahli beasiswa LPDP. Analisis resume/CV kandidat dan aspirasi Asta Cita mereka secara mendalam.

ANALISIS YANG HARUS DILAKUKAN:
1. **Latar Belakang Pendidikan (S1/S2)**
2. **Pengalaman Kerja**
3. **Keahlian & Kompetensi**
4. **Keselarasan Asta Cita** (8 prioritas: Ketahanan pangan, Kesehatan, Energi, Hilirisasi industri, Transformasi ekonomi/pendidikan/digital, Maritim & dirgantara)
5. **Rekomendasi Universitas** (5 paling cocok dari daftar LPDP)

BERIKAN RESPONS DALAM BAHASA INDONESIA dengan format JSON:
{
    "overall_score": 75,
    "profile_summary": "Ringkasan profil kandidat...",
    "education_analysis": "Analisis latar belakang pendidikan...",
    "work_analysis": "Analisis pengalaman kerja...",
    "asta_cita_alignment": "Penilaian keselarasan dengan Asta Cita...",
    "strengths": ["Kekuatan 1", "Kekuatan 2", "Kekuatan 3"],
    "areas_to_improve": ["Area 1", "Area 2"],
    "top_5_recommendations": [
        {
            "rank": 1,
            "university": "Nama Universitas",
            "program": "Nama Program", 
            "location": "Negara",
            "score": 85,
            "reasoning": "Alasan mengapa cocok..."
        }
    ],
    "advice": "Saran utama untuk memperkuat aplikasi..."
}"""


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        self.send_response(200)
        self._send_cors_headers()
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            'name': 'LPDP CTRL+F API',
            'version': '1.0.0',
            'status': 'healthy',
            'openai_configured': client is not None,
            'endpoints': ['/api/analyze']
        }
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            path = self.path.split('?')[0]
            
            if path == '/api/analyze' or path == '/api':
                self._handle_analyze(post_data)
            else:
                self._send_error(404, 'Endpoint not found')
        except Exception as e:
            self._send_error(500, str(e))
    
    def _handle_analyze(self, post_data):
        if not client:
            self._send_error(500, 'OpenAI API key tidak dikonfigurasi')
            return
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            resume_text = data.get('resume_text', '')
            asta_cita = data.get('asta_cita', '')
            universities = data.get('universities', '[]')
            
            if not resume_text or len(resume_text.strip()) < 50:
                self._send_error(400, 'Resume/CV terlalu pendek atau kosong')
                return
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"""
RESUME/CV KANDIDAT:
{resume_text[:6000]}

ASPIRASI ASTA CITA:
{asta_cita or 'Tidak disebutkan'}

DAFTAR UNIVERSITAS LPDP (sample):
{universities[:3000]}

Lakukan analisis mendalam dan berikan rekomendasi dalam Bahasa Indonesia.
"""}
                ],
                temperature=0.7,
                max_tokens=2500
            )
            
            result_text = response.choices[0].message.content
            
            # Parse JSON from response
            try:
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0]
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0]
                
                result = json.loads(result_text)
                self._send_json(result)
            except:
                self._send_json({'raw_response': result_text})
                
        except json.JSONDecodeError:
            self._send_error(400, 'Invalid JSON')
        except Exception as e:
            self._send_error(500, str(e))
    
    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def _send_json(self, data, status=200):
        self.send_response(status)
        self._send_cors_headers()
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _send_error(self, status, message):
        self._send_json({'error': message}, status)
