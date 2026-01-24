/**
 * LPDP CTRL+F - Main JavaScript
 * Full Bahasa Indonesia
 */

// Use relative URL for production, localhost for development
const API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8001/api' 
    : '/api';

// State
let allUniversities = [];
let filteredUniversities = [];
let currentPage = 1;
const ITEMS_PER_PAGE = 10;
let resumeText = '';
let userFingerprint = '';
let myWishlist = []; // Saved in DB
let draftWishlist = []; // Local draft, not yet saved
let hasUnsavedChanges = false;

// Init
document.addEventListener('DOMContentLoaded', async () => {
    userFingerprint = getOrCreateFingerprint();
    await loadData();
    await loadMyWishlist();
    setupEventListeners();
    displayResults();
    setupNavbarScroll();
    loadInsights();
    loadDownloadsConfig();
});

// Load downloads last update
async function loadDownloadsConfig() {
    try {
        const res = await fetch('/assets/config/downloads.json');
        if (res.ok) {
            const config = await res.json();
            const el = document.getElementById('downloadsLastUpdate');
            if (el && config.lastUpdateDisplay) {
                el.textContent = config.lastUpdateDisplay;
            }
        }
    } catch (e) {
        console.error('Error loading downloads config:', e);
    }
}

// Navbar scroll effect
function setupNavbarScroll() {
    const navbar = document.querySelector('.navbar');
    const hero = document.querySelector('.hero');
    
    if (!navbar || !hero) return;
    
    const heroHeight = hero.offsetHeight;
    
    function updateNavbar() {
        // When in hero area (dark background) - navbar should be dark
        if (window.scrollY < heroHeight - 80) {
            navbar.classList.add('in-hero');
        } else {
            navbar.classList.remove('in-hero');
        }
    }
    
    window.addEventListener('scroll', updateNavbar);
    updateNavbar(); // Initial check
}

// Load Data
async function loadData() {
    try {
        const paths = ['universities.json', 'data/processed/universities.json'];
        for (const path of paths) {
            try {
                const res = await fetch(path);
                if (res.ok) {
                    allUniversities = await res.json();
                    filteredUniversities = [...allUniversities];
                    console.log(`Loaded ${allUniversities.length} universities`);
                    updateResultCount();
                    return;
                }
            } catch (e) { continue; }
        }
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

// Event Listeners
function setupEventListeners() {
    // Search input - live search
    const searchInput = document.getElementById('globalSearch');
    if (searchInput) {
        let timeout;
        searchInput.addEventListener('input', () => {
            clearTimeout(timeout);
            timeout = setTimeout(() => performSearch(), 200);
        });
    }

    // Filter tabs - Jenis
    document.querySelectorAll('.filter-tab.filter-jenis').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.filter-tab.filter-jenis').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            performSearch();
        });
    });

    // Filter tabs - Jenjang
    document.querySelectorAll('.filter-tab.filter-jenjang').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.filter-tab.filter-jenjang').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            performSearch();
        });
    });

    // Filter dropdown - Lokasi
    const lokasiFilter = document.getElementById('lokasiFilter');
    if (lokasiFilter) {
        lokasiFilter.addEventListener('change', () => performSearch());
    }

    // Analyzer filters - Jenis
    document.querySelectorAll('.filter-tab.filter-jenis-analyzer').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.filter-tab.filter-jenis-analyzer').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
        });
    });

    // Analyzer filters - Jenjang
    document.querySelectorAll('.filter-tab.filter-jenjang-analyzer').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.filter-tab.filter-jenjang-analyzer').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
        });
    });

    // Resume upload
    const resumeInput = document.getElementById('resumeUpload');
    const dropZone = document.getElementById('dropZone');
    
    if (resumeInput) {
        resumeInput.addEventListener('change', handleFileSelect);
    }
    
    if (dropZone) {
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = 'var(--accent)';
            dropZone.style.background = 'rgba(99, 102, 241, 0.05)';
        });
        dropZone.addEventListener('dragleave', () => {
            dropZone.style.borderColor = 'var(--border)';
            dropZone.style.background = 'var(--white)';
        });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = 'var(--border)';
            dropZone.style.background = 'var(--white)';
            if (e.dataTransfer.files.length) {
                resumeInput.files = e.dataTransfer.files;
                handleFileSelect();
            }
        });
    }
}

// Scroll to Analyzer
function scrollToAnalyzer() {
    document.getElementById('analyzer').scrollIntoView({ behavior: 'smooth' });
}

// Search
function performSearch() {
    const searchInput = document.getElementById('globalSearch');
    const searchTerm = searchInput ? searchInput.value.trim().toLowerCase() : '';

    // Get Jenis filter
    const activeJenisTab = document.querySelector('.filter-tab.filter-jenis.active');
    const filterJenis = activeJenisTab ? activeJenisTab.dataset.filter : 'all';

    // Get Jenjang filter
    const activeJenjangTab = document.querySelector('.filter-tab.filter-jenjang.active');
    const filterJenjang = activeJenjangTab ? activeJenjangTab.dataset.jenjang : 'all';

    // Get Lokasi filter
    const lokasiSelect = document.getElementById('lokasiFilter');
    const filterLokasi = lokasiSelect ? lokasiSelect.value : 'all';

    let results = allUniversities;

    // Search term filter
    if (searchTerm) {
        results = results.filter(uni => {
            const text = `${uni['Perguruan Tinggi'] || ''} ${uni['Program Studi'] || ''} ${uni.Lokasi || ''} ${uni.Bidang || ''}`.toLowerCase();
            return text.includes(searchTerm);
        });
    }

    // Jenis filter (Beasiswa type)
    if (filterJenis && filterJenis !== 'all') {
        results = results.filter(uni => uni.Beasiswa === filterJenis);
    }

    // Jenjang filter (Degree level)
    if (filterJenjang && filterJenjang !== 'all') {
        results = results.filter(uni => {
            const jenjang = (uni['Jenjang Studi'] || '').toLowerCase();
            if (filterJenjang === 'magister') {
                return jenjang === 'magister' || jenjang === 'master';
            } else if (filterJenjang === 'doktor') {
                return jenjang === 'doktor';
            }
            return true;
        });
    }

    // Lokasi filter
    if (filterLokasi && filterLokasi !== 'all') {
        results = results.filter(uni => uni.Lokasi === filterLokasi);
    }

    filteredUniversities = results;
    currentPage = 1;
    updateResultCount();
    displayResults();
}

function updateResultCount() {
    const countEl = document.getElementById('resultCount');
    if (countEl) {
        countEl.textContent = `Menampilkan ${filteredUniversities.length.toLocaleString('id-ID')} hasil`;
    }
}

// Display Results
function displayResults() {
    const tbody = document.getElementById('tableBody');
    if (!tbody) return;

    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;
    const pageData = filteredUniversities.slice(start, end);

    tbody.innerHTML = pageData.map((uni, idx) => {
        const globalIdx = start + idx;
        const inWishlist = isInWishlist(uni);
        return `
            <tr>
                <td>${uni['Perguruan Tinggi'] || '-'}</td>
                <td>${uni['Program Studi'] || '-'}</td>
                <td><span class="badge ${getBadgeClass(uni.Beasiswa)}">${getTypeLabel(uni.Beasiswa)}</span></td>
                <td>${uni['Jenjang Studi'] || '-'}</td>
                <td>${uni.Lokasi || '-'}</td>
                <td>
                    <button class="wishlist-btn ${inWishlist ? 'active' : ''}" onclick="toggleWishlist(${globalIdx})" title="${inWishlist ? 'Hapus dari wishlist' : 'Tambah ke wishlist'}">
                        <i class="fas fa-heart"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    renderPagination();
}

function getBadgeClass(type) {
    if (!type) return '';
    if (type.includes('STEM Bidang STEM')) return 'badge-stem';
    if (type.includes('SHARE')) return 'badge-share';
    if (type.includes('Pendukung')) return 'badge-support';
    return '';
}

function getTypeLabel(type) {
    if (!type) return '-';
    if (type.includes('STEM Bidang STEM')) return 'STEM';
    if (type.includes('SHARE')) return 'SHARE';
    if (type.includes('Pendukung')) return 'Pendukung';
    return type;
}

// Pagination
function renderPagination() {
    const container = document.getElementById('paginationContainer');
    if (!container) return;

    const totalPages = Math.ceil(filteredUniversities.length / ITEMS_PER_PAGE);
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = `<button class="page-btn" onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
    </button>`;

    const pages = getPageNumbers(currentPage, totalPages);
    pages.forEach(p => {
        if (p === '...') {
            html += `<span class="page-btn page-dots">...</span>`;
        } else {
            html += `<button class="page-btn ${p === currentPage ? 'active' : ''}" onclick="goToPage(${p})">${p}</button>`;
        }
    });

    html += `<button class="page-btn" onclick="goToPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
    </button>`;
    container.innerHTML = html;
}

function getPageNumbers(current, total) {
    if (total <= 7) return Array.from({length: total}, (_, i) => i + 1);
    const pages = [1];
    if (current > 3) pages.push('...');
    for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
        pages.push(i);
    }
    if (current < total - 2) pages.push('...');
    pages.push(total);
    return pages;
}

function goToPage(page) {
    const totalPages = Math.ceil(filteredUniversities.length / ITEMS_PER_PAGE);
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    displayResults();
    document.querySelector('.results-section').scrollIntoView({ behavior: 'smooth' });
}

// File handling - Client-side PDF parsing using pdf.js
async function handleFileSelect() {
    const input = document.getElementById('resumeUpload');
    const fileInfo = document.getElementById('fileInfo');
    
    if (!input.files || !input.files[0]) return;
    
    const file = input.files[0];
    const fileName = file.name.toLowerCase();
    
    // Show loading state
    fileInfo.style.display = 'block';
    fileInfo.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Membaca file...';
    
    try {
        if (fileName.endsWith('.txt')) {
            // Handle TXT files
            resumeText = await file.text();
        } else if (fileName.endsWith('.pdf')) {
            // Handle PDF files using pdf.js
            resumeText = await extractTextFromPDF(file);
        } else {
            throw new Error('Format file tidak didukung. Gunakan PDF atau TXT.');
        }
        
        if (!resumeText || resumeText.trim().length < 50) {
            throw new Error('File kosong atau terlalu pendek');
        }
        
        fileInfo.innerHTML = `<i class="fas fa-check-circle"></i> ${file.name}`;
        fileInfo.style.background = 'linear-gradient(135deg, #DCFCE7, #BBF7D0)';
        fileInfo.style.color = '#16A34A';
        
        console.log(`File parsed successfully: ${resumeText.length} characters`);
        
    } catch (error) {
        console.error('Error parsing file:', error);
        fileInfo.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${error.message || 'Gagal membaca file'}`;
        fileInfo.style.background = '#FEE2E2';
        fileInfo.style.color = '#DC2626';
        resumeText = '';
    }
}

// Extract text from PDF using pdf.js
async function extractTextFromPDF(file) {
    // Load pdf.js dynamically if not already loaded
    if (!window.pdfjsLib) {
        await loadPdfJs();
    }
    
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    
    let fullText = '';
    for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        const pageText = textContent.items.map(item => item.str).join(' ');
        fullText += pageText + '\n\n';
    }
    
    return fullText.trim();
}

// Load pdf.js library dynamically
function loadPdfJs() {
    return new Promise((resolve, reject) => {
        if (window.pdfjsLib) {
            resolve();
            return;
        }
        
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
        script.onload = () => {
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
            resolve();
        };
        script.onerror = () => reject(new Error('Gagal memuat PDF reader'));
        document.head.appendChild(script);
    });
}

// Get filtered universities for analyzer
function getFilteredUniversitiesForAnalyzer() {
    // Get Jenis filter
    const activeJenisTab = document.querySelector('.filter-tab.filter-jenis-analyzer.active');
    const filterJenis = activeJenisTab ? activeJenisTab.dataset.filter : 'all';

    // Get Jenjang filter
    const activeJenjangTab = document.querySelector('.filter-tab.filter-jenjang-analyzer.active');
    const filterJenjang = activeJenjangTab ? activeJenjangTab.dataset.jenjang : 'all';

    // Get Lokasi filter
    const lokasiSelect = document.getElementById('lokasiFilterAnalyzer');
    const filterLokasi = lokasiSelect ? lokasiSelect.value : 'all';

    let results = allUniversities;

    // Jenis filter (Beasiswa type)
    if (filterJenis && filterJenis !== 'all') {
        results = results.filter(uni => uni.Beasiswa === filterJenis);
    }

    // Jenjang filter (Degree level)
    if (filterJenjang && filterJenjang !== 'all') {
        results = results.filter(uni => {
            const jenjang = (uni['Jenjang Studi'] || '').toLowerCase();
            if (filterJenjang === 'magister') {
                return jenjang === 'magister' || jenjang === 'master';
            } else if (filterJenjang === 'doktor') {
                return jenjang === 'doktor';
            }
            return true;
        });
    }

    // Lokasi filter
    if (filterLokasi && filterLokasi !== 'all') {
        results = results.filter(uni => uni.Lokasi === filterLokasi);
    }

    return results;
}

// Resume Analysis
async function analyzeResume() {
    const astaCita = document.getElementById('astaCita').value.trim();
    const resultDiv = document.getElementById('analysisResult');
    const analyzeBtn = document.getElementById('analyzeBtn');

    if (!resumeText) {
        alert('Silakan unggah resume/CV terlebih dahulu');
        return;
    }

    // Get filtered universities based on analyzer filters
    const filteredForAnalysis = getFilteredUniversitiesForAnalyzer();

    if (filteredForAnalysis.length === 0) {
        alert('Tidak ada universitas yang sesuai dengan filter. Silakan ubah filter.');
        return;
    }

    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Menganalisis...';
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = `
        <div class="analyzing-state">
            <div class="analyzing-spinner"></div>
            <p>Menganalisis profilmu dengan AI...</p>
            <p class="analyzing-hint">Ini mungkin memakan waktu 10-30 detik</p>
        </div>
    `;

    try {
        // Include saved dream universities for scoring
        const response = await fetch(`${API_URL}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                resume_text: resumeText,
                asta_cita: astaCita,
                universities: JSON.stringify(filteredForAnalysis.slice(0, 50)),
                dream_universities: myWishlist // Pass saved wishlist
            })
        });

        if (!response.ok) throw new Error('API error');
        
        const result = await response.json();
        displayAnalysisResult(result);
        
    } catch (error) {
        console.error('Analysis error:', error);
        resultDiv.innerHTML = `
            <div class="error-state">
                <i class="fas fa-exclamation-circle"></i>
                <p>Terjadi kesalahan. Silakan coba lagi.</p>
            </div>
        `;
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<i class="fas fa-wand-magic-sparkles"></i> Analisis Profilku';
    }
}

function displayAnalysisResult(result) {
    const div = document.getElementById('analysisResult');
    
    if (result.error) {
        div.innerHTML = `
            <div class="error-state">
                <i class="fas fa-exclamation-circle"></i>
                <p>${result.error}</p>
            </div>
        `;
        return;
    }

    let html = '';
    
    // Overall Score
    if (result.overall_score !== undefined) {
        const scoreColor = result.overall_score >= 70 ? '#10B981' : result.overall_score >= 50 ? '#F59E0B' : '#EF4444';
        html += `
            <div class="result-score">
                <div class="score-circle" style="background: ${scoreColor};">${result.overall_score}</div>
                <p class="score-label">Skor Kecocokan</p>
            </div>
        `;
    }

    // Profile Summary
    if (result.profile_summary) {
        html += `
            <div class="result-section">
                <h4><i class="fas fa-user"></i> Ringkasan Profil</h4>
                <p class="result-text">${result.profile_summary}</p>
            </div>
        `;
    }
    
    // Education Analysis
    if (result.education_analysis) {
        html += `
            <div class="result-section">
                <h4><i class="fas fa-graduation-cap"></i> Analisis Pendidikan</h4>
                <p class="result-text">${result.education_analysis}</p>
            </div>
        `;
    }

    // Work Analysis
    if (result.work_analysis) {
        html += `
            <div class="result-section">
                <h4><i class="fas fa-briefcase"></i> Analisis Pengalaman Kerja</h4>
                <p class="result-text">${result.work_analysis}</p>
            </div>
        `;
    }
    
    // Asta Cita Alignment
    if (result.asta_cita_alignment) {
        html += `
            <div class="result-section highlight-section">
                <h4><i class="fas fa-star"></i> Keselarasan Asta Cita</h4>
                <p class="result-text">${result.asta_cita_alignment}</p>
            </div>
        `;
    }
    
    // Strengths & Areas to Improve
    if ((result.strengths && result.strengths.length) || (result.areas_to_improve && result.areas_to_improve.length)) {
        html += '<div class="result-grid">';
        
        if (result.strengths && result.strengths.length) {
            html += `
                <div class="result-section strength-section">
                    <h4><i class="fas fa-check-circle"></i> Kekuatan</h4>
                    <ul>${result.strengths.map(s => `<li>${s}</li>`).join('')}</ul>
                </div>
            `;
        }
        
        if (result.areas_to_improve && result.areas_to_improve.length) {
            html += `
                <div class="result-section improve-section">
                    <h4><i class="fas fa-arrow-up"></i> Perlu Ditingkatkan</h4>
                    <ul>${result.areas_to_improve.map(a => `<li>${a}</li>`).join('')}</ul>
                </div>
            `;
        }
        
        html += '</div>';
    }

    // Dream University Scores (if user has saved wishlists)
    if (result.dream_scores && result.dream_scores.length) {
        html += `<div class="result-section dream-scores-section">
            <h4><i class="fas fa-heart"></i> Skor Universitas Impianmu</h4>
            <div class="dream-scores-list">`;
        result.dream_scores.forEach(dream => {
            const scoreColor = dream.score >= 80 ? '#10B981' : dream.score >= 60 ? '#F59E0B' : '#EF4444';
            html += `
                <div class="dream-score-card">
                    <div class="dream-header">
                        <h5>${dream.university}</h5>
                        <span class="dream-score" style="background: ${scoreColor};">${dream.score}</span>
                    </div>
                    <div class="dream-program">${dream.program || ''}</div>
                    <div class="dream-assessment">
                        <strong>Penilaian:</strong> ${dream.assessment || ''}
                    </div>
                    ${dream.gap_analysis ? `<div class="dream-gap">
                        <strong>Yang perlu ditingkatkan:</strong> ${dream.gap_analysis}
                    </div>` : ''}
                </div>
            `;
        });
        html += '</div></div>';
    }

    // Top 5 Recommendations
    if (result.top_5_recommendations && result.top_5_recommendations.length) {
        html += `<div class="result-section"><h4><i class="fas fa-university"></i> Rekomendasi Sistem</h4><div class="recommendations-list">`;
        result.top_5_recommendations.forEach(rec => {
            const scoreColor = rec.score >= 80 ? '#10B981' : rec.score >= 60 ? '#F59E0B' : '#6B7280';
            html += `
                <div class="recommendation-card">
                    <div class="rec-header">
                        <span class="rec-rank">#${rec.rank}</span>
                        <span class="rec-score" style="background: ${scoreColor};">${rec.score}</span>
                    </div>
                    <h5>${rec.university}</h5>
                    <div class="rec-program">${rec.program}</div>
                    <div class="rec-location"><i class="fas fa-map-marker-alt"></i> ${rec.location || '-'}</div>
                    <p class="rec-reasoning">${rec.reasoning || ''}</p>
                </div>
            `;
        });
        html += '</div></div>';
    }
    
    // Advice
    if (result.advice) {
        html += `
            <div class="result-section advice-section">
                <h4><i class="fas fa-lightbulb"></i> Saran</h4>
                <p class="result-text">${result.advice}</p>
            </div>
        `;
    }
    
    // Raw response fallback
    if (result.raw_response && !result.overall_score) {
        html = `<div class="raw-response">${result.raw_response}</div>`;
    }

    div.innerHTML = html || '<p>Tidak ada hasil analisis</p>';
}

// ============ WISHLIST FUNCTIONS ============

// Generate or get user fingerprint
function getOrCreateFingerprint() {
    let fp = localStorage.getItem('lpdp_fingerprint');
    if (!fp) {
        fp = 'user_' + Math.random().toString(36).substring(2) + Date.now().toString(36);
        localStorage.setItem('lpdp_fingerprint', fp);
    }
    return fp;
}

// Load user's wishlist from API
async function loadMyWishlist() {
    try {
        const res = await fetch(`${API_URL}/wishlist?fingerprint=${userFingerprint}`);
        if (res.ok) {
            const data = await res.json();
            myWishlist = data.wishlists || [];
            // Initialize draft from saved (deep copy)
            draftWishlist = myWishlist.map(w => ({...w}));
            hasUnsavedChanges = false;
            updateWishlistUI();
        }
    } catch (e) {
        console.error('Error loading wishlist:', e);
    }
}

// Check if university is in draft wishlist
function isInWishlist(uni) {
    return draftWishlist.some(w =>
        w.university_name === uni['Perguruan Tinggi'] &&
        w.program_name === uni['Program Studi']
    );
}

// Add to draft wishlist (local only)
function addToDraft(uni) {
    if (draftWishlist.length >= 3) {
        alert('Maksimal 3 studi impian. Hapus salah satu untuk menambahkan yang baru.');
        return;
    }

    // Check if already in draft
    const exists = draftWishlist.some(w =>
        w.university_name === uni['Perguruan Tinggi'] &&
        w.program_name === uni['Program Studi']
    );
    if (exists) return;

    // Add to draft with temporary ID
    draftWishlist.push({
        id: 'draft_' + Date.now(),
        university_name: uni['Perguruan Tinggi'] || '',
        program_name: uni['Program Studi'] || '',
        location: uni.Lokasi || '',
        jenjang: uni['Jenjang Studi'] || '',
        beasiswa: uni.Beasiswa || '',
        isNew: true // Mark as new (not in DB yet)
    });

    hasUnsavedChanges = true;
    updateWishlistUI();
    displayResults();
}

// Remove from draft wishlist (local only)
function removeFromDraft(id) {
    draftWishlist = draftWishlist.filter(w => w.id !== id);
    hasUnsavedChanges = true;
    updateWishlistUI();
    displayResults();
}

// Toggle draft wishlist
function toggleWishlist(uniIndex) {
    const uni = filteredUniversities[uniIndex];
    if (!uni) return;

    const existing = draftWishlist.find(w =>
        w.university_name === uni['Perguruan Tinggi'] &&
        w.program_name === uni['Program Studi']
    );

    if (existing) {
        removeFromDraft(existing.id);
    } else {
        addToDraft(uni);
    }
}

// Save draft to database
async function saveWishlist() {
    const saveBtn = document.getElementById('saveWishlistBtn');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Menyimpan...';
    }

    try {
        // Delete items that were removed
        const toDelete = myWishlist.filter(saved =>
            !draftWishlist.some(d => d.id === saved.id)
        );
        for (const item of toDelete) {
            await fetch(`${API_URL}/wishlist?id=${item.id}&fingerprint=${userFingerprint}`, {
                method: 'DELETE'
            });
        }

        // Add new items
        const toAdd = draftWishlist.filter(d => d.isNew);
        for (const item of toAdd) {
            await fetch(`${API_URL}/wishlist`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_fingerprint: userFingerprint,
                    university_name: item.university_name,
                    program_name: item.program_name,
                    location: item.location,
                    jenjang: item.jenjang,
                    beasiswa: item.beasiswa
                })
            });
        }

        // Reload from DB to get proper IDs
        await loadMyWishlist();
        alert('Studi impian berhasil disimpan!');
        loadInsights(); // Refresh insights
    } catch (e) {
        console.error('Error saving wishlist:', e);
        alert('Gagal menyimpan. Coba lagi.');
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="fas fa-save"></i> Simpan Impian';
        }
    }
}

// Update wishlist UI
function updateWishlistUI() {
    const container = document.getElementById('myWishlist');
    const saveBtn = document.getElementById('saveWishlistBtn');
    if (!container) return;

    // Show/hide save button based on changes
    if (saveBtn) {
        saveBtn.style.display = hasUnsavedChanges ? 'inline-flex' : 'none';
    }

    if (draftWishlist.length === 0) {
        container.innerHTML = `
            <div class="wishlist-empty">
                <i class="fas fa-heart"></i>
                <p>Belum ada studi impian</p>
                <p class="wishlist-hint">Klik ❤️ pada universitas untuk menambahkan</p>
            </div>
        `;
        return;
    }

    container.innerHTML = draftWishlist.map(w => `
        <div class="wishlist-card ${w.isNew ? 'wishlist-card-new' : ''}">
            <button class="wishlist-remove" onclick="removeFromDraft('${w.id}')">
                <i class="fas fa-times"></i>
            </button>
            ${w.isNew ? '<span class="wishlist-new-badge">Baru</span>' : ''}
            <h4>${w.university_name}</h4>
            <p class="wishlist-program">${w.program_name}</p>
            <div class="wishlist-meta">
                <span><i class="fas fa-map-marker-alt"></i> ${w.location}</span>
                <span class="badge ${getBadgeClass(w.beasiswa)}">${getTypeLabel(w.beasiswa)}</span>
            </div>
        </div>
    `).join('');
}

// ============ INSIGHTS FUNCTIONS ============

let insightsData = null;
let insightsFilters = { location: null, jenjang: null, beasiswa: null, university: null };
let chartInstances = { location: null, jenjang: null, beasiswa: null };

async function loadInsights(filters = {}) {
    try {
        // Build query string with filters
        const params = new URLSearchParams();
        if (filters.location) params.append('location', filters.location);
        if (filters.jenjang) params.append('jenjang', filters.jenjang);
        if (filters.beasiswa) params.append('beasiswa', filters.beasiswa);
        if (filters.university) params.append('university', filters.university);

        const queryString = params.toString();
        const url = queryString ? `${API_URL}/insights?${queryString}` : `${API_URL}/insights`;

        const res = await fetch(url);
        if (res.ok) {
            insightsData = await res.json();
            insightsFilters = filters;
            renderInsights();
            updateFilterIndicator();
        }
    } catch (e) {
        console.error('Error loading insights:', e);
    }
}

function renderInsights() {
    if (!insightsData) return;

    // Update stats
    const totalEl = document.getElementById('totalWishlists');
    const usersEl = document.getElementById('totalUsers');
    if (totalEl) totalEl.textContent = insightsData.total_wishlists.toLocaleString('id-ID');
    if (usersEl) usersEl.textContent = insightsData.total_users.toLocaleString('id-ID');

    // Render charts if Chart.js is loaded
    if (window.Chart) {
        renderLocationChart();
        renderJenjangChart();
        renderBeasiswaChart();
    }

    // Render top universities list
    renderTopUniversities();

    // Render word cloud
    renderWordCloud();
}

function updateFilterIndicator() {
    const indicator = document.getElementById('filterIndicator');
    if (!indicator) return;

    const hasFilters = insightsFilters.location || insightsFilters.jenjang || insightsFilters.beasiswa || insightsFilters.university;

    if (hasFilters) {
        const parts = [];
        if (insightsFilters.location) parts.push(insightsFilters.location);
        if (insightsFilters.jenjang) parts.push(insightsFilters.jenjang);
        if (insightsFilters.beasiswa) parts.push(getTypeLabel(insightsFilters.beasiswa));
        if (insightsFilters.university) parts.push(insightsFilters.university);
        indicator.innerHTML = `<span class="filter-active"><i class="fas fa-filter"></i> Filter aktif: ${parts.join(', ')} <button onclick="clearInsightsFilter()" class="clear-filter-btn"><i class="fas fa-times"></i></button></span>`;
        indicator.style.display = 'block';
    } else {
        indicator.style.display = 'none';
    }
}

function clearInsightsFilter() {
    insightsFilters = { location: null, jenjang: null, beasiswa: null, university: null };
    loadInsights({});
}

function applyInsightsFilter(type, value) {
    // Toggle filter - if same value clicked, clear it
    if (insightsFilters[type] === value) {
        insightsFilters[type] = null;
    } else {
        insightsFilters[type] = value;
    }
    loadInsights(insightsFilters);
}

function renderLocationChart() {
    const ctx = document.getElementById('locationChart');
    if (!ctx || !insightsData.top_locations) return;

    // Destroy existing chart
    if (chartInstances.location) {
        chartInstances.location.destroy();
    }

    const locations = insightsData.top_locations.slice(0, 8);

    chartInstances.location = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: locations.map(l => l.name),
            datasets: [{
                label: 'Jumlah',
                data: locations.map(l => l.count),
                backgroundColor: locations.map(l =>
                    insightsFilters.location === l.name ? '#4F46E5' : '#6366F1'
                ),
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { x: { beginAtZero: true } },
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const location = locations[index].name;
                    applyInsightsFilter('location', location);
                }
            }
        }
    });
}

function renderJenjangChart() {
    const ctx = document.getElementById('jenjangChart');
    if (!ctx || !insightsData.by_jenjang) return;

    // Destroy existing chart
    if (chartInstances.jenjang) {
        chartInstances.jenjang.destroy();
    }

    const labels = Object.keys(insightsData.by_jenjang);
    const data = Object.values(insightsData.by_jenjang);
    const baseColors = ['#6366F1', '#0D9488', '#F59E0B', '#EF4444'];

    chartInstances.jenjang = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: baseColors,
                borderWidth: labels.map((l, i) => insightsFilters.jenjang === l ? 4 : 1),
                borderColor: labels.map((l, i) => insightsFilters.jenjang === l ? '#1F2937' : '#fff')
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { position: 'bottom' } },
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const jenjang = labels[index];
                    applyInsightsFilter('jenjang', jenjang);
                }
            }
        }
    });
}

function renderBeasiswaChart() {
    const ctx = document.getElementById('beasiswaChart');
    if (!ctx || !insightsData.by_beasiswa) return;

    // Destroy existing chart
    if (chartInstances.beasiswa) {
        chartInstances.beasiswa.destroy();
    }

    const rawLabels = Object.keys(insightsData.by_beasiswa);
    const labels = rawLabels.map(b => getTypeLabel(b));
    const data = Object.values(insightsData.by_beasiswa);
    const baseColors = ['#10B981', '#3B82F6', '#F59E0B', '#6B7280'];

    chartInstances.beasiswa = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: baseColors,
                borderWidth: rawLabels.map(l => insightsFilters.beasiswa === l ? 4 : 1),
                borderColor: rawLabels.map(l => insightsFilters.beasiswa === l ? '#1F2937' : '#fff')
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { position: 'bottom' } },
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const beasiswa = rawLabels[index];
                    applyInsightsFilter('beasiswa', beasiswa);
                }
            }
        }
    });
}

function renderTopUniversities() {
    const container = document.getElementById('topUniversities');
    if (!container || !insightsData.top_universities) return;

    if (insightsData.top_universities.length === 0) {
        container.innerHTML = '<p class="no-data">Belum ada data</p>';
        return;
    }

    container.innerHTML = insightsData.top_universities.slice(0, 5).map((u, i) => `
        <div class="ranking-item ${insightsFilters.university === u.name ? 'ranking-item-active' : ''}" onclick="applyInsightsFilter('university', '${u.name.replace(/'/g, "\\'")}')">
            <span class="ranking-number">${i + 1}</span>
            <div class="ranking-info">
                <span class="ranking-name">${u.name}</span>
                <span class="ranking-count">${u.count} impian</span>
            </div>
        </div>
    `).join('');
}

function renderWordCloud() {
    const container = document.getElementById('programWordCloud');
    if (!container || !insightsData.program_keywords) return;

    if (insightsData.program_keywords.length === 0) {
        container.innerHTML = '<p class="no-data">Belum ada data</p>';
        return;
    }

    // Get max count for scaling
    const maxCount = Math.max(...insightsData.program_keywords.map(k => k.count));
    const minSize = 12;
    const maxSize = 36;

    // Color palette
    const colors = ['#6366F1', '#0D9488', '#F59E0B', '#EC4899', '#10B981', '#3B82F6', '#8B5CF6', '#EF4444'];

    container.innerHTML = insightsData.program_keywords.map((keyword, i) => {
        // Scale font size based on count
        const size = minSize + ((keyword.count / maxCount) * (maxSize - minSize));
        const color = colors[i % colors.length];
        const opacity = 0.7 + (keyword.count / maxCount) * 0.3;

        return `<span class="word-cloud-item" style="font-size: ${size}px; color: ${color}; opacity: ${opacity};" title="${keyword.count} kali">${keyword.word}</span>`;
    }).join('');
}

// Expose to global
window.performSearch = performSearch;
window.goToPage = goToPage;
window.analyzeResume = analyzeResume;
window.scrollToAnalyzer = scrollToAnalyzer;
window.toggleWishlist = toggleWishlist;
window.removeFromDraft = removeFromDraft;
window.saveWishlist = saveWishlist;
window.loadInsights = loadInsights;
window.clearInsightsFilter = clearInsightsFilter;
