#!/usr/bin/env python3
"""
Generate a single-page application for the restaurants database.
Outputs: index.html + data.json
"""

import os
import json
import sqlite3
from datetime import datetime
from collections import defaultdict

DB_PATH = "restaurants.db"
OUTPUT_DIR = "site"


def parse_json_field(value):
    if not value:
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else [result]
    except:
        return [value] if value else []


def get_all_restaurants(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM restaurants ORDER BY restaurant_name")
    restaurants = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    for r in restaurants:
        r['dishes_list'] = parse_json_field(r.get('signature_dishes'))
        r['awards_list'] = parse_json_field(r.get('awards'))
        r['categories_list'] = parse_json_field(r.get('llm_categories', [])) + parse_json_field(r.get('user_categories', []))
    
    return restaurants


def generate_data_json(restaurants):
    data = {
        'restaurants': [],
        'stats': {
            'total': len(restaurants),
            'visited': sum(1 for r in restaurants if r.get('visit_status') == 'visited'),
            'wishlist': sum(1 for r in restaurants if r.get('visit_status') == 'want_to_visit'),
        },
        'cuisines': defaultdict(list),
        'locations': defaultdict(list),
        'price_ranges': defaultdict(list),
    }
    
    ratings = [r['rating'] for r in restaurants if r.get('rating') and r.get('visit_status') == 'visited']
    data['stats']['avg_rating'] = round(sum(ratings) / len(ratings), 1) if ratings else 0
    
    for r in restaurants:
        rest_data = {
            'id': r['id'],
            'name': r['restaurant_name'],
            'location': r.get('location') or '',
            'cuisine': r.get('cuisine') or '',
            'status': r.get('visit_status') or 'want_to_visit',
            'date_visited': r.get('date_visited') or '',
            'rating': r.get('rating'),
            'date_added': r['date_added'][:10] if r.get('date_added') else '',
            'price': r.get('price_range') or '',
            'address': r.get('full_address') or '',
            'phone': r.get('phone_number') or '',
            'website': r.get('website') or '',
            'hours': r.get('hours_summary') or '',
            'type': r.get('restaurant_type') or '',
            'atmosphere': r.get('atmosphere') or '',
            'dishes': r['dishes_list'],
            'awards': r['awards_list'],
            'notes': r.get('personal_notes') or '',
        }
        data['restaurants'].append(rest_data)
        
        if r.get('cuisine'):
            if r['id'] not in data['cuisines'][r['cuisine']]:
                data['cuisines'][r['cuisine']].append(r['id'])
        
        if r.get('location'):
            if r['id'] not in data['locations'][r['location']]:
                data['locations'][r['location']].append(r['id'])
        
        if r.get('price_range'):
            if r['id'] not in data['price_ranges'][r['price_range']]:
                data['price_ranges'][r['price_range']].append(r['id'])
    
    data['stats']['cuisine_count'] = len(data['cuisines'])
    data['stats']['location_count'] = len(data['locations'])
    
    data['cuisines'] = dict(data['cuisines'])
    data['locations'] = dict(data['locations'])
    data['price_ranges'] = dict(data['price_ranges'])
    
    return data


CUISINE_COLORS = {
    'italian': '#e74c3c', 'japanese': '#e91e63', 'chinese': '#f39c12',
    'mexican': '#e67e22', 'indian': '#9b59b6', 'thai': '#16a085',
    'french': '#3498db', 'american': '#34495e', 'mediterranean': '#27ae60',
    'korean': '#c0392b', 'vietnamese': '#2ecc71', 'steakhouse': '#8e44ad',
    'seafood': '#1abc9c', 'bbq': '#d35400', 'pizza': '#e74c3c',
    'sushi': '#e91e63', 'fusion': '#95a5a6', 'bakery': '#8b4513', 'cafe': '#6b4423'
}


def generate_html():
    cuisine_colors_js = json.dumps(CUISINE_COLORS)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paul's Restaurants</title>
    <style>
        :root {{
            --bg: #ffffff;
            --bg-card: #f8f9fa;
            --text: #2c3e50;
            --text-muted: #7f8c8d;
            --accent: #d97706;
            --accent-hover: #b45309;
            --border: #e0e0e0;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: Georgia, serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }}
        .back-link {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 0.85rem;
            margin-bottom: 1.5rem;
        }}
        .back-link a {{ color: var(--text-muted); text-decoration: none; }}
        .back-link a:hover {{ color: var(--accent); }}
        h1 {{ color: var(--accent); font-size: 2.5rem; font-weight: normal; text-align: center; margin-bottom: 0.5rem; }}
        .subtitle {{ text-align: center; color: var(--text-muted); font-style: italic; margin-bottom: 2rem; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat {{
            background: var(--bg-card);
            padding: 1.25rem;
            text-align: center;
            border: 2px solid var(--border);
            border-radius: 8px;
        }}
        .stat-value {{ font-size: 2rem; color: var(--accent); }}
        .stat-label {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; font-family: -apple-system, sans-serif; }}
        .nav-tabs {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 2rem;
            border-bottom: 2px solid var(--border);
            padding-bottom: 1rem;
        }}
        .nav-tab {{
            padding: 0.5rem 1rem;
            background: var(--bg-card);
            border: 2px solid var(--border);
            border-radius: 6px;
            cursor: pointer;
            font-family: -apple-system, sans-serif;
            font-size: 0.9rem;
            transition: all 0.2s;
        }}
        .nav-tab:hover, .nav-tab.active {{ background: var(--accent); color: white; border-color: var(--accent); }}
        .search-box {{
            width: 100%;
            padding: 0.75rem 1rem;
            font-size: 1rem;
            border: 2px solid var(--border);
            border-radius: 8px;
            margin-bottom: 1.5rem;
            font-family: Georgia, serif;
        }}
        .search-box:focus {{ outline: none; border-color: var(--accent); }}
        .filter-section {{ margin-bottom: 2rem; }}
        .filter-title {{ font-size: 1.1rem; margin-bottom: 1rem; color: var(--text); }}
        .filter-tags {{ display: flex; flex-wrap: wrap; gap: 0.5rem; }}
        .filter-tag {{
            padding: 0.4rem 0.8rem;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85rem;
            font-family: -apple-system, sans-serif;
            transition: all 0.2s;
        }}
        .filter-tag:hover {{ border-color: var(--accent); color: var(--accent); }}
        .filter-tag .count {{ color: var(--text-muted); margin-left: 0.3rem; }}
        .restaurant-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
        }}
        .restaurant-card {{
            background: var(--bg-card);
            padding: 1.5rem;
            border: 2px solid var(--border);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .restaurant-card:hover {{ border-color: var(--accent); transform: translateY(-2px); box-shadow: 0 4px 12px rgba(217,119,6,0.1); }}
        .restaurant-card h3 {{ font-size: 1.05rem; font-weight: 600; margin-bottom: 0.5rem; font-family: -apple-system, sans-serif; }}
        .restaurant-card .location {{ color: var(--text-muted); font-style: italic; font-size: 0.95rem; }}
        .restaurant-card .meta {{ font-size: 0.85rem; color: var(--text-muted); margin-top: 0.75rem; font-family: -apple-system, sans-serif; }}
        .restaurant-card .rating {{ color: var(--accent); }}
        .status {{ 
            display: inline-block;
            padding: 0.2rem 0.5rem;
            font-size: 0.7rem;
            text-transform: uppercase;
            border-radius: 4px;
            font-family: -apple-system, sans-serif;
        }}
        .status.visited {{ background: #d4edda; color: #155724; }}
        .status.want_to_visit {{ background: #fff3cd; color: #856404; }}
        .cuisine-badge {{ 
            display: inline-block;
            color: white;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            margin-right: 0.5rem;
            font-family: -apple-system, sans-serif;
        }}
        .price-badge {{
            display: inline-block;
            background: #95a5a6;
            color: white;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-family: -apple-system, sans-serif;
        }}
        
        /* Modal */
        .modal-overlay {{
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            overflow-y: auto;
            padding: 2rem;
        }}
        .modal-overlay.active {{ display: block; }}
        .modal {{
            background: white;
            max-width: 700px;
            margin: 0 auto;
            border-radius: 12px;
            padding: 2rem;
            position: relative;
        }}
        .modal-close {{
            position: absolute;
            top: 1rem; right: 1rem;
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--text-muted);
        }}
        .modal-close:hover {{ color: var(--accent); }}
        .modal h2 {{ color: var(--accent); margin-bottom: 0.5rem; font-weight: normal; }}
        .modal .location {{ font-style: italic; color: var(--text-muted); margin-bottom: 1rem; font-size: 1.1rem; }}
        .modal .meta-row {{ margin: 1rem 0; }}
        .modal .label {{ font-weight: 600; color: var(--text-muted); font-size: 0.85rem; text-transform: uppercase; font-family: -apple-system, sans-serif; }}
        .modal .dishes {{ background: var(--bg-card); padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
        .modal .dishes ul {{ margin-left: 1.5rem; }}
        .modal .dishes li {{ margin: 0.3rem 0; }}
        
        .results-count {{ color: var(--text-muted); margin-bottom: 1rem; font-family: -apple-system, sans-serif; }}
        footer {{ margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border); color: var(--text-muted); font-size: 0.85rem; text-align: center; font-family: -apple-system, sans-serif; }}
    </style>
</head>
<body>
    <div class="back-link"><a href="https://pauls-collections.vercel.app">← All Collections</a></div>
    <h1>Paul's Restaurants</h1>
    <p class="subtitle">A personal dining collection</p>
    
    <div class="stats" id="stats"></div>
    
    <div class="nav-tabs">
        <button class="nav-tab active" data-view="all">All Restaurants</button>
        <button class="nav-tab" data-view="cuisines">Cuisines</button>
        <button class="nav-tab" data-view="locations">Locations</button>
        <button class="nav-tab" data-view="price_ranges">Price Range</button>
    </div>
    
    <input type="text" class="search-box" id="search" placeholder="Search restaurants, cuisines, locations...">
    
    <div id="filters" class="filter-section" style="display:none;"></div>
    <div class="results-count" id="results-count"></div>
    <div class="restaurant-grid" id="restaurants"></div>
    
    <div class="modal-overlay" id="modal">
        <div class="modal">
            <button class="modal-close" onclick="closeModal()">&times;</button>
            <div id="modal-content"></div>
        </div>
    </div>
    
    <footer>Generated <span id="timestamp"></span></footer>
    
    <script>
    const CUISINE_COLORS = {cuisine_colors_js};
    let DATA = null;
    let currentView = 'all';
    let currentFilter = null;
    
    function getCuisineColor(cuisine) {{
        if (!cuisine) return '#95a5a6';
        return CUISINE_COLORS[cuisine.toLowerCase()] || '#95a5a6';
    }}
    
    async function init() {{
        const resp = await fetch('data.json');
        DATA = await resp.json();
        document.getElementById('timestamp').textContent = new Date().toLocaleDateString();
        renderStats();
        renderRestaurants(DATA.restaurants);
        setupEventListeners();
    }}
    
    function renderStats() {{
        const s = DATA.stats;
        document.getElementById('stats').innerHTML = `
            <div class="stat"><div class="stat-value">${{s.total}}</div><div class="stat-label">Restaurants</div></div>
            <div class="stat"><div class="stat-value">${{s.visited}}</div><div class="stat-label">Visited</div></div>
            <div class="stat"><div class="stat-value">${{s.wishlist}}</div><div class="stat-label">Wishlist</div></div>
            <div class="stat"><div class="stat-value">${{s.avg_rating || 'N/A'}}</div><div class="stat-label">Avg Rating</div></div>
            <div class="stat"><div class="stat-value">${{s.location_count}}</div><div class="stat-label">Locations</div></div>
        `;
    }}
    
    function renderRestaurants(restaurants) {{
        document.getElementById('results-count').textContent = `${{restaurants.length}} restaurant${{restaurants.length !== 1 ? 's' : ''}}`;
        document.getElementById('restaurants').innerHTML = restaurants.map(r => `
            <div class="restaurant-card" onclick="showRestaurant(${{r.id}})">
                <h3>${{esc(r.name)}}</h3>
                <div class="location">📍 ${{esc(r.location) || 'Unknown'}}</div>
                <div class="meta">
                    ${{r.cuisine ? `<span class="cuisine-badge" style="background:${{getCuisineColor(r.cuisine)}}">${{esc(r.cuisine)}}</span>` : ''}}
                    <span class="status ${{r.status}}">${{r.status === 'visited' ? 'Visited' : 'Wishlist'}}</span>
                    ${{r.rating ? ` <span class="rating">${{'★'.repeat(r.rating)}}</span>` : ''}}
                    ${{r.price ? ` <span class="price-badge">${{esc(r.price)}}</span>` : ''}}
                </div>
            </div>
        `).join('');
    }}
    
    function renderFilters(type) {{
        let items = [];
        if (type === 'cuisines') items = Object.entries(DATA.cuisines).map(([k,v]) => [k, v.length]).sort((a,b) => b[1]-a[1]);
        else if (type === 'locations') items = Object.entries(DATA.locations).map(([k,v]) => [k, v.length]).sort((a,b) => b[1]-a[1]);
        else if (type === 'price_ranges') items = Object.entries(DATA.price_ranges).map(([k,v]) => [k, v.length]).sort((a,b) => a[0].length - b[0].length);
        
        if (items.length === 0) {{
            document.getElementById('filters').style.display = 'none';
            return;
        }}
        
        const title = type.replace('_', ' ').replace(/\\b\\w/g, l => l.toUpperCase());
        document.getElementById('filters').style.display = 'block';
        document.getElementById('filters').innerHTML = `
            <div class="filter-title">${{title}} (${{items.length}})</div>
            <div class="filter-tags">
                ${{items.map(([name, count]) => `<span class="filter-tag" data-filter="${{esc(name)}}">${{esc(name)}}<span class="count">(${{count}})</span></span>`).join('')}}
            </div>
        `;
    }}
    
    function filterRestaurants(type, value) {{
        let ids = [];
        if (type === 'cuisines') ids = DATA.cuisines[value] || [];
        else if (type === 'locations') ids = DATA.locations[value] || [];
        else if (type === 'price_ranges') ids = DATA.price_ranges[value] || [];
        
        const restaurants = DATA.restaurants.filter(r => ids.includes(r.id));
        renderRestaurants(restaurants);
    }}
    
    function searchRestaurants(query) {{
        const q = query.toLowerCase();
        const restaurants = DATA.restaurants.filter(r => 
            r.name.toLowerCase().includes(q) ||
            (r.location && r.location.toLowerCase().includes(q)) ||
            (r.cuisine && r.cuisine.toLowerCase().includes(q))
        );
        renderRestaurants(restaurants);
    }}
    
    function showRestaurant(id) {{
        const r = DATA.restaurants.find(x => x.id === id);
        if (!r) return;
        
        document.getElementById('modal-content').innerHTML = `
            <h2>${{esc(r.name)}}</h2>
            <div class="location">📍 ${{esc(r.location) || 'Unknown'}}</div>
            <div class="meta-row">
                ${{r.cuisine ? `<span class="cuisine-badge" style="background:${{getCuisineColor(r.cuisine)}}">${{esc(r.cuisine)}}</span>` : ''}}
                <span class="status ${{r.status}}">${{r.status === 'visited' ? 'Visited' : 'Wishlist'}}</span>
                ${{r.price ? ` <span class="price-badge">${{esc(r.price)}}</span>` : ''}}
                ${{r.rating ? ` <span class="rating">${{'★'.repeat(r.rating)}}</span> ${{r.rating}}/10` : ''}}
            </div>
            ${{r.date_visited ? `<div class="meta-row"><span class="label">Date Visited:</span> ${{r.date_visited}}</div>` : ''}}
            ${{r.address ? `<div class="meta-row"><span class="label">Address:</span> ${{esc(r.address)}}</div>` : ''}}
            ${{r.phone ? `<div class="meta-row"><span class="label">Phone:</span> ${{esc(r.phone)}}</div>` : ''}}
            ${{r.website ? `<div class="meta-row"><span class="label">Website:</span> <a href="${{esc(r.website)}}" target="_blank">${{esc(r.website)}}</a></div>` : ''}}
            ${{r.hours ? `<div class="meta-row"><span class="label">Hours:</span> ${{esc(r.hours)}}</div>` : ''}}
            ${{r.type ? `<div class="meta-row"><span class="label">Type:</span> ${{esc(r.type)}}</div>` : ''}}
            ${{r.atmosphere ? `<div class="meta-row"><span class="label">Atmosphere:</span> ${{esc(r.atmosphere)}}</div>` : ''}}
            ${{r.dishes.length ? `<div class="meta-row"><span class="label">Signature Dishes</span><div class="dishes"><ul>${{r.dishes.map(d => `<li>${{esc(d)}}</li>`).join('')}}</ul></div></div>` : ''}}
            ${{r.awards.length ? `<div class="meta-row"><span class="label">Awards:</span> ${{esc(r.awards.join(', '))}}</div>` : ''}}
            ${{r.notes ? `<div class="meta-row"><span class="label">Notes:</span> ${{esc(r.notes)}}</div>` : ''}}
            <div class="meta-row" style="color: var(--text-muted); font-size: 0.85rem;">Added: ${{r.date_added}}</div>
        `;
        document.getElementById('modal').classList.add('active');
    }}
    
    function closeModal() {{
        document.getElementById('modal').classList.remove('active');
    }}
    
    function setupEventListeners() {{
        document.querySelectorAll('.nav-tab').forEach(tab => {{
            tab.addEventListener('click', () => {{
                document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentView = tab.dataset.view;
                currentFilter = null;
                document.getElementById('search').value = '';
                
                if (currentView === 'all') {{
                    document.getElementById('filters').style.display = 'none';
                    renderRestaurants(DATA.restaurants);
                }} else {{
                    renderFilters(currentView);
                    renderRestaurants(DATA.restaurants);
                }}
            }});
        }});
        
        document.getElementById('filters').addEventListener('click', e => {{
            if (e.target.classList.contains('filter-tag')) {{
                currentFilter = e.target.dataset.filter;
                filterRestaurants(currentView, currentFilter);
            }}
        }});
        
        document.getElementById('search').addEventListener('input', e => {{
            if (e.target.value) searchRestaurants(e.target.value);
            else if (currentFilter) filterRestaurants(currentView, currentFilter);
            else renderRestaurants(DATA.restaurants);
        }});
        
        document.getElementById('modal').addEventListener('click', e => {{
            if (e.target.id === 'modal') closeModal();
        }});
        
        document.addEventListener('keydown', e => {{
            if (e.key === 'Escape') closeModal();
        }});
    }}
    
    function esc(s) {{ 
        if (!s) return '';
        return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); 
    }}
    
    init();
    </script>
</body>
</html>'''


def generate_site():
    print("Generating restaurants SPA...")
    
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    restaurants = get_all_restaurants(DB_PATH)
    print(f"Found {len(restaurants)} restaurants")
    
    data = generate_data_json(restaurants)
    with open(os.path.join(OUTPUT_DIR, 'data.json'), 'w') as f:
        json.dump(data, f)
    print("Generated data.json")
    
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w') as f:
        f.write(generate_html())
    print("Generated index.html")
    
    print(f"\n✓ Site generated in '{OUTPUT_DIR}/' (2 files)")


if __name__ == "__main__":
    generate_site()
