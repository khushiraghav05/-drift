const API_BASE = '/api';

async function fetchWatchlist() {
    const res = await fetch(`${API_BASE}/watchlist`);
    const data = await res.json();
    renderDashboard(data);
}

async function reviewStock(symbol) {
    await fetch(`${API_BASE}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols: [symbol] })
    });
    fetchWatchlist();
}

async function removeStock(symbol) {
    if (confirm(`Remove ${symbol}?`)) {
        await fetch(`${API_BASE}/watchlist/${symbol}`, { method: 'DELETE' });
        fetchWatchlist();
    }
}

function renderDashboard(data) {
    // Market Bar
    const market = data.market;
    if (market) {
        document.getElementById('nifty-text').innerHTML = `NIFTY 50: ₹${market.nifty_price} <span class="${market.nifty_change_pct >= 0 ? 'pos' : 'neg'}">${market.nifty_change_pct}%</span>`;
    }

    const queue = document.getElementById('attention-queue');
    const tbody = document.getElementById('watchlist-body');
    queue.innerHTML = '';
    tbody.innerHTML = '';

    // Sort attention descending
    const items = data.stocks;
    const attentionItems = items.filter(i => i.attention && i.attention.score > 20)
        .sort((a, b) => b.attention.score - a.attention.score);

    attentionItems.forEach(item => {
        const card = document.createElement('div');
        card.className = 'card';
        card.onclick = () => showDetail(item.symbol);

        const changeCls = item.change_pct >= 0 ? 'pos' : 'neg';

        card.innerHTML = `
            <div class="card-header">
                <strong>${item.display_name}</strong>
                <span class="badge badge-${item.attention.level}">${item.attention.level.toUpperCase()}</span>
            </div>
            <div class="price">₹${item.price} <span class="${changeCls}">${item.change_pct}%</span></div>
            <p style="font-size:13px; color:var(--text-sec); margin-top:10px;">${item.attention.summary || item.attention.explanation}</p>
        `;
        queue.appendChild(card);
    });

    if (attentionItems.length === 0 && items.length > 0) {
        queue.innerHTML = '<p style="color:var(--text-sec)">Nothing requires your attention right now.</p>';
    }

    items.forEach(item => {
        const tr = document.createElement('tr');
        const changeCls = item.change_pct >= 0 ? 'pos' : 'neg';
        const isDemo = item.data_meta && item.data_meta.freshness === 'demo';

        tr.innerHTML = `
            <td><strong>${item.symbol}</strong><br><small style="color:var(--text-sec)">${item.display_name}</small></td>
            <td><span class="badge badge-${item.attention.level}">${item.attention.level.toUpperCase()}</span></td>
            <td>₹${item.price}</td>
            <td class="${changeCls}">${item.change_pct}%</td>
            <td>
                <button class="btn btn-secondary" onclick="showDetail('${item.symbol}')">View</button>
                <button class="btn btn-secondary" onclick="removeStock('${item.symbol}')">Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// Add Stock
document.getElementById('add-stock-btn').onclick = () => document.getElementById('add-modal').classList.add('active');
document.querySelector('.close-btn').onclick = () => document.getElementById('add-modal').classList.remove('active');
document.querySelector('.close-detail-btn').onclick = () => document.getElementById('detail-modal').classList.remove('active');

document.getElementById('search-btn').onclick = async () => {
    const q = document.getElementById('search-input').value;
    const res = await fetch(`${API_BASE}/search?q=${q}`);
    const results = await res.json();

    let html = '';
    results.forEach(r => {
        html += `<div class="search-result-item">
            <div><strong>${r.symbol}</strong> - ${r.name}</div>
            <button class="btn btn-primary" onclick="addStock('${r.symbol}')">Add</button>
        </div>`;
    });
    document.getElementById('search-results').innerHTML = html;
};

async function addStock(symbol) {
    const res = await fetch(`${API_BASE}/watchlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol })
    });
    if (res.ok) {
        document.getElementById('add-modal').classList.remove('active');
        fetchWatchlist();
    } else {
        alert(await res.text());
    }
}

async function showDetail(symbol) {
    const res = await fetch(`${API_BASE}/stock/${symbol}`);
    const data = await res.json();

    document.getElementById('detail-title').innerText = data.display_name;
    const b = document.getElementById('detail-body');

    let signalsHtml = '';
    if (data.change && data.change.signals) {
        data.change.signals.forEach(s => {
            if (s.available && s.signal_score > 0) {
                signalsHtml += `<div style="margin-bottom:10px;"><strong>${s.name.toUpperCase()}:</strong> ${s.description} (Impact: ${s.weighted_score})</div>`;
            }
        });
    }

    b.innerHTML = `
        <div style="font-size:24px; margin-bottom:10px;">₹${data.current.price} <small style="font-size:14px; color:var(--text-sec);">vs baseline ₹${data.baseline.price}</small></div>
        <p style="background:var(--surface-hover); padding:10px; border-radius:4px;">${data.change.explanation || 'Normal'}</p>
        <div style="margin-top:20px;">
            <h4>Signals</h4>
            ${signalsHtml || '<p>No significant signals</p>'}
        </div>
        <div style="margin-top:20px; display:flex; gap:10px;">
            <button class="btn btn-primary" onclick="reviewStock('${data.symbol}'); document.getElementById('detail-modal').classList.remove('active');">Mark as Reviewed</button>
        </div>
    `;

    document.getElementById('detail-modal').classList.add('active');
}

document.getElementById('review-all-btn').onclick = () => reviewStock('all');

// Init
fetchWatchlist();
