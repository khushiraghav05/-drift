const API_BASE = '/api';

let currentWatchlist = [];
let currentMarket = null;
let isLoaded = false;
let filterAttention = false;

async function fetchWatchlist() {
    try {
        const queue = document.getElementById('attention-queue');
        if (!isLoaded && queue) {
            queue.innerHTML = '<div class="state-msg">Loading dashboard...</div>';
            document.getElementById('watchlist-body').innerHTML = '<tr><td colspan="5" class="state-msg">Loading watchlist...</td></tr>';
        }

        const res = await fetch(`${API_BASE}/watchlist`);
        if (!res.ok) throw new Error('API Response not ok');

        const data = await res.json();
        currentWatchlist = data.stocks || [];
        currentMarket = data.market || null;
        isLoaded = true;

        renderDashboard();
    } catch (err) {
        console.error(err);
        document.getElementById('attention-queue').innerHTML = '<div class="state-msg error">Failed to load data. API might be down.</div>';
    }
}

function calculateHealth() {
    let high = 0, med = 0, low = 0, norm = 0;
    currentWatchlist.forEach(i => {
        const lvl = i.attention?.level;
        if (lvl === 'high') high++;
        else if (lvl === 'medium') med++;
        else if (lvl === 'low') low++;
        else norm++;
    });
    return { high, med, low, norm };
}

function renderDashboard() {
    if (currentMarket) {
        document.getElementById('nifty-text').innerHTML = `NIFTY 50: ₹${currentMarket.nifty_price || '--'} <span class="${currentMarket.nifty_change_pct >= 0 ? 'pos' : 'neg'}">${currentMarket.nifty_change_pct || 0}%</span>`;
    }

    const health = calculateHealth();
    document.getElementById('watchlist-health').innerHTML = `
        <span style="font-weight:600; margin-right:5px; color:var(--text-sec)">Watchlist Health</span>
        <span class="health-item badge-high">🔴 ${health.high} High</span>
        <span class="health-item badge-medium">🟡 ${health.med} Medium</span>
        <span class="health-item badge-low">⚪ ${health.low} Low</span>
        <span class="health-item badge-normal">🟢 ${health.norm} Normal</span>
    `;

    const queue = document.getElementById('attention-queue');
    const tbody = document.getElementById('watchlist-body');
    queue.innerHTML = '';
    tbody.innerHTML = '';

    let attentionItems = currentWatchlist
        .filter(i => {
            if (filterAttention) return i.attention && (i.attention.level === 'high' || i.attention.level === 'medium');
            return i.attention && i.attention.level !== 'normal'; // meaningful changes
        })
        .sort((a, b) => b.attention.score - a.attention.score);

    if (currentWatchlist.length === 0) {
        queue.innerHTML = '<div class="state-msg">Your watchlist is empty. Add a stock below.</div>';
        tbody.innerHTML = '<tr><td colspan="5" class="state-msg">No stocks in watchlist</td></tr>';
        return;
    }

    if (attentionItems.length === 0) {
        queue.innerHTML = `
            <div class="caught-up">
                <div style="font-size:32px; color:var(--pos); margin-bottom:10px;">✓</div>
                <h3>You're caught up</h3>
                <p style="color:var(--text-sec)">Nothing meaningful has changed since your last check.</p>
            </div>
        `;
    } else {
        attentionItems.forEach(item => {
            const card = document.createElement('div');
            card.className = 'card attention-card';
            card.id = `card-${item.symbol}`;

            const changeCls = item.change_pct >= 0 ? 'pos' : 'neg';

            let signalsHtml = '';
            item.attention.signals?.forEach(s => {
                if (s.available && s.signal_score > 0) {
                    signalsHtml += `<div class="signal-item"><strong>${s.name.toUpperCase()}</strong>: ${s.description}</div>`;
                }
            });

            let conf = 'HIGH', confCls = 'pos';
            const f = item.data_meta?.freshness;
            if (f === 'stale' || f === 'delayed') { conf = 'LOW'; confCls = 'neg'; }
            else if (f === 'cached') { conf = 'MEDIUM'; confCls = 'text-sec'; }

            // Extract relative movement for market context
            let moveVsMarket = '';
            const relSignal = item.attention.signals?.find(s => s.name === 'relative' && s.available);
            if (relSignal && currentMarket?.nifty_change_pct != null) {
                moveVsMarket = `
                    <div style="margin-top:10px; font-size:12px; color:var(--text-sec);">
                        Market Context: <span class="${relSignal.raw_value >= 0 ? 'pos' : 'neg'}">${relSignal.description}</span>
                    </div>
                `;
            }

            const timeStr = item.data_meta?.timestamp ? new Date(item.data_meta.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--';

            card.innerHTML = `
                <div class="card-header" onclick="toggleCard(this)">
                    <div>
                        <strong>${item.display_name}</strong>
                        <span class="badge badge-${item.attention.level}">${item.attention.level.toUpperCase()}</span>
                    </div>
                    <div>
                        <span class="expand-icon" style="color:var(--text-sec); font-size:12px;">▼ Expand</span>
                    </div>
                </div>
                <div class="price" style="cursor:pointer" onclick="toggleCard(this)">
                    ₹${item.price} <span class="${changeCls}">${item.change_pct}%</span>
                </div>
                <p style="font-size:13px; color:var(--text-sec); margin-top:10px; cursor:pointer" onclick="toggleCard(this)">
                    ${item.attention.summary || item.attention.explanation}
                </p>
                
                <div class="card-details" style="display:none; margin-top:15px; border-top:1px solid var(--border-color); padding-top:15px;">
                    <div style="margin-bottom:15px;">
                        <span style="font-size:12px; color:var(--${confCls})">Data Confidence: ${conf} <span style="opacity:0.7">(${f || 'unknown'})</span></span>
                    </div>
                    
                    <div class="breakdown">
                        <div class="timeline-step">
                            <small>Baseline Price</small>
                            <div style="font-weight:600;">₹${item.baseline_price || '--'}</div>
                        </div>
                        <div class="timeline-step">
                            <small>Current (${timeStr})</small>
                            <div style="font-weight:600;">₹${item.price}</div>
                        </div>
                    </div>
                    
                    ${moveVsMarket}

                    <div class="signals-box" style="margin-top:15px;">
                        <h4 style="margin:5px 0 10px 0; font-size:14px;">Why this matters?</h4>
                        ${signalsHtml || '<div class="signal-item">No strong signals available.</div>'}
                    </div>
                    
                    <div style="display:flex; justify-content:space-between; margin-top:15px; gap:10px;">
                        <button class="btn btn-secondary flex-1" onclick="showDetail('${item.symbol}')">More</button>
                        <button class="btn btn-primary flex-1" onclick="reviewStock('${item.symbol}')">Review ✓</button>
                    </div>
                </div>
            `;
            queue.appendChild(card);
        });
    }

    currentWatchlist.forEach(item => {
        const tr = document.createElement('tr');
        const changeCls = item.change_pct >= 0 ? 'pos' : 'neg';
        tr.innerHTML = `
            <td><strong>${item.symbol}</strong><br><small style="color:var(--text-sec)">${item.display_name}</small></td>
            <td><span class="badge badge-${item.attention.level}">${item.attention.level.toUpperCase()}</span></td>
            <td>₹${item.price}</td>
            <td class="${changeCls}">${item.change_pct}%</td>
            <td>
                <button class="btn btn-secondary" style="margin-right:5px;" onclick="showDetail('${item.symbol}')">View</button>
                <button class="btn btn-secondary" onclick="removeStock('${item.symbol}')">Remove</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function toggleCard(el) {
    const detail = el.closest('.card').querySelector('.card-details');
    const icon = el.closest('.card').querySelector('.expand-icon');
    if (detail.style.display === 'none') {
        detail.style.display = 'block';
        if (icon) icon.innerText = '▲ Hide';
    } else {
        detail.style.display = 'none';
        if (icon) icon.innerText = '▼ Expand';
    }
}

function showToast(msg, isError = false) {
    const t = document.getElementById('toast');
    t.innerText = msg;
    t.className = isError ? 'toast error' : 'toast';
    t.style.opacity = '1';
    setTimeout(() => t.style.opacity = '0', 2500);
}

async function reviewStock(symbol) {
    try {
        const payload = symbol === 'all'
            ? currentWatchlist.map(i => i.symbol)
            : [symbol];

        if (payload.length === 0) return;

        if (symbol !== 'all') {
            const el = document.getElementById(`card-${symbol}`);
            if (el) {
                el.style.opacity = '0.5';
                el.style.transform = 'scale(0.98)';
                setTimeout(() => el.remove(), 300);
            }
        }

        const res = await fetch(`${API_BASE}/review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbols: payload })
        });

        if (!res.ok) throw new Error('Failed to review');

        showToast(symbol === 'all' ? 'All items reviewed ✓' : `${symbol} reviewed ✓`);

        setTimeout(fetchWatchlist, 300);
    } catch (err) {
        console.error(err);
        showToast('Error reviewing stock', true);
        fetchWatchlist();
    }
}

async function removeStock(symbol) {
    if (confirm(`Remove ${symbol}?`)) {
        try {
            const res = await fetch(`${API_BASE}/watchlist/${symbol}`, { method: 'DELETE' });
            if (!res.ok) throw new Error();
            fetchWatchlist();
        } catch (e) {
            showToast('Failed to remove stock', true);
        }
    }
}

// Add Stock / Search
document.getElementById('add-stock-btn').onclick = () => {
    document.getElementById('add-modal').classList.add('active');
    document.getElementById('search-input').focus();
};
document.querySelector('.close-btn').onclick = () => document.getElementById('add-modal').classList.remove('active');
document.querySelector('.close-detail-btn').onclick = () => document.getElementById('detail-modal').classList.remove('active');

document.getElementById('search-btn').onclick = async () => {
    const q = document.getElementById('search-input').value.trim();
    if (!q) return;

    const resultsContainer = document.getElementById('search-results');
    resultsContainer.innerHTML = '<div class="state-msg">Searching...</div>';

    try {
        const res = await fetch(`${API_BASE}/search?q=${q}`);
        if (!res.ok) throw new Error();
        const results = await res.json();

        if (results.length === 0) {
            resultsContainer.innerHTML = '<div class="state-msg">No results found</div>';
            return;
        }

        let html = '';
        results.forEach(r => {
            html += `<div class="search-result-item">
                <div>
                    <strong>${r.symbol}</strong><br>
                    <small style="color:var(--text-sec)">${r.name}</small>
                </div>
                <button class="btn btn-primary" onclick="addStock('${r.symbol}')">Add</button>
            </div>`;
        });
        resultsContainer.innerHTML = html;
    } catch (e) {
        resultsContainer.innerHTML = '<div class="state-msg error">Search failed. Try again.</div>';
    }
};

document.getElementById('search-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') document.getElementById('search-btn').click();
});

async function addStock(symbol) {
    try {
        const res = await fetch(`${API_BASE}/watchlist`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol })
        });
        if (res.ok) {
            document.getElementById('add-modal').classList.remove('active');
            showToast(`${symbol} added to watchlist`);
            fetchWatchlist();
        } else {
            const err = await res.json();
            alert(err.detail || 'Failed to add');
        }
    } catch (e) {
        showToast('Error adding stock', true);
    }
}

async function showDetail(symbol) {
    try {
        document.getElementById('detail-body').innerHTML = '<div class="state-msg">Loading details...</div>';
        document.getElementById('detail-modal').classList.add('active');

        const res = await fetch(`${API_BASE}/stock/${symbol}`);
        if (!res.ok) throw new Error();
        const data = await res.json();

        document.getElementById('detail-title').innerText = data.display_name;

        let signalsHtml = '';
        if (data.change && data.change.signals) {
            data.change.signals.forEach(s => {
                if (s.available && s.signal_score > 0) {
                    signalsHtml += `<div class="signal-item"><strong>${s.name.toUpperCase()}</strong>: ${s.description} (Impact: ${s.weighted_score})</div>`;
                }
            });
        }

        document.getElementById('detail-body').innerHTML = `
            <div style="font-size:24px; margin-bottom:10px;">₹${data.current.price} <small style="font-size:14px; color:var(--text-sec);">vs baseline ₹${data.baseline.price}</small></div>
            <p style="background:var(--surface-hover); padding:10px; border-radius:4px;">${data.change.explanation || 'Normal movement'}</p>
            <div style="margin-top:20px;">
                <h4>Signals Overview</h4>
                ${signalsHtml || '<p style="color:var(--text-sec)">No significant signals</p>'}
            </div>
        `;
    } catch (e) {
        document.getElementById('detail-body').innerHTML = '<div class="state-msg error">Failed to load stock detail</div>';
    }
}

document.getElementById('review-all-btn').onclick = () => reviewStock('all');

document.getElementById('filter-attention-btn').onclick = (e) => {
    filterAttention = !filterAttention;
    e.target.innerText = filterAttention ? 'Filter: High/Med Only' : 'Filter: All Meaningful';
    renderDashboard();
};

// Init
fetchWatchlist();
