"""Natural-language clarification parsing and indicative expense estimates."""
import json
import re
import re
from datetime import datetime

def parse_clarification_reply(user_reply, parsed_request, llm):
    if not user_reply or not user_reply.strip():
        raise ValueError("Please enter your answer.")

    requirements = parsed_request.get("requirements", parsed_request)

    prompt = f"""
You are the clarification-answer parser for a travel planning system.

Existing trip details:
{json.dumps(requirements, default=str)}

User's clarification reply:
{user_reply}

Extract ONLY information explicitly stated or clearly implied by the user's reply.

Return valid JSON with these possible fields:
{{
  "departure_date": "YYYY-MM-DD or null",
  "origin_airport_code": "IATA code or null",
  "destination_airport_code": "IATA code or null",
  "expenses": {{
    "flights": number,
    "accommodation": number,
    "food": number,
    "local_transport": number,
    "activities": number
  }},
  "expense_currency": "three-letter currency code or null",
  "estimate_expenses": true or false
}}

Rules:
1. Heathrow = LHR, Gatwick = LGW, Stansted = STN,
   Haneda = HND, Narita = NRT.
2. Do not invent a departure date.
3. Only include expense categories when the user provides estimates.
4. If the user asks you to estimate expenses, set estimate_expenses=true.
5. Do not invent expense amounts.
6. Use the trip's existing year when a date is given without a year.
7. Return JSON only. Use null for unknown fields.
"""

    response = llm.generate_with_fallback(
        prompt=prompt,
        system_prompt="Extract travel clarification information accurately. Return only valid JSON."
    )

    raw_text = response.get("text", "").strip()

    # Handle accidental Markdown fences.
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        answers = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Could not understand the reply. Please rephrase it. Parser output: {raw_text}"
        ) from error

    if not isinstance(answers, dict):
        raise ValueError("The parser did not return a valid answer object.")

    # Remove fields that the user did not provide.
    answers = {
        key: value for key, value in answers.items()
        if value is not None
    }

    return answers


import json
import re

def estimate_travel_expenses(parsed_request, llm, currency="INR"):
    requirements = parsed_request.get("requirements", parsed_request)

    prompt = f"""
Create a realistic, approximate travel expense breakdown.

Trip details:
- Origin: {requirements.get('origin')}
- Destination: {requirements.get('destination')}
- Country: {requirements.get('country')}
- Duration: {requirements.get('duration_days')} days
- Departure date: {requirements.get('departure_date')}
- Passengers: {requirements.get('passengers', 1)}
- Origin airport: {requirements.get('origin_airport_code')}
- Destination airport: {requirements.get('destination_airport_code')}
- Currency: {currency}
- Total budget: {requirements.get('budget')} {requirements.get('budget_currency')}

Return ONLY valid JSON:
{{
  "flights": 0,
  "accommodation": 0,
  "food": 0,
  "local_transport": 0,
  "activities": 0
}}

Requirements:
- All values must be positive numeric estimates in {currency}.
- Estimate for the entire trip and all passengers.
- Account for the stated duration.
- Include a reasonable one-way flight estimate.
- Do not force the total to fit the budget.
- These are approximate planning estimates, NOT live prices.
"""

    response = llm.generate_with_fallback(
        prompt=prompt,
        system_prompt="You are a travel cost estimation assistant. Return only valid JSON."
    )

    raw = response["text"].strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    expenses = json.loads(raw)

    categories = [
        "flights", "accommodation", "food",
        "local_transport", "activities"
    ]

    for category in categories:
        value = expenses.get(category)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"Invalid estimated value for {category}: {value}")

    expenses["total_estimated"] = sum(
        expenses[category] for category in categories
    )

    return expenses


def process_conversational_reply(user_reply, parsed_request, orchestrator):
    answers = parse_clarification_reply(
        user_reply, parsed_request, orchestrator.llm
    )
    if answers.get("estimate_expenses"):
        currency = answers.get("expense_currency", "INR")
        estimates = estimate_travel_expenses(
            parsed_request, orchestrator.llm, currency=currency
        )
        estimates.pop("total_estimated", None)
        answers["expenses"] = estimates
        answers["expense_currency"] = currency
    answers.pop("estimate_expenses", None)
    return orchestrator.run_trip(
        parsed_request=parsed_request, answers=answers
    )
