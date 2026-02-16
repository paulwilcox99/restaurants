import re
from typing import Dict, Any, List, Optional, Tuple
from database import Database
from llm_providers import LLMProvider


class RestaurantManager:
    def __init__(self, db: Database, llm_provider: LLMProvider, config: Dict[str, Any]):
        self.db = db
        self.llm_provider = llm_provider
        self.config = config

    def normalize_string(self, s: str) -> str:
        """Normalize string for comparison (lowercase, remove punctuation, trim)."""
        s = s.lower().strip()
        s = re.sub(r'[^\w\s]', '', s)
        s = re.sub(r'\s+', ' ', s)
        return s

    def find_duplicate(self, restaurant_name: str, location: str, date_visited: str = None) -> Optional[Dict[str, Any]]:
        """Check if restaurant already exists using fuzzy matching."""
        normalized_name = self.normalize_string(restaurant_name)
        normalized_location = self.normalize_string(location)

        all_restaurants = self.db.search_restaurants({})

        for restaurant in all_restaurants:
            rest_name_norm = self.normalize_string(restaurant['restaurant_name'])
            rest_location_norm = self.normalize_string(restaurant['location'])

            # Match on name and location
            if rest_name_norm == normalized_name and rest_location_norm == normalized_location:
                # If date_visited is specified, check for exact match
                if date_visited:
                    if restaurant.get('date_visited') == date_visited:
                        return restaurant
                else:
                    # No date specified, return first match
                    return restaurant

        return None

    def add_restaurant(self, restaurant_data: Dict[str, Any], source: str = 'manual', auto_enrich: bool = None) -> Tuple[int, str]:
        """
        Add a new restaurant to the database.
        Returns (restaurant_id, status) where status is 'added' or 'duplicate'.
        """
        # Check for duplicates
        duplicate = self.find_duplicate(
            restaurant_data['restaurant_name'],
            restaurant_data['location'],
            restaurant_data.get('date_visited')
        )

        if duplicate:
            return duplicate['id'], 'duplicate'

        # Add the restaurant
        restaurant_id = self.db.add_restaurant(restaurant_data)

        # Auto-enrich if enabled
        should_enrich = auto_enrich if auto_enrich is not None else self.config['settings'].get('auto_enrich', True)

        if should_enrich:
            try:
                self.enrich_restaurant(restaurant_id, force=False)
            except Exception as e:
                print(f"Warning: Failed to enrich restaurant: {e}")

        return restaurant_id, 'added'

    def enrich_restaurant(self, restaurant_id: int, force: bool = False) -> Dict[str, Any]:
        """
        Enrich a restaurant with LLM metadata.
        If force=False, only fetch fields that are empty/null.
        If force=True, re-fetch all fields.
        """
        restaurant = self.db.get_restaurant(restaurant_id)
        if not restaurant:
            raise ValueError(f"Restaurant with ID {restaurant_id} not found")

        # Determine which fields need enrichment
        enrichable_fields = [
            'full_address', 'phone_number', 'price_range', 'hours_summary',
            'website', 'restaurant_type', 'chef_owner', 'established_year',
            'cuisine_details', 'signature_dishes', 'dietary_accommodations',
            'atmosphere', 'dress_code', 'awards', 'reviews_summary',
            'similar_restaurants', 'reservations_info', 'llm_categories'
        ]

        if force:
            missing_fields = None  # Fetch all fields
        else:
            missing_fields = []
            for field in enrichable_fields:
                value = restaurant.get(field)
                if value is None or value == '' or (isinstance(value, list) and len(value) == 0):
                    missing_fields.append(field)

            if not missing_fields:
                return restaurant  # Nothing to enrich

        # Call LLM for enrichment
        print(f"Enriching restaurant: {restaurant['restaurant_name']} in {restaurant['location']}")
        enriched_data = self.llm_provider.enrich_restaurant_info(
            restaurant['restaurant_name'],
            restaurant['location'],
            missing_fields=missing_fields
        )

        # Update only the fields that were fetched
        updates = {}
        for field, value in enriched_data.items():
            if force or field in (missing_fields or enrichable_fields):
                updates[field] = value

        # Match against user categories if we have reviews_summary or atmosphere
        reviews_summary = updates.get('reviews_summary') or restaurant.get('reviews_summary')
        atmosphere = updates.get('atmosphere') or restaurant.get('atmosphere')
        cuisine = restaurant.get('cuisine') or ''

        if (reviews_summary or atmosphere) and self.config['settings'].get('user_categories'):
            print("Matching user categories...")
            user_cats = self.llm_provider.match_user_categories(
                restaurant['restaurant_name'],
                restaurant['location'],
                reviews_summary or '',
                cuisine,
                atmosphere or '',
                self.config['settings']['user_categories']
            )
            updates['user_categories'] = user_cats

        # Update the database
        if updates:
            self.db.update_restaurant(restaurant_id, updates)

        # Return updated restaurant
        return self.db.get_restaurant(restaurant_id)

    def update_restaurant(self, restaurant_id: int, updates: Dict[str, Any]):
        """Update an existing restaurant."""
        self.db.update_restaurant(restaurant_id, updates)

    def get_restaurant(self, restaurant_id: int) -> Optional[Dict[str, Any]]:
        """Get a restaurant by ID."""
        return self.db.get_restaurant(restaurant_id)

    def get_restaurant_by_name(self, restaurant_name: str, location: str = None) -> Optional[Dict[str, Any]]:
        """Get a restaurant by name."""
        return self.db.get_restaurant_by_name(restaurant_name, location)

    def search_restaurants(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search restaurants with filters."""
        return self.db.search_restaurants(filters)

    def format_restaurant_display(self, restaurant: Dict[str, Any], detailed: bool = False) -> str:
        """Format restaurant information for display."""
        output = []
        output.append(f"ID: {restaurant['id']}")
        output.append(f"Restaurant: {restaurant['restaurant_name']}")
        output.append(f"Location: {restaurant['location']}")

        if restaurant.get('cuisine'):
            output.append(f"Cuisine: {restaurant['cuisine']}")

        status = "Visited" if restaurant['visit_status'] == 'visited' else "Want to Visit"
        output.append(f"Status: {status}")

        if restaurant.get('date_visited'):
            output.append(f"Date Visited: {restaurant['date_visited']}")

        if restaurant.get('rating'):
            stars = '★' * restaurant['rating'] + '☆' * (10 - restaurant['rating'])
            output.append(f"Rating: {stars} ({restaurant['rating']}/10)")

        if detailed:
            if restaurant.get('full_address'):
                output.append(f"Address: {restaurant['full_address']}")

            if restaurant.get('phone_number'):
                output.append(f"Phone: {restaurant['phone_number']}")

            if restaurant.get('website'):
                output.append(f"Website: {restaurant['website']}")

            if restaurant.get('price_range'):
                output.append(f"Price Range: {restaurant['price_range']}")

            if restaurant.get('hours_summary'):
                output.append(f"Hours: {restaurant['hours_summary']}")

            if restaurant.get('restaurant_type'):
                output.append(f"Type: {restaurant['restaurant_type']}")

            if restaurant.get('chef_owner'):
                output.append(f"Chef/Owner: {restaurant['chef_owner']}")

            if restaurant.get('established_year'):
                output.append(f"Established: {restaurant['established_year']}")

            if restaurant.get('cuisine_details'):
                output.append(f"Cuisine Details: {restaurant['cuisine_details']}")

            if restaurant.get('signature_dishes') and len(restaurant['signature_dishes']) > 0:
                output.append("Signature Dishes:")
                for dish in restaurant['signature_dishes']:
                    output.append(f"  • {dish}")

            if restaurant.get('dietary_accommodations') and len(restaurant['dietary_accommodations']) > 0:
                output.append(f"Dietary Options: {', '.join(restaurant['dietary_accommodations'])}")

            if restaurant.get('atmosphere'):
                output.append(f"Atmosphere: {restaurant['atmosphere']}")

            if restaurant.get('dress_code'):
                output.append(f"Dress Code: {restaurant['dress_code']}")

            if restaurant.get('reservations_info'):
                output.append(f"Reservations: {restaurant['reservations_info']}")

            if restaurant.get('awards') and len(restaurant['awards']) > 0:
                output.append("Awards:")
                for award in restaurant['awards']:
                    output.append(f"  • {award}")

            if restaurant.get('reviews_summary'):
                output.append(f"Reviews: {restaurant['reviews_summary']}")

            if restaurant.get('similar_restaurants') and len(restaurant['similar_restaurants']) > 0:
                output.append(f"Similar Restaurants: {', '.join(restaurant['similar_restaurants'])}")

            if restaurant.get('llm_categories') and len(restaurant['llm_categories']) > 0:
                output.append(f"Categories: {', '.join(restaurant['llm_categories'])}")

            if restaurant.get('user_categories') and len(restaurant['user_categories']) > 0:
                output.append(f"User Categories: {', '.join(restaurant['user_categories'])}")

            if restaurant.get('personal_notes'):
                output.append(f"Notes: {restaurant['personal_notes']}")

            if restaurant.get('source_image_path'):
                output.append(f"Source Image: {restaurant['source_image_path']}")

            output.append(f"Date Added: {restaurant['date_added']}")

        return "\n".join(output)
