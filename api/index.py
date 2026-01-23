"""
Vercel Serverless Function for LPDP CTRL+F API
"""

import os
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# OpenAI client
from openai import OpenAI

# Supabase client
from supabase import create_client, Client

client = None
if os.getenv('OPENAI_API_KEY'):
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

supabase: Client = None
if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_ANON_KEY')
    )

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
    "dream_scores": [
        {"university": "Nama Univ Impian", "program": "Program", "score": 70, "assessment": "Penilaian jujur kecocokan kandidat dengan universitas ini", "gap_analysis": "Apa yang perlu diperbaiki untuk meningkatkan peluang"}
    ],
    "top_5_recommendations": [
        {"rank": 1, "university": "Nama", "program": "Program", "location": "Negara", "score": 75, "reasoning": "Alasan spesifik mengapa cocok"}
    ],
    "advice": "Saran KONKRET dan ACTIONABLE untuk memperkuat aplikasi..."
}

PENTING: Jika ada UNIVERSITAS IMPIAN yang diberikan, WAJIB sertakan "dream_scores" dengan penilaian untuk SETIAP universitas impian tersebut."""


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == '/api/wishlist':
            self._handle_get_wishlist(query)
        elif path == '/api/insights':
            self._handle_get_insights()
        else:
            # Default health check
            self._send_json({
                'name': 'LPDP CTRL+F API',
                'version': '2.0.0',
                'status': 'healthy',
                'openai_configured': client is not None,
                'supabase_configured': supabase is not None,
                'endpoints': ['/api/analyze', '/api/wishlist', '/api/insights']
            })

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            path = self.path.split('?')[0]

            if path == '/api/analyze' or path == '/api':
                self._handle_analyze(post_data)
            elif path == '/api/wishlist':
                self._handle_add_wishlist(post_data)
            else:
                self._send_error(404, 'Endpoint not found')
        except Exception as e:
            self._send_error(500, str(e))

    def do_DELETE(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)

            if path == '/api/wishlist':
                self._handle_delete_wishlist(query)
            else:
                self._send_error(404, 'Endpoint not found')
        except Exception as e:
            self._send_error(500, str(e))

    # ============ ANALYZE ENDPOINT ============
    def _handle_analyze(self, post_data):
        if not client:
            self._send_error(500, 'OpenAI API key tidak dikonfigurasi')
            return

        try:
            data = json.loads(post_data.decode('utf-8'))
            resume_text = data.get('resume_text', '')
            asta_cita = data.get('asta_cita', '')
            universities = data.get('universities', '[]')
            dream_universities = data.get('dream_universities', [])

            if not resume_text or len(resume_text.strip()) < 50:
                self._send_error(400, 'Resume/CV terlalu pendek atau kosong')
                return

            # Build dream universities section
            dream_section = ""
            if dream_universities and len(dream_universities) > 0:
                dream_list = "\n".join([f"- {d.get('university_name', '')} - {d.get('program_name', '')} ({d.get('location', '')})" for d in dream_universities])
                dream_section = f"""

UNIVERSITAS IMPIAN KANDIDAT (WAJIB nilai kecocokannya di dream_scores):
{dream_list}

Berikan penilaian JUJUR untuk setiap universitas impian di atas."""

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
{universities[:2000]}{dream_section}

Analisis dan rekomendasikan 5 universitas terbaik dari daftar di atas.
"""}
                ],
                temperature=0.5,
                max_tokens=1800
            )

            result_text = response.choices[0].message.content

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

    # ============ WISHLIST ENDPOINTS ============
    def _handle_get_wishlist(self, query):
        if not supabase:
            self._send_error(500, 'Database tidak dikonfigurasi')
            return

        fingerprint = query.get('fingerprint', [None])[0]
        if not fingerprint:
            self._send_error(400, 'Fingerprint diperlukan')
            return

        try:
            result = supabase.table('wishlists').select('*').eq('user_fingerprint', fingerprint).execute()
            self._send_json({'wishlists': result.data})
        except Exception as e:
            self._send_error(500, str(e))

    def _handle_add_wishlist(self, post_data):
        if not supabase:
            self._send_error(500, 'Database tidak dikonfigurasi')
            return

        try:
            data = json.loads(post_data.decode('utf-8'))
            fingerprint = data.get('user_fingerprint')

            if not fingerprint:
                self._send_error(400, 'Fingerprint diperlukan')
                return

            # Check current count
            existing = supabase.table('wishlists').select('id').eq('user_fingerprint', fingerprint).execute()
            if len(existing.data) >= 3:
                self._send_error(400, 'Maksimal 3 wishlist per user')
                return

            # Check if already exists
            check = supabase.table('wishlists').select('id').eq('user_fingerprint', fingerprint).eq('university_name', data.get('university_name')).eq('program_name', data.get('program_name')).execute()
            if len(check.data) > 0:
                self._send_error(400, 'Sudah ada di wishlist')
                return

            # Insert
            result = supabase.table('wishlists').insert({
                'user_fingerprint': fingerprint,
                'university_name': data.get('university_name', ''),
                'program_name': data.get('program_name', ''),
                'location': data.get('location', ''),
                'jenjang': data.get('jenjang', ''),
                'beasiswa': data.get('beasiswa', '')
            }).execute()

            self._send_json({'success': True, 'data': result.data[0] if result.data else None})
        except Exception as e:
            self._send_error(500, str(e))

    def _handle_delete_wishlist(self, query):
        if not supabase:
            self._send_error(500, 'Database tidak dikonfigurasi')
            return

        wishlist_id = query.get('id', [None])[0]
        fingerprint = query.get('fingerprint', [None])[0]

        if not wishlist_id or not fingerprint:
            self._send_error(400, 'ID dan fingerprint diperlukan')
            return

        try:
            result = supabase.table('wishlists').delete().eq('id', wishlist_id).eq('user_fingerprint', fingerprint).execute()
            self._send_json({'success': True, 'deleted': len(result.data) > 0})
        except Exception as e:
            self._send_error(500, str(e))

    # ============ INSIGHTS ENDPOINT ============
    def _handle_get_insights(self):
        if not supabase:
            self._send_error(500, 'Database tidak dikonfigurasi')
            return

        try:
            # Get all wishlists
            all_data = supabase.table('wishlists').select('*').execute()
            wishlists = all_data.data

            # Aggregate stats
            total_wishlists = len(wishlists)
            unique_users = len(set(w['user_fingerprint'] for w in wishlists))

            # Top locations
            location_counts = {}
            for w in wishlists:
                loc = w.get('location', '') or 'Unknown'
                location_counts[loc] = location_counts.get(loc, 0) + 1
            top_locations = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            # Top universities
            uni_counts = {}
            for w in wishlists:
                uni = w.get('university_name', 'Unknown')
                uni_counts[uni] = uni_counts.get(uni, 0) + 1
            top_universities = sorted(uni_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            # By jenjang
            jenjang_counts = {}
            for w in wishlists:
                j = w.get('jenjang', 'Unknown') or 'Unknown'
                jenjang_counts[j] = jenjang_counts.get(j, 0) + 1

            # By beasiswa
            beasiswa_counts = {}
            for w in wishlists:
                b = w.get('beasiswa', 'Unknown') or 'Unknown'
                beasiswa_counts[b] = beasiswa_counts.get(b, 0) + 1

            # Program study word cloud - extract meaningful keywords
            stop_words = {
                # Common degree prefixes/suffixes
                'master', 'masters', 'ms', 'msc', 'm.sc', 'ma', 'm.a', 'mba', 'phd', 'ph.d',
                'doctor', 'doctoral', 'bachelor', 'bachelors', 'bs', 'bsc', 'ba', 'b.a',
                'magister', 'sarjana', 's1', 's2', 's3', 'degree', 'program', 'programme',
                # Common filler words
                'of', 'in', 'and', 'the', 'for', 'with', 'to', 'a', 'an', 'on', 'at',
                'dan', 'untuk', 'dengan', 'atau', 'yang', 'di', 'ke',
                # Generic terms
                'science', 'sciences', 'study', 'studies', 'arts', 'applied', 'advanced',
                'international', 'general', 'specialization', 'concentration', 'track'
            }

            word_counts = {}
            for w in wishlists:
                program = w.get('program_name', '') or ''
                # Clean and split into words
                words = program.lower().replace('-', ' ').replace('/', ' ').replace('(', ' ').replace(')', ' ').split()
                for word in words:
                    # Clean punctuation
                    word = ''.join(c for c in word if c.isalnum())
                    if word and len(word) > 2 and word not in stop_words:
                        word_counts[word] = word_counts.get(word, 0) + 1

            # Get top keywords
            top_keywords = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:30]

            self._send_json({
                'total_wishlists': total_wishlists,
                'total_users': unique_users,
                'top_locations': [{'name': loc, 'count': cnt} for loc, cnt in top_locations],
                'top_universities': [{'name': uni, 'count': cnt} for uni, cnt in top_universities],
                'by_jenjang': jenjang_counts,
                'by_beasiswa': beasiswa_counts,
                'program_keywords': [{'word': w, 'count': c} for w, c in top_keywords]
            })
        except Exception as e:
            self._send_error(500, str(e))

    # ============ HELPER METHODS ============
    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _send_json(self, data, status=200):
        self.send_response(status)
        self._send_cors_headers()
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_error(self, status, message):
        self._send_json({'error': message}, status)
