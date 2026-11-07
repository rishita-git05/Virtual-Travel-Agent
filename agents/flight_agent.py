from datetime import datetime
import requests
import re


class FlightAgent:

    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.duffel.com/air"

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Duffel-Version": "v2",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def _parse_time(self, value):
        if not value:
            return None

        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    def _duration_minutes(self, start, end):
        start_time = self._parse_time(start)
        end_time = self._parse_time(end)

        if not start_time or not end_time:
            return None

        return int((end_time - start_time).total_seconds() / 60)

    def search_flights(
        self,
        origin,
        destination,
        departure_date,
        passengers=1,
        cabin_class="economy"
    ):

        if not re.fullmatch(r"[A-Za-z]{3}", origin):
            raise ValueError("Origin must be a 3-letter IATA airport code.")

        if not re.fullmatch(r"[A-Za-z]{3}", destination):
            raise ValueError("Destination must be a 3-letter IATA airport code.")

        if origin.upper() == destination.upper():
            raise ValueError("Origin and destination cannot be identical.")

        if passengers < 1:
            raise ValueError("At least one passenger is required.")

        if cabin_class not in {
            "economy", "premium_economy", "business", "first"
        }:
            raise ValueError("Invalid cabin class.")

        departure = datetime.strptime(
            departure_date, "%Y-%m-%d"
        ).date()

        if departure <= datetime.now().date():
            raise ValueError("Departure date must be in the future.")

        payload = {
            "data": {
                "slices": [{
                    "origin": origin.upper(),
                    "destination": destination.upper(),
                    "departure_date": departure_date
                }],
                "passengers": [
                    {"type": "adult"} for _ in range(passengers)
                ],
                "cabin_class": cabin_class
            }
        }

        response = requests.post(
            f"{self.base_url}/offer_requests",
            headers=self._headers(),
            json=payload,
            params={"supplier_timeout": 20000},
            timeout=70
        )

        response.raise_for_status()

        data = response.json()["data"]

        offers = [
            self._normalise_offer(offer)
            for offer in data.get("offers", [])
        ]

        return {
            "request_id": data.get("id"),
            "live_mode": data.get("live_mode"),
            "search": {
                "origin": origin.upper(),
                "destination": destination.upper(),
                "departure_date": departure_date,
                "passengers": passengers,
                "cabin_class": cabin_class
            },
            "total_offers": len(offers),
            "offers": offers
        }

    def _normalise_offer(self, offer):

        slices = offer.get("slices", [])

        segments = []
        total_stops = 0
        total_duration = 0

        for slice_data in slices:

            slice_segments = slice_data.get("segments", [])

            total_stops += max(0, len(slice_segments) - 1)

            if slice_segments:
                first_segment = slice_segments[0]
                last_segment = slice_segments[-1]

                duration = self._duration_minutes(
                    first_segment.get("departing_at"),
                    last_segment.get("arriving_at")
                )

                if duration is not None:
                    total_duration += duration

            for segment in slice_segments:

                segments.append({
                    "airline": segment.get(
                        "operating_carrier", {}
                    ).get("name"),

                    "flight_number": segment.get("operating_carrier_flight_number"),

                    "origin": segment.get(
                        "origin", {}
                    ).get("iata_code"),

                    "destination": segment.get(
                        "destination", {}
                    ).get("iata_code"),

                    "departure": segment.get("departing_at"),
                    "arrival": segment.get("arriving_at")
                })

        return {
            "offer_id": offer.get("id"),
            "airline": offer.get("owner", {}).get("name"),
            "price": float(offer.get("total_amount", 0)),
            "currency": offer.get("total_currency"),
            "stops": total_stops,
            "duration_minutes": total_duration,
            "segments": segments
        }

    def rank_offers(self, offers, preference="balanced"):

        if preference == "cheapest":
            return sorted(
                offers,
                key=lambda x: (x["price"], x["duration_minutes"])
            )

        if preference == "fastest":
            return sorted(
                offers,
                key=lambda x: (x["duration_minutes"], x["price"])
            )

        if preference == "direct":
          direct_flights = [
              offer for offer in offers
              if offer["stops"] == 0
          ]

          if direct_flights:
              return sorted(
                  direct_flights,
                  key=lambda x: (x["price"], x["duration_minutes"])
              )

          print("No direct flights available.")
          print("Showing flights with the fewest stops instead.")

          return sorted(
              offers,
              key=lambda x: (
                  x["stops"],
                  x["price"],
                  x["duration_minutes"]
              )
          )

        if preference == "balanced":
          min_price = min(x["price"] for x in offers)
          max_price = max(x["price"] for x in offers)

          min_duration = min(x["duration_minutes"] for x in offers)
          max_duration = max(x["duration_minutes"] for x in offers)

          def normalize(value, minimum, maximum):
              if maximum == minimum:
                  return 0
              return (value - minimum) / (maximum - minimum)

          for offer in offers:
              price_score = normalize(
                  offer["price"], min_price, max_price
              )

              duration_score = normalize(
                  offer["duration_minutes"],
                  min_duration,
                  max_duration
              )

              offer["balanced_score"] = (
                  0.5 * price_score +
                  0.5 * duration_score
              )

          return sorted(
              offers,
              key=lambda x: x["balanced_score"]
          )

        raise ValueError("Unknown ranking preference.")
