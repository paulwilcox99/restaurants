import base64
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path


class LLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def extract_restaurants_from_image(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract restaurant information from an image."""
        pass

    @abstractmethod
    def enrich_restaurant_info(self, restaurant_name: str, location: str, missing_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Enrich restaurant information with detailed metadata."""
        pass

    @abstractmethod
    def match_user_categories(self, restaurant_name: str, location: str, reviews_summary: str, cuisine: str, atmosphere: str, predefined_categories: List[str]) -> List[str]:
        """Match restaurant against predefined user categories."""
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def extract_restaurants_from_image(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract restaurant information from an image using GPT-4 Vision."""
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

        prompt = """Analyze this image of a menu or receipt. Extract the restaurant name and location.
Return ONLY a JSON array in this exact format, with no additional text:
[{"restaurant_name": "Restaurant Name", "location": "City, State or Neighborhood"}]

If you cannot clearly read the restaurant's information, return an empty array []."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )

            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error extracting restaurants from image: {e}")
            return []

    def enrich_restaurant_info(self, restaurant_name: str, location: str, missing_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Enrich restaurant information with detailed metadata."""
        if missing_fields:
            fields_prompt = f"Provide ONLY the following information: {', '.join(missing_fields)}"
        else:
            fields_prompt = """Provide the following information:
- full_address (complete street address)
- phone_number (phone number with area code)
- price_range ($, $$, $$$, or $$$$)
- hours_summary (brief summary of operating hours)
- website (restaurant website URL)
- restaurant_type (fine dining, casual, fast-casual, etc.)
- chef_owner (chef or owner name)
- established_year (year restaurant opened)
- cuisine_details (detailed cuisine description)
- signature_dishes (list of must-try dishes)
- dietary_accommodations (list: vegetarian, vegan, gluten-free, etc.)
- atmosphere (description of ambiance/vibe)
- dress_code (casual, business casual, formal, etc.)
- awards (list of awards/recognitions)
- reviews_summary (2-3 sentence critical summary)
- similar_restaurants (list of similar restaurants)
- reservations_info (how to make reservations)
- llm_categories (list of categories like "romantic", "family-friendly", "date night", etc.)"""

        prompt = f"""Provide detailed information about the restaurant "{restaurant_name}" in {location}.

{fields_prompt}

Return ONLY a JSON object in this exact format, with no additional text:
{{
    "full_address": "street address",
    "phone_number": "(xxx) xxx-xxxx",
    "price_range": "$$",
    "hours_summary": "hours summary",
    "website": "https://...",
    "restaurant_type": "fine dining",
    "chef_owner": "chef name",
    "established_year": 2020,
    "cuisine_details": "detailed cuisine description",
    "signature_dishes": ["dish1", "dish2"],
    "dietary_accommodations": ["vegetarian", "vegan"],
    "atmosphere": "ambiance description",
    "dress_code": "casual",
    "awards": ["award1", "award2"],
    "reviews_summary": "2-3 sentence summary",
    "similar_restaurants": ["restaurant1", "restaurant2"],
    "reservations_info": "reservation details",
    "llm_categories": ["romantic", "date night"]
}}

Use null for unavailable single values or [] for unavailable lists."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000
            )

            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error enriching restaurant info: {e}")
            return {}

    def match_user_categories(self, restaurant_name: str, location: str, reviews_summary: str, cuisine: str, atmosphere: str, predefined_categories: List[str]) -> List[str]:
        """Match restaurant against predefined user categories."""
        categories_str = ", ".join([f'"{cat}"' for cat in predefined_categories])

        prompt = f"""Given this restaurant:
Restaurant: {restaurant_name}
Location: {location}
Reviews: {reviews_summary}
Cuisine: {cuisine}
Atmosphere: {atmosphere}

Which of these predefined categories does it fit into? {categories_str}

Return ONLY a JSON array of matching category names, with no additional text:
["category1", "category2"]

Only include categories that clearly match. If no categories match, return an empty array []."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200
            )

            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error matching user categories: {e}")
            return []


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def extract_restaurants_from_image(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract restaurant information from an image using Claude Vision."""
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

        # Detect image type
        suffix = Path(image_path).suffix.lower()
        media_type = "image/jpeg" if suffix in [".jpg", ".jpeg"] else "image/png"

        prompt = """Analyze this image of a menu or receipt. Extract the restaurant name and location.
Return ONLY a JSON array in this exact format, with no additional text:
[{"restaurant_name": "Restaurant Name", "location": "City, State or Neighborhood"}]

If you cannot clearly read the restaurant's information, return an empty array []."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )

            content = response.content[0].text.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error extracting restaurants from image: {e}")
            return []

    def enrich_restaurant_info(self, restaurant_name: str, location: str, missing_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Enrich restaurant information with detailed metadata."""
        if missing_fields:
            fields_prompt = f"Provide ONLY the following information: {', '.join(missing_fields)}"
        else:
            fields_prompt = """Provide the following information:
- full_address (complete street address)
- phone_number (phone number with area code)
- price_range ($, $$, $$$, or $$$$)
- hours_summary (brief summary of operating hours)
- website (restaurant website URL)
- restaurant_type (fine dining, casual, fast-casual, etc.)
- chef_owner (chef or owner name)
- established_year (year restaurant opened)
- cuisine_details (detailed cuisine description)
- signature_dishes (list of must-try dishes)
- dietary_accommodations (list: vegetarian, vegan, gluten-free, etc.)
- atmosphere (description of ambiance/vibe)
- dress_code (casual, business casual, formal, etc.)
- awards (list of awards/recognitions)
- reviews_summary (2-3 sentence critical summary)
- similar_restaurants (list of similar restaurants)
- reservations_info (how to make reservations)
- llm_categories (list of categories like "romantic", "family-friendly", "date night", etc.)"""

        prompt = f"""Provide detailed information about the restaurant "{restaurant_name}" in {location}.

{fields_prompt}

Return ONLY a JSON object in this exact format, with no additional text:
{{
    "full_address": "street address",
    "phone_number": "(xxx) xxx-xxxx",
    "price_range": "$$",
    "hours_summary": "hours summary",
    "website": "https://...",
    "restaurant_type": "fine dining",
    "chef_owner": "chef name",
    "established_year": 2020,
    "cuisine_details": "detailed cuisine description",
    "signature_dishes": ["dish1", "dish2"],
    "dietary_accommodations": ["vegetarian", "vegan"],
    "atmosphere": "ambiance description",
    "dress_code": "casual",
    "awards": ["award1", "award2"],
    "reviews_summary": "2-3 sentence summary",
    "similar_restaurants": ["restaurant1", "restaurant2"],
    "reservations_info": "reservation details",
    "llm_categories": ["romantic", "date night"]
}}

Use null for unavailable single values or [] for unavailable lists."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            content = response.content[0].text.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error enriching restaurant info: {e}")
            return {}

    def match_user_categories(self, restaurant_name: str, location: str, reviews_summary: str, cuisine: str, atmosphere: str, predefined_categories: List[str]) -> List[str]:
        """Match restaurant against predefined user categories."""
        categories_str = ", ".join([f'"{cat}"' for cat in predefined_categories])

        prompt = f"""Given this restaurant:
Restaurant: {restaurant_name}
Location: {location}
Reviews: {reviews_summary}
Cuisine: {cuisine}
Atmosphere: {atmosphere}

Which of these predefined categories does it fit into? {categories_str}

Return ONLY a JSON array of matching category names, with no additional text:
["category1", "category2"]

Only include categories that clearly match. If no categories match, return an empty array []."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            content = response.content[0].text.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error matching user categories: {e}")
            return []


class GoogleProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def extract_restaurants_from_image(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract restaurant information from an image using Gemini Vision."""
        from PIL import Image

        prompt = """Analyze this image of a menu or receipt. Extract the restaurant name and location.
Return ONLY a JSON array in this exact format, with no additional text:
[{"restaurant_name": "Restaurant Name", "location": "City, State or Neighborhood"}]

If you cannot clearly read the restaurant's information, return an empty array []."""

        try:
            image = Image.open(image_path)
            response = self.model.generate_content([prompt, image])

            content = response.text.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error extracting restaurants from image: {e}")
            return []

    def enrich_restaurant_info(self, restaurant_name: str, location: str, missing_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Enrich restaurant information with detailed metadata."""
        if missing_fields:
            fields_prompt = f"Provide ONLY the following information: {', '.join(missing_fields)}"
        else:
            fields_prompt = """Provide the following information:
- full_address (complete street address)
- phone_number (phone number with area code)
- price_range ($, $$, $$$, or $$$$)
- hours_summary (brief summary of operating hours)
- website (restaurant website URL)
- restaurant_type (fine dining, casual, fast-casual, etc.)
- chef_owner (chef or owner name)
- established_year (year restaurant opened)
- cuisine_details (detailed cuisine description)
- signature_dishes (list of must-try dishes)
- dietary_accommodations (list: vegetarian, vegan, gluten-free, etc.)
- atmosphere (description of ambiance/vibe)
- dress_code (casual, business casual, formal, etc.)
- awards (list of awards/recognitions)
- reviews_summary (2-3 sentence critical summary)
- similar_restaurants (list of similar restaurants)
- reservations_info (how to make reservations)
- llm_categories (list of categories like "romantic", "family-friendly", "date night", etc.)"""

        prompt = f"""Provide detailed information about the restaurant "{restaurant_name}" in {location}.

{fields_prompt}

Return ONLY a JSON object in this exact format, with no additional text:
{{
    "full_address": "street address",
    "phone_number": "(xxx) xxx-xxxx",
    "price_range": "$$",
    "hours_summary": "hours summary",
    "website": "https://...",
    "restaurant_type": "fine dining",
    "chef_owner": "chef name",
    "established_year": 2020,
    "cuisine_details": "detailed cuisine description",
    "signature_dishes": ["dish1", "dish2"],
    "dietary_accommodations": ["vegetarian", "vegan"],
    "atmosphere": "ambiance description",
    "dress_code": "casual",
    "awards": ["award1", "award2"],
    "reviews_summary": "2-3 sentence summary",
    "similar_restaurants": ["restaurant1", "restaurant2"],
    "reservations_info": "reservation details",
    "llm_categories": ["romantic", "date night"]
}}

Use null for unavailable single values or [] for unavailable lists."""

        try:
            response = self.model.generate_content(prompt)

            content = response.text.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error enriching restaurant info: {e}")
            return {}

    def match_user_categories(self, restaurant_name: str, location: str, reviews_summary: str, cuisine: str, atmosphere: str, predefined_categories: List[str]) -> List[str]:
        """Match restaurant against predefined user categories."""
        categories_str = ", ".join([f'"{cat}"' for cat in predefined_categories])

        prompt = f"""Given this restaurant:
Restaurant: {restaurant_name}
Location: {location}
Reviews: {reviews_summary}
Cuisine: {cuisine}
Atmosphere: {atmosphere}

Which of these predefined categories does it fit into? {categories_str}

Return ONLY a JSON array of matching category names, with no additional text:
["category1", "category2"]

Only include categories that clearly match. If no categories match, return an empty array []."""

        try:
            response = self.model.generate_content(prompt)

            content = response.text.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)
        except Exception as e:
            print(f"Error matching user categories: {e}")
            return []


def get_provider(config: Dict[str, Any]) -> LLMProvider:
    """Factory function to get the appropriate LLM provider."""
    provider_name = config['llm']['provider']

    if provider_name == 'openai':
        return OpenAIProvider(
            api_key=config['llm']['openai_api_key'],
            model=config['llm']['model']['openai']
        )
    elif provider_name == 'anthropic':
        return AnthropicProvider(
            api_key=config['llm']['anthropic_api_key'],
            model=config['llm']['model']['anthropic']
        )
    elif provider_name == 'google':
        return GoogleProvider(
            api_key=config['llm']['google_api_key'],
            model=config['llm']['model']['google']
        )
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
