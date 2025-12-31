// Configuration
const BASE_API_URL = 'https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?pageno=1&strCat=Company+Update&strPrevDate=20251231&strScrip=&strSearch=P&strToDate=20251231&strType=C&subcategory=Award+of+Order+%2F+Receipt+of+Order';
// Use local proxy server if available (recommended for 403 errors)
const LOCAL_PROXY_URL = '/api/announcements';
// Try multiple CORS proxy options as fallback
const CORS_PROXIES = [
    'https://api.allorigins.win/raw?url=',
    'https://corsproxy.io/?',
];
const POLL_INTERVAL = 2000; // 2 seconds

// State
let isMonitoring = false;
let pollInterval = null;
let seenAnnouncementIds = new Set();
let allAnnouncements = [];
let soundEnabled = true;
let stockPriceCache = new Map(); // Cache for stock prices

// DOM Elements
const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');
const statusDot = document.querySelector('.status-dot');
const lastUpdate = document.getElementById('lastUpdate');
const toggleBtn = document.getElementById('toggleBtn');
const clearBtn = document.getElementById('clearBtn');
const testSoundBtn = document.getElementById('testSoundBtn');
const soundToggle = document.getElementById('soundToggle');
const filterAmountToggle = document.getElementById('filterAmountToggle');
const kiteConfigBtn = document.getElementById('kiteConfigBtn');
const kiteLoginBtn = document.getElementById('kiteLoginBtn');
const announcementsList = document.getElementById('announcementsList');
const totalCount = document.getElementById('totalCount');
const newCount = document.getElementById('newCount');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    toggleBtn.addEventListener('click', toggleMonitoring);
    clearBtn.addEventListener('click', clearAll);
    testSoundBtn.addEventListener('click', () => {
        playNotificationSound();
    });
    soundToggle.addEventListener('change', (e) => {
        soundEnabled = e.target.checked;
    });
    filterAmountToggle.addEventListener('change', (e) => {
        filterAnnouncements(e.target.checked);
    });
    
    // Kite API handlers
    if (kiteConfigBtn) {
        kiteConfigBtn.addEventListener('click', showKiteConfig);
    }
    if (kiteLoginBtn) {
        kiteLoginBtn.addEventListener('click', kiteLogin);
    }
    
    // Listen for authentication success message from popup
    window.addEventListener('message', (event) => {
        if (event.data && event.data.type === 'kite_auth_success') {
            // Wait a moment for server to save token, then check status
            setTimeout(() => {
                checkKiteStatus();
            }, 1000);
            // Also check again after a longer delay to ensure it's updated
            setTimeout(() => {
                checkKiteStatus();
            }, 2000);
        }
    });
    
    // Modal handlers
    const modal = document.getElementById('kiteModal');
    const closeBtn = document.querySelector('.modal-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }
    if (document.getElementById('saveKiteConfig')) {
        document.getElementById('saveKiteConfig').addEventListener('click', saveKiteConfig);
    }
    
    // Check Kite status on load
    checkKiteStatus();
    
    updateStatus('paused', 'Ready to start');
});

// Filter announcements by amount
function filterAnnouncements(showOnlyWithAmounts) {
    const cards = announcementsList.querySelectorAll('.announcement-card');
    cards.forEach(card => {
        if (showOnlyWithAmounts) {
            card.style.display = card.classList.contains('has-amount') ? 'block' : 'none';
        } else {
            card.style.display = 'block';
        }
    });
}

// Toggle monitoring
function toggleMonitoring() {
    if (isMonitoring) {
        stopMonitoring();
    } else {
        startMonitoring();
    }
}

// Start monitoring
function startMonitoring() {
    isMonitoring = true;
    toggleBtn.textContent = 'Stop Monitoring';
    toggleBtn.classList.remove('btn-primary');
    toggleBtn.classList.add('btn-secondary');
    updateStatus('active', 'Monitoring...');
    
    // Fetch immediately
    fetchAnnouncements();
    
    // Then poll every 2 seconds
    pollInterval = setInterval(fetchAnnouncements, POLL_INTERVAL);
}

// Stop monitoring
function stopMonitoring() {
    isMonitoring = false;
    toggleBtn.textContent = 'Start Monitoring';
    toggleBtn.classList.remove('btn-secondary');
    toggleBtn.classList.add('btn-primary');
    updateStatus('paused', 'Paused');
    
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

// Fetch announcements from API
async function fetchAnnouncements() {
    let lastError = null;
    
    // Try local proxy server first (best for 403 errors)
    try {
        const response = await fetch(LOCAL_PROXY_URL, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
            }
        });

        if (response.ok) {
            const data = await response.json();
            processApiResponse(data);
            return;
        } else {
            lastError = new Error(`Proxy HTTP ${response.status}: ${response.statusText}`);
        }
    } catch (proxyError) {
        lastError = proxyError;
        console.log('Local proxy not available, trying direct fetch...');
    }
    
    // Try direct fetch with all headers
    try {
        const response = await fetch(BASE_API_URL, {
            method: 'GET',
            mode: 'cors',
            credentials: 'omit',
            headers: {
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://www.bseindia.com/',
                'Origin': 'https://www.bseindia.com',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'DNT': '1',
            }
        });

        if (response.ok) {
            const data = await response.json();
            processApiResponse(data);
            return;
        } else {
            lastError = new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
    } catch (corsError) {
        lastError = corsError;
        console.log('Direct fetch failed, trying CORS proxies...');
    }

    // Try CORS proxies
    for (const proxy of CORS_PROXIES) {
        try {
            const proxyUrl = proxy === 'https://api.allorigins.win/raw?url=' 
                ? proxy + encodeURIComponent(BASE_API_URL)
                : proxy + BASE_API_URL;
            
            const response = await fetch(proxyUrl, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json, text/plain, */*',
                }
            });

            if (response.ok) {
                let data;
                // allorigins returns wrapped response
                if (proxy.includes('allorigins')) {
                    const text = await response.text();
                    try {
                        data = JSON.parse(text);
                    } catch {
                        data = JSON.parse(text);
                    }
                } else {
                    data = await response.json();
                }
                
                processApiResponse(data);
                return;
            } else {
                lastError = new Error(`Proxy HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (proxyError) {
            lastError = proxyError;
            console.log(`Proxy ${proxy} failed, trying next...`);
        }
    }

    // All methods failed
    handleFetchError(lastError);
}

// Process API response
function processApiResponse(data) {
    let announcements = [];
    
    if (data && Array.isArray(data.Table)) {
        announcements = data.Table;
    } else if (data && data.Table) {
        announcements = Array.isArray(data.Table) ? data.Table : [data.Table];
    } else {
        console.warn('Unexpected API response format:', data);
        updateStatus('active', 'Monitoring... (No data)');
        return;
    }
    
    // Process for new announcements
    processAnnouncements(announcements);
    
    // On first load, render all announcements
    if (allAnnouncements.length === 0 && announcements.length > 0) {
        announcements.forEach(announcement => {
            const id = createAnnouncementId(announcement);
            seenAnnouncementIds.add(id);
            allAnnouncements.push({ ...announcement, id, isNew: false });
            renderAnnouncement({ ...announcement, id }, false);
        });
        updateStats();
    }
    
    updateStatus('active', 'Monitoring...');
    updateLastUpdate();
}

// Handle fetch errors
function handleFetchError(error) {
    console.error('Error fetching announcements:', error);
    let errorMsg = `Error: ${error.message}`;
    
    if (error.message.includes('403')) {
        errorMsg = '403 Forbidden: API is blocking requests. The BSE API may require authentication or be blocking automated requests.';
    } else if (error.message.includes('Failed to fetch') || error.message.includes('CORS')) {
        errorMsg = 'CORS Error: API blocked by browser. Try using a CORS browser extension.';
    }
    
    updateStatus('paused', errorMsg);
    
    // Show user-friendly error in UI
    const existingError = announcementsList.querySelector('.error-state');
    if (!existingError) {
        const emptyState = announcementsList.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
        announcementsList.innerHTML = `
            <div class="empty-state error-state" style="color: #dc2626;">
                <strong>⚠️ Connection Error</strong><br>
                ${errorMsg}<br><br>
                <small>Possible solutions:<br>
                • Install a CORS browser extension<br>
                • The API might be blocking automated requests<br>
                • Try accessing the API directly in browser first</small>
            </div>
        `;
    }
}

// Process announcements and detect new ones
function processAnnouncements(announcements) {
    const newAnnouncements = [];
    
    announcements.forEach(announcement => {
        // Create a unique ID from announcement data
        const id = createAnnouncementId(announcement);
        
        if (!seenAnnouncementIds.has(id)) {
            seenAnnouncementIds.add(id);
            newAnnouncements.push({ ...announcement, id, isNew: true });
        }
    });
    
    // Add new announcements to the beginning of the list
    if (newAnnouncements.length > 0) {
        allAnnouncements = [...newAnnouncements, ...allAnnouncements];
        
        // Play sound for new announcements
        if (soundEnabled) {
            playNotificationSound();
        }
        
        // Render new announcements
        newAnnouncements.forEach(announcement => {
            renderAnnouncement(announcement, true);
        });
        
        updateStats();
    }
}

// Fetch stock price for a scrip code
async function fetchStockPrice(scripCode, symbol = null) {
    if (!scripCode) return null;
    
    // Check cache first (cache for 30 seconds)
    const cacheKey = `${scripCode}_${symbol || ''}`;
    const cached = stockPriceCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < 30000) {
        return cached.data;
    }
    
    try {
        let url = `/api/stock-price?scrip=${scripCode}`;
        if (symbol) {
            url += `&symbol=${encodeURIComponent(symbol)}`;
        }
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            // Cache the result
            stockPriceCache.set(cacheKey, {
                data: data,
                timestamp: Date.now()
            });
            return data;
        } else {
            console.log(`Price API returned ${response.status} for scrip ${scripCode}`);
        }
    } catch (error) {
        console.error(`Error fetching price for scrip ${scripCode}:`, error);
    }
    
    return null;
}

// Extract current price from API response
function extractPrice(priceData) {
    if (!priceData) return null;
    
    try {
        // New format: direct price field
        if (priceData.price !== undefined && priceData.price !== null) {
            return parseFloat(priceData.price);
        }
        // Old BSE API formats
        if (priceData.CurrentPrice) {
            return parseFloat(priceData.CurrentPrice);
        }
        if (priceData.LTP) {
            return parseFloat(priceData.LTP);
        }
        if (priceData.LastPrice) {
            return parseFloat(priceData.LastPrice);
        }
        if (priceData.CurrRate) {
            return parseFloat(priceData.CurrRate);
        }
        if (priceData.WAP) {
            return parseFloat(priceData.WAP);
        }
        // Try if it's an array with price data
        if (Array.isArray(priceData) && priceData.length > 0) {
            const first = priceData[0];
            return extractPrice(first);
        }
    } catch (e) {
        console.error('Error extracting price:', e);
    }
    
    return null;
}

// Extract stock symbol from NSURL
// Example: https://www.bseindia.com/stock-share-price/waaree-renewable-technologies-ltd/waareertl/534618/
// Returns: waareertl
function extractSymbol(announcement) {
    if (!announcement.NSURL) return null;
    
    try {
        const url = announcement.NSURL;
        // Extract the symbol from URL path: /company-name/symbol/scrip-code/
        const match = url.match(/\/stock-share-price\/[^\/]+\/([^\/]+)\/\d+\/?$/);
        if (match && match[1]) {
            return match[1].toUpperCase();
        }
    } catch (e) {
        console.error('Error extracting symbol:', e);
    }
    
    return null;
}

// Extract rupee amount from text
function extractRupeeAmount(announcement) {
    // Check both HEADLINE and MORE fields
    const text = `${announcement.HEADLINE || ''} ${announcement.MORE || ''}`.toLowerCase();
    
    // Patterns to match rupee amounts:
    // Rs. 28.75 Crore, INR 170.25 Crores, ₹ 1,746 Crores, Rs 15.67 crores, etc.
    const patterns = [
        /(?:rs\.?|inr|₹)\s*([\d,]+\.?\d*)\s*(?:crore|crores|cr|lakh|lakhs|lac|thousand|thousands|million|millions|billion|billions)/gi,
        /([\d,]+\.?\d*)\s*(?:crore|crores|cr|lakh|lakhs|lac)\s*(?:rupee|rupees|rs\.?|inr|₹)/gi,
        /(?:order|value|worth|amount|of)\s*(?:rs\.?|inr|₹)\s*([\d,]+\.?\d*)\s*(?:crore|crores|cr)/gi,
    ];
    
    for (const pattern of patterns) {
        const matches = text.match(pattern);
        if (matches && matches.length > 0) {
            // Return the first match, cleaned up
            return matches[0].trim();
        }
    }
    
    return null;
}

// Create unique ID for announcement
function createAnnouncementId(announcement) {
    // Use a combination of fields to create unique ID
    const key = `${announcement.SCRIP_CD || ''}_${announcement.NEWSID || ''}_${announcement.DT_TM || ''}_${announcement.NEWS_SUB || ''}`;
    return btoa(key).replace(/[^a-zA-Z0-9]/g, '');
}

// Render announcement card
function renderAnnouncement(announcement, isNew = false) {
    const card = document.createElement('div');
    card.className = `announcement-card ${isNew ? 'new' : ''}`;
    card.dataset.id = announcement.id;
    
    const title = announcement.NEWS_SUB || announcement.SLONGNAME || 'No Title';
    const date = formatDate(announcement.DT_TM);
    const company = announcement.SLONGNAME || announcement.SCRIP_CD || 'N/A';
    const scripCode = announcement.SCRIP_CD || 'N/A';
    const headline = announcement.HEADLINE || '';
    const more = announcement.MORE || '';
    
    // Extract symbol and rupee amount
    const symbol = extractSymbol(announcement);
    const rupeeAmount = extractRupeeAmount(announcement);
    const hasAmount = rupeeAmount !== null;
    
    // Add highlight class if amount found
    if (hasAmount) {
        card.classList.add('has-amount');
    }
    
    card.innerHTML = `
        <div class="announcement-header">
            <div class="announcement-title">
                ${escapeHtml(title)}
                ${isNew ? '<span class="new-badge">NEW</span>' : ''}
                ${hasAmount ? '<span class="amount-badge">💰 Amount</span>' : ''}
            </div>
            <div class="announcement-date">${date}</div>
        </div>
        ${symbol ? `
        <div class="symbol-badge">
            <span class="symbol-label">Symbol:</span>
            <span class="symbol-value">${escapeHtml(symbol)}</span>
            <span class="price-loading" id="price-${scripCode}" style="margin-left: auto; font-size: 0.9em; opacity: 0.7;">Loading price...</span>
        </div>
        <div class="units-calculation" id="units-${scripCode}" style="display: none;"></div>
        ` : ''}
        ${hasAmount ? `
        <div class="amount-highlight">
            <div class="amount-label">Order Value:</div>
            <div class="amount-value">${escapeHtml(rupeeAmount)}</div>
        </div>
        ` : ''}
        ${headline ? `
        <div class="headline-section">
            <div class="headline-text">${escapeHtml(headline)}</div>
        </div>
        ` : ''}
        <div class="announcement-details">
            <div class="detail-item">
                <div class="detail-label">Company</div>
                <div class="detail-value">${escapeHtml(company)}</div>
            </div>
            ${symbol ? `
            <div class="detail-item">
                <div class="detail-label">Symbol</div>
                <div class="detail-value symbol-highlight">${escapeHtml(symbol)}</div>
            </div>
            ` : ''}
            <div class="detail-item">
                <div class="detail-label">Scrip Code</div>
                <div class="detail-value">${escapeHtml(scripCode)}</div>
            </div>
            ${announcement.CATEGORYNAME ? `
            <div class="detail-item">
                <div class="detail-label">Category</div>
                <div class="detail-value">${escapeHtml(announcement.CATEGORYNAME)}</div>
            </div>
            ` : ''}
        </div>
        ${symbol ? `
        <div class="order-actions">
            <button class="btn-buy" onclick="placeKiteOrder('${escapeHtml(symbol)}', ${scripCode}, '${scripCode}')">
                🛒 Buy with ₹3000
            </button>
        </div>
        ` : ''}
    `;
    
    // Insert at the beginning of the list
    const emptyState = announcementsList.querySelector('.empty-state');
    if (emptyState) {
        emptyState.remove();
    }
    
    announcementsList.insertBefore(card, announcementsList.firstChild);
    
    // Fetch and display stock price
    if (scripCode && scripCode !== 'N/A') {
        fetchStockPrice(scripCode, symbol).then(priceData => {
            const priceElement = card.querySelector(`#price-${scripCode}`);
            const unitsElement = card.querySelector(`#units-${scripCode}`);
            
            if (priceElement) {
                const price = extractPrice(priceData);
                if (price !== null && !isNaN(price) && price > 0) {
                    priceElement.innerHTML = `<span class="price-value">₹${price.toFixed(2)}</span>`;
                    priceElement.className = 'price-display';
                    
                    // Calculate units that can be purchased with ₹3000
                    const investmentAmount = 3000;
                    const units = Math.floor(investmentAmount / price);
                    const remainingAmount = investmentAmount - (units * price);
                    
                    if (unitsElement) {
                        if (units > 0) {
                            unitsElement.innerHTML = `
                                <div class="units-info">
                                    <span class="units-label">With ₹${investmentAmount}:</span>
                                    <span class="units-value">${units} share${units !== 1 ? 's' : ''}</span>
                                    ${remainingAmount > 0 ? `<span class="units-remaining">(₹${remainingAmount.toFixed(2)} remaining)</span>` : ''}
                                </div>
                            `;
                            unitsElement.style.display = 'block';
                        } else {
                            unitsElement.innerHTML = `<span style="color: #999; font-size: 0.85em;">Price too high for ₹${investmentAmount} investment</span>`;
                            unitsElement.style.display = 'block';
                        }
                    }
                } else {
                    priceElement.innerHTML = '<span style="color: #999;">Price unavailable</span>';
                    priceElement.className = 'price-display';
                    if (unitsElement) {
                        unitsElement.style.display = 'none';
                    }
                }
            }
        }).catch(err => {
            console.error('Price fetch error:', err);
            const priceElement = card.querySelector(`#price-${scripCode}`);
            const unitsElement = card.querySelector(`#units-${scripCode}`);
            if (priceElement) {
                priceElement.innerHTML = '<span style="color: #999;">Price unavailable</span>';
                priceElement.className = 'price-display';
            }
            if (unitsElement) {
                unitsElement.style.display = 'none';
            }
        });
    }
    
    // Remove 'new' class after animation
    if (isNew) {
        setTimeout(() => {
            card.classList.remove('new');
        }, 3000);
    }
}

// Format date
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleString('en-IN', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return dateString;
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Play notification sound
// Creates a loud, attention-grabbing 6-beep notification pattern:
// - Six distinct beeps with ascending then descending pitch pattern
// - Frequencies: 1000, 1200, 1400, 1400, 1200, 1000 Hz
// - Each beep is 0.15 seconds long with 0.08 second gaps
// - High volume (0.85) for maximum audibility
// - Total duration: ~1.4 seconds
// This creates a very prominent alert sound that can be heard from anywhere
function playNotificationSound() {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const now = audioContext.currentTime;
        
        // Helper function to create a beep
        const createBeep = (frequency, startTime, duration = 0.15) => {
            const osc = audioContext.createOscillator();
            const gain = audioContext.createGain();
            osc.type = 'sine';
            osc.frequency.value = frequency;
            osc.connect(gain);
            gain.connect(audioContext.destination);
            gain.gain.setValueAtTime(0, startTime);
            gain.gain.setValueAtTime(0.85, startTime + 0.02);
            gain.gain.setValueAtTime(0.85, startTime + duration - 0.02);
            gain.gain.exponentialRampToValueAtTime(0.01, startTime + duration);
            osc.start(startTime);
            osc.stop(startTime + duration);
        };
        
        // Pattern: Up-Down-Up-Down for maximum attention
        // Beep 1: 1000 Hz
        createBeep(1000, now);
        
        // Beep 2: 1200 Hz
        createBeep(1200, now + 0.23);
        
        // Beep 3: 1400 Hz (peak)
        createBeep(1400, now + 0.46);
        
        // Beep 4: 1400 Hz (sustain peak)
        createBeep(1400, now + 0.69);
        
        // Beep 5: 1200 Hz
        createBeep(1200, now + 0.92);
        
        // Beep 6: 1000 Hz
        createBeep(1000, now + 1.15);
        
    } catch (error) {
        console.error('Error playing sound:', error);
    }
}

// Update status
function updateStatus(state, text) {
    statusText.textContent = text;
    statusDot.className = 'status-dot';
    
    if (state === 'active') {
        statusDot.classList.add('active');
    } else if (state === 'paused') {
        statusDot.classList.add('paused');
    }
}

// Update last update time
function updateLastUpdate() {
    const now = new Date();
    lastUpdate.textContent = `Last updated: ${now.toLocaleTimeString()}`;
}

// Update statistics
function updateStats() {
    totalCount.textContent = allAnnouncements.length;
    
    // Count announcements from today
    const today = new Date().toDateString();
    const todayCount = allAnnouncements.filter(ann => {
        if (!ann.DT_TM) return false;
        try {
            return new Date(ann.DT_TM).toDateString() === today;
        } catch {
            return false;
        }
    }).length;
    
    newCount.textContent = todayCount;
}

// Clear all announcements
function clearAll() {
    if (confirm('Are you sure you want to clear all announcements?')) {
        allAnnouncements = [];
        seenAnnouncementIds.clear();
        announcementsList.innerHTML = '<div class="empty-state">No announcements yet. Click "Start Monitoring" to begin.</div>';
        updateStats();
    }
}

// Kite API Functions
let kiteAuthenticated = false;

async function checkKiteStatus() {
    try {
        const response = await fetch('/api/kite/status');
        const data = await response.json();
        kiteAuthenticated = data.authenticated;
        
        // Hide config button if environment variables are set (production)
        if (kiteConfigBtn && data.has_env_vars) {
            kiteConfigBtn.style.display = 'none';
            // Show info that config is from environment variables
            const envInfo = document.createElement('span');
            envInfo.className = 'env-info';
            envInfo.textContent = '⚙️ Kite: Using Env Vars';
            envInfo.style.cssText = 'font-size: 0.85em; color: #10b981; margin-left: 10px;';
            if (!document.querySelector('.env-info')) {
                kiteConfigBtn.parentElement.insertBefore(envInfo, kiteConfigBtn.nextSibling);
            }
        }
        
        if (kiteLoginBtn) {
            if (data.configured && !data.authenticated) {
                kiteLoginBtn.style.display = 'inline-block';
                kiteLoginBtn.textContent = '🔐 Login to Kite';
                kiteLoginBtn.style.background = ''; // Reset background
            } else if (data.authenticated) {
                kiteLoginBtn.style.display = 'inline-block';
                kiteLoginBtn.textContent = '✅ Kite Connected';
                kiteLoginBtn.style.background = '#10b981';
            } else if (!data.configured) {
                kiteLoginBtn.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error checking Kite status:', error);
    }
}

function showKiteConfig() {
    const modal = document.getElementById('kiteModal');
    if (modal) {
        // Load existing config if available
        fetch('/api/kite/status').then(r => r.json()).then(data => {
            // Config is stored server-side, but we can show placeholders
        }).catch(() => {});
        modal.style.display = 'block';
    }
}

async function saveKiteConfig() {
    const apiKey = document.getElementById('kiteApiKey').value;
    const apiSecret = document.getElementById('kiteApiSecret').value;
    const redirectUrl = document.getElementById('kiteRedirectUrl').value;
    const postbackUrl = document.getElementById('kitePostbackUrl').value;
    
    if (!apiKey || !apiSecret) {
        alert('Please enter both API Key and API Secret');
        return;
    }
    
    if (!redirectUrl || !postbackUrl) {
        alert('Please ensure both Redirect URL and Postback URL are set');
        return;
    }
    
    // Validate HTTPS URLs
    if (!redirectUrl.startsWith('https://')) {
        alert('❌ Redirect URL must start with https://\n\nFor local development, use ngrok:\n1. Run: ngrok http 8000\n2. Copy the HTTPS URL\n3. Use: https://your-url.ngrok.io/kite/callback');
        return;
    }
    
    if (!postbackUrl.startsWith('https://')) {
        alert('❌ Postback URL must start with https://\n\nFor local development, use ngrok:\n1. Run: ngrok http 8000\n2. Copy the HTTPS URL\n3. Use: https://your-url.ngrok.io/kite/postback');
        return;
    }
    
    try {
        const response = await fetch('/api/kite/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                api_key: apiKey,
                api_secret: apiSecret,
                redirect_url: redirectUrl,
                postback_url: postbackUrl
            })
        });
        
        const data = await response.json();
        if (data.success) {
            alert('Configuration saved!\n\nIMPORTANT: Make sure you have added these URLs in your Kite app settings:\n• Redirect URL: ' + redirectUrl + '\n• Postback URL: ' + postbackUrl + '\n\nThen click "Login to Kite" to authenticate.');
            document.getElementById('kiteModal').style.display = 'none';
            checkKiteStatus();
        } else {
            if (data.has_env_vars) {
                alert('⚠️ Configuration is managed via Render environment variables.\n\nTo update:\n1. Go to Render Dashboard → Your Service → Environment\n2. Update KITE_API_KEY, KITE_API_SECRET, etc.\n3. Render will auto-redeploy\n\nThis form is only for local development.');
            } else {
                alert('Error: ' + (data.error || 'Failed to save configuration'));
            }
        }
    } catch (error) {
        alert('Error saving configuration: ' + error.message);
    }
}

async function kiteLogin() {
    try {
        const response = await fetch('/api/kite/login');
        const data = await response.json();
        
        if (data.login_url) {
            window.open(data.login_url, '_blank', 'width=600,height=700');
            // Check status after a delay
            setTimeout(checkKiteStatus, 5000);
        } else {
            alert('Error: ' + (data.error || 'Failed to get login URL'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function placeKiteOrder(symbol, scripCode, cardId) {
    // Check if authenticated
    if (!kiteAuthenticated) {
        const shouldLogin = confirm('You need to login to Kite first. Would you like to login now?');
        if (shouldLogin) {
            kiteLogin();
        }
        return;
    }
    
    // Get the units from the calculation
    const unitsElement = document.querySelector(`#units-${scripCode}`);
    let quantity = 1;
    
    if (unitsElement) {
        const unitsText = unitsElement.textContent;
        const match = unitsText.match(/(\d+)\s+share/);
        if (match) {
            quantity = parseInt(match[1]);
        }
    }
    
    // Confirm order
    const confirmMsg = `Place order to buy ${quantity} share(s) of ${symbol}?\n\nThis will execute a MARKET BUY order via Kite.`;
    if (!confirm(confirmMsg)) {
        return;
    }
    
    try {
        // Note: Kite uses NSE symbols, you may need to map BSE symbols to NSE
        // For now, using the symbol as-is (you'll need to adjust based on your mapping)
        const response = await fetch('/api/kite/order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                symbol: symbol,
                exchange: 'NSE', // Kite primarily uses NSE
                quantity: quantity,
                transaction_type: 'BUY',
                order_type: 'MARKET',
                product: 'CNC' // CNC for delivery
            })
        });
        
        const data = await response.json();
        if (data.success) {
            alert(`✅ Order placed successfully!\nOrder ID: ${data.order_id}\n${data.message}`);
        } else {
            alert('❌ Order failed: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        alert('❌ Error placing order: ' + error.message);
    }
}

