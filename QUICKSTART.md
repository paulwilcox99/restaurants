# Quick Start Guide

Get started with Restaurant Tracker in 5 minutes!

## Step 1: Install Dependencies

```bash
cd ~/code/restaurants
pip install -r requirements.txt
```

## Step 2: Configure API Key

1. Copy the example configuration:
```bash
cp config.yaml.example config.yaml
```

2. Open `config.yaml` and add your API key:
```yaml
llm:
  provider: "openai"  # or "anthropic" or "google"
  openai_api_key: "your-actual-api-key-here"
```

**Getting API Keys:**
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/
- Google: https://makersuite.google.com/app/apikey

## Step 3: Create Image Directories

```bash
mkdir restaurants_visited restaurants_wishlist
```

## Step 4: Add Your First Restaurant

### Option A: From an Image

1. Place a photo of a menu or receipt in `restaurants_visited/`
2. Run the scanner:
```bash
python restaurant_tracker.py scan --directory visited
```
3. Follow the prompts to add cuisine, date, and rating

### Option B: Manual Entry

```bash
python restaurant_tracker.py add \
  --name "Your Favorite Restaurant" \
  --location "City, State" \
  --cuisine "Italian" \
  --visited \
  --date-visited "2024-03-15" \
  --rating 9 \
  --notes "Amazing pasta!"
```

## Step 5: View Your Restaurant

```bash
# Show detailed information
python restaurant_tracker.py show 1

# List all restaurants
python restaurant_tracker.py list
```

## Step 6: Generate Website

```bash
python generate_site.py
```

Open `site/index.html` in your browser to see your restaurant collection!

## Common Commands Cheat Sheet

```bash
# Add a wishlist restaurant
python restaurant_tracker.py add --name "Restaurant" --location "City" --cuisine "Type" --wishlist

# Search for Italian restaurants
python restaurant_tracker.py search --cuisine Italian

# Update a rating
python restaurant_tracker.py update 1 --rating 10

# Enrich with AI metadata
python restaurant_tracker.py enrich 1

# Export to JSON
python restaurant_tracker.py export --format json --output backup.json

# Force regenerate website
python generate_site.py --force
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Add more restaurants from your photos or manually
- Customize categories in `config.yaml`
- Browse your collection via the generated website
- Export your data regularly for backups

## Troubleshooting

**Problem**: "Error: Please configure your API key"
**Solution**: Make sure you copied `config.yaml.example` to `config.yaml` and added a valid API key

**Problem**: "No restaurants detected in image"
**Solution**: Ensure the image clearly shows the restaurant name and location. Try a different photo or add manually.

**Problem**: Website doesn't regenerate
**Solution**: The website only regenerates when the database changes. Use `--force` flag to override.

## Tips

1. **Start Simple**: Add a few restaurants manually to understand the workflow
2. **Image Quality Matters**: Clear, well-lit photos work best for scanning
3. **Use Auto-Enrich**: Leave `auto_enrich: true` in config to automatically fetch metadata
4. **Track Revisits**: Add the same restaurant multiple times with different dates to track return visits
5. **Backup Often**: Use the export command to create backups of your data

Enjoy tracking your culinary adventures!
