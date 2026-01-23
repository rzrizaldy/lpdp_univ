"""
Resume Analyzer API with proper PDF parsing
"""

import os
import json
import io
from flask import Blueprint, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

analyze_bp = Blueprint('analyze', __name__)

# OpenAI client
client = None
if os.getenv('OPENAI_API_KEY'):
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Try to import PDF parser
try:
    from pypdf import PdfReader
    PDF_SUPPORT = True
except ImportError:
    try:
        from PyPDF2 import PdfReader
        PDF_SUPPORT = True
    except ImportError:
        PDF_SUPPORT = False

SYSTEM_PROMPT = """Kamu adalah konsultan ahli beasiswa LPDP. Analisis resume/CV kandidat dan aspirasi Asta Cita mereka secara mendalam.

ANALISIS YANG HARUS DILAKUKAN:
1. **Latar Belakang Pendidikan (S1/S2)**
   - Institusi dan program studi
   - IPK dan prestasi akademik
   - Relevansi dengan program yang dituju

2. **Pengalaman Kerja**
   - Posisi dan tanggung jawab
   - Durasi pengalaman
   - Relevansi dengan rencana studi

3. **Keahlian & Kompetensi**
   - Technical skills
   - Soft skills
   - Sertifikasi

4. **Keselarasan Asta Cita**
   LPDP Asta Cita fokus pada 8 prioritas:
   - Ketahanan pangan
   - Kesehatan
   - Energi
   - Hilirisasi industri
   - Transformasi ekonomi
   - Transformasi pendidikan
   - Transformasi digital
   - Maritim & dirgantara

5. **Rekomendasi Universitas**
   - 5 universitas paling cocok dari daftar LPDP
   - Alasan spesifik untuk setiap rekomendasi

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
}

Berikan penilaian yang jujur, konstruktif, dan berbasis data dari resume."""


def extract_text_from_pdf(pdf_bytes):
    """Extract text from PDF bytes"""
    if not PDF_SUPPORT:
        return None, "PDF library tidak tersedia"
    
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        
        full_text = "\n\n".join(text_parts)
        
        if not full_text.strip():
            return None, "PDF tidak mengandung teks yang dapat diekstrak"
        
        return full_text, None
        
    except Exception as e:
        return None, f"Error parsing PDF: {str(e)}"


@analyze_bp.route('/parse-pdf', methods=['POST', 'OPTIONS'])
def parse_pdf():
    """Parse uploaded PDF and return text"""
    if request.method == 'OPTIONS':
        return '', 200
    
    if 'file' not in request.files:
        return jsonify({'error': 'File tidak ditemukan'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'File tidak dipilih'}), 400
    
    filename = file.filename.lower()
    
    # Handle TXT files
    if filename.endswith('.txt'):
        try:
            text = file.read().decode('utf-8')
            return jsonify({'text': text, 'filename': file.filename})
        except:
            return jsonify({'error': 'Gagal membaca file TXT'}), 400
    
    # Handle PDF files
    if filename.endswith('.pdf'):
        pdf_bytes = file.read()
        text, error = extract_text_from_pdf(pdf_bytes)
        
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify({'text': text, 'filename': file.filename})
    
    return jsonify({'error': 'Format file tidak didukung. Gunakan PDF atau TXT'}), 400


@analyze_bp.route('/analyze', methods=['POST', 'OPTIONS'])
def analyze():
    if request.method == 'OPTIONS':
        return '', 200
    
    if not client:
        return jsonify({'error': 'OpenAI API key tidak dikonfigurasi'}), 500
    
    try:
        data = request.get_json()
        resume_text = data.get('resume_text', '')
        asta_cita = data.get('asta_cita', '')
        universities = data.get('universities', '[]')
        
        if not resume_text or len(resume_text.strip()) < 50:
            return jsonify({'error': 'Resume/CV terlalu pendek atau kosong. Pastikan file PDF dapat dibaca.'}), 400
        
        # Call OpenAI
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
        
        # Parse JSON
        try:
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result = json.loads(result_text)
            return jsonify(result)
        except:
            return jsonify({'raw_response': result_text})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@analyze_bp.route('/analyze/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'openai_configured': client is not None,
        'pdf_support': PDF_SUPPORT
    })
