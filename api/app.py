"""
LPDP CTRL+F API — Flask app for DigitalOcean App Platform.

Serves the /api/* endpoints behind the App Platform ingress:
  POST   /api/analyze   -> OpenAI gpt-4o-mini resume scoring
  GET    /api/wishlist  -> list a user's wishlist
  POST   /api/wishlist  -> add to wishlist (max 3 per fingerprint, deduped)
  DELETE /api/wishlist  -> remove a wishlist item
  GET    /api/insights  -> aggregated wishlist stats + program keyword cloud

Data is stored in PostgreSQL (DATABASE_URL). AI stays on OpenAI gpt-4o-mini.
"""

import os
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from openai import OpenAI

import midtrans as midtrans_lib

load_dotenv()

app = Flask(__name__)
CORS(app)

# OpenAI client
client = None
if os.getenv('OPENAI_API_KEY'):
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

DATABASE_URL = os.getenv('DATABASE_URL')

# Provinces used to split wishlist location stats (DN vs LN)
def _load_dn_provinces() -> set[str]:
    """Load Indonesian province names from PT lookup + common provinces."""
    provinces = {
        'DKI Jakarta', 'Jawa Barat', 'Jawa Tengah', 'Jawa Timur', 'DI Yogyakarta',
        'Banten', 'Bali', 'Sumatera Utara', 'Sumatera Barat', 'Sumatera Selatan',
        'Riau', 'Lampung', 'Kalimantan Selatan', 'Kalimantan Timur', 'Sulawesi Selatan',
        'Sulawesi Utara', 'Papua', 'Maluku', 'Nusa Tenggara Timur', 'Bangka Belitung',
    }
    lookup_path = Path(__file__).resolve().parent.parent / 'data' / 'lookups' / 'pt_province.json'
    if lookup_path.exists():
        try:
            with open(lookup_path, encoding='utf-8') as f:
                for entry in json.load(f).values():
                    loc = (entry.get('lokasi') or '').strip()
                    if loc:
                        provinces.add(loc)
        except (json.JSONDecodeError, OSError):
            pass
    return provinces


_DN_PROVINCES = _load_dn_provinces()


def _is_dn_location(location: str) -> bool:
    return (location or '').strip() in _DN_PROVINCES


def get_conn():
    """Open a new PostgreSQL connection with dict rows."""
    if not DATABASE_URL:
        return None
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def _bootstrap_schema():
    """Idempotent schema creation, run once at process startup."""
    if not DATABASE_URL:
        return
    try:
        with psycopg.connect(DATABASE_URL, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS wishlists (
                    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_fingerprint text NOT NULL,
                    university_name  text NOT NULL DEFAULT '',
                    program_name     text NOT NULL DEFAULT '',
                    location         text DEFAULT '',
                    jenjang          text DEFAULT '',
                    beasiswa         text DEFAULT '',
                    created_at       timestamptz DEFAULT now()
                )
            """)
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_wishlists_fingerprint ON wishlists (user_fingerprint)"
            )
            cur.execute("""
                CREATE TABLE IF NOT EXISTS donations (
                    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    order_id                text UNIQUE NOT NULL,
                    amount                  int NOT NULL CHECK (amount >= 5000),
                    status                  text NOT NULL DEFAULT 'pending',
                    payment_type            text,
                    midtrans_transaction_id text,
                    raw_notification        jsonb,
                    created_at              timestamptz DEFAULT now(),
                    paid_at                 timestamptz
                )
            """)
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_donations_order_id ON donations (order_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_donations_status ON donations (status)"
            )
    except Exception as e:
        print(f"schema bootstrap failed (will retry on next request): {e}", flush=True)


_bootstrap_schema()


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


# ============ HEALTH ============
@app.route('/api', methods=['GET'])
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'name': 'LPDP CTRL+F API',
        'version': '2.0.0',
        'status': 'healthy',
        'openai_configured': client is not None,
        'database_configured': DATABASE_URL is not None,
        'endpoints': ['/api/analyze', '/api/wishlist', '/api/insights', '/api/donations/create', '/api/donations/config']
    })


# ============ ANALYZE ENDPOINT ============
@app.route('/api/analyze', methods=['POST'])
@app.route('/api', methods=['POST'])
def analyze():
    if not client:
        return jsonify({'error': 'OpenAI API key tidak dikonfigurasi'}), 500

    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        return jsonify({'error': 'Invalid JSON'}), 400

    resume_text = data.get('resume_text', '')
    asta_cita = data.get('asta_cita', '')
    universities = data.get('universities', '')
    dream_universities = data.get('dream_universities', [])
    field_keywords = data.get('field_keywords', [])

    if not resume_text or len(resume_text.strip()) < 50:
        return jsonify({'error': 'Resume/CV terlalu pendek atau kosong'}), 400

    # Build target field keywords section
    keywords_section = ""
    if field_keywords and isinstance(field_keywords, list) and len(field_keywords) > 0:
        keywords_section = f"""

BIDANG/JURUSAN YANG DISASAR KANDIDAT:
{', '.join(str(k) for k in field_keywords[:5])}

Prioritaskan rekomendasi yang relevan dengan bidang-bidang ini."""

    # Build dream universities section
    dream_section = ""
    if dream_universities and len(dream_universities) > 0:
        dream_list = "\n".join([
            f"- {d.get('university_name', '')} - {d.get('program_name', '')} ({d.get('location', '')})"
            for d in dream_universities
        ])
        dream_section = f"""

UNIVERSITAS IMPIAN KANDIDAT (WAJIB nilai kecocokannya di dream_scores):
{dream_list}

Berikan penilaian JUJUR untuk setiap universitas impian di atas."""

    try:
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"""
RESUME KANDIDAT:
{resume_text[:15000]}

ASPIRASI ASTA CITA:
{asta_cita or 'Tidak disebutkan'}{keywords_section}

DAFTAR UNIVERSITAS (sudah difilter sesuai preferensi kandidat):
{universities[:80000]}{dream_section}

Analisis dan rekomendasikan 5 universitas terbaik dari daftar di atas.
"""}
            ],
            reasoning_effort="low",
            max_completion_tokens=3000
        )

        result_text = response.choices[0].message.content

        try:
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            result = json.loads(result_text)
            return jsonify(result)
        except Exception:
            return jsonify({'raw_response': result_text})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ WISHLIST ENDPOINTS ============
@app.route('/api/wishlist', methods=['GET'])
def get_wishlist():
    if not DATABASE_URL:
        return jsonify({'error': 'Database tidak dikonfigurasi'}), 500

    fingerprint = request.args.get('fingerprint')
    if not fingerprint:
        return jsonify({'error': 'Fingerprint diperlukan'}), 400

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM wishlists WHERE user_fingerprint = %s ORDER BY created_at",
                (fingerprint,)
            )
            rows = cur.fetchall()
        return jsonify({'wishlists': _jsonable(rows)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/wishlist', methods=['POST'])
def add_wishlist():
    if not DATABASE_URL:
        return jsonify({'error': 'Database tidak dikonfigurasi'}), 500

    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        return jsonify({'error': 'Invalid JSON'}), 400

    fingerprint = data.get('user_fingerprint')
    if not fingerprint:
        return jsonify({'error': 'Fingerprint diperlukan'}), 400

    university_name = data.get('university_name', '')
    program_name = data.get('program_name', '')

    try:
        with get_conn() as conn, conn.cursor() as cur:
            # Check current count (max 3 per user)
            cur.execute(
                "SELECT COUNT(*) AS n FROM wishlists WHERE user_fingerprint = %s",
                (fingerprint,)
            )
            if cur.fetchone()['n'] >= 3:
                return jsonify({'error': 'Maksimal 3 wishlist per user'}), 400

            # Check if already exists
            cur.execute(
                """SELECT id FROM wishlists
                   WHERE user_fingerprint = %s AND university_name = %s AND program_name = %s""",
                (fingerprint, university_name, program_name)
            )
            if cur.fetchone():
                return jsonify({'error': 'Sudah ada di wishlist'}), 400

            # Insert
            cur.execute(
                """INSERT INTO wishlists
                   (user_fingerprint, university_name, program_name, location, jenjang, beasiswa)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (
                    fingerprint,
                    university_name,
                    program_name,
                    data.get('location', ''),
                    data.get('jenjang', ''),
                    data.get('beasiswa', ''),
                )
            )
            row = cur.fetchone()
            conn.commit()

        return jsonify({'success': True, 'data': _jsonable(row) if row else None})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/wishlist', methods=['DELETE'])
def delete_wishlist():
    if not DATABASE_URL:
        return jsonify({'error': 'Database tidak dikonfigurasi'}), 500

    wishlist_id = request.args.get('id')
    fingerprint = request.args.get('fingerprint')

    if not wishlist_id or not fingerprint:
        return jsonify({'error': 'ID dan fingerprint diperlukan'}), 400

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM wishlists WHERE id = %s::uuid AND user_fingerprint = %s RETURNING id",
                (wishlist_id, fingerprint)
            )
            deleted = cur.fetchall()
            conn.commit()
        return jsonify({'success': True, 'deleted': len(deleted) > 0})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ INSIGHTS ENDPOINT ============
@app.route('/api/insights', methods=['GET'])
def insights():
    if not DATABASE_URL:
        return jsonify({'error': 'Database tidak dikonfigurasi'}), 500

    filter_location = request.args.get('location')
    filter_jenjang = request.args.get('jenjang')
    filter_beasiswa = request.args.get('beasiswa')
    filter_university = request.args.get('university')

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM wishlists")
            wishlists = cur.fetchall()

        # Apply filters
        if filter_location:
            wishlists = [w for w in wishlists if w.get('location') == filter_location]
        if filter_jenjang:
            wishlists = [w for w in wishlists if w.get('jenjang') == filter_jenjang]
        if filter_beasiswa:
            wishlists = [w for w in wishlists if w.get('beasiswa') == filter_beasiswa]
        if filter_university:
            wishlists = [w for w in wishlists if w.get('university_name') == filter_university]

        # Aggregate stats
        total_wishlists = len(wishlists)
        unique_users = len(set(w['user_fingerprint'] for w in wishlists))

        # Top locations — split LN (country) vs DN (province)
        ln_counts: dict[str, int] = {}
        dn_counts: dict[str, int] = {}
        for w in wishlists:
            loc = (w.get('location') or '').strip() or 'Unknown'
            if _is_dn_location(loc):
                dn_counts[loc] = dn_counts.get(loc, 0) + 1
            else:
                ln_counts[loc] = ln_counts.get(loc, 0) + 1
        top_locations_ln = sorted(ln_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_locations_dn = sorted(dn_counts.items(), key=lambda x: x[1], reverse=True)[:10]

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
            words = program.lower().replace('-', ' ').replace('/', ' ').replace('(', ' ').replace(')', ' ').split()
            for word in words:
                word = ''.join(c for c in word if c.isalnum())
                if word and len(word) > 2 and word not in stop_words:
                    word_counts[word] = word_counts.get(word, 0) + 1

        top_keywords = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:30]

        return jsonify({
            'total_wishlists': total_wishlists,
            'total_users': unique_users,
            'top_locations_ln': [{'name': loc, 'count': cnt} for loc, cnt in top_locations_ln],
            'top_locations_dn': [{'name': loc, 'count': cnt} for loc, cnt in top_locations_dn],
            'top_universities': [{'name': uni, 'count': cnt} for uni, cnt in top_universities],
            'by_jenjang': jenjang_counts,
            'by_beasiswa': beasiswa_counts,
            'program_keywords': [{'word': w, 'count': c} for w, c in top_keywords],
            'active_filters': {
                'location': filter_location,
                'jenjang': filter_jenjang,
                'beasiswa': filter_beasiswa,
                'university': filter_university
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ DONATIONS (Midtrans Snap) ============
DONATION_MIN_AMOUNT = 5000
DONATION_MAX_AMOUNT = 10_000_000


@app.route('/api/donations/config', methods=['GET'])
def donations_config():
    client_key = os.getenv('MIDTRANS_CLIENT_KEY')
    if not client_key:
        return jsonify({'enabled': False})
    return jsonify({
        'enabled': True,
        'client_key': client_key,
        'is_production': midtrans_lib._is_production(),
        'snap_script_url': midtrans_lib.snap_script_url(),
        'min_amount': DONATION_MIN_AMOUNT,
    })


@app.route('/api/donations/create', methods=['POST'])
def donations_create():
    if not os.getenv('MIDTRANS_SERVER_KEY'):
        return jsonify({'error': 'Pembayaran belum dikonfigurasi'}), 503

    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        return jsonify({'error': 'Invalid JSON'}), 400

    try:
        amount = int(data.get('amount', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Nominal tidak valid'}), 400

    if amount < DONATION_MIN_AMOUNT:
        return jsonify({'error': f'Nominal minimal Rp{DONATION_MIN_AMOUNT:,}'.replace(',', '.')}), 400
    if amount > DONATION_MAX_AMOUNT:
        return jsonify({'error': 'Nominal terlalu besar'}), 400

    order_id = f"LPDP-SDKH-{int(datetime.now(timezone.utc).timestamp())}-{uuid.uuid4().hex[:8]}"
    origin = request.headers.get('Origin') or request.host_url.rstrip('/')
    if 'localhost' in origin:
        origin = 'https://lpdpfind.allrize.tech'

    notification_url = os.getenv(
        'DONATION_NOTIFICATION_URL',
        'https://lpdpfind.allrize.tech/api/donations/notification',
    )

    try:
        snap = midtrans_lib.create_snap_transaction(
            {
                'transaction_details': {
                    'order_id': order_id,
                    'gross_amount': amount,
                },
                'item_details': [{
                    'id': 'sedekah',
                    'price': amount,
                    'quantity': 1,
                    'name': 'Sedekah LPDP CTRL+F',
                    'category': 'Donation',
                    'merchant_name': 'LPDP CTRL+F',
                }],
                'customer_details': {
                    'first_name': 'Supporter',
                },
                'callbacks': {
                    'finish': f'{origin}/?sedekah=success',
                },
            },
            extra_headers={
                # Shared merchant: append lpdpfind webhook alongside Colorize dashboard URL
                'X-Append-Notification': notification_url,
            },
        )
    except ValueError as e:
        return jsonify({'error': str(e)}), 502

    conn = get_conn()
    if conn:
        try:
            with conn, conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO donations (order_id, amount, status)
                       VALUES (%s, %s, 'pending')""",
                    (order_id, amount),
                )
        except Exception as e:
            print(f'donation insert failed: {e}', flush=True)
        finally:
            conn.close()

    return jsonify({
        'token': snap['token'],
        'order_id': order_id,
        'amount': amount,
    })


@app.route('/api/donations/notification', methods=['POST'])
def donations_notification():
    try:
        payload = request.get_json(force=True, silent=True) or {}
    except Exception:
        return jsonify({'error': 'Invalid JSON'}), 400

    if not midtrans_lib.verify_signature(payload):
        return jsonify({'error': 'Invalid signature'}), 401

    order_id = payload.get('order_id')
    if not order_id:
        return jsonify({'error': 'Missing order_id'}), 400

    local_status = midtrans_lib.to_local_status(
        payload.get('transaction_status'),
        payload.get('fraud_status'),
    )

    gross_raw = payload.get('gross_amount', '0')
    try:
        gross_amount = int(float(str(gross_raw)))
    except (TypeError, ValueError):
        gross_amount = DONATION_MIN_AMOUNT

    conn = get_conn()
    if not conn:
        return jsonify({'error': 'Database not configured'}), 503

    try:
        with conn, conn.cursor() as cur:
            paid_at = datetime.now(timezone.utc) if local_status == 'paid' else None
            cur.execute(
                """INSERT INTO donations (
                     order_id, amount, status, payment_type,
                     midtrans_transaction_id, raw_notification, paid_at
                   ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (order_id) DO UPDATE SET
                     status = EXCLUDED.status,
                     payment_type = COALESCE(EXCLUDED.payment_type, donations.payment_type),
                     midtrans_transaction_id = COALESCE(EXCLUDED.midtrans_transaction_id, donations.midtrans_transaction_id),
                     raw_notification = EXCLUDED.raw_notification,
                     paid_at = COALESCE(EXCLUDED.paid_at, donations.paid_at)""",
                (
                    order_id,
                    gross_amount,
                    local_status,
                    payload.get('payment_type'),
                    payload.get('transaction_id'),
                    Json(payload),
                    paid_at,
                ),
            )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

    return jsonify({'ok': True})


# ============ HELPERS ============
def _jsonable(rows):
    """Coerce non-JSON-native values (uuid, datetime) from DB rows to strings."""
    def fix(row):
        return {k: (v if _is_native(v) else str(v)) for k, v in row.items()}
    if isinstance(rows, list):
        return [fix(r) for r in rows]
    return fix(rows)


def _is_native(v):
    return v is None or isinstance(v, (str, int, float, bool))


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
