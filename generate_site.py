#!/usr/bin/env python3
"""
Generate a static website from the restaurants database.
Only regenerates if the database has changed since last run.
"""

import os
import sys
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from html import escape

# Configuration
DB_PATH = "restaurants.db"
OUTPUT_DIR = "site"
STATE_FILE = ".site_state.json"

# Cuisine colors for badges
CUISINE_COLORS = {
    'italian': '#e74c3c',
    'japanese': '#e91e63',
    'chinese': '#f39c12',
    'mexican': '#e67e22',
    'indian': '#9b59b6',
    'thai': '#16a085',
    'french': '#3498db',
    'american': '#34495e',
    'mediterranean': '#27ae60',
    'korean': '#c0392b',
    'vietnamese': '#2ecc71',
    'steakhouse': '#8e44ad',
    'seafood': '#1abc9c',
    'bbq': '#d35400',
    'pizza': '#e74c3c',
    'sushi': '#e91e63',
    'fusion': '#95a5a6'
}


def get_db_hash(db_path):
    """Get hash of database file to detect changes."""
    with open(db_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def load_state():
    """Load previous generation state."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_state(state):
    """Save generation state."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


def parse_json_field(value):
    """Parse a JSON field, returning empty list if invalid."""
    if not value:
        return []
    try:
        result = json.loads(value)
        if isinstance(result, list):
            return result
        return [result]
    except:
        return [value] if value else []


def slugify(text):
    """Convert text to URL-safe slug."""
    if not text:
        return "unknown"
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")[:50]


def get_cuisine_color(cuisine):
    """Get color for cuisine badge."""
    if not cuisine:
        return '#95a5a6'
    return CUISINE_COLORS.get(cuisine.lower(), '#95a5a6')


def get_all_restaurants(db_path):
    """Fetch all restaurants from database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM restaurants ORDER BY restaurant_name")
    restaurants = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Parse JSON fields
    for restaurant in restaurants:
        restaurant['signature_dishes_list'] = parse_json_field(restaurant['signature_dishes'])
        restaurant['dietary_accommodations_list'] = parse_json_field(restaurant['dietary_accommodations'])
        restaurant['awards_list'] = parse_json_field(restaurant['awards'])
        restaurant['similar_restaurants_list'] = parse_json_field(restaurant['similar_restaurants'])
        restaurant['llm_categories_list'] = parse_json_field(restaurant['llm_categories'])
        restaurant['user_categories_list'] = parse_json_field(restaurant['user_categories'])

    return restaurants


# HTML Templates
def html_header(title, breadcrumbs=None, home_link="index.html"):
    """Generate HTML header."""
    bc_html = ""
    if breadcrumbs:
        bc_parts = [f'<a href="{home_link}">Home</a>']
        for name, link in breadcrumbs:
            if link:
                bc_parts.append(f'<a href="{link}">{escape(name)}</a>')
            else:
                bc_parts.append(escape(name))
        bc_html = f'<nav class="breadcrumbs">{" → ".join(bc_parts)}</nav>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)} - Restaurant Tracker</title>
    <style>
        :root {{
            --bg: #faf8f5;
            --bg-card: #ffffff;
            --text: #2c2c2c;
            --text-muted: #666666;
            --accent: #e74c3c;
            --accent-hover: #c0392b;
            --link: #3498db;
            --link-hover: #2980b9;
            --border: #d4cfc7;
            --border-light: #e8e4dd;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.7;
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }}
        a {{ color: var(--link); text-decoration: none; }}
        a:hover {{ color: var(--link-hover); text-decoration: underline; }}
        h1 {{
            color: var(--text);
            margin-bottom: 1.5rem;
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            border-bottom: 3px solid var(--accent);
            padding-bottom: 0.75rem;
        }}
        h2 {{
            color: var(--text);
            margin: 2rem 0 1rem;
            font-size: 1.5rem;
            font-weight: 600;
            border-bottom: 2px solid var(--border);
            padding-bottom: 0.5rem;
        }}
        h3 {{ color: var(--text); margin: 1.25rem 0 0.75rem; font-size: 1.2rem; font-weight: 600; }}
        .breadcrumbs {{ margin-bottom: 2rem; color: var(--text-muted); font-size: 0.9rem; }}
        .breadcrumbs a {{ color: var(--link); }}
        .card {{
            background: var(--bg-card);
            padding: 2rem;
            margin-bottom: 1.5rem;
            border: 1px solid var(--border-light);
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        }}
        .restaurant-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
        }}
        .restaurant-card {{
            background: var(--bg-card);
            padding: 1.5rem;
            border: 1px solid var(--border-light);
            border-radius: 8px;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .restaurant-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(231,76,60,0.1); }}
        .restaurant-card h3 {{ margin: 0 0 0.5rem; font-size: 1.1rem; font-weight: 700; }}
        .restaurant-card h3 a {{ text-decoration: none; color: var(--text); }}
        .restaurant-card h3 a:hover {{ color: var(--accent); }}
        .restaurant-card .location {{ color: var(--text-muted); font-size: 0.95rem; margin-bottom: 0.75rem; }}
        .restaurant-card .meta {{ font-size: 0.9rem; color: var(--text-muted); margin-top: 0.75rem; }}
        .rating {{ color: var(--accent); font-weight: 600; }}
        .status {{
            display: inline-block;
            padding: 0.2rem 0.6rem;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
            border-radius: 4px;
        }}
        .status.visited {{ background: #d4edda; color: #155724; }}
        .status.want_to_visit {{ background: #fff3cd; color: #856404; }}
        .cuisine-badge {{
            display: inline-block;
            color: white;
            padding: 0.2rem 0.6rem;
            font-size: 0.75rem;
            margin-right: 0.5rem;
            border-radius: 4px;
            font-weight: 500;
            text-transform: capitalize;
        }}
        .price-badge {{
            display: inline-block;
            background: #95a5a6;
            color: white;
            padding: 0.2rem 0.5rem;
            font-size: 0.75rem;
            border-radius: 4px;
            font-weight: 600;
            margin-left: 0.5rem;
        }}
        .tag {{
            display: inline-block;
            background: var(--bg);
            color: var(--text-muted);
            padding: 0.3rem 0.8rem;
            font-size: 0.85rem;
            margin: 0.25rem;
            border: 1px solid var(--border);
            border-radius: 4px;
            text-decoration: none;
        }}
        .tag:hover {{ background: var(--accent); color: white; border-color: var(--accent); text-decoration: none; }}
        .nav-sections {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }}
        .nav-section {{
            background: var(--bg-card);
            padding: 1.5rem;
            border: 1px solid var(--border-light);
            border-radius: 8px;
        }}
        .nav-section h3 {{ margin-bottom: 1rem; color: var(--accent); font-size: 1rem; font-weight: 700; }}
        .nav-section ul {{ list-style: none; }}
        .nav-section li {{ margin: 0.5rem 0; font-size: 0.95rem; }}
        .nav-section a {{ text-decoration: none; }}
        .nav-section a:hover {{ text-decoration: underline; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }}
        .stat {{
            background: var(--bg-card);
            padding: 1.5rem;
            text-align: center;
            border: 1px solid var(--border-light);
            border-radius: 8px;
        }}
        .stat-value {{ font-size: 2.5rem; color: var(--accent); font-weight: 700; }}
        .stat-label {{ font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.5rem; }}
        .timeline-year {{
            margin-bottom: 3rem;
            padding-bottom: 2rem;
            border-bottom: 2px solid var(--border-light);
        }}
        .timeline-year h2 {{
            color: var(--accent);
            font-size: 2rem;
            margin-bottom: 1.5rem;
            border: none;
        }}
        .timeline-month {{ margin-bottom: 2rem; }}
        .timeline-month h3 {{
            color: var(--text-muted);
            font-size: 1.2rem;
            margin-bottom: 1rem;
            font-weight: 600;
        }}
        dl {{ margin: 1.25rem 0; }}
        dt {{ color: var(--text-muted); font-size: 0.85rem; margin-top: 1rem; text-transform: uppercase; letter-spacing: 0.03em; font-weight: 600; }}
        dd {{ margin-left: 0; margin-top: 0.5rem; }}
        ul.dish-list {{ margin-left: 1.5rem; line-height: 1.8; }}
        ul.dish-list li {{ margin: 0.25rem 0; }}
    </style>
</head>
<body>
{bc_html}
<h1>{escape(title)}</h1>
'''


def html_footer():
    """Generate HTML footer."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f'''
<footer style="margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border); color: var(--text-muted); font-size: 0.85rem; text-align: center;">
    Generated on {timestamp}
</footer>
</body>
</html>
'''


def generate_restaurant_page(restaurant, output_dir):
    """Generate individual restaurant page."""
    slug = f"restaurant-{restaurant['id']}-{slugify(restaurant['restaurant_name'])}"
    filepath = os.path.join(output_dir, "restaurants", f"{slug}.html")

    html = html_header(restaurant['restaurant_name'], [("Restaurants", "../restaurants.html"), (restaurant['restaurant_name'], None)], home_link="../index.html")

    html += '<div class="card">'
    html += f'<p class="location" style="font-size: 1.1rem; color: var(--text-muted); margin-bottom: 1rem;">📍 {escape(restaurant["location"])}</p>'

    # Cuisine, status and rating
    html += '<p style="margin: 1rem 0;">'
    if restaurant['cuisine']:
        cuisine_color = get_cuisine_color(restaurant['cuisine'])
        html += f'<span class="cuisine-badge" style="background:{cuisine_color};">{escape(restaurant["cuisine"])}</span>'

    status_class = restaurant['visit_status']
    status_text = "Visited" if status_class == "visited" else "Want to Visit"
    html += f' <span class="status {status_class}">{status_text}</span>'

    if restaurant['price_range']:
        html += f' <span class="price-badge">{escape(restaurant["price_range"])}</span>'

    if restaurant['rating']:
        html += f' <span class="rating">{"★" * restaurant["rating"]}{"☆" * (10 - restaurant["rating"])}</span> {restaurant["rating"]}/10'
    html += '</p>'

    html += '<dl>'

    if restaurant['date_visited']:
        html += f'<dt>Date Visited</dt><dd>{escape(restaurant["date_visited"])}</dd>'

    if restaurant['full_address']:
        html += f'<dt>Address</dt><dd>{escape(restaurant["full_address"])}</dd>'

    if restaurant['phone_number']:
        html += f'<dt>Phone</dt><dd>{escape(restaurant["phone_number"])}</dd>'

    if restaurant['website']:
        html += f'<dt>Website</dt><dd><a href="{escape(restaurant["website"])}" target="_blank">{escape(restaurant["website"])}</a></dd>'

    if restaurant['hours_summary']:
        html += f'<dt>Hours</dt><dd>{escape(restaurant["hours_summary"])}</dd>'

    if restaurant['restaurant_type']:
        html += f'<dt>Type</dt><dd>{escape(restaurant["restaurant_type"])}</dd>'

    if restaurant['chef_owner']:
        html += f'<dt>Chef/Owner</dt><dd>{escape(restaurant["chef_owner"])}</dd>'

    if restaurant['established_year']:
        html += f'<dt>Established</dt><dd>{restaurant["established_year"]}</dd>'

    if restaurant['reservations_info']:
        html += f'<dt>Reservations</dt><dd>{escape(restaurant["reservations_info"])}</dd>'

    if restaurant['dress_code']:
        html += f'<dt>Dress Code</dt><dd>{escape(restaurant["dress_code"])}</dd>'

    html += '</dl>'

    if restaurant['cuisine_details']:
        html += f'<h2>Cuisine</h2><p>{escape(restaurant["cuisine_details"])}</p>'

    if restaurant['signature_dishes_list']:
        html += '<h2>Signature Dishes</h2><ul class="dish-list">'
        for dish in restaurant['signature_dishes_list']:
            html += f'<li>{escape(dish)}</li>'
        html += '</ul>'

    if restaurant['dietary_accommodations_list']:
        html += '<h2>Dietary Options</h2><p>'
        html += ", ".join(escape(d) for d in restaurant['dietary_accommodations_list'])
        html += '</p>'

    if restaurant['atmosphere']:
        html += f'<h2>Atmosphere</h2><p>{escape(restaurant["atmosphere"])}</p>'

    if restaurant['reviews_summary']:
        html += f'<h2>Reviews</h2><p>{escape(restaurant["reviews_summary"])}</p>'

    if restaurant['awards_list']:
        html += '<h2>Awards & Recognition</h2><ul>'
        for award in restaurant['awards_list']:
            html += f'<li>{escape(award)}</li>'
        html += '</ul>'

    if restaurant['similar_restaurants_list']:
        html += '<h2>Similar Restaurants</h2><p>'
        html += ", ".join(escape(r) for r in restaurant['similar_restaurants_list'])
        html += '</p>'

    all_categories = restaurant['llm_categories_list'] + restaurant['user_categories_list']
    if all_categories:
        html += '<h2>Categories</h2><p>'
        for cat in all_categories:
            cat_slug = slugify(cat)
            html += f'<a href="../categories/{cat_slug}.html" class="tag">{escape(cat)}</a>'
        html += '</p>'

    if restaurant['personal_notes']:
        html += f'<h2>Personal Notes</h2><p>{escape(restaurant["personal_notes"])}</p>'

    html += f'<p style="margin-top: 1.5rem; font-size: 0.85rem; color: var(--text-muted);">Added: {restaurant["date_added"][:10]}</p>'

    html += '</div>'
    html += html_footer()

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(html)

    return slug


def generate_list_page(title, items, output_path, breadcrumbs, intro=""):
    """Generate a list page (cuisines, locations, categories index)."""
    html = html_header(title, breadcrumbs)

    if intro:
        html += f'<p style="margin-bottom: 1.5rem; color: var(--text-muted);">{intro}</p>'

    html += '<ul style="list-style: none; columns: 2; column-gap: 2rem;">'
    for name, link, count in sorted(items, key=lambda x: x[0].lower()):
        html += f'<li style="margin: 0.5rem 0;"><a href="{link}">{escape(name)}</a> <span style="color: var(--text-muted);">({count})</span></li>'
    html += '</ul>'

    html += html_footer()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)


def generate_group_page(title, restaurants, output_path, breadcrumbs, home_link="index.html"):
    """Generate a page showing a group of restaurants."""
    html = html_header(title, breadcrumbs, home_link=home_link)

    visited_count = sum(1 for r in restaurants if r['visit_status'] == 'visited')
    wishlist_count = len(restaurants) - visited_count
    rated_restaurants = [r for r in restaurants if r['rating']]
    avg_rating = sum(r['rating'] for r in rated_restaurants) / len(rated_restaurants) if rated_restaurants else 0

    html += f'''<div class="stats">
        <div class="stat"><div class="stat-value">{len(restaurants)}</div><div class="stat-label">Total</div></div>
        <div class="stat"><div class="stat-value">{visited_count}</div><div class="stat-label">Visited</div></div>
        <div class="stat"><div class="stat-value">{wishlist_count}</div><div class="stat-label">Wishlist</div></div>
        <div class="stat"><div class="stat-value">{avg_rating:.1f}</div><div class="stat-label">Avg Rating</div></div>
    </div>'''

    html += '<div class="restaurant-grid">'
    for restaurant in sorted(restaurants, key=lambda r: r['restaurant_name'].lower()):
        slug = f"restaurant-{restaurant['id']}-{slugify(restaurant['restaurant_name'])}"

        html += f'''<div class="restaurant-card">
            <h3><a href="../restaurants/{slug}.html">{escape(restaurant['restaurant_name'])}</a></h3>
            <p class="location">📍 {escape(restaurant['location'])}</p>
            <p class="meta">'''

        if restaurant['cuisine']:
            cuisine_color = get_cuisine_color(restaurant['cuisine'])
            html += f'<span class="cuisine-badge" style="background:{cuisine_color};">{escape(restaurant["cuisine"])}</span>'

        if restaurant['rating']:
            html += f' <span class="rating">{"★" * restaurant["rating"]}</span>'

        if restaurant['price_range']:
            html += f' <span class="price-badge">{escape(restaurant["price_range"])}</span>'

        html += '</p></div>'
    html += '</div>'

    html += html_footer()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)


def generate_timeline(restaurants, output_dir):
    """Generate timeline view grouped by year and month."""
    html = html_header("Timeline", [("Timeline", None)])

    # Separate visited restaurants with dates from wishlist
    visited_restaurants = [r for r in restaurants if r['visit_status'] == 'visited' and r['date_visited']]
    wishlist_restaurants = [r for r in restaurants if r['visit_status'] == 'want_to_visit']

    # Group by year and month
    timeline = defaultdict(lambda: defaultdict(list))
    for restaurant in visited_restaurants:
        try:
            date = datetime.fromisoformat(restaurant['date_visited'])
            year = date.year
            month = date.strftime('%B')  # Full month name
            timeline[year][month].append(restaurant)
        except:
            pass

    # Wishlist section
    if wishlist_restaurants:
        html += '<div class="timeline-year">'
        html += '<h2>📌 Want to Visit</h2>'
        html += '<div class="restaurant-grid">'
        for restaurant in sorted(wishlist_restaurants, key=lambda r: r['restaurant_name'].lower()):
            slug = f"restaurant-{restaurant['id']}-{slugify(restaurant['restaurant_name'])}"
            cuisine_color = get_cuisine_color(restaurant['cuisine'])
            html += f'''<div class="restaurant-card">
                <h3><a href="restaurants/{slug}.html">{escape(restaurant['restaurant_name'])}</a></h3>
                <p class="location">📍 {escape(restaurant['location'])}</p>
                <p class="meta"><span class="cuisine-badge" style="background:{cuisine_color};">{escape(restaurant['cuisine'])}</span></p>
            </div>'''
        html += '</div></div>'

    # Year sections (most recent first)
    for year in sorted(timeline.keys(), reverse=True):
        html += f'<div class="timeline-year"><h2>{year}</h2>'

        # Month sections within year
        month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']

        for month in month_order:
            if month not in timeline[year]:
                continue

            month_restaurants = timeline[year][month]
            html += f'<div class="timeline-month"><h3>{month}</h3>'
            html += '<div class="restaurant-grid">'

            for restaurant in sorted(month_restaurants, key=lambda r: r['date_visited'], reverse=True):
                slug = f"restaurant-{restaurant['id']}-{slugify(restaurant['restaurant_name'])}"
                cuisine_color = get_cuisine_color(restaurant['cuisine'])
                html += f'''<div class="restaurant-card">
                    <h3><a href="restaurants/{slug}.html">{escape(restaurant['restaurant_name'])}</a></h3>
                    <p class="location">📍 {escape(restaurant['location'])}</p>'''

                if restaurant['date_visited']:
                    html += f'<p class="location">📅 {escape(restaurant["date_visited"])}</p>'

                html += '<p class="meta">'
                html += f'<span class="cuisine-badge" style="background:{cuisine_color};">{escape(restaurant["cuisine"])}</span>'
                if restaurant['rating']:
                    html += f' <span class="rating">{"★" * restaurant["rating"]}</span> {restaurant["rating"]}/10'
                html += '</p></div>'

            html += '</div></div>'

        html += '</div>'

    html += html_footer()

    with open(os.path.join(output_dir, "timeline.html"), 'w') as f:
        f.write(html)


def generate_restaurants_index(restaurants, output_dir):
    """Generate all restaurants index page."""
    html = html_header("All Restaurants", [("All Restaurants", None)])

    visited_count = sum(1 for r in restaurants if r['visit_status'] == 'visited')
    wishlist_count = len(restaurants) - visited_count

    html += f'''<div class="stats">
        <div class="stat"><div class="stat-value">{len(restaurants)}</div><div class="stat-label">Total</div></div>
        <div class="stat"><div class="stat-value">{visited_count}</div><div class="stat-label">Visited</div></div>
        <div class="stat"><div class="stat-value">{wishlist_count}</div><div class="stat-label">Wishlist</div></div>
    </div>'''

    html += '<div class="restaurant-grid">'
    for restaurant in sorted(restaurants, key=lambda r: r['restaurant_name'].lower()):
        slug = f"restaurant-{restaurant['id']}-{slugify(restaurant['restaurant_name'])}"
        cuisine_color = get_cuisine_color(restaurant['cuisine'])

        html += f'''<div class="restaurant-card">
            <h3><a href="restaurants/{slug}.html">{escape(restaurant['restaurant_name'])}</a></h3>
            <p class="location">📍 {escape(restaurant['location'])}</p>
            <p class="meta">'''

        html += f'<span class="cuisine-badge" style="background:{cuisine_color};">{escape(restaurant["cuisine"])}</span>'

        status_class = restaurant['visit_status']
        status_text = "Visited" if status_class == "visited" else "Wishlist"
        html += f' <span class="status {status_class}">{status_text}</span>'

        if restaurant['rating']:
            html += f' <span class="rating">{"★" * restaurant["rating"]}</span>'

        html += '</p></div>'
    html += '</div>'

    html += html_footer()

    with open(os.path.join(output_dir, "restaurants.html"), 'w') as f:
        f.write(html)


def generate_price_ranges_page(restaurants, price_ranges_index, output_dir):
    """Generate price ranges overview page."""
    html = html_header("By Price Range", [("Price Ranges", None)])

    html += '<p style="margin-bottom: 1.5rem; color: var(--text-muted);">Browse restaurants by price range</p>'

    for price_range in ['$', '$$', '$$$', '$$$$']:
        if price_range not in price_ranges_index:
            continue

        count = len(price_ranges_index[price_range])
        html += f'<h2 style="margin-top: 2rem;">{price_range} ({count} restaurants)</h2>'
        html += '<div class="restaurant-grid">'

        for restaurant in sorted(price_ranges_index[price_range], key=lambda r: r['restaurant_name'].lower()):
            slug = f"restaurant-{restaurant['id']}-{slugify(restaurant['restaurant_name'])}"
            cuisine_color = get_cuisine_color(restaurant['cuisine'])

            html += f'''<div class="restaurant-card">
                <h3><a href="restaurants/{slug}.html">{escape(restaurant['restaurant_name'])}</a></h3>
                <p class="location">📍 {escape(restaurant['location'])}</p>
                <p class="meta">'''

            html += f'<span class="cuisine-badge" style="background:{cuisine_color};">{escape(restaurant["cuisine"])}</span>'

            if restaurant['rating']:
                html += f' <span class="rating">{"★" * restaurant["rating"]}</span>'

            html += '</p></div>'

        html += '</div>'

    html += html_footer()

    with open(os.path.join(output_dir, "price-ranges.html"), 'w') as f:
        f.write(html)


def generate_index(restaurants, cuisines_count, locations_count, categories_count, output_dir):
    """Generate main index page with statistics dashboard."""
    html = html_header("Restaurant Tracker")

    visited_restaurants = [r for r in restaurants if r['visit_status'] == 'visited']
    wishlist_restaurants = [r for r in restaurants if r['visit_status'] == 'want_to_visit']
    rated_restaurants = [r for r in visited_restaurants if r['rating']]
    avg_rating = sum(r['rating'] for r in rated_restaurants) / len(rated_restaurants) if rated_restaurants else 0

    # Get most common cuisine
    cuisine_counts = defaultdict(int)
    for r in restaurants:
        if r['cuisine']:
            cuisine_counts[r['cuisine']] += 1
    most_common_cuisine = max(cuisine_counts.items(), key=lambda x: x[1])[0] if cuisine_counts else "N/A"

    # Get unique locations count
    unique_locations = len(set(r['location'] for r in restaurants if r['location']))

    html += f'''<div class="stats">
        <div class="stat"><div class="stat-value">{len(restaurants)}</div><div class="stat-label">Total Restaurants</div></div>
        <div class="stat"><div class="stat-value">{len(visited_restaurants)}</div><div class="stat-label">Visited</div></div>
        <div class="stat"><div class="stat-value">{len(wishlist_restaurants)}</div><div class="stat-label">Wishlist</div></div>
        <div class="stat"><div class="stat-value">{avg_rating:.1f}</div><div class="stat-label">Avg Rating</div></div>
        <div class="stat"><div class="stat-value">{unique_locations}</div><div class="stat-label">Locations</div></div>
        <div class="stat"><div class="stat-value">{escape(most_common_cuisine)}</div><div class="stat-label">Top Cuisine</div></div>
    </div>'''

    html += '<div class="nav-sections">'

    html += f'''<div class="nav-section">
        <h3>🍽️ Browse</h3>
        <ul>
            <li><a href="restaurants.html">All Restaurants ({len(restaurants)})</a></li>
            <li><a href="timeline.html">Timeline View</a></li>
            <li><a href="cuisines.html">By Cuisine ({cuisines_count})</a></li>
            <li><a href="locations.html">By Location ({locations_count})</a></li>
            <li><a href="categories.html">By Category ({categories_count})</a></li>
            <li><a href="price-ranges.html">By Price Range</a></li>
        </ul>
    </div>'''

    # Recently added
    recent = sorted(restaurants, key=lambda r: r['date_added'], reverse=True)[:5]
    html += '<div class="nav-section"><h3>🕐 Recently Added</h3><ul>'
    for restaurant in recent:
        slug = f"restaurant-{restaurant['id']}-{slugify(restaurant['restaurant_name'])}"
        html += f'<li><a href="restaurants/{slug}.html">{escape(restaurant["restaurant_name"])}</a></li>'
    html += '</ul></div>'

    # Top rated
    top_rated = sorted(rated_restaurants, key=lambda r: r['rating'], reverse=True)[:5]
    if top_rated:
        html += '<div class="nav-section"><h3>⭐ Top Rated</h3><ul>'
        for restaurant in top_rated:
            slug = f"restaurant-{restaurant['id']}-{slugify(restaurant['restaurant_name'])}"
            html += f'<li><a href="restaurants/{slug}.html">{escape(restaurant["restaurant_name"])}</a> ({restaurant["rating"]}/10)</li>'
        html += '</ul></div>'

    # Wishlist
    if wishlist_restaurants:
        html += '<div class="nav-section"><h3>📌 Want to Visit</h3><ul>'
        for restaurant in wishlist_restaurants[:5]:
            slug = f"restaurant-{restaurant['id']}-{slugify(restaurant['restaurant_name'])}"
            html += f'<li><a href="restaurants/{slug}.html">{escape(restaurant["restaurant_name"])}</a></li>'
        html += '</ul></div>'

    html += '</div>'
    html += html_footer()

    with open(os.path.join(output_dir, "index.html"), 'w') as f:
        f.write(html)


def generate_site(force=False):
    """Generate the complete static site."""
    # Check if regeneration needed
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return False

    current_hash = get_db_hash(DB_PATH)
    state = load_state()

    if not force and state.get('db_hash') == current_hash:
        print("Database unchanged. Use --force to regenerate anyway.")
        return True

    print("Generating site...")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "restaurants"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "cuisines"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "locations"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "categories"), exist_ok=True)

    # Get all restaurants
    restaurants = get_all_restaurants(DB_PATH)
    print(f"Found {len(restaurants)} restaurants")

    # Generate individual restaurant pages
    for restaurant in restaurants:
        generate_restaurant_page(restaurant, OUTPUT_DIR)
    print(f"Generated {len(restaurants)} restaurant pages")

    # Build indexes
    cuisines_index = defaultdict(list)
    locations_index = defaultdict(list)
    categories_index = defaultdict(list)
    price_ranges_index = defaultdict(list)

    for restaurant in restaurants:
        if restaurant['cuisine']:
            cuisines_index[restaurant['cuisine']].append(restaurant)
        if restaurant['location']:
            locations_index[restaurant['location']].append(restaurant)
        if restaurant['price_range']:
            price_ranges_index[restaurant['price_range']].append(restaurant)
        for cat in restaurant['llm_categories_list'] + restaurant['user_categories_list']:
            if cat:
                categories_index[cat].append(restaurant)

    # Generate cuisine pages
    cuisine_items = []
    for cuisine, cuisine_restaurants in cuisines_index.items():
        slug = slugify(cuisine)
        filepath = os.path.join(OUTPUT_DIR, "cuisines", f"{slug}.html")
        generate_group_page(cuisine, cuisine_restaurants, filepath, [("Cuisines", "../cuisines.html"), (cuisine, None)], home_link="../index.html")
        cuisine_items.append((cuisine, f"cuisines/{slug}.html", len(cuisine_restaurants)))

    generate_list_page("Cuisines", cuisine_items,
                      os.path.join(OUTPUT_DIR, "cuisines.html"),
                      [("Cuisines", None)],
                      f"{len(cuisines_index)} cuisines")
    print(f"Generated {len(cuisines_index)} cuisine pages")

    # Generate location pages
    location_items = []
    for location, location_restaurants in locations_index.items():
        slug = slugify(location)
        filepath = os.path.join(OUTPUT_DIR, "locations", f"{slug}.html")
        generate_group_page(location, location_restaurants, filepath, [("Locations", "../locations.html"), (location, None)], home_link="../index.html")
        location_items.append((location, f"locations/{slug}.html", len(location_restaurants)))

    generate_list_page("Locations", location_items,
                      os.path.join(OUTPUT_DIR, "locations.html"),
                      [("Locations", None)],
                      f"{len(locations_index)} locations")
    print(f"Generated {len(locations_index)} location pages")

    # Generate category pages
    category_items = []
    for cat, cat_restaurants in categories_index.items():
        slug = slugify(cat)
        filepath = os.path.join(OUTPUT_DIR, "categories", f"{slug}.html")
        generate_group_page(cat, cat_restaurants, filepath, [("Categories", "../categories.html"), (cat, None)], home_link="../index.html")
        category_items.append((cat, f"categories/{slug}.html", len(cat_restaurants)))

    generate_list_page("Categories", category_items,
                      os.path.join(OUTPUT_DIR, "categories.html"),
                      [("Categories", None)],
                      f"{len(categories_index)} categories")
    print(f"Generated {len(categories_index)} category pages")

    # Generate price ranges page
    generate_price_ranges_page(restaurants, price_ranges_index, OUTPUT_DIR)
    print("Generated price ranges page")

    # Generate timeline view
    generate_timeline(restaurants, OUTPUT_DIR)
    print("Generated timeline view")

    # Generate all restaurants page
    generate_restaurants_index(restaurants, OUTPUT_DIR)

    # Generate main index
    generate_index(restaurants, len(cuisines_index), len(locations_index), len(categories_index), OUTPUT_DIR)

    # Save state
    save_state({'db_hash': current_hash, 'generated_at': datetime.now().isoformat()})

    print(f"\n✓ Site generated in '{OUTPUT_DIR}/'")
    print(f"  Open {OUTPUT_DIR}/index.html to view")

    return True


if __name__ == "__main__":
    force = "--force" in sys.argv
    success = generate_site(force=force)
    sys.exit(0 if success else 1)
