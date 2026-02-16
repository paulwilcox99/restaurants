# Restaurant Tracker

A powerful personal restaurant tracking system with AI-powered metadata enrichment. Track restaurants you've visited or want to visit, with comprehensive details including ratings, cuisine types, signature dishes, atmosphere, and more.

## Features

### Core Functionality
- **Dual Entry Methods**: Extract restaurant info from menu/receipt photos OR manually add restaurants
- **Visit Tracking**: Track specific visit dates, allowing multiple visits to the same restaurant
- **Comprehensive Ratings**: Rate restaurants on a 1-10 scale with personal notes
- **Smart Organization**: Browse by cuisine type, location, price range, or custom categories

### AI-Powered Enrichment
Automatically fetch detailed metadata using OpenAI, Anthropic, or Google AI:
- Contact information (address, phone, website, hours)
- Signature dishes and dietary accommodations
- Atmosphere, dress code, and reservations info
- Awards, reviews summary, and similar restaurants
- Restaurant type, chef/owner, and establishment year
- Intelligent category matching

### Static Website Generation
Generate a beautiful static website from your database:
- **Timeline View**: Visits organized by year and month
- **Cuisine Pages**: Color-coded cuisine badges and filtering
- **Location Pages**: Browse restaurants by city/neighborhood
- **Statistics Dashboard**: Track visit counts, ratings, and trends
- **MD5 Change Detection**: Only regenerates when database changes

## Installation

### Prerequisites
- Python 3.8 or higher
- API key for one of: OpenAI, Anthropic, or Google

### Setup

1. Clone or download this repository:
```bash
cd ~/code/restaurants
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create configuration file:
```bash
cp config.yaml.example config.yaml
```

4. Edit `config.yaml` and add your API key:
```yaml
llm:
  provider: "openai"  # or "anthropic" or "google"
  openai_api_key: "your-key-here"
```

5. Create directories for images:
```bash
mkdir restaurants_visited restaurants_wishlist
```

## Quick Start

See [QUICKSTART.md](QUICKSTART.md) for a 5-minute getting started guide.

## Usage

### Scanning Images

Extract restaurant information from menu or receipt photos:

```bash
# Scan all directories
python restaurant_tracker.py scan

# Scan only visited restaurants
python restaurant_tracker.py scan --directory visited

# Scan only wishlist
python restaurant_tracker.py scan --directory wishlist
```

The CLI will:
1. Extract restaurant name and location from each image
2. Prompt you for cuisine type
3. For visited restaurants, ask for date visited and rating
4. Optionally add personal notes
5. Automatically enrich with AI metadata (if enabled)

### Manually Adding Restaurants

Add a restaurant directly without an image:

```bash
# Add a visited restaurant
python restaurant_tracker.py add \
  --name "Joe's Pizza" \
  --location "NYC" \
  --cuisine "Pizza" \
  --visited \
  --date-visited "2024-03-15" \
  --rating 9 \
  --notes "Best margherita in Manhattan"

# Add to wishlist
python restaurant_tracker.py add \
  --name "The French Laundry" \
  --location "Yountville, CA" \
  --cuisine "French" \
  --wishlist
```

### Listing & Searching

```bash
# List all restaurants
python restaurant_tracker.py list

# List by cuisine
python restaurant_tracker.py list --cuisine Italian

# List only visited restaurants
python restaurant_tracker.py list --visited

# Search for restaurants
python restaurant_tracker.py search --name "Pizza" --location "NYC"

# Search by rating
python restaurant_tracker.py search --rating-min 8

# Search by cuisine and price range
python restaurant_tracker.py search --cuisine Japanese --price-range "$$$$"
```

### Viewing Details

```bash
# Show detailed information by ID
python restaurant_tracker.py show 1

# Show by name
python restaurant_tracker.py show "Joe's Pizza"
```

### Updating Restaurants

```bash
# Update rating and notes
python restaurant_tracker.py update 1 --rating 10 --notes "Even better on second visit!"

# Mark as visited with date
python restaurant_tracker.py update 1 --visited --date-visited "2024-03-20"

# Change cuisine
python restaurant_tracker.py update 1 --cuisine "Neapolitan Pizza"
```

### AI Enrichment

```bash
# Enrich with missing fields only (default)
python restaurant_tracker.py enrich 1

# Re-fetch all metadata
python restaurant_tracker.py enrich 1 --force

# Enrich by name
python restaurant_tracker.py enrich "Joe's Pizza"
```

### Exporting Data

```bash
# Export to JSON
python restaurant_tracker.py export --format json --output restaurants.json

# Export to CSV
python restaurant_tracker.py export --format csv --output restaurants.csv
```

### Managing Categories

```bash
# List predefined user categories
python restaurant_tracker.py categories list

# Add a new category
python restaurant_tracker.py categories add "romantic"

# Remove a category
python restaurant_tracker.py categories remove "quick bite"
```

### Generating Website

```bash
# Generate static website (only if database changed)
python generate_site.py

# Force regeneration
python generate_site.py --force
```

Open `site/index.html` in your browser to view the generated website.

## Database Schema

### Restaurants Table

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Primary key |
| restaurant_name | TEXT | Restaurant name |
| location | TEXT | City/neighborhood |
| cuisine | TEXT | Primary cuisine type |
| date_added | TEXT | When added to database (ISO format) |
| date_visited | TEXT | When visited (NULL for wishlist) |
| visit_status | TEXT | 'visited' or 'want_to_visit' |
| rating | INTEGER | Rating 1-10 |
| personal_notes | TEXT | User notes |
| full_address | TEXT | Complete street address |
| phone_number | TEXT | Phone with area code |
| price_range | TEXT | $, $$, $$$, or $$$$ |
| hours_summary | TEXT | Operating hours |
| website | TEXT | Restaurant website |
| restaurant_type | TEXT | Fine dining, casual, etc. |
| chef_owner | TEXT | Chef or owner name |
| established_year | INTEGER | Year opened |
| cuisine_details | TEXT | Detailed cuisine description |
| signature_dishes | TEXT | JSON array of must-try dishes |
| dietary_accommodations | TEXT | JSON array of dietary options |
| atmosphere | TEXT | Ambiance description |
| dress_code | TEXT | Dress code requirements |
| awards | TEXT | JSON array of awards |
| reviews_summary | TEXT | 2-3 sentence summary |
| similar_restaurants | TEXT | JSON array of similar places |
| reservations_info | TEXT | How to make reservations |
| llm_categories | TEXT | JSON array of AI-assigned categories |
| user_categories | TEXT | JSON array of user-defined categories |
| source_image_path | TEXT | Path to source image |
| last_updated | TEXT | Last update timestamp |

**Unique Constraint**: `(restaurant_name, location, date_visited)` allows multiple visits to the same restaurant on different dates.

## Configuration

### LLM Providers

The system supports three LLM providers:

**OpenAI (GPT-4)**:
```yaml
llm:
  provider: "openai"
  openai_api_key: "your-key"
  model:
    openai: "gpt-4o"
```

**Anthropic (Claude)**:
```yaml
llm:
  provider: "anthropic"
  anthropic_api_key: "your-key"
  model:
    anthropic: "claude-3-5-sonnet-20241022"
```

**Google (Gemini)**:
```yaml
llm:
  provider: "google"
  google_api_key: "your-key"
  model:
    google: "gemini-2.0-flash-exp"
```

### Settings

- **auto_enrich**: Automatically enrich restaurants after adding (default: true)
- **image_extensions**: Supported image formats for scanning
- **predefined_cuisines**: List of cuisine types for quick selection
- **user_categories**: Custom categories for semantic matching

## Website Organization

The generated static site includes:

### Pages
- **index.html**: Dashboard with statistics and quick navigation
- **restaurants.html**: Grid view of all restaurants
- **timeline.html**: Visits organized by year/month (wishlist at top)
- **cuisines.html** + **cuisines/*.html**: Browse by cuisine with color coding
- **locations.html** + **locations/*.html**: Browse by city/neighborhood
- **categories.html** + **categories/*.html**: Browse by category tags
- **price-ranges.html**: Filter by $ to $$$$
- **restaurants/*.html**: Individual restaurant detail pages

### Features
- Responsive grid layouts
- Color-coded cuisine badges
- Star ratings display
- Visit status indicators
- Statistics per grouping
- Breadcrumb navigation
- Clean, minimal design

## Architecture

### Core Components

1. **database.py** (280 lines): SQLite operations with JSON field handling
2. **llm_providers.py** (480 lines): Multi-provider LLM abstraction
3. **restaurant_manager.py** (230 lines): Business logic and duplicate detection
4. **image_processor.py** (35 lines): Directory scanning for images
5. **restaurant_tracker.py** (520 lines): Click-based CLI interface
6. **generate_site.py** (800 lines): Static website generator

### Design Patterns

- **Duplicate Detection**: Fuzzy string matching on restaurant name + location
- **Smart Enrichment**: Only fetch missing fields by default (saves API costs)
- **Change Detection**: MD5 hash prevents unnecessary website regeneration
- **JSON Serialization**: Lists stored as JSON in SQLite, parsed on retrieval
- **Provider Abstraction**: Unified interface for multiple LLM providers

## Tips & Best Practices

1. **Image Quality**: Use clear photos of menus or receipts for best extraction
2. **Incremental Enrichment**: Let auto-enrich fetch basics, then use `--force` later for full details
3. **Multiple Visits**: Track return visits by adding same restaurant with different `date_visited`
4. **Categories**: Define user categories that match your dining preferences for better matching
5. **Export Regularly**: Backup your data with periodic JSON exports
6. **Website Hosting**: The generated `site/` directory can be hosted on any static web host

## Troubleshooting

**"Error: Please configure your API key"**
- Edit `config.yaml` and add your API key for the selected provider

**"No restaurants detected in image"**
- Ensure image clearly shows restaurant name and location
- Try a different LLM provider (some perform better on handwriting)

**"Database unchanged. Use --force to regenerate anyway."**
- Website generator uses MD5 hashing to skip unnecessary regeneration
- Use `python generate_site.py --force` to regenerate anyway

**Enrichment fails or returns null values**
- Some restaurants may not have public information available
- Try different spellings or add more location details
- Use `--force` flag to retry enrichment

## Contributing

This is a personal tracking system, but feel free to adapt it for your needs. Key areas for customization:

- Add more predefined cuisines in `config.yaml`
- Customize website colors in `generate_site.py` (CUISINE_COLORS)
- Adjust enrichment fields in `llm_providers.py` prompts
- Modify database schema in `database.py` for additional fields

## License

This is a personal project with no specific license. Use and modify as needed.

## Acknowledgments

Inspired by personal album, book, and Broadway show tracking systems. Built with:
- Click (CLI framework)
- OpenAI/Anthropic/Google AI APIs (metadata enrichment)
- SQLite (local database)
- Pure HTML/CSS (static website, no framework dependencies)
