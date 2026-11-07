import requests
import re
import math


class BudgetAgent:

    BASE_URL = "https://v6.exchangerate-api.com/v6"

    def __init__(self, api_key):
        if not api_key:
            raise ValueError("ExchangeRate API key is required.")

        self.api_key = api_key
        self.session = requests.Session()

    def _validate_currency(self, currency):
        if not isinstance(currency, str):
            raise ValueError("Currency must be a string.")

        currency = currency.strip().upper()

        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError(
                "Currency must be a valid three-letter code, e.g. USD or INR."
            )

        return currency

    def _validate_amount(self, amount):
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError("Amount must be a number.")

        if not math.isfinite(amount) or amount < 0:
            raise ValueError("Amount must be finite and non-negative.")

        return float(amount)

    def get_exchange_rates(self, base_currency="USD"):

        base_currency = self._validate_currency(base_currency)

        url = (
            f"{self.BASE_URL}/{self.api_key}/latest/{base_currency}"
        )

        response = self.session.get(url, timeout=20)
        response.raise_for_status()

        data = response.json()

        if data.get("result") != "success":
            raise RuntimeError(
                f"ExchangeRate API error: "
                f"{data.get('error-type', 'Unknown error')}"
            )

        return {
            "base_currency": data["base_code"],
            "last_updated": data.get("time_last_update_utc"),
            "rates": data["conversion_rates"]
        }

    def convert_currency(self, amount, from_currency, to_currency):

        amount = self._validate_amount(amount)
        from_currency = self._validate_currency(from_currency)
        to_currency = self._validate_currency(to_currency)

        if from_currency == to_currency:
            return {
                "amount": amount,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "exchange_rate": 1.0,
                "converted_amount": amount
            }

        exchange_data = self.get_exchange_rates(from_currency)
        rates = exchange_data["rates"]

        if to_currency not in rates:
            raise ValueError(
                f"Currency {to_currency} is not supported by the API."
            )

        rate = rates[to_currency]
        converted_amount = amount * rate

        return {
            "amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": rate,
            "converted_amount": round(converted_amount, 2)
        }

    def calculate_budget(
    self,
    expenses,
    source_currency,
    target_currency,
    budget_limit=None
    ):
        """
        expenses: dictionary such as
        {
            "flights": 500,
            "hotel": 300,
            "food": 150
        }

        All expense amounts must use source_currency.
        Budget limit must use target_currency.
        """

        if not isinstance(expenses, dict) or not expenses:
            raise ValueError("Expenses must be a non-empty dictionary.")

        source_currency = self._validate_currency(source_currency)
        target_currency = self._validate_currency(target_currency)

        if budget_limit is not None:
            budget_limit = self._validate_amount(budget_limit)

        for category, amount in expenses.items():

            if not isinstance(category, str) or not category.strip():
                raise ValueError("Expense categories must have valid names.")

            self._validate_amount(amount)

        # Get exchange rate
        if source_currency == target_currency:
            rate = 1.0

        else:
            exchange_data = self.get_exchange_rates(source_currency)
            rates = exchange_data["rates"]

            if target_currency not in rates:
                raise ValueError(
                    f"Currency {target_currency} is not supported."
                )

            rate = rates[target_currency]

        # Convert expenses
        converted_expenses = {
            category: round(amount * rate, 2)
            for category, amount in expenses.items()
        }

        # Calculate total
        total_expenses = round(sum(converted_expenses.values()), 2)

        # Create result
        result = {
            "source_currency": source_currency,
            "target_currency": target_currency,
            "exchange_rate": rate,
            "expenses": converted_expenses,
            "total_expenses": total_expenses,
            "budget_limit": budget_limit,
            "remaining_budget": None,
            "within_budget": None,
            "budget_utilization_percent": None,
            "budget_status": "NOT ASSESSED"
        }

        # Budget evaluation
        if budget_limit is not None:

            remaining = round(budget_limit - total_expenses, 2)

            result["remaining_budget"] = remaining
            result["within_budget"] = remaining >= 0

            if budget_limit == 0:

                utilization = 0 if total_expenses == 0 else None

                status = (
                    "ZERO BUDGET"
                    if total_expenses == 0
                    else "OVER BUDGET"
                )

            else:

                utilization = round(
                    (total_expenses / budget_limit) * 100, 2
                )

                if utilization < 80:
                    status = "COMFORTABLE"

                elif utilization < 90:
                    status = "MODERATE"

                elif utilization <= 100:
                    status = "TIGHT"

                else:
                    status = "OVER BUDGET"

            result["budget_utilization_percent"] = utilization
            result["budget_status"] = status

        return result
