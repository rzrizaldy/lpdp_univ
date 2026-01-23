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

// Init
document.addEventListener('DOMContentLoaded', async () => {
    await loadData();
    setupEventListeners();
    displayResults();
    setupNavbarScroll();
});

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

    tbody.innerHTML = pageData.map(uni => `
        <tr>
            <td>${uni['Perguruan Tinggi'] || '-'}</td>
            <td>${uni['Program Studi'] || '-'}</td>
            <td><span class="badge ${getBadgeClass(uni.Beasiswa)}">${getTypeLabel(uni.Beasiswa)}</span></td>
            <td>${uni['Jenjang Studi'] || '-'}</td>
            <td>${uni.Lokasi || '-'}</td>
        </tr>
    `).join('');

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
        const response = await fetch(`${API_URL}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                resume_text: resumeText,
                asta_cita: astaCita,
                universities: JSON.stringify(filteredForAnalysis.slice(0, 50))
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
    
    // Top 5 Recommendations
    if (result.top_5_recommendations && result.top_5_recommendations.length) {
        html += `<div class="result-section"><h4><i class="fas fa-university"></i> Rekomendasi Universitas</h4><div class="recommendations-list">`;
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

// Expose to global
window.performSearch = performSearch;
window.goToPage = goToPage;
window.analyzeResume = analyzeResume;
window.scrollToAnalyzer = scrollToAnalyzer;
