import requests
import math
from typing import Optional


class DiscoveryAgent:

    SERPAPI_URL = "https://serpapi.com/search.json"
    PEXELS_URL = "https://api.pexels.com/v1/search"

    def __init__(self, serp_api_key, pexels_api_key, timeout=20):

        if not serp_api_key or not pexels_api_key:
            raise ValueError("SerpAPI and Pexels API keys are required.")

        self.serp_api_key = serp_api_key
        self.pexels_api_key = pexels_api_key
        self.timeout = timeout

        self.session = requests.Session()

    # ---------------------------------------------------------
    # COMMON HELPERS
    # ---------------------------------------------------------

    def _clean_link(self, value):
        """Extract URL from Markdown-style links if necessary."""

        if not value:
            return None

        value = str(value).strip()

        if "](" in value:
            value = value.split("](", 1)[1]
            value = value.rsplit(")", 1)[0]

        value = value.strip().strip("'\"")

        if value.startswith(("http://", "https://")):
            return value

        return None

    def _get_json(self, url, params=None, headers=None):

        response = self.session.get(
            url,
            params=params,
            headers=headers,
            timeout=self.timeout
        )

        response.raise_for_status()

        data = response.json()

        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(f"API error: {data['error']}")

        return data

    # ---------------------------------------------------------
    # 1. SEARCH ATTRACTIONS USING SERPAPI
    # ---------------------------------------------------------

    def search_attractions(
        self,
        city,
        country,
        country_code="us"
    ):

        if not isinstance(city, str) or not city.strip():
            raise ValueError("City must be a non-empty string.")

        if not isinstance(country, str) or not country.strip():
            raise ValueError("Country must be a non-empty string.")

        if not isinstance(country_code, str) or len(country_code) != 2:
            raise ValueError("Country code must contain 2 characters.")

        params = {
            "engine": "google",
            "q": f"top tourist attractions in {city} {country}",
            "api_key": self.serp_api_key,
            "gl": country_code.lower(),
            "hl": "en"
        }

        data = self._get_json(
            self.SERPAPI_URL,
            params=params
        )

        top_sights = data.get("top_sights", {})

        if isinstance(top_sights, dict):
            sights = top_sights.get("sights", [])
        else:
            sights = []

        if not isinstance(sights, list):
            sights = []

        attractions = []

        for sight in sights:

            if not isinstance(sight, dict):
                continue

            title = sight.get("title")

            if not title:
                continue

            price_display = sight.get("price")
            extracted_price = sight.get("extracted_price")

            # Preserve the displayed price.
            # Convert Free to numeric zero when appropriate.
            if extracted_price is not None:
                try:
                    price_amount = float(extracted_price)
                except (TypeError, ValueError):
                    price_amount = None

            elif isinstance(price_display, str) and price_display.lower() == "free":
                price_amount = 0.0

            else:
                price_amount = None

            attractions.append({

                "name": title,

                "rating": sight.get("rating"),

                "reviews": sight.get("reviews"),

                "price_display": price_display,

                "price_amount": price_amount,

                "reported_status": sight.get("description"),

                "google_link": self._clean_link(
                    sight.get("link")
                ),

                "thumbnail": self._clean_link(
                    sight.get("thumbnail")
                )

            })

        return attractions

    # ---------------------------------------------------------
    # 2. RANK ATTRACTIONS
    # ---------------------------------------------------------

    def rank_attractions(self, attractions):

        if not attractions:
            return []

        max_reviews = max(
            [
                math.log1p(a["reviews"])
                for a in attractions
                if isinstance(a.get("reviews"), (int, float))
                and a["reviews"] >= 0
            ],
            default=1
        )

        for attraction in attractions:

            rating = attraction.get("rating")
            reviews = attraction.get("reviews")

            rating_score = 0
            popularity_score = 0

            if isinstance(rating, (int, float)) and 0 <= rating <= 5:
                rating_score = rating / 5

            if isinstance(reviews, (int, float)) and reviews >= 0:
                popularity_score = (
                    math.log1p(reviews) / max_reviews
                    if max_reviews > 0 else 0
                )

            # Rating receives 70%, popularity receives 30%.
            attraction["ranking_score"] = round(
                (0.7 * rating_score) +
                (0.3 * popularity_score),
                4
            )

        return sorted(
            attractions,
            key=lambda a: a["ranking_score"],
            reverse=True
        )

    # ---------------------------------------------------------
    # 3. SEARCH IMAGES USING PEXELS
    # ---------------------------------------------------------

    def get_attraction_images(
        self,
        attraction_name,
        city,
        per_page=1
    ):

        if not attraction_name or not city:
            return []

        params = {
            "query": f"{attraction_name} {city}",
            "per_page": per_page,
            "orientation": "landscape"
        }

        headers = {
            "Authorization": self.pexels_api_key
        }

        data = self._get_json(
            self.PEXELS_URL,
            params=params,
            headers=headers
        )

        photos = data.get("photos", [])

        images = []

        for photo in photos:

            if not isinstance(photo, dict):
                continue

            src = photo.get("src", {})

            images.append({

                "image_id": photo.get("id"),

                "image_url": self._clean_link(
                    src.get("large")
                ),

                "photographer": photo.get("photographer"),

                "photographer_url": self._clean_link(
                    photo.get("photographer_url")
                ),

                "pexels_url": self._clean_link(
                    photo.get("url")
                ),

                "alt": photo.get("alt")

            })

        return images

    # ---------------------------------------------------------
    # 4. COMBINE ATTRACTIONS AND IMAGES
    # ---------------------------------------------------------


    def get_discovery_report(
        self,
        city,
        country,
        country_code="us",
        max_attractions=10,
        max_images=5
    ):

        if not isinstance(max_attractions, int) or max_attractions < 1:
            raise ValueError("max_attractions must be a positive integer.")

        if not isinstance(max_images, int) or max_images < 0:
            raise ValueError("max_images must be a non-negative integer.")

        # Fetch attractions
        attractions = self.search_attractions(
            city,
            country,
            country_code
        )

        # Check whether results were returned
        if not attractions:
            raise RuntimeError(
                f"No attractions were found for {city}, {country}."
            )

        # Rank attractions
        ranked_attractions = self.rank_attractions(attractions)

        # Limit returned attractions
        ranked_attractions = ranked_attractions[:max_attractions]

        # Fetch images
        for index, attraction in enumerate(ranked_attractions):

            attraction["images"] = []

            if index >= max_images:
                continue

            try:
                attraction["images"] = self.get_attraction_images(
                    attraction["name"],
                    city,
                    per_page=1
                )

            except requests.RequestException as error:
                print(
                    f"Image retrieval failed for "
                    f"{attraction['name']}: {error}"
                )

            except Exception as error:
                print(
                    f"Unexpected image error for "
                    f"{attraction['name']}: {error}"
                )

        return {
            "city": city,
            "country": country,
            "total_attractions_found": len(attractions),
            "attractions": ranked_attractions
        }
