import unittest
from datetime import date, timedelta
from agents.flight_agent import FlightAgent
from agents.budget_agent import BudgetAgent

class ValidationTests(unittest.TestCase):
    def test_flight_agent_rejects_bad_airport_code(self):
        agent = FlightAgent("dummy")
        with self.assertRaises(ValueError):
            agent.search_flights("LONDON", "HND", (date.today()+timedelta(days=10)).isoformat())

    def test_flight_agent_rejects_same_airport(self):
        agent = FlightAgent("dummy")
        with self.assertRaises(ValueError):
            agent.search_flights("LHR", "LHR", (date.today()+timedelta(days=10)).isoformat())

    def test_budget_currency_validation(self):
        agent = BudgetAgent("dummy")
        self.assertEqual(agent._validate_currency("inr"), "INR")
        with self.assertRaises(ValueError):
            agent._validate_currency("IN")

    def test_budget_amount_validation(self):
        agent = BudgetAgent("dummy")
        with self.assertRaises(ValueError):
            agent._validate_amount(-1)
        with self.assertRaises(ValueError):
            agent._validate_amount(True)

if __name__ == "__main__":
    unittest.main()
