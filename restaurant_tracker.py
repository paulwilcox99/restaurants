#!/usr/bin/env python3
import click
import yaml
import json
import csv
from pathlib import Path
from typing import Optional

from database import Database
from llm_providers import get_provider
from image_processor import ImageProcessor
from restaurant_manager import RestaurantManager


def load_config():
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def save_config(config):
    """Save configuration to config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def get_managers():
    """Initialize and return database, LLM provider, and restaurant manager."""
    config = load_config()

    db = Database(config['database']['path'])

    # Only validate API key if auto_enrich is enabled or for commands that need LLM
    provider_name = config['llm']['provider']
    api_key_field = f"{provider_name}_api_key"
    has_api_key = config['llm'].get(api_key_field) and config['llm'][api_key_field] != ""

    llm_provider = None
    if has_api_key:
        llm_provider = get_provider(config)

    restaurant_manager = RestaurantManager(db, llm_provider, config)

    return config, db, llm_provider, restaurant_manager


@click.group()
def cli():
    """Restaurant Tracker - Track restaurants you've visited or want to visit with AI-powered metadata."""
    pass


@cli.command()
@click.option('--directory', type=click.Choice(['visited', 'wishlist', 'all']), default='all',
              help='Directory to scan for images')
def scan(directory):
    """Scan directories for menu/receipt images and extract information."""
    config, db, llm_provider, restaurant_manager = get_managers()

    if llm_provider is None:
        click.echo("Error: LLM provider not configured. Please add an API key in config.yaml", err=True)
        raise click.Abort()

    image_processor = ImageProcessor(config, db)

    directories = []
    if directory == 'all':
        directories = [
            (config['directories']['restaurants_visited'], 'visited'),
            (config['directories']['restaurants_wishlist'], 'want_to_visit')
        ]
    elif directory == 'visited':
        directories = [(config['directories']['restaurants_visited'], 'visited')]
    else:  # wishlist
        directories = [(config['directories']['restaurants_wishlist'], 'want_to_visit')]

    total_restaurants_added = 0

    for dir_name, visit_status in directories:
        click.echo(f"\nScanning directory: {dir_name}")
        unprocessed_images = image_processor.scan_directory(dir_name)

        if not unprocessed_images:
            click.echo(f"No new images found in {dir_name}")
            continue

        click.echo(f"Found {len(unprocessed_images)} unprocessed image(s)")

        for image_path in unprocessed_images:
            click.echo(f"\nProcessing: {Path(image_path).name}")

            try:
                # Extract restaurants from image
                restaurants = llm_provider.extract_restaurants_from_image(image_path)

                if not restaurants:
                    click.echo("  No restaurants detected in image")
                    db.mark_image_processed(image_path, 0)
                    continue

                click.echo(f"  Detected {len(restaurants)} restaurant(s)")

                restaurants_added = 0
                for restaurant_data in restaurants:
                    restaurant_name = restaurant_data['restaurant_name']
                    location = restaurant_data['location']

                    click.echo(f"  - {restaurant_name} in {location}")

                    # Prompt for cuisine (required)
                    predefined_cuisines = config['settings'].get('predefined_cuisines', [])
                    click.echo(f"    Available cuisines: {', '.join(predefined_cuisines)}")
                    cuisine = click.prompt("    Cuisine", type=str)

                    # For visited restaurants, prompt for date and rating
                    date_visited = None
                    rating = None
                    if visit_status == 'visited':
                        date_visited = click.prompt("    Date visited (YYYY-MM-DD)", type=str)
                        rating = click.prompt("    Rating (1-10, or 0 to skip)", type=int, default=0)
                        if rating == 0:
                            rating = None

                    # Prompt for notes (optional)
                    notes = click.prompt("    Personal notes (optional)", type=str, default="")

                    # Prepare restaurant data
                    restaurant_entry = {
                        'restaurant_name': restaurant_name,
                        'location': location,
                        'cuisine': cuisine,
                        'visit_status': visit_status,
                        'source_image_path': image_path
                    }

                    if date_visited:
                        restaurant_entry['date_visited'] = date_visited

                    if rating:
                        restaurant_entry['rating'] = rating

                    if notes:
                        restaurant_entry['personal_notes'] = notes

                    # Add restaurant
                    restaurant_id, status = restaurant_manager.add_restaurant(restaurant_entry)

                    if status == 'duplicate':
                        click.echo(f"    Already in database (ID: {restaurant_id})")
                    elif status == 'added':
                        click.echo(f"    Added to database (ID: {restaurant_id})")
                        restaurants_added += 1

                total_restaurants_added += restaurants_added

                # Mark image as processed
                db.mark_image_processed(image_path, restaurants_added)

            except Exception as e:
                click.echo(f"  Error processing image: {e}", err=True)
                continue

    click.echo(f"\n✓ Scan complete. Added {total_restaurants_added} new restaurant(s).")


@cli.command()
@click.option('--name', required=True, help='Restaurant name')
@click.option('--location', required=True, help='Location (city, neighborhood)')
@click.option('--cuisine', required=True, help='Cuisine type')
@click.option('--visited', 'visit_status_flag', flag_value='visited', help='Mark as visited')
@click.option('--wishlist', 'visit_status_flag', flag_value='want_to_visit', help='Mark as wishlist')
@click.option('--date-visited', help='Date visited (YYYY-MM-DD, for visited restaurants)')
@click.option('--rating', type=click.IntRange(1, 10), help='Rating (1-10)')
@click.option('--notes', help='Personal notes')
def add(name, location, cuisine, visit_status_flag, date_visited, rating, notes):
    """Manually add a restaurant to the database."""
    config, db, llm_provider, restaurant_manager = get_managers()

    # Determine visit status
    if not visit_status_flag:
        click.echo("Error: Must specify either --visited or --wishlist", err=True)
        raise click.Abort()

    # Prepare restaurant data
    restaurant_data = {
        'restaurant_name': name,
        'location': location,
        'cuisine': cuisine,
        'visit_status': visit_status_flag
    }

    if date_visited:
        restaurant_data['date_visited'] = date_visited

    if rating:
        restaurant_data['rating'] = rating

    if notes:
        restaurant_data['personal_notes'] = notes

    # Add restaurant
    try:
        restaurant_id, status = restaurant_manager.add_restaurant(restaurant_data)

        if status == 'duplicate':
            click.echo(f"Restaurant already exists in database (ID: {restaurant_id})")
            if click.confirm("Do you want to update it?"):
                updates = {}
                if rating:
                    updates['rating'] = rating
                if notes:
                    updates['personal_notes'] = notes
                if date_visited:
                    updates['date_visited'] = date_visited
                if updates:
                    restaurant_manager.update_restaurant(restaurant_id, updates)
                    click.echo("✓ Restaurant updated")
        elif status == 'added':
            click.echo(f"✓ Restaurant added successfully (ID: {restaurant_id})")

    except Exception as e:
        click.echo(f"Error adding restaurant: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--name', help='Filter by restaurant name (partial match)')
@click.option('--location', help='Filter by location (partial match)')
@click.option('--cuisine', help='Filter by cuisine (partial match)')
@click.option('--category', help='Filter by category')
@click.option('--visited', 'status_filter', flag_value='visited', help='Show only visited')
@click.option('--wishlist', 'status_filter', flag_value='want_to_visit', help='Show only wishlist')
@click.option('--rating-min', type=click.IntRange(1, 10), help='Minimum rating')
@click.option('--rating-max', type=click.IntRange(1, 10), help='Maximum rating')
@click.option('--price-range', help='Filter by price range ($, $$, $$$, $$$$)')
def search(name, location, cuisine, category, status_filter, rating_min, rating_max, price_range):
    """Search for restaurants with various filters."""
    config, db, llm_provider, restaurant_manager = get_managers()

    filters = {}

    if name:
        filters['restaurant_name'] = name
    if location:
        filters['location'] = location
    if cuisine:
        filters['cuisine'] = cuisine
    if category:
        filters['category'] = category
    if status_filter:
        filters['visit_status'] = status_filter
    if rating_min:
        filters['rating_min'] = rating_min
    if rating_max:
        filters['rating_max'] = rating_max
    if price_range:
        filters['price_range'] = price_range

    restaurants = restaurant_manager.search_restaurants(filters)

    if not restaurants:
        click.echo("No restaurants found matching the criteria.")
        return

    click.echo(f"\nFound {len(restaurants)} restaurant(s):\n")

    for restaurant in restaurants:
        click.echo(restaurant_manager.format_restaurant_display(restaurant))
        click.echo()


@cli.command(name='list')
@click.option('--cuisine', help='Filter by cuisine')
@click.option('--location', help='Filter by location')
@click.option('--visited', 'status_filter', flag_value='visited', help='Show only visited')
@click.option('--wishlist', 'status_filter', flag_value='want_to_visit', help='Show only wishlist')
@click.option('--sort-by', type=click.Choice(['name', 'location', 'cuisine', 'rating', 'date_visited', 'date_added']),
              default='date_added', help='Sort by field')
def list_restaurants(cuisine, location, status_filter, sort_by):
    """List all restaurants in the database."""
    config, db, llm_provider, restaurant_manager = get_managers()

    filters = {}
    if cuisine:
        filters['cuisine'] = cuisine
    if location:
        filters['location'] = location
    if status_filter:
        filters['visit_status'] = status_filter

    filters['sort_by'] = sort_by

    restaurants = restaurant_manager.search_restaurants(filters)

    if not restaurants:
        click.echo("No restaurants in database.")
        return

    click.echo(f"\n{len(restaurants)} restaurant(s) in database:\n")

    for restaurant in restaurants:
        click.echo(restaurant_manager.format_restaurant_display(restaurant))
        click.echo()


@cli.command()
@click.argument('restaurant_identifier')
def show(restaurant_identifier):
    """Show detailed information about a restaurant (by ID or name)."""
    config, db, llm_provider, restaurant_manager = get_managers()

    # Try to parse as ID first
    restaurant = None
    try:
        restaurant_id = int(restaurant_identifier)
        restaurant = restaurant_manager.get_restaurant(restaurant_id)
    except ValueError:
        # Not an ID, try name
        restaurant = restaurant_manager.get_restaurant_by_name(restaurant_identifier)

    if not restaurant:
        click.echo(f"Restaurant not found: {restaurant_identifier}", err=True)
        raise click.Abort()

    click.echo("\n" + restaurant_manager.format_restaurant_display(restaurant, detailed=True) + "\n")


@cli.command()
@click.argument('restaurant_id', type=int)
@click.option('--rating', type=click.IntRange(1, 10), help='Update rating')
@click.option('--notes', help='Update personal notes')
@click.option('--cuisine', help='Update cuisine')
@click.option('--date-visited', help='Update date visited (YYYY-MM-DD)')
@click.option('--visited', 'new_status', flag_value='visited', help='Mark as visited')
@click.option('--wishlist', 'new_status', flag_value='want_to_visit', help='Mark as wishlist')
def update(restaurant_id, rating, notes, cuisine, date_visited, new_status):
    """Update restaurant information."""
    config, db, llm_provider, restaurant_manager = get_managers()

    restaurant = restaurant_manager.get_restaurant(restaurant_id)
    if not restaurant:
        click.echo(f"Restaurant not found: {restaurant_id}", err=True)
        raise click.Abort()

    updates = {}

    if rating:
        updates['rating'] = rating
    if notes:
        updates['personal_notes'] = notes
    if cuisine:
        updates['cuisine'] = cuisine
    if date_visited:
        updates['date_visited'] = date_visited
    if new_status:
        updates['visit_status'] = new_status

    if not updates:
        click.echo("No updates specified.")
        return

    restaurant_manager.update_restaurant(restaurant_id, updates)
    click.echo("✓ Restaurant updated successfully")


@cli.command()
@click.argument('restaurant_identifier')
@click.option('--force', is_flag=True, help='Re-fetch all fields, overwriting existing data')
def enrich(restaurant_identifier, force):
    """Enrich a restaurant with detailed metadata from LLM."""
    config, db, llm_provider, restaurant_manager = get_managers()

    if llm_provider is None:
        click.echo("Error: LLM provider not configured. Please add an API key in config.yaml", err=True)
        raise click.Abort()

    # Try to parse as ID first
    restaurant = None
    try:
        restaurant_id = int(restaurant_identifier)
        restaurant = restaurant_manager.get_restaurant(restaurant_id)
    except ValueError:
        # Not an ID, try name
        restaurant = restaurant_manager.get_restaurant_by_name(restaurant_identifier)
        if restaurant:
            restaurant_id = restaurant['id']

    if not restaurant:
        click.echo(f"Restaurant not found: {restaurant_identifier}", err=True)
        raise click.Abort()

    try:
        if force:
            click.echo("Re-fetching all metadata fields...")
        else:
            click.echo("Fetching missing metadata fields...")

        updated_restaurant = restaurant_manager.enrich_restaurant(restaurant_id, force=force)
        click.echo("✓ Restaurant enriched successfully\n")
        click.echo(restaurant_manager.format_restaurant_display(updated_restaurant, detailed=True))

    except Exception as e:
        click.echo(f"Error enriching restaurant: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--format', 'output_format', type=click.Choice(['csv', 'json']), required=True, help='Export format')
@click.option('--output', required=True, help='Output file path')
def export(output_format, output):
    """Export all restaurants to CSV or JSON."""
    config, db, llm_provider, restaurant_manager = get_managers()

    restaurants = restaurant_manager.search_restaurants({})

    if not restaurants:
        click.echo("No restaurants to export.")
        return

    try:
        if output_format == 'json':
            with open(output, 'w') as f:
                json.dump(restaurants, f, indent=2)
        elif output_format == 'csv':
            with open(output, 'w', newline='') as f:
                # Get all possible fields
                fieldnames = [
                    'id', 'restaurant_name', 'location', 'cuisine', 'visit_status',
                    'date_visited', 'rating', 'personal_notes', 'full_address',
                    'phone_number', 'price_range', 'hours_summary', 'website',
                    'restaurant_type', 'chef_owner', 'established_year',
                    'cuisine_details', 'signature_dishes', 'dietary_accommodations',
                    'atmosphere', 'dress_code', 'awards', 'reviews_summary',
                    'similar_restaurants', 'reservations_info', 'llm_categories',
                    'user_categories', 'source_image_path', 'date_added', 'last_updated'
                ]

                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for restaurant in restaurants:
                    # Convert lists to comma-separated strings for CSV
                    row = restaurant.copy()
                    for field in ['signature_dishes', 'dietary_accommodations', 'awards',
                                  'similar_restaurants', 'llm_categories', 'user_categories']:
                        if isinstance(row.get(field), list):
                            row[field] = ', '.join(str(x) for x in row[field])
                    writer.writerow(row)

        click.echo(f"✓ Exported {len(restaurants)} restaurant(s) to {output}")

    except Exception as e:
        click.echo(f"Error exporting restaurants: {e}", err=True)
        raise click.Abort()


@cli.group()
def categories():
    """Manage predefined user categories."""
    pass


@categories.command(name='list')
def list_categories():
    """List all predefined user categories."""
    config = load_config()
    user_categories = config['settings'].get('user_categories', [])

    if not user_categories:
        click.echo("No user categories defined.")
        return

    click.echo("\nPredefined user categories:")
    for i, category in enumerate(user_categories, 1):
        click.echo(f"  {i}. {category}")
    click.echo()


@categories.command(name='add')
@click.argument('category')
def add_category(category):
    """Add a new predefined user category."""
    config = load_config()

    # Normalize category (lowercase, trim)
    category = category.lower().strip()

    if not category:
        click.echo("Category name cannot be empty.", err=True)
        raise click.Abort()

    user_categories = config['settings'].get('user_categories', [])

    if category in user_categories:
        click.echo(f"Category '{category}' already exists.")
        return

    user_categories.append(category)
    config['settings']['user_categories'] = user_categories

    save_config(config)

    click.echo(f"✓ Added category: {category}")


@categories.command(name='remove')
@click.argument('category')
def remove_category(category):
    """Remove a predefined user category."""
    config = load_config()

    category = category.lower().strip()
    user_categories = config['settings'].get('user_categories', [])

    if category not in user_categories:
        click.echo(f"Category '{category}' not found.")
        return

    user_categories.remove(category)
    config['settings']['user_categories'] = user_categories

    save_config(config)

    click.echo(f"✓ Removed category: {category}")


if __name__ == '__main__':
    cli()
