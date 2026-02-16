import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, List, Any


class Database:
    def __init__(self, db_path: str = "restaurants.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database with schema."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Create restaurants table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS restaurants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Core Fields (user-entered or LLM-extracted)
                restaurant_name TEXT NOT NULL,
                location TEXT NOT NULL,
                cuisine TEXT NOT NULL,
                date_added TEXT NOT NULL,
                date_visited TEXT,
                visit_status TEXT CHECK(visit_status IN ('visited', 'want_to_visit')) NOT NULL,
                rating INTEGER CHECK(rating >= 1 AND rating <= 10),
                personal_notes TEXT,

                -- Basic Info (LLM-enriched)
                full_address TEXT,
                phone_number TEXT,
                price_range TEXT,
                hours_summary TEXT,
                website TEXT,

                -- Food Details (LLM-enriched)
                restaurant_type TEXT,
                chef_owner TEXT,
                established_year INTEGER,
                cuisine_details TEXT,
                signature_dishes TEXT,
                dietary_accommodations TEXT,

                -- Atmosphere & Reviews (LLM-enriched)
                atmosphere TEXT,
                dress_code TEXT,
                awards TEXT,
                reviews_summary TEXT,
                similar_restaurants TEXT,
                reservations_info TEXT,

                -- Categories & Classification
                llm_categories TEXT,
                user_categories TEXT,

                -- Metadata
                source_image_path TEXT,
                last_updated TEXT NOT NULL,

                UNIQUE(restaurant_name, location, date_visited)
            )
        """)

        # Create processed_images table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT UNIQUE NOT NULL,
                processed_date TEXT NOT NULL,
                restaurants_extracted INTEGER NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    def add_restaurant(self, restaurant_data: Dict[str, Any]) -> int:
        """Add a new restaurant to the database."""
        conn = self.get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        restaurant_data['date_added'] = now
        restaurant_data['last_updated'] = now

        # Convert lists to JSON strings
        json_fields = [
            'signature_dishes', 'dietary_accommodations', 'awards',
            'similar_restaurants', 'llm_categories', 'user_categories'
        ]
        for field in json_fields:
            if field in restaurant_data and isinstance(restaurant_data[field], list):
                restaurant_data[field] = json.dumps(restaurant_data[field])

        columns = ', '.join(restaurant_data.keys())
        placeholders = ', '.join(['?' for _ in restaurant_data])

        cursor.execute(
            f"INSERT INTO restaurants ({columns}) VALUES ({placeholders})",
            list(restaurant_data.values())
        )

        restaurant_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return restaurant_id

    def update_restaurant(self, restaurant_id: int, updates: Dict[str, Any]):
        """Update an existing restaurant."""
        conn = self.get_connection()
        cursor = conn.cursor()

        updates['last_updated'] = datetime.now().isoformat()

        # Convert lists to JSON strings
        json_fields = [
            'signature_dishes', 'dietary_accommodations', 'awards',
            'similar_restaurants', 'llm_categories', 'user_categories'
        ]
        for field in json_fields:
            if field in updates and isinstance(updates[field], list):
                updates[field] = json.dumps(updates[field])

        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])

        cursor.execute(
            f"UPDATE restaurants SET {set_clause} WHERE id = ?",
            list(updates.values()) + [restaurant_id]
        )

        conn.commit()
        conn.close()

    def get_restaurant(self, restaurant_id: int) -> Optional[Dict[str, Any]]:
        """Get a restaurant by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM restaurants WHERE id = ?", (restaurant_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def get_restaurant_by_name(self, restaurant_name: str, location: str = None) -> Optional[Dict[str, Any]]:
        """Get a restaurant by name and optionally location."""
        conn = self.get_connection()
        cursor = conn.cursor()

        if location:
            cursor.execute(
                "SELECT * FROM restaurants WHERE restaurant_name = ? AND location = ?",
                (restaurant_name, location)
            )
        else:
            cursor.execute("SELECT * FROM restaurants WHERE restaurant_name = ?", (restaurant_name,))

        row = cursor.fetchone()

        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def search_restaurants(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search restaurants with various filters."""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM restaurants WHERE 1=1"
        params = []

        if 'restaurant_name' in filters:
            query += " AND restaurant_name LIKE ?"
            params.append(f"%{filters['restaurant_name']}%")

        if 'location' in filters:
            query += " AND location LIKE ?"
            params.append(f"%{filters['location']}%")

        if 'cuisine' in filters:
            query += " AND cuisine LIKE ?"
            params.append(f"%{filters['cuisine']}%")

        if 'visit_status' in filters:
            query += " AND visit_status = ?"
            params.append(filters['visit_status'])

        if 'rating_min' in filters:
            query += " AND rating >= ?"
            params.append(filters['rating_min'])

        if 'rating_max' in filters:
            query += " AND rating <= ?"
            params.append(filters['rating_max'])

        if 'category' in filters:
            query += " AND llm_categories LIKE ?"
            params.append(f"%{filters['category']}%")

        if 'user_category' in filters:
            query += " AND user_categories LIKE ?"
            params.append(f"%{filters['user_category']}%")

        if 'price_range' in filters:
            query += " AND price_range = ?"
            params.append(filters['price_range'])

        if 'sort_by' in filters:
            sort_field = filters['sort_by']
            sort_order = filters.get('sort_order', 'ASC')
            query += f" ORDER BY {sort_field} {sort_order}"
        else:
            query += " ORDER BY date_added DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def get_all_restaurants(self) -> List[Dict[str, Any]]:
        """Get all restaurants."""
        return self.search_restaurants({})

    def mark_image_processed(self, image_path: str, restaurants_extracted: int):
        """Mark an image as processed."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT OR REPLACE INTO processed_images (image_path, processed_date, restaurants_extracted) VALUES (?, ?, ?)",
            (image_path, datetime.now().isoformat(), restaurants_extracted)
        )

        conn.commit()
        conn.close()

    def is_image_processed(self, image_path: str) -> bool:
        """Check if an image has been processed."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM processed_images WHERE image_path = ?", (image_path,))
        result = cursor.fetchone()

        conn.close()

        return result is not None

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a dictionary with JSON fields parsed."""
        restaurant = dict(row)

        # Parse JSON fields
        json_fields = [
            'signature_dishes', 'dietary_accommodations', 'awards',
            'similar_restaurants', 'llm_categories', 'user_categories'
        ]
        for field in json_fields:
            if restaurant.get(field):
                try:
                    restaurant[field] = json.loads(restaurant[field])
                except json.JSONDecodeError:
                    restaurant[field] = []

        return restaurant
