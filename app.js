// Main application logic
(function () {
    'use strict';

    const ITEMS_PER_PAGE = 9;
    let currentPage = 1;
    let allRoutes = [];
    let filteredRoutes = [];
    let athleteData = null;
    let ENCRYPTION_KEY = 'Run2026';

    // Initialize the app when DOM is ready
    document.addEventListener('DOMContentLoaded', initApp);

    async function initApp() {
        try {
            // Load Data
            const [dataRes, athleteRes, legalRes] = await Promise.all([
                fetch('data.json'),
                fetch('athlete.json'),
                fetch('legal.json')
            ]);

            if (dataRes.ok) {
                const data = await dataRes.json();
                if (data.routes && Array.isArray(data.routes)) {
                    allRoutes = [...data.routes];
                }
                if (data.encryptionKey) {
                    ENCRYPTION_KEY = data.encryptionKey;
                }
                updateLastUpdateTime(data.lastUpdated);
            } else {
                console.error("Failed to load data.json");
            }

            if (athleteRes.ok) {
                athleteData = await athleteRes.json();

                // Set Avatar Logo
                const avatarEl = document.getElementById('athlete-avatar');
                if (avatarEl && athleteData && athleteData.profile) {
                    avatarEl.src = athleteData.profile;
                    avatarEl.alt = athleteData.name || 'Athlete Profile';
                    avatarEl.style.display = 'block';

                    // Set Favicon
                    let favicon = document.querySelector('link[rel="icon"]');
                    if (!favicon) {
                        favicon = document.createElement('link');
                        favicon.rel = 'icon';
                        document.head.appendChild(favicon);
                    }
                    favicon.href = athleteData.profile;
                }
            }

            if (legalRes.ok) {
                const legalData = await legalRes.json();
                const tosContent = document.getElementById('tosContent');
                const aboutContent = document.getElementById('aboutContent');
                if (tosContent && legalData.tos) tosContent.innerHTML = legalData.tos;
                if (aboutContent && legalData.about) aboutContent.innerHTML = legalData.about;
            }

            // Initial Render
            applyFilters();
            renderAttribution();
            initTooltipSystem();

        } catch (e) {
            console.error("Error initializing app:", e);
            document.getElementById('routes-grid').innerHTML = '<div class="loading">Error loading routes. Please check console.</div>';
        }

        // Listeners for Filters
        document.getElementById('filterDistance')?.addEventListener('change', () => { currentPage = 1; applyFilters(); });
        document.getElementById('filterElevation')?.addEventListener('change', () => { currentPage = 1; applyFilters(); });
        document.getElementById('filterEffort')?.addEventListener('change', () => { currentPage = 1; applyFilters(); });
        document.getElementById('sortBy')?.addEventListener('change', () => { currentPage = 1; applyFilters(); });
        document.getElementById('filterType')?.addEventListener('change', () => { currentPage = 1; applyFilters(); });
        document.getElementById('filterRecency')?.addEventListener('change', () => { currentPage = 1; applyFilters(); });
        document.getElementById('searchQuery')?.addEventListener('input', () => { currentPage = 1; applyFilters(); });

        // Toggle Filters Logic
        const toggleBtn = document.getElementById('toggleFilters');
        const wrapper = document.getElementById('filtersWrapper');
        if (toggleBtn && wrapper) {
            // Start collapsed if on mobile or by preference (optional)
            // For now, let's start expanded but allow toggle
            toggleBtn.addEventListener('click', () => {
                const isCollapsed = wrapper.classList.toggle('collapsed');
                toggleBtn.classList.toggle('active', !isCollapsed);
                const textSpan = toggleBtn.querySelector('.text');
                if (textSpan) {
                    textSpan.textContent = isCollapsed ? 'Show Filters' : 'Hide Filters';
                }
            });
        }
    }

    function renderAttribution() {
        if (athleteData && athleteData.id) {
            const footerDiv = document.querySelector('footer .container');
            if (footerDiv) {
                // Check if already exists to avoid dupes on re-run (though init only runs once)
                const existing = footerDiv.querySelector('.attribution'); // Add class if needed, or just append
                if (!existing) {
                    const p = document.createElement('p');
                    p.className = 'attribution';
                    p.innerHTML = `Activities by <a href="https://www.strava.com/athletes/${athleteData.id}" target="_blank" class="has-tooltip" data-tooltip="View Strava Profile">${athleteData.name}</a>`;
                    footerDiv.appendChild(p);
                }
            }
        }
    }

    function applyFilters() {
        if (!allRoutes.length) {
            renderRoutesPage(1);
            return;
        }

        const distVal = document.getElementById('filterDistance')?.value || 'all';
        const elevVal = document.getElementById('filterElevation')?.value || 'all';
        const effortVal = document.getElementById('filterEffort')?.value || 'all';
        const sortVal = document.getElementById('sortBy')?.value || 'date-desc';
        const typeVal = document.getElementById('filterType')?.value || 'all';
        const recencyVal = document.getElementById('filterRecency')?.value || 'all';
        const searchQuery = document.getElementById('searchQuery')?.value.toLowerCase() || '';

        // Filter
        filteredRoutes = allRoutes.filter(r => {
            // Search (Name, Location, Tags, or POIs)
            const tagsText = (r.tags || []).join(' ');
            const poiText = (r.pois || []).map(p => p.name).join(' ');
            const searchableText = `${r.name} ${r.location || ''} ${tagsText} ${poiText}`.toLowerCase();
            if (searchQuery && !searchableText.includes(searchQuery)) return false;

            // Type (Race/Training/Route)
            if (typeVal !== 'all') {
                if (typeVal === 'race' && r.type !== 'race') return false;
                if (typeVal === 'training' && r.type !== 'train') return false;
                if (typeVal === 'route' && r.type !== 'route') return false;
            }

            // Recency
            if (recencyVal !== 'all') {
                const today = new Date();
                const routeDate = new Date(r.dateFull);
                const diffDays = (today - routeDate) / (1000 * 60 * 60 * 24);

                if (recencyVal === 'week' && diffDays >= 7) return false;
                if (recencyVal === 'month' && diffDays >= 30) return false;
                if (recencyVal === 'year' && diffDays >= 365) return false;
                if (recencyVal === 'legacy' && diffDays < 365) return false;
            }

            // Distance
            if (distVal !== 'all') {
                const km = r.distance / 1000;
                if (distVal === '0-10' && km >= 10) return false;
                if (distVal === '10-20' && (km < 10 || km >= 20)) return false;
                if (distVal === '20-30' && (km < 20 || km >= 30)) return false;
                if (distVal === '30-40' && (km < 30 || km >= 40)) return false;
                if (distVal === '40+' && km < 40) return false;
            }
            // Elevation
            if (elevVal !== 'all') {
                const m = r.elevation;
                if (elevVal === '0-500' && m >= 500) return false;
                if (elevVal === '500-1000' && (m < 500 || m >= 1000)) return false;
                if (elevVal === '1000-2000' && (m < 1000 || m >= 2000)) return false;
                if (elevVal === '2000-3000' && (m < 2000 || m >= 3000)) return false;
                if (elevVal === '3000+' && m < 3000) return false;
            }

            // Effort
            if (effortVal !== 'all') {
                const eff = (r.distance / 1000) + (0.01 * r.elevation);
                if (effortVal === '0-25' && eff >= 25) return false;
                if (effortVal === '25-45' && (eff < 25 || eff >= 45)) return false;
                if (effortVal === '45-75' && (eff < 45 || eff >= 75)) return false;
                if (effortVal === '75-115' && (eff < 75 || eff >= 115)) return false;
                if (effortVal === '115-155' && (eff < 115 || eff >= 155)) return false;
                if (effortVal === '155-210' && (eff < 155 || eff >= 210)) return false;
                if (effortVal === '210+' && eff < 210) return false;
            }
            return true;
        });

        // Sort
        filteredRoutes.sort((a, b) => {
            if (sortVal === 'date-desc') return new Date(b.dateFull) - new Date(a.dateFull);
            if (sortVal === 'date-asc') return new Date(a.dateFull) - new Date(b.dateFull);
            if (sortVal === 'dist-desc') return b.distance - a.distance;
            if (sortVal === 'dist-asc') return a.distance - b.distance;
            if (sortVal === 'elev-desc') return b.elevation - a.elevation;
            if (sortVal === 'elev-asc') return a.elevation - b.elevation;
            if (sortVal === 'effort-desc') {
                const effA = (a.distance / 1000) + (0.01 * a.elevation);
                const effB = (b.distance / 1000) + (0.01 * b.elevation);
                return effB - effA;
            }
            if (sortVal === 'effort-asc') {
                const effA = (a.distance / 1000) + (0.01 * a.elevation);
                const effB = (b.distance / 1000) + (0.01 * b.elevation);
                return effA - effB;
            }
            return 0;
        });

        renderRoutesPage(currentPage);
    }

    function renderRoutesPage(page) {
        currentPage = page;
        const gridContainer = document.getElementById('routes-grid');
        const paginationContainer = document.getElementById('pagination');

        if (!filteredRoutes || filteredRoutes.length === 0) {
            gridContainer.innerHTML = '<div class="loading">No routes match your filters.</div>';
            if (paginationContainer) paginationContainer.innerHTML = '';
            return;
        }

        // Clear grid
        gridContainer.innerHTML = '';

        // Slice data
        const start = (page - 1) * ITEMS_PER_PAGE;
        const end = start + ITEMS_PER_PAGE;
        const pageItems = filteredRoutes.slice(start, end);

        // Create cards
        pageItems.forEach(route => {
            const card = createRouteCard(route);
            gridContainer.appendChild(card);
        });

        renderPagination();

        // Scroll to top on page change
        if (page > 1) {
            document.querySelector('main').scrollIntoView({ behavior: 'smooth' });
        }
    }

    function renderPagination() {
        const container = document.getElementById('pagination');
        if (!container) return;

        container.innerHTML = '';
        const totalPages = Math.ceil(filteredRoutes.length / ITEMS_PER_PAGE);

        if (totalPages <= 1) return;

        // Prev
        const prevBtn = document.createElement('button');
        prevBtn.innerText = '←';
        prevBtn.className = 'page-btn';
        prevBtn.disabled = currentPage === 1;
        prevBtn.onclick = () => renderRoutesPage(currentPage - 1);
        container.appendChild(prevBtn);

        // Page Numbers logic
        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(totalPages, startPage + 4);

        if (endPage - startPage < 4) {
            startPage = Math.max(1, endPage - 4);
        }

        for (let i = startPage; i <= endPage; i++) {
            const btn = document.createElement('button');
            btn.innerText = i;
            btn.className = `page-btn ${i === currentPage ? 'active' : ''}`;
            btn.onclick = () => renderRoutesPage(i);
            container.appendChild(btn);
        }

        // Next
        const nextBtn = document.createElement('button');
        nextBtn.innerText = '→';
        nextBtn.className = 'page-btn';
        nextBtn.disabled = currentPage === totalPages;
        nextBtn.onclick = () => renderRoutesPage(currentPage + 1);
        container.appendChild(nextBtn);
    }

    function createRouteCard(route) {
        const card = document.createElement('div');
        // We'll determine classes below

        const mapImage = route.mapImage || 'assets/maps/placeholder.png';
        const distance = formatDistance(route.distance);
        const elevation = formatElevation(route.elevation);

        // Effort = km + 0.01 * elevation(m)
        const effortValue = (route.distance / 1000) + (0.01 * route.elevation);
        const effort = `${Math.round(effortValue)} km`;

        // Strava URL: Activities vs Routes
        const isRouteSource = route.type === 'route';
        const stravaUrl = isRouteSource
            ? `https://www.strava.com/routes/${route.stravaId}`
            : `https://www.strava.com/activities/${route.stravaId}`;

        const rType = route.type || (route.isRace ? 'race' : 'train');

        const today = new Date();
        const routeDate = route.dateFull ? new Date(route.dateFull) : null;
        const diffDays = routeDate ? Math.floor((today - routeDate) / (1000 * 60 * 60 * 24)) : 9999;
        const routeYear = routeDate ? routeDate.getFullYear() : 0;
        const currentYear = today.getFullYear();

        let timeLabel = '';
        let timeClass = '';
        let hasWarning = false;

        if (diffDays < 7) {
            timeLabel = '< 1 week';
            timeClass = 'fresh';
        } else if (diffDays < 30) {
            timeLabel = '< 1 month';
            timeClass = 'active';
        } else if (diffDays < 365) {
            timeLabel = '< 1 year';
            timeClass = 'stable';
        } else {
            timeLabel = '> 1 year';
            timeClass = 'legacy';
            hasWarning = true;
        }

        // Apply classes to card
        card.className = `route-card ${route.type || ''}`;

        // Parse Creator from Name: [Creator] Route Name
        let displayTitle = route.name;
        let creatorName = route.athleteName || null;

        // If it has bracketed name in title, prefer that (legacy support)
        const creatorMatch = route.name.match(/^\[(.*?)\]\s*(.*)/);
        if (creatorMatch) {
            creatorName = creatorMatch[1];
            displayTitle = creatorMatch[2];
        }

        if (creatorName && (route.isPublic || creatorMatch)) {
            const tooltipText = route.isPublic ? `Activity by: ${creatorName}` : `Route by: ${creatorName}`;
            const athleteUrl = route.athleteId ? `https://www.strava.com/athletes/${route.athleteId}` : null;

            if (athleteUrl && route.isPublic) {
                displayTitle = `
                    <a href="${athleteUrl}" target="_blank" rel="noopener" class="creator-icon-link has-tooltip" data-tooltip="${tooltipText}">
                        <i class="fas fa-gift"></i>
                    </a> ${displayTitle}`;
            } else {
                displayTitle = `
                    <span class="creator-icon-static has-tooltip" data-tooltip="${tooltipText}">
                        <i class="fas fa-gift"></i>
                    </span> ${displayTitle}`;
            }
        }

        // Determine date label
        let datePrefix = 'Activity date';
        if (isRouteSource) {
            datePrefix = creatorName ? `Route created from ${creatorName}'s activity` : 'Route created date';
        }

        const hoverTitle = `${datePrefix}: ${route.dateDisplay || ''}`;

        card.innerHTML = `
            <div class="card-image-wrapper">
                <img src="${mapImage}" alt="${route.name} map" loading="lazy">
            </div>
            <div class="route-info">
                <div class="route-location">
                    <div class="loc-left">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>${route.location || 'Unknown Location'}</span>
                    </div>
                    ${timeLabel ? `
                        <span class="route-date ${timeClass} has-tooltip" data-tooltip="${hoverTitle}">
                            ${timeLabel}
                            ${hasWarning ? '<i class="fas fa-exclamation-triangle warning-icon"></i>' : ''}
                        </span>` : ''}
                </div>
                <h3>${displayTitle}</h3>
                <div class="route-stats">
                    <div class="stat">
                        <div class="stat-label">Distance</div>
                        <div class="stat-value">${distance}</div>
                    </div>
                    <div class="stat">
                        <div class="stat-label">Elevation</div>
                        <div class="stat-value">${elevation}</div>
                    </div>
                    <div class="stat has-tooltip" data-tooltip="Effort = distance(km) + 0.01 * elevation(m)">
                        <div class="stat-label">Effort</div>
                        <div class="stat-value">${effort}</div>
                    </div>
                </div>
                
                ${renderPoiSection(route.pois, route.location)}

                <div class="route-actions">
                    <div class="route-type-badge ${rType}">
                        ${rType === 'race' ? 'Race' : (rType === 'route' ? 'Route' : 'Training')}
                    </div>
                    <div class="action-buttons">
                        <a href="${stravaUrl}" target="_blank" rel="noopener" class="btn-action strava" title="View on Strava">
                            <i class="fab fa-strava"></i>
                        </a>
                        <button class="btn-action primary" onclick="downloadGPX('${route.stravaId}', '${route.name}')" title="Download GPX">
                            <i class="fas fa-download"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;

        return card;
    }

    function renderPoiSection(pois, currentLocation) {
        // Remove duplicates by name and filter out route location
        const unique = [];
        const seen = new Set();

        if (pois && pois.length > 0) {
            pois.forEach(p => {
                if (!seen.has(p.name)) {
                    if (p.name !== currentLocation) {
                        unique.push(p);
                    }
                    seen.add(p.name);
                }
            });
        }

        if (unique.length === 0) {
            unique.push({
                name: currentLocation,
                type: ['start']
            });
        }

        // Note: No sorting here anymore, we respect the backend order
        // which is sorted by first match along the route.

        // Logic: Show max 5 items total (either 5 POIs or 4 POIs + "+N" badge)
        const totalPois = unique.length;
        let displayPois = [];
        let extraCount = 0;

        if (totalPois > 5) {
            displayPois = unique.slice(0, 4);
            extraCount = totalPois - 4;
        } else {
            displayPois = unique;
            extraCount = 0;
        }

        let html = '<div class="poi-section">';

        displayPois.forEach(p => {
            const type = (p.type && p.type[0]) ? p.type[0].toLowerCase() : 'generic';
            let icon = '📍';
            if (type === 'start') icon = '🏁';
            else if (type === 'parking') icon = '🅿️';
            else if (type === 'hill' || type === 'mountain') icon = '⛰️';
            else if (type === 'warung' || type === 'caffe') icon = '☕';
            else if (type === 'curug' || type === 'lake') icon = '🌊';
            else if (type === 'campground') icon = '⛺';
            else if (type === 'incline' || type === 'climb') icon = '🚀';

            html += `<span class="poi-badge ${type} has-tooltip" data-tooltip="${p.name}">${icon} <span class="poi-name">${p.name}</span></span>`;
        });

        if (extraCount > 0) {
            const hiddenNames = unique.slice(4).map(p => p.name).join(', ');
            html += `<span class="poi-badge more has-tooltip" data-tooltip="${hiddenNames}">+${extraCount} more</span>`;
        }
        html += '</div>';
        return html;
    }

    function formatDistance(meters) {
        const km = (meters / 1000).toFixed(1);
        return `${km} km`;
    }

    function formatElevation(meters) {
        return `${Math.round(meters)} m`;
    }

    function updateLastUpdateTime(lastUpdated) {
        const lastUpdateElement = document.getElementById('last-update');
        if (lastUpdated && lastUpdateElement) {
            const date = new Date(lastUpdated);
            lastUpdateElement.textContent = date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        }
    }

    // --- GPX Generation Utilities ---

    function decodePolyline(str, precision) {
        var index = 0,
            lat = 0,
            lng = 0,
            coordinates = [],
            shift = 0,
            result = 0,
            byte = null,
            latitude_change,
            longitude_change,
            factor = Math.pow(10, precision || 5);

        if (!str) return [];

        while (index < str.length) {
            byte = null;
            shift = 0;
            result = 0;

            do {
                byte = str.charCodeAt(index++) - 63;
                result |= (byte & 0x1f) << shift;
                shift += 5;
            } while (byte >= 0x20);

            latitude_change = ((result & 1) ? ~(result >> 1) : (result >> 1));
            shift = result = 0;

            do {
                byte = str.charCodeAt(index++) - 63;
                result |= (byte & 0x1f) << shift;
                shift += 5;
            } while (byte >= 0x20);

            longitude_change = ((result & 1) ? ~(result >> 1) : (result >> 1));

            lat += latitude_change;
            lng += longitude_change;

            coordinates.push([lat / factor, lng / factor]);
        }

        return coordinates;
    }

    function deObfuscate(str) {
        if (!str) return null;
        try {
            // Use local scoped KEY
            const KEY = ENCRYPTION_KEY;
            const decoded = atob(str);
            let result = '';
            for (let i = 0; i < decoded.length; i++) {
                const charCode = decoded.charCodeAt(i);
                const keyCode = KEY.charCodeAt(i % KEY.length);
                result += String.fromCharCode(charCode ^ keyCode);
            }
            return result;
        } catch (e) {
            console.error("De-obfuscation failed", e);
            return null;
        }
    }

    function generateGPX(coords, name, route) {
        const isRouteSource = route && route.type === 'route';
        const stravaUrl = route ? (isRouteSource
            ? `https://www.strava.com/routes/${route.stravaId}`
            : `https://www.strava.com/activities/${route.stravaId}`) : null;

        let gpx = '<?xml version="1.0" encoding="UTF-8"?>\n';
        gpx += '<gpx version="1.1" creator="The Trail Archive" xmlns="http://www.topografix.com/GPX/1/1">\n';
        gpx += `  <metadata>\n    <name>${name}</name>\n    <desc>Downloaded from https://trail.nurandi.id${stravaUrl ? `\nOriginal source: ${stravaUrl}` : ''}</desc>\n    <link href="https://trail.nurandi.id">\n      <text>The Trail Archive</text>\n    </link>\n`;
        if (stravaUrl) {
            gpx += `    <link href="${stravaUrl}">\n      <text>Original Source</text>\n    </link>\n`;
        }
        gpx += `  </metadata>\n`;
        gpx += '  <trk>\n';
        gpx += `    <name>${name}</name>\n`;
        gpx += '    <trkseg>\n';

        coords.forEach(point => {
            let pt = `      <trkpt lat="${point[0]}" lon="${point[1]}">`;
            if (point.length > 2) {
                pt += `<ele>${point[2]}</ele>`;
            }
            pt += `</trkpt>\n`;
            gpx += pt;
        });

        gpx += '    </trkseg>\n  </trk>\n</gpx>';
        return gpx;
    }

    // --- TOC Modal Logic ---
    const modal = document.getElementById("tocModal");
    const closeBtn = document.getElementsByClassName("close")[0];
    const cancelBtn = document.getElementById("cancelBtn");
    const confirmBtn = document.getElementById("confirmDownloadBtn");
    const checkbox = document.getElementById("tocCheckbox");

    let pendingRoute = null;

    function openModal(stravaId, routeName) {
        pendingRoute = { id: stravaId, name: routeName };
        if (checkbox) checkbox.checked = false;
        if (confirmBtn) confirmBtn.disabled = true;

        const route = allRoutes.find(r => r.stravaId === stravaId);
        const warningEl = document.getElementById('oldRouteWarning');

        if (warningEl) {
            warningEl.style.display = 'none';
            if (route && route.dateFull) {
                const oneYearAgo = new Date();
                oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);

                if (new Date(route.dateFull) < oneYearAgo) {
                    const dateStr = route.dateDisplay || new Date(route.dateFull).toLocaleDateString();
                    warningEl.innerHTML = `< strong >⚠️ Old Route Warning:</strong > This activity was recorded in ${dateStr}. Trail conditions may have changed significantly.`;
                    warningEl.style.display = 'block';
                }
            }
        }

        if (modal) modal.style.display = "block";
    }

    function closeModal() {
        if (modal) modal.style.display = "none";
        pendingRoute = null;
    }

    if (closeBtn) closeBtn.onclick = closeModal;
    if (cancelBtn) cancelBtn.onclick = closeModal;

    // --- About Modal Logic ---
    const aboutModal = document.getElementById("aboutModal");
    const aboutLink = document.getElementById("aboutLink");
    const closeAboutSpan = document.getElementById("closeAbout");
    const closeAboutBtn = document.getElementById("closeAboutBtn");

    if (aboutLink) {
        aboutLink.onclick = function (e) {
            e.preventDefault();
            if (aboutModal) aboutModal.style.display = "block";
        }
    }

    function closeAboutModal() {
        if (aboutModal) aboutModal.style.display = "none";
    }

    if (closeAboutSpan) closeAboutSpan.onclick = closeAboutModal;
    if (closeAboutBtn) closeAboutBtn.onclick = closeAboutModal;

    window.onclick = function (event) {
        if (event.target == modal) {
            closeModal();
        }
        if (event.target == aboutModal) {
            closeAboutModal();
        }
    }

    if (checkbox) {
        checkbox.onchange = function () {
            confirmBtn.disabled = !this.checked;
        }
    }

    if (confirmBtn) {
        confirmBtn.onclick = async function () {
            if (!pendingRoute) return;

            const originalText = confirmBtn.innerText;
            confirmBtn.innerText = "Generating...";
            confirmBtn.disabled = true;

            try {
                await executeDownload(pendingRoute.id, pendingRoute.name);
                closeModal();
            } catch (e) {
                console.error(e);
                alert("Download failed. Please try again.");
            } finally {
                confirmBtn.innerText = originalText;
                confirmBtn.disabled = false;
                if (modal.style.display !== "none") {
                    confirmBtn.disabled = !checkbox.checked;
                }
            }
        };
    }

    function checkDownloadLimit() {
        const LIMIT = 10; // Max 10 downloads
        const WINDOW_MS = 60 * 60 * 1000; // 1 hour
        const now = Date.now();

        let history = [];
        try {
            history = JSON.parse(localStorage.getItem('download_history') || '[]');
        } catch (e) {
            history = [];
        }

        // Clean up old timestamps
        history = history.filter(ts => now - ts < WINDOW_MS);

        if (history.length >= LIMIT) {
            const oldest = history[0];
            const remaining = Math.ceil((WINDOW_MS - (now - oldest)) / 60000);
            alert(`Download limit reached (${LIMIT} per hour). Please try again in about ${remaining} minutes.`);
            return false;
        }

        history.push(now);
        localStorage.setItem('download_history', JSON.stringify(history));
        return true;
    }

    window.downloadGPX = function (stravaId, routeName) {
        openModal(stravaId, routeName);
    };

    async function executeDownload(stravaId, routeName) {
        // Rate limiting
        if (!checkDownloadLimit()) return;

        const route = allRoutes.find(r => r.stravaId === stravaId);
        if (!route) {
            alert('Route not found.');
            return;
        }

        // Track GPX Download Event
        if (typeof trackEvent === 'function') {
            trackEvent('download_gpx', 'File', `${stravaId} - ${routeName}`);
        }

        try {
            let coords = [];

            // 1. Try to fetch detailed stream (NOW .dat)
            try {
                const response = await fetch(`assets/streams/${stravaId}.dat`);
                if (response.ok) {
                    const encryptedText = await response.text();

                    try {
                        const decryptedText = deObfuscate(encryptedText);
                        const parsed = JSON.parse(decryptedText);
                        if (Array.isArray(parsed)) {
                            coords = parsed;
                        }
                    } catch (decryptionError) {
                        console.warn("Decryption failed", decryptionError);
                    }
                }
            } catch (e) {
                console.log("Could not fetch stream data", e);
            }

            // 2. Fallback to Polyline
            if (coords.length === 0) {
                if (route.ePolyline) {
                    const polylineStr = deObfuscate(route.ePolyline);
                    coords = decodePolyline(polylineStr);
                }
            }

            if (coords.length === 0) {
                alert('GPX data not available. Redirecting to Strava...');
                window.open(`https://www.strava.com/activities/${stravaId}/export_gpx`, '_blank');
                return;
            }

            const gpxContent = generateGPX(coords, routeName, route);
            const blob = new Blob([gpxContent], { type: 'application/gpx+xml' });
            const url = URL.createObjectURL(blob);

            const link = document.createElement('a');
            link.href = url;

            const distK = Math.round(route.distance / 1000);
            const elevM = Math.round(route.elevation);
            link.download = `${stravaId}_${distK}K_${elevM}m.gpx`;

            document.body.appendChild(link);
            link.click();

            setTimeout(() => {
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);
            }, 100);

        } catch (e) {
            throw e;
        }
    };

    let tooltipEl = null;

    function initTooltipSystem() {
        tooltipEl = document.createElement('div');
        tooltipEl.className = 'custom-tooltip';
        document.body.appendChild(tooltipEl);

        document.addEventListener('mouseover', e => {
            const target = e.target.closest('.has-tooltip');
            if (target) showTooltip(target.getAttribute('data-tooltip'), target);
        });

        document.addEventListener('mouseout', e => {
            if (e.target.closest('.has-tooltip')) hideTooltip();
        });

        document.addEventListener('click', e => {
            const target = e.target.closest('.has-tooltip');
            if (target) {
                showTooltip(target.getAttribute('data-tooltip'), target);
                e.stopPropagation();
            } else {
                hideTooltip();
            }
        });

        window.addEventListener('scroll', hideTooltip, { passive: true });
    }

    function showTooltip(text, target) {
        if (!tooltipEl || !text) return;
        tooltipEl.textContent = text;
        tooltipEl.classList.add('visible');

        const targetRect = target.getBoundingClientRect();
        const tooltipRect = tooltipEl.getBoundingClientRect();

        let top = targetRect.top - tooltipRect.height - 8;
        let left = targetRect.left + (targetRect.width / 2) - (tooltipRect.width / 2);

        if (top < 10) top = targetRect.bottom + 8;
        if (left < 10) left = 10;
        if (left + tooltipRect.width > window.innerWidth - 10) {
            left = window.innerWidth - tooltipRect.width - 10;
        }

        tooltipEl.style.top = `${top}px`;
        tooltipEl.style.left = `${left}px`;
    }

    function hideTooltip() {
        if (tooltipEl) tooltipEl.classList.remove('visible');
    }

})();
