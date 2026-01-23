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

SYSTEM_PROMPT = """Kamu adalah konsultan senior beasiswa LPDP yang KRITIS dan JUJUR. Tugasmu menilai kandidat secara objektif - jangan terlalu mudah memberi skor tinggi.

STANDAR PENILAIAN (KETAT):
- Skor 80-100: Luar biasa, pengalaman sangat relevan, track record terbukti, Asta Cita sangat jelas
- Skor 60-79: Bagus tapi ada gap yang perlu diperbaiki
- Skor 40-59: Cukup, masih banyak yang perlu ditingkatkan
- Skor <40: Perlu persiapan lebih matang sebelum mendaftar

KRITERIA PENILAIAN:
1. **Pendidikan**: IPK, relevansi jurusan, prestasi akademik
2. **Pengalaman Kerja**: Relevansi dengan bidang studi, dampak nyata, kepemimpinan
3. **Keselarasan Asta Cita**: Harus SPESIFIK dan TERUKUR, bukan hanya retorika
   - 8 Prioritas: Ketahanan pangan, Kesehatan, Energi, Hilirisasi industri, Transformasi ekonomi/pendidikan/digital, Maritim & dirgantara
4. **Keunikan Profil**: Apa yang membedakan dari kandidat lain?

BERIKAN KRITIK KONSTRUKTIF - jelaskan APA yang kurang dan BAGAIMANA memperbaikinya.
Jangan hanya memuji, tapi motivasi dengan menunjukkan potensi perbaikan.

RESPONS dalam Bahasa Indonesia, format JSON:
{
    "overall_score": 65,
    "profile_summary": "Ringkasan objektif profil kandidat...",
    "education_analysis": "Analisis kritis latar belakang pendidikan...",
    "work_analysis": "Analisis kritis pengalaman kerja...",
    "asta_cita_alignment": "Penilaian JUJUR keselarasan dengan Asta Cita - apakah cukup spesifik atau masih terlalu umum?",
    "strengths": ["Kekuatan nyata 1", "Kekuatan nyata 2"],
    "areas_to_improve": ["Kelemahan 1 + cara memperbaiki", "Kelemahan 2 + cara memperbaiki", "Kelemahan 3 + cara memperbaiki"],
    "top_5_recommendations": [
        {"rank": 1, "university": "Nama", "program": "Program", "location": "Negara", "score": 75, "reasoning": "Alasan spesifik mengapa cocok"}
    ],
    "advice": "Saran KONKRET dan ACTIONABLE untuk memperkuat aplikasi..."
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
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"""
RESUME KANDIDAT:
{resume_text[:4000]}

ASPIRASI ASTA CITA:
{asta_cita or 'Tidak disebutkan'}

DAFTAR UNIVERSITAS (sudah difilter sesuai preferensi kandidat):
{universities[:2000]}

Analisis dan rekomendasikan 5 universitas terbaik dari daftar di atas.
"""}
                ],
                temperature=0.5,
                max_tokens=1500
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
