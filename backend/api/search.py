"""
Search API Endpoint
Advanced search with pagination and filtering
"""

from flask import Blueprint, request, jsonify
import json
import os

# Create Blueprint
search_bp = Blueprint('search', __name__)

# Global universities data (loaded on startup)
_universities_data = None


def load_universities_data():
    """Load universities data from JSON file"""
    global _universities_data
    if _universities_data is None:
        # Try multiple possible locations
        possible_paths = [
            'data/processed/universities.json',
            'universities.json',
            '../universities.json',
            '../../universities.json'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    _universities_data = json.load(f)
                print(f"Loaded {len(_universities_data)} universities from {path}")
                break
        
        if _universities_data is None:
            print("Warning: Could not load universities data")
            _universities_data = []
    
    return _universities_data


@search_bp.route('/search', methods=['POST', 'OPTIONS'])
def search():
    """
    Advanced search endpoint with pagination
    
    Request JSON:
    {
        "query": "computer science",
        "filters": {
            "beasiswa": "STEM Bidang STEM",
            "jenjang": "Magister",
            "region": "Amerika",
            "kategori": "Unggulan"
        },
        "page": 1,
        "per_page": 12,
        "sort": "relevance"  // or "name", "location"
    }
    
    Response JSON:
    {
        "results": [...],
        "total": 1523,
        "page": 1,
        "per_page": 12,
        "total_pages": 127
    }
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        # Get parameters
        query = data.get('query', '').lower()
        filters = data.get('filters', {})
        page = data.get('page', 1)
        per_page = data.get('per_page', 12)
        sort = data.get('sort', 'relevance')
        
        # Load data
        universities = load_universities_data()
        
        # Apply filters
        filtered = universities
        
        # Text search
        if query:
            filtered = [
                uni for uni in filtered
                if query in (uni.get('Perguruan Tinggi', '') or '').lower() or
                   query in (uni.get('Program Studi', '') or '').lower() or
                   query in (uni.get('Lokasi', '') or '').lower() or
                   query in (uni.get('Bidang', '') or '').lower()
            ]
        
        # Apply filters
        if filters.get('beasiswa'):
            filtered = [uni for uni in filtered if uni.get('Beasiswa') == filters['beasiswa']]
        
        if filters.get('jenjang'):
            filtered = [uni for uni in filtered if uni.get('Jenjang Studi') == filters['jenjang']]
        
        if filters.get('region'):
            filtered = [uni for uni in filtered if uni.get('Region') == filters['region']]
        
        if filters.get('kategori'):
            filtered = [uni for uni in filtered if (uni.get('Kategori', '') or '').lower() == filters['kategori'].lower()]
        
        # Sort results
        if sort == 'name':
            filtered.sort(key=lambda x: x.get('Perguruan Tinggi', ''))
        elif sort == 'location':
            filtered.sort(key=lambda x: x.get('Lokasi', ''))
        # For 'relevance', keep current order (could implement scoring)
        
        # Pagination
        total = len(filtered)
        total_pages = (total + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = start + per_page
        results = filtered[start:end]
        
        return jsonify({
            'results': results,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages
        })
        
    except Exception as e:
        print(f"Error in search endpoint: {e}")
        return jsonify({
            'error': str(e),
            'results': [],
            'total': 0
        }), 500


@search_bp.route('/search/filters', methods=['GET'])
def get_filters():
    """Get available filter options"""
    try:
        universities = load_universities_data()
        
        # Extract unique values for each filter
        filters = {
            'beasiswa': sorted(list(set(uni.get('Beasiswa', '') for uni in universities if uni.get('Beasiswa')))),
            'jenjang': sorted(list(set(uni.get('Jenjang Studi', '') for uni in universities if uni.get('Jenjang Studi')))),
            'region': sorted(list(set(uni.get('Region', '') for uni in universities if uni.get('Region')))),
            'kategori': sorted(list(set(uni.get('Kategori', '') for uni in universities if uni.get('Kategori')))),
            'lokasi': sorted(list(set(uni.get('Lokasi', '') for uni in universities if uni.get('Lokasi'))))
        }
        
        return jsonify(filters)
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500
