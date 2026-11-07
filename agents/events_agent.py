import requests
import re


class EventsAgent:

    BASE_URL = "https://serpapi.com/search.json"

    def __init__(self, api_key):
        if not api_key:
            raise ValueError("SerpAPI key is required.")

        self.api_key = api_key
        self.session = requests.Session()

    def _clean_link(self, value):
      """Extract the actual URL from a Markdown-style link."""

      if not value:
          return None

      value = str(value).strip()

      # Extract URL between parentheses in [text](URL)
      if "](" in value:
          value = value.split("](", 1)[1]
          value = value.rsplit(")", 1)[0]

      # Remove surrounding whitespace and quotes
      value = value.strip().strip("'\"")

      return value if value.startswith(("http://", "https://")) else None

    def _get(self, params):
        """Send a request to SerpAPI and handle API errors."""

        params["api_key"] = self.api_key

        response = self.session.get(
            self.BASE_URL,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        if "error" in data:
            raise RuntimeError(data["error"])

        return data

    def search_events(
        self,
        city,
        month,
        year,
        max_events=5,
        country_code="us"
    ):
        """Search events and retrieve detailed information."""

        # ---------------- INPUT VALIDATION ----------------

        if not isinstance(city, str) or not city.strip():
            raise ValueError("City cannot be empty.")

        if not isinstance(month, str) or not month.strip():
            raise ValueError("Month cannot be empty.")

        if not isinstance(year, int) or year < 2026:
            raise ValueError("Please provide a valid future year.")

        if not isinstance(max_events, int) or not 1 <= max_events <= 10:
            raise ValueError("max_events must be between 1 and 10.")

        if (
            not isinstance(country_code, str)
            or not re.fullmatch(r"[a-zA-Z]{2}", country_code.strip())
        ):
            raise ValueError("country_code must be a valid two-letter country code.")

        city = city.strip()
        month = month.strip()
        country_code = country_code.strip().lower()

        # ---------------- EVENT SEARCH ----------------

        query = f"events in {city} {month} {year}"

        search_data = self._get({
            "engine": "google",
            "q": query,
            "gl": country_code,
            "hl": "en"
        })

        search_results = search_data.get("events_results") or []

        if not isinstance(search_results, list) or not search_results:
            return []

        normalized_events = []

        # ---------------- PROCESS EACH EVENT ----------------

        for event in search_results[:max_events]:

            if not isinstance(event, dict):
                continue

            details = {}

            # Fetch detailed information using event token.
            token = event.get("event_token")

            if token:
                try:
                    details_data = self._get({
                        "engine": "google_event_details",
                        "event_token": token,
                        "gl": country_code,
                        "hl": "en"
                    })

                    details = details_data.get("event_details") or {}

                    if not isinstance(details, dict):
                        details = {}

                except (requests.RequestException, RuntimeError) as e:
                    print(f"Could not fetch event details: {e}")

            # ---------------- DATE EXTRACTION ----------------

            date_info = details.get("date") or {}

            if not isinstance(date_info, dict):
                date_info = {}

            event_date = (
                date_info.get("when")
                or date_info.get("start_date")
                or event.get("date")
            )

            # ---------------- VENUE EXTRACTION ----------------

            venue_info = details.get("venue") or {}

            if not isinstance(venue_info, dict):
                venue_info = {}

            search_address = event.get("address") or []

            if isinstance(search_address, list):
                fallback_venue = (
                    search_address[0] if search_address else None
                )
            else:
                fallback_venue = None

            venue_name = (
                venue_info.get("name")
                or fallback_venue
            )

            # ---------------- ADDRESS EXTRACTION ----------------

            address = (
                details.get("address")
                or event.get("address")
                or []
            )

            if isinstance(address, list):
                address = ", ".join(
                    str(part) for part in address if part
                )
            elif not isinstance(address, str):
                address = str(address)

            # ---------------- VENUE URL ----------------

            venue_url = self._clean_link(
                venue_info.get("link")
            )

            # ---------------- TICKET SOURCES ----------------

            raw_tickets = details.get("ticket_info") or []

            ticket_sources = []

            if isinstance(raw_tickets, list):

                for ticket in raw_tickets:

                    if not isinstance(ticket, dict):
                        continue

                    ticket_sources.append({
                        "source": ticket.get("source"),
                        "url": self._clean_link(
                            ticket.get("link")
                        )
                    })

            # ---------------- IMAGE EXTRACTION ----------------

            image_url = self._clean_link(
                details.get("thumbnail")
                or event.get("thumbnail")
            )

            # ---------------- NORMALIZED EVENT ----------------

            normalized_events.append({

                "title": (
                    details.get("title")
                    or event.get("title")
                ),

                "date": event_date,

                "venue": venue_name,

                "venue_type": venue_info.get("type"),

                "venue_rating": venue_info.get("rating"),

                "venue_reviews": venue_info.get("reviews"),

                "address": address,

                "description": details.get("description"),

                "price": details.get("price"),

                "venue_url": venue_url,

                "ticket_sources": ticket_sources,

                "image": image_url,

                "details_available": bool(details)
            })

        return normalized_events
