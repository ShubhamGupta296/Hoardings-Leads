/**
 * Smart Leads Agent for Hoardings - Frontend Dashboard Logic
 * DigiPlus IT Agentic AI Hackathon
 * 
 * Strict compliance with fixed API Contract:
 * - GET /api/vacancies
 * - GET /api/leads/{site_id}
 * - POST /api/pitch  { site_id, customer_id }
 * 
 * Grounded directly in real CSV dataset:
 * - hoardings.csv (HRD-100 to HRD-124)
 * - customers.csv (CUST-30 to CUST-49, low/mid/high, real industries)
 * - bookings.csv (B-2201 to B-2249)
 */

(function () {
  'use strict';

  // API Base Endpoint Configuration
  const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : '';

  // App State
  const state = {
    isDemoMode: false,
    vacancies: [],
    filteredVacancies: [],
    selectedSiteId: null,
    selectedSite: null,
    leads: [],
    searchQuery: '',
    rateBandFilter: 'all',
    urgencyFilter: 'all',
    currentPitch: null
  };

  // Real Dataset Grounded Mock for Fallback/Demo Mode (15 real vacancies out of 25 sites in next 90d)
  const MOCK_DATA = {
    today: "2026-08-08",
    window_days: 90,
    vacancies: [
      { site_id: "HRD-122", location: "SV Road Junction Borivali #3", size_sqft: 800, traffic_score: 5.9, monthly_rate_inr: 400000, free_from: "2026-08-15", days_until_vacant: 7, revenue_at_risk: 400000 },
      { site_id: "HRD-118", location: "Sion Circle #2", size_sqft: 600, traffic_score: 9.4, monthly_rate_inr: 250000, free_from: "2026-08-28", days_until_vacant: 20, revenue_at_risk: 250000 },
      { site_id: "HRD-103", location: "WEH Goregaon North", size_sqft: 400, traffic_score: 8.0, monthly_rate_inr: 250000, free_from: "2026-08-30", days_until_vacant: 22, revenue_at_risk: 250000 },
      { site_id: "HRD-120", location: "Kandivali Flyover WEB #3", size_sqft: 1200, traffic_score: 9.1, monthly_rate_inr: 120000, free_from: "2026-09-15", days_until_vacant: 38, revenue_at_risk: 120000 },
      { site_id: "HRD-123", location: "WEH Goregaon North #3", size_sqft: 400, traffic_score: 6.7, monthly_rate_inr: 180000, free_from: "2026-09-28", days_until_vacant: 51, revenue_at_risk: 180000 },
      { site_id: "HRD-106", location: "Thane Ghodbunder Rd", size_sqft: 800, traffic_score: 8.3, monthly_rate_inr: 400000, free_from: "2026-09-30", days_until_vacant: 53, revenue_at_risk: 400000 },
      { site_id: "HRD-108", location: "Sion Circle", size_sqft: 800, traffic_score: 8.2, monthly_rate_inr: 120000, free_from: "2026-09-30", days_until_vacant: 53, revenue_at_risk: 120000 },
      { site_id: "HRD-101", location: "Andheri Metro Facing", size_sqft: 1200, traffic_score: 7.1, monthly_rate_inr: 120000, free_from: "2026-10-15", days_until_vacant: 68, revenue_at_risk: 120000 },
      { site_id: "HRD-107", location: "BKC Approach", size_sqft: 400, traffic_score: 9.8, monthly_rate_inr: 250000, free_from: "2026-10-15", days_until_vacant: 68, revenue_at_risk: 250000 },
      { site_id: "HRD-121", location: "Andheri Metro Facing #3", size_sqft: 400, traffic_score: 6.3, monthly_rate_inr: 180000, free_from: "2026-10-15", days_until_vacant: 68, revenue_at_risk: 180000 },
      { site_id: "HRD-124", location: "Link Road Malad #3", size_sqft: 1200, traffic_score: 6.2, monthly_rate_inr: 120000, free_from: "2026-10-15", days_until_vacant: 68, revenue_at_risk: 120000 },
      { site_id: "HRD-105", location: "Dahisar Toll Naka", size_sqft: 400, traffic_score: 8.1, monthly_rate_inr: 120000, free_from: "2026-10-28", days_until_vacant: 81, revenue_at_risk: 120000 },
      { site_id: "HRD-112", location: "SV Road Junction Borivali #2", size_sqft: 600, traffic_score: 9.2, monthly_rate_inr: 180000, free_from: "2026-10-30", days_until_vacant: 83, revenue_at_risk: 180000 },
      { site_id: "HRD-117", location: "BKC Approach #2", size_sqft: 800, traffic_score: 9.1, monthly_rate_inr: 250000, free_from: "2026-10-30", days_until_vacant: 83, revenue_at_risk: 250000 },
      { site_id: "HRD-119", location: "Powai Hiranandani #2", size_sqft: 400, traffic_score: 9.5, monthly_rate_inr: 400000, free_from: "2026-10-30", days_until_vacant: 83, revenue_at_risk: 400000 }
    ],
    leadsDatabase: {
      "HRD-122": [
        { customer_id: "CUST-38", name: "Prime Autos", industry: "retail", budget_band: "high", score: 95, reasons: ["✅ High budget band aligns with ₹400,000/mo premium rate (+25 pts)", "✅ Previous booking history at SV Road Junction Borivali (+20 pts)", "✅ Retail sector top historical rebooking affinity (+15 pts)", "✅ Strong relationship score: 7/10 (+20 pts)", "✅ Contacted recently (+15 pts)"] },
        { customer_id: "CUST-49", name: "ZenCare Clinics", industry: "automotive", budget_band: "high", score: 88, reasons: ["✅ High budget band fits premium site (+25 pts)", "✅ Automotive sector high visibility preference (+15 pts)", "✅ Relationship score: 7/10 (+20 pts)", "✅ Solid client booking volume (+15 pts)"] },
        { customer_id: "CUST-40", name: "Shine Jewels", industry: "fmcg", budget_band: "high", score: 82, reasons: ["✅ High budget band fit (+25 pts)", "✅ FMCG industry affinity for high-traffic billboard (+15 pts)", "✅ Relationship score: 5/10 (+15 pts)", "✅ High renewal probability (+15 pts)"] }
      ],
      "HRD-118": [
        { customer_id: "CUST-47", name: "NovaBikes", industry: "real_estate", budget_band: "mid", score: 94, reasons: ["✅ Prior booking history at Sion Circle location (+20 pts)", "✅ Mid budget band matches site ₹250k/mo rate (+25 pts)", "✅ Excellent Relationship score: 9/10 (+20 pts)", "✅ Real estate ad campaign fit (+15 pts)", "✅ Recency of last contact (+14 pts)"] },
        { customer_id: "CUST-43", name: "PixelWorld TV", industry: "healthcare", budget_band: "mid", score: 87, reasons: ["✅ Latest site customer history (+20 pts)", "✅ Mid budget band match (+25 pts)", "✅ Healthcare location affinity (+15 pts)", "✅ Relationship score: 4/10 (+15 pts)"] },
        { customer_id: "CUST-30", name: "SunGold Jewellers", industry: "retail", budget_band: "mid", score: 81, reasons: ["✅ Mid budget band tier (+25 pts)", "✅ Retail jewellery campaign fit (+15 pts)", "✅ Relationship score: 6/10 (+18 pts)", "✅ Active repeat client (+13 pts)"] }
      ],
      "HRD-103": [
        { customer_id: "CUST-35", name: "CarePlus Hospitals", industry: "healthcare", budget_band: "low", score: 90, reasons: ["✅ Latest booking history on WEH Goregaon site (+20 pts)", "✅ Healthcare local footprint (+15 pts)", "✅ Portfolio booking volume (+15 pts)", "✅ Relationship score: 4/10 (+15 pts)", "✅ High renewal affinity (+15 pts)"] },
        { customer_id: "CUST-30", name: "SunGold Jewellers", industry: "retail", budget_band: "mid", score: 84, reasons: ["✅ Mid budget band match for ₹250k site (+25 pts)", "✅ Retail sector highway visibility (+15 pts)", "✅ Relationship score: 6/10 (+18 pts)", "✅ Recent contact logged (+16 pts)"] },
        { customer_id: "CUST-48", name: "BrightFuture Edu", industry: "fmcg", budget_band: "low", score: 79, reasons: ["✅ Excellent relationship score: 9/10 (+20 pts)", "✅ Education/FMCG campaign affinity (+15 pts)", "✅ Past WEH hoarding bookings (+14 pts)"] }
      ],
      "HRD-106": [
        { customer_id: "CUST-38", name: "Prime Autos", industry: "retail", budget_band: "high", score: 96, reasons: ["✅ High budget band fits ₹400,000/mo rate (+25 pts)", "✅ Thane Ghodbunder corridor high traffic preference (+15 pts)", "✅ Relationship score: 7/10 (+20 pts)", "✅ Strong payment history (+20 pts)", "✅ Active enquiry logged (+16 pts)"] },
        { customer_id: "CUST-49", name: "ZenCare Clinics", industry: "automotive", budget_band: "high", score: 89, reasons: ["✅ High budget band tier (+25 pts)", "✅ Automotive sector highway billboard preference (+15 pts)", "✅ Relationship score: 7/10 (+20 pts)", "✅ Last contact 3 weeks ago (+14 pts)"] },
        { customer_id: "CUST-40", name: "Shine Jewels", industry: "fmcg", budget_band: "high", score: 83, reasons: ["✅ High budget band tier (+25 pts)", "✅ FMCG brand high visibility campaign (+15 pts)", "✅ Relationship score: 5/10 (+15 pts)"] }
      ],
      "DEFAULT": [
        { customer_id: "CUST-38", name: "Prime Autos", industry: "retail", budget_band: "high", score: 89, reasons: ["✅ High budget band alignment (+25 pts)", "✅ Strong portfolio history across Mumbai hoardings (+15 pts)", "✅ Relationship score: 7/10 (+20 pts)", "✅ Active campaign enquiry (+14 pts)"] },
        { customer_id: "CUST-30", name: "SunGold Jewellers", industry: "retail", budget_band: "mid", score: 84, reasons: ["✅ Mid budget band alignment (+25 pts)", "✅ Retail industry billboard affinity (+15 pts)", "✅ Relationship score: 6/10 (+18 pts)", "✅ Consistent client (+16 pts)"] },
        { customer_id: "CUST-48", name: "BrightFuture Edu", industry: "fmcg", budget_band: "low", score: 78, reasons: ["✅ High relationship score: 9/10 (+20 pts)", "✅ Regional campaign history (+15 pts)", "✅ High response probability (+13 pts)"] }
      ]
    }
  };

  // DOM Element References
  const elements = {
    connectionStatus: document.getElementById('connectionStatus'),
    statusDot: document.getElementById('statusDot'),
    statusText: document.getElementById('statusText'),
    toggleDemoBtn: document.getElementById('toggleDemoBtn'),

    statVacanciesCount: document.getElementById('statVacanciesCount'),
    statRevenueRisk: document.getElementById('statRevenueRisk'),
    statUrgentCount: document.getElementById('statUrgentCount'),
    statAvgRate: document.getElementById('statAvgRate'),

    timelineGrid: document.getElementById('timelineGrid'),

    vacancyList: document.getElementById('vacancyList'),
    vacancyListCount: document.getElementById('vacancyListCount'),
    vacancyLoading: document.getElementById('vacancyLoading'),

    searchInput: document.getElementById('searchInput'),
    clearSearchBtn: document.getElementById('clearSearchBtn'),
    budgetBandFilters: document.getElementById('budgetBandFilters'),
    urgencyFilters: document.getElementById('urgencyFilters'),

    emptyDetailState: document.getElementById('emptyDetailState'),
    activeDetailContent: document.getElementById('activeDetailContent'),

    selectedSiteId: document.getElementById('selectedSiteId'),
    selectedSiteLocation: document.getElementById('selectedSiteLocation'),
    selectedSiteRate: document.getElementById('selectedSiteRate'),
    selectedSiteSize: document.getElementById('selectedSiteSize'),
    selectedSiteTraffic: document.getElementById('selectedSiteTraffic'),
    selectedSiteFreeFrom: document.getElementById('selectedSiteFreeFrom'),
    selectedSiteRevenueRisk: document.getElementById('selectedSiteRevenueRisk'),

    leadsContainer: document.getElementById('leadsContainer'),
    leadsLoading: document.getElementById('leadsLoading'),

    pitchModal: document.getElementById('pitchModal'),
    closePitchModalBtn: document.getElementById('closePitchModalBtn'),
    cancelPitchBtn: document.getElementById('cancelPitchBtn'),
    copyPitchBtn: document.getElementById('copyPitchBtn'),
    pitchModalTitle: document.getElementById('pitchModalTitle'),
    pitchModalSubtitle: document.getElementById('pitchModalSubtitle'),
    pitchLoading: document.getElementById('pitchLoading'),
    pitchContentWrapper: document.getElementById('pitchContentWrapper'),
    pitchSuggestedRate: document.getElementById('pitchSuggestedRate'),
    pitchReasonsList: document.getElementById('pitchReasonsList'),
    pitchTextArea: document.getElementById('pitchTextArea'),

    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toastMessage')
  };

  // Format Helper Functions
  function formatCurrency(amount) {
    if (typeof amount !== 'number') return '₹0';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount);
  }

  function formatDateString(dateStr) {
    if (!dateStr) return 'N/A';
    try {
      const parts = dateStr.split('-');
      if (parts.length === 3) {
        const d = new Date(parts[0], parts[1] - 1, parts[2]);
        return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
      }
      return dateStr;
    } catch (e) {
      return dateStr;
    }
  }

  function formatIndustryName(ind) {
    if (!ind) return 'Commercial';
    const map = {
      'real_estate': 'Real Estate',
      'fmcg': 'FMCG',
      'automotive': 'Automotive',
      'retail': 'Retail',
      'education': 'Education',
      'healthcare': 'Healthcare',
      'jewellery': 'Jewellery',
      'electronics': 'Electronics'
    };
    const key = String(ind).toLowerCase();
    return map[key] || (ind.charAt(0).toUpperCase() + ind.slice(1));
  }

  function showToast(message) {
    elements.toastMessage.textContent = message;
    elements.toast.classList.remove('hidden');
    setTimeout(() => {
      elements.toast.classList.add('hidden');
    }, 3000);
  }

  function determineRateBand(monthlyRate) {
    if (monthlyRate < 150000) return 'low';
    if (monthlyRate <= 250000) return 'mid';
    return 'high';
  }

  function getUrgencyCategory(days) {
    if (days <= 30) return 'urgent';
    if (days <= 60) return 'upcoming';
    return 'future';
  }

  // API Call Functions with Auto-Fallback
  async function fetchVacancies() {
    elements.vacancyLoading.classList.remove('hidden');
    
    if (state.isDemoMode) {
      setTimeout(() => {
        state.vacancies = MOCK_DATA.vacancies;
        onVacanciesLoaded();
      }, 300);
      return;
    }

    try {
      elements.statusText.textContent = 'Connecting to API...';
      elements.statusDot.className = 'status-dot';

      const response = await fetch(`${API_BASE}/api/vacancies`, { signal: AbortSignal.timeout(3000) });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const data = await response.json();
      state.vacancies = data.vacancies || [];
      state.isDemoMode = false;
      
      elements.statusDot.className = 'status-dot live';
      elements.statusText.textContent = 'Live Backend Connected';
      
      onVacanciesLoaded();
    } catch (err) {
      console.warn('Backend API connection failed, switching to Demo Mode:', err.message);
      state.isDemoMode = true;
      state.vacancies = MOCK_DATA.vacancies;
      
      elements.statusDot.className = 'status-dot demo';
      elements.statusText.textContent = 'Demo Mode (Offline Mock)';
      
      onVacanciesLoaded();
    }
  }

  async function fetchLeads(siteId) {
    elements.leadsLoading.classList.remove('hidden');
    elements.leadsContainer.innerHTML = '';

    if (state.isDemoMode) {
      setTimeout(() => {
        const mockLeads = MOCK_DATA.leadsDatabase[siteId] || MOCK_DATA.leadsDatabase['DEFAULT'];
        state.leads = mockLeads;
        renderLeadsList();
        elements.leadsLoading.classList.add('hidden');
      }, 350);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/leads/${encodeURIComponent(siteId)}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      state.leads = data.leads || [];
      renderLeadsList();
    } catch (err) {
      console.warn(`Failed to fetch live leads for ${siteId}, using fallback:`, err.message);
      const mockLeads = MOCK_DATA.leadsDatabase[siteId] || MOCK_DATA.leadsDatabase['DEFAULT'];
      state.leads = mockLeads;
      renderLeadsList();
    } finally {
      elements.leadsLoading.classList.add('hidden');
    }
  }

  async function requestPitch(siteId, customerId) {
    elements.pitchLoading.classList.remove('hidden');
    elements.pitchContentWrapper.classList.add('hidden');
    elements.pitchModal.classList.remove('hidden');

    if (state.isDemoMode) {
      setTimeout(() => {
        const site = state.selectedSite || { location: 'Location', monthly_rate_inr: 250000, size_sqft: 600, traffic_score: 8.5 };
        const lead = state.leads.find(l => l.customer_id === customerId) || { name: 'Client', industry: 'retail' };
        
        const mockPitch = {
          suggested_rate: site.monthly_rate_inr,
          reasons: lead.reasons || ["✅ Proven category match", "✅ Premium location visibility"],
          pitch: `Subject: Exclusive Outdoor Branding Rights: Billboard at ${site.location} (${site.site_id})\n\nDear ${lead.name} Team,\n\nI hope this email finds you well.\n\nWe are pleased to offer your team first-right-of-refusal for our flagship high-visibility billboard located at ${site.location}.\n\nKEY SITE HIGHLIGHTS:\n- Site ID: ${site.site_id}\n- Location: ${site.location}\n- Dimensions: ${site.size_sqft} sq.ft.\n- Daily Traffic Score: ${site.traffic_score}/10\n- Special Suggested Rate: ${formatCurrency(site.monthly_rate_inr)} / month (Aligned with your ${formatIndustryName(lead.industry)} budget band)\n\nGiven your strong campaign profile, this site represents an extraordinary fit for your upcoming brand awareness push.\n\nThis location falls vacant on ${formatDateString(site.free_from)}. Shall we lock this slot in for your upcoming campaign?\n\nBest regards,\nSales Team | Smart Hoardings Agent`
        };

        renderPitchModal(lead, mockPitch);
        elements.pitchLoading.classList.add('hidden');
        elements.pitchContentWrapper.classList.remove('hidden');
      }, 400);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/pitch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ site_id: siteId, customer_id: customerId })
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      const lead = state.leads.find(l => l.customer_id === customerId) || { name: 'Client' };
      
      renderPitchModal(lead, data);
    } catch (err) {
      console.warn('Failed to fetch AI pitch from server, using template:', err.message);
      const site = state.selectedSite || { location: 'Location', monthly_rate_inr: 250000, size_sqft: 600, traffic_score: 8.5 };
      const lead = state.leads.find(l => l.customer_id === customerId) || { name: 'Client', industry: 'retail' };
      
      const fallbackPitch = {
        suggested_rate: site.monthly_rate_inr,
        reasons: lead.reasons || ["✅ Budget band aligned", "✅ Historical affinity"],
        pitch: `Subject: Proposal for Hoarding Site ${site.site_id} (${site.location})\n\nDear ${lead.name},\n\nWe have an upcoming vacant billboard at ${site.location} available starting ${formatDateString(site.free_from)}.\n\nSite Specs:\n- Dimensions: ${site.size_sqft} sqft\n- Traffic Index: ${site.traffic_score}/10\n- Offered Rate: ${formatCurrency(site.monthly_rate_inr)} / month\n\nPlease let us know if you would like to reserve this site.`
      };
      renderPitchModal(lead, fallbackPitch);
    } finally {
      elements.pitchLoading.classList.add('hidden');
      elements.pitchContentWrapper.classList.remove('hidden');
    }
  }

  // UI Event & Logic Handler
  function onVacanciesLoaded() {
    elements.vacancyLoading.classList.add('hidden');
    
    // Sort soonest-first (ascending by days_until_vacant)
    state.vacancies.sort((a, b) => a.days_until_vacant - b.days_until_vacant);
    
    computeHeaderMetrics();
    renderTimelineVisual();
    applyFilters();

    // Auto select first vacancy if available
    if (state.filteredVacancies.length > 0) {
      selectSite(state.filteredVacancies[0].site_id);
    }
  }

  function computeHeaderMetrics() {
    const totalVacancies = state.vacancies.length;
    const totalRevenueRisk = state.vacancies.reduce((sum, v) => sum + (v.revenue_at_risk || v.monthly_rate_inr || 0), 0);
    const urgentCount = state.vacancies.filter(v => v.days_until_vacant <= 30).length;
    const avgRate = totalVacancies > 0 ? Math.round(totalRevenueRisk / totalVacancies) : 0;

    elements.statVacanciesCount.textContent = totalVacancies;
    elements.statRevenueRisk.textContent = formatCurrency(totalRevenueRisk);
    elements.statUrgentCount.textContent = urgentCount;
    elements.statAvgRate.textContent = formatCurrency(avgRate);
  }

  function renderTimelineVisual() {
    elements.timelineGrid.innerHTML = '';

    if (state.vacancies.length === 0) {
      elements.timelineGrid.innerHTML = '<div style="color:var(--text-muted);font-size:0.8rem;padding:0.5rem;">No vacancies found</div>';
      return;
    }

    state.vacancies.forEach(site => {
      const days = site.days_until_vacant;
      const urgencyClass = getUrgencyCategory(days);
      const percent = Math.min(Math.max(Math.round((days / 90) * 100), 10), 100);

      const row = document.createElement('div');
      row.className = `timeline-item ${state.selectedSiteId === site.site_id ? 'active' : ''}`;
      row.dataset.siteId = site.site_id;

      row.innerHTML = `
        <div class="timeline-label" title="${site.site_id} - ${site.location}">${site.site_id} &bull; ${site.location.split('#')[0]}</div>
        <div class="timeline-bar-bg">
          <div class="timeline-bar-fill ${urgencyClass}" style="width: ${percent}%;">
            ${days}d
          </div>
        </div>
      `;

      row.addEventListener('click', () => selectSite(site.site_id));
      elements.timelineGrid.appendChild(row);
    });
  }

  function applyFilters() {
    state.filteredVacancies = state.vacancies.filter(site => {
      // Search query filter (location or site_id)
      if (state.searchQuery) {
        const q = state.searchQuery.toLowerCase();
        const locMatch = site.location.toLowerCase().includes(q);
        const idMatch = site.site_id.toLowerCase().includes(q);
        if (!locMatch && !idMatch) return false;
      }

      // Rate band filter
      if (state.rateBandFilter !== 'all') {
        const band = determineRateBand(site.monthly_rate_inr);
        if (band !== state.rateBandFilter) return false;
      }

      // Urgency filter
      if (state.urgencyFilter !== 'all') {
        const limitDays = parseInt(state.urgencyFilter, 10);
        if (limitDays === 30 && site.days_until_vacant > 30) return false;
        if (limitDays === 60 && (site.days_until_vacant <= 30 || site.days_until_vacant > 60)) return false;
        if (limitDays === 90 && (site.days_until_vacant <= 60 || site.days_until_vacant > 90)) return false;
      }

      return true;
    });

    elements.vacancyListCount.textContent = state.filteredVacancies.length;
    renderVacancyList();
  }

  function renderVacancyList() {
    elements.vacancyList.innerHTML = '';

    if (state.filteredVacancies.length === 0) {
      elements.vacancyList.innerHTML = `
        <div class="loading-spinner-box">
          <p>No vacant billboards match your filter criteria.</p>
        </div>
      `;
      return;
    }

    state.filteredVacancies.forEach(site => {
      const urgencyClass = getUrgencyCategory(site.days_until_vacant);
      const isSelected = site.site_id === state.selectedSiteId;

      const card = document.createElement('div');
      card.className = `vacancy-card ${isSelected ? 'selected' : ''}`;
      card.dataset.siteId = site.site_id;

      card.innerHTML = `
        <div class="card-top-row">
          <div class="card-location-info">
            <span class="card-site-id">${site.site_id}</span>
            <h4 class="card-location-title">${site.location}</h4>
          </div>
          <span class="badge-urgency ${urgencyClass}">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
            In ${site.days_until_vacant} days
          </span>
        </div>

        <div class="card-metrics-grid">
          <div class="card-metric-item">
            <span class="card-metric-label">Monthly Rate</span>
            <span class="card-metric-value">${formatCurrency(site.monthly_rate_inr)}</span>
          </div>
          <div class="card-metric-item">
            <span class="card-metric-label">Size</span>
            <span class="card-metric-value">${site.size_sqft} sqft</span>
          </div>
          <div class="card-metric-item">
            <span class="card-metric-label">Traffic Score</span>
            <span class="card-metric-value">⭐ ${site.traffic_score}/10</span>
          </div>
        </div>

        <div class="card-bottom-row">
          <span class="free-date">Vacant From: <strong>${formatDateString(site.free_from)}</strong></span>
          <span class="revenue-at-risk">Risk: ${formatCurrency(site.revenue_at_risk || site.monthly_rate_inr)}</span>
        </div>
      `;

      card.addEventListener('click', () => selectSite(site.site_id));
      elements.vacancyList.appendChild(card);
    });
  }

  function selectSite(siteId) {
    state.selectedSiteId = siteId;
    state.selectedSite = state.vacancies.find(s => s.site_id === siteId);

    // Update vacancy list card highlight
    document.querySelectorAll('.vacancy-card').forEach(card => {
      if (card.dataset.siteId === siteId) {
        card.classList.add('selected');
      } else {
        card.classList.remove('selected');
      }
    });

    // Update timeline highlight
    document.querySelectorAll('.timeline-item').forEach(item => {
      if (item.dataset.siteId === siteId) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });

    if (!state.selectedSite) return;

    // Show Detail Panel
    elements.emptyDetailState.classList.add('hidden');
    elements.activeDetailContent.classList.remove('hidden');

    // Populate Selected Site Header
    elements.selectedSiteId.textContent = state.selectedSite.site_id;
    elements.selectedSiteLocation.textContent = state.selectedSite.location;
    elements.selectedSiteRate.textContent = formatCurrency(state.selectedSite.monthly_rate_inr);
    elements.selectedSiteSize.textContent = `${state.selectedSite.size_sqft} sqft`;
    elements.selectedSiteTraffic.textContent = `${state.selectedSite.traffic_score} / 10`;
    elements.selectedSiteFreeFrom.textContent = formatDateString(state.selectedSite.free_from);
    elements.selectedSiteRevenueRisk.textContent = formatCurrency(state.selectedSite.revenue_at_risk || state.selectedSite.monthly_rate_inr);

    // Fetch Top-3 Leads for this site
    fetchLeads(siteId);
  }

  function renderLeadsList() {
    elements.leadsContainer.innerHTML = '';

    if (!state.leads || state.leads.length === 0) {
      elements.leadsContainer.innerHTML = `
        <div style="color:var(--text-muted);padding:1.5rem;text-align:center;">
          No matching leads available for this billboard.
        </div>
      `;
      return;
    }

    state.leads.slice(0, 3).forEach((lead, index) => {
      const card = document.createElement('div');
      card.className = 'lead-card';

      const reasonsHtml = (lead.reasons || [])
        .map(reason => `<li><span class="reason-check">&#10003;</span> ${reason}</li>`)
        .join('');

      card.innerHTML = `
        <div class="lead-header">
          <div class="lead-rank-badge">#${index + 1}</div>
          <div class="lead-info">
            <h4 class="lead-name">${lead.name}</h4>
            <div class="lead-tags">
              <span class="tag-industry">${formatIndustryName(lead.industry)}</span>
              <span class="tag-budget ${(lead.budget_band || 'mid').toLowerCase()}">
                Budget: ${lead.budget_band || 'Mid'}
              </span>
            </div>
          </div>
          <div class="lead-score-box">
            <span class="score-number">${lead.score}%</span>
            <span class="score-label">Fit Score</span>
          </div>
        </div>

        <div class="reasons-container">
          <div class="reasons-title">Why this client is a top fit:</div>
          <ul class="reasons-list">
            ${reasonsHtml}
          </ul>
        </div>

        <div class="lead-action-row">
          <button type="button" class="btn-generate-pitch" data-customer-id="${lead.customer_id}">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"></path></svg>
            Generate AI Pitch
          </button>
        </div>
      `;

      // Event listener for pitch button
      card.querySelector('.btn-generate-pitch').addEventListener('click', (e) => {
        const custId = e.currentTarget.dataset.customerId;
        requestPitch(state.selectedSiteId, custId);
      });

      elements.leadsContainer.appendChild(card);
    });
  }

  function renderPitchModal(lead, pitchData) {
    state.currentPitch = pitchData;

    elements.pitchModalTitle.textContent = `AI Pitch Draft: ${lead.name}`;
    elements.pitchModalSubtitle.textContent = `Site: ${state.selectedSite ? state.selectedSite.location : ''} (${state.selectedSiteId})`;
    elements.pitchSuggestedRate.textContent = formatCurrency(pitchData.suggested_rate);

    // Value propositions list
    elements.pitchReasonsList.innerHTML = (pitchData.reasons || [])
      .map(r => `<li>${r}</li>`)
      .join('');

    // Pitch email textarea
    elements.pitchTextArea.value = pitchData.pitch || '';
  }

  // Attach Event Listeners
  function attachEventListeners() {
    // Search Input
    elements.searchInput.addEventListener('input', (e) => {
      state.searchQuery = e.target.value.trim();
      elements.clearSearchBtn.classList.toggle('hidden', state.searchQuery === '');
      applyFilters();
    });

    elements.clearSearchBtn.addEventListener('click', () => {
      elements.searchInput.value = '';
      state.searchQuery = '';
      elements.clearSearchBtn.classList.add('hidden');
      applyFilters();
    });

    // Budget Band Filter Chips
    elements.budgetBandFilters.addEventListener('click', (e) => {
      if (e.target.classList.contains('chip')) {
        elements.budgetBandFilters.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
        e.target.classList.add('active');
        state.rateBandFilter = e.target.dataset.filter;
        applyFilters();
      }
    });

    // Urgency Filter Chips
    elements.urgencyFilters.addEventListener('click', (e) => {
      if (e.target.classList.contains('chip')) {
        elements.urgencyFilters.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
        e.target.classList.add('active');
        state.urgencyFilter = e.target.dataset.urgency;
        applyFilters();
      }
    });

    // Toggle Backend / Demo Mode Button
    elements.toggleDemoBtn.addEventListener('click', () => {
      state.isDemoMode = !state.isDemoMode;
      fetchVacancies();
    });

    // Close Modal
    elements.closePitchModalBtn.addEventListener('click', () => {
      elements.pitchModal.classList.add('hidden');
    });

    elements.cancelPitchBtn.addEventListener('click', () => {
      elements.pitchModal.classList.add('hidden');
    });

    // Copy Pitch to Clipboard
    elements.copyPitchBtn.addEventListener('click', () => {
      const textToCopy = elements.pitchTextArea.value;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(textToCopy)
          .then(() => showToast('Copied pitch draft to clipboard!'))
          .catch(() => fallbackCopyTextToClipboard(textToCopy));
      } else {
        fallbackCopyTextToClipboard(textToCopy);
      }
    });
  }

  function fallbackCopyTextToClipboard(text) {
    elements.pitchTextArea.select();
    document.execCommand('copy');
    showToast('Copied pitch draft to clipboard!');
  }

  // Initialization
  function init() {
    attachEventListeners();
    fetchVacancies();
  }

  // Run on DOM Ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
