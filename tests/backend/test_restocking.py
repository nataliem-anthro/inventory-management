"""
Tests for restocking API endpoints (recommendations + submitted orders).
"""
from datetime import datetime

import pytest


class TestRestockingRecommendations:
    """Test suite for the budget-constrained recommendations endpoint."""

    def test_demand_forecasts_include_unit_cost(self, client):
        """Demand forecasts must expose unit_cost so the budget math works."""
        response = client.get("/api/demand")
        assert response.status_code == 200

        data = response.json()
        assert len(data) > 0
        for forecast in data:
            assert "unit_cost" in forecast
            assert isinstance(forecast["unit_cost"], (int, float))
            assert forecast["unit_cost"] >= 0

    def test_get_recommendations_structure(self, client):
        """Recommendations response has the expected top-level shape."""
        response = client.get("/api/restocking/recommendations?budget=5000")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)
        for key in ("budget", "recommended", "candidates", "total_cost", "remaining_budget"):
            assert key in data

        assert isinstance(data["recommended"], list)
        assert isinstance(data["candidates"], list)
        assert data["budget"] == 5000

    def test_recommended_item_structure(self, client):
        """Each recommended line has the fields the UI and order submit need."""
        response = client.get("/api/restocking/recommendations?budget=5000")
        data = response.json()
        assert len(data["recommended"]) > 0

        for item in data["recommended"]:
            for key in ("item_sku", "item_name", "shortfall", "quantity",
                        "unit_cost", "line_total"):
                assert key in item
            # Order quantity equals the forecast shortfall
            assert item["quantity"] == item["shortfall"]
            assert item["shortfall"] > 0
            # Line total is quantity * unit cost
            assert abs(item["line_total"] - item["quantity"] * item["unit_cost"]) < 0.01

    def test_candidates_only_positive_shortfalls(self, client):
        """Items whose forecast does not exceed current demand are excluded."""
        response = client.get("/api/restocking/recommendations?budget=100000")
        data = response.json()

        # MTR-304 has forecasted (35) < current (50) -> never a candidate
        candidate_skus = [c["item_sku"] for c in data["candidates"]]
        assert "MTR-304" not in candidate_skus

        for c in data["candidates"]:
            assert c["shortfall"] > 0

    def test_recommendations_respect_budget(self, client):
        """Total recommended cost never exceeds the budget."""
        for budget in (0, 100, 1000, 2500, 5000):
            response = client.get(f"/api/restocking/recommendations?budget={budget}")
            data = response.json()
            assert data["total_cost"] <= budget + 0.01
            assert abs(data["remaining_budget"] - (budget - data["total_cost"])) < 0.01

    def test_zero_budget_recommends_nothing(self, client):
        """A zero budget yields no recommended items but still lists candidates."""
        response = client.get("/api/restocking/recommendations?budget=0")
        data = response.json()
        assert data["recommended"] == []
        assert data["total_cost"] == 0
        assert len(data["candidates"]) > 0

    def test_larger_budget_recommends_at_least_as_many(self, client):
        """Increasing the budget should never reduce how much is affordable."""
        small = client.get("/api/restocking/recommendations?budget=500").json()
        large = client.get("/api/restocking/recommendations?budget=5000").json()
        assert large["total_cost"] >= small["total_cost"]
        assert len(large["recommended"]) >= len(small["recommended"])

    def test_full_budget_covers_all_candidates(self, client):
        """A very large budget recommends every positive-shortfall candidate."""
        response = client.get("/api/restocking/recommendations?budget=1000000")
        data = response.json()
        assert len(data["recommended"]) == len(data["candidates"])

    def test_candidates_sorted_by_shortfall_desc(self, client):
        """Candidates are ordered biggest-shortfall-first."""
        response = client.get("/api/restocking/recommendations?budget=5000")
        candidates = response.json()["candidates"]
        shortfalls = [c["shortfall"] for c in candidates]
        assert shortfalls == sorted(shortfalls, reverse=True)

    def test_negative_budget_rejected(self, client):
        """A negative budget is a client error."""
        response = client.get("/api/restocking/recommendations?budget=-50")
        assert response.status_code == 400
        assert "detail" in response.json()


class TestRestockingOrders:
    """Test suite for submitting and listing restocking orders."""

    def _valid_payload(self):
        return {
            "budget": 2500,
            "items": [
                {
                    "item_sku": "WDG-001",
                    "item_name": "Industrial Widget Type A",
                    "quantity": 150,
                    "unit_cost": 12.5,
                    "line_total": 1875.0,
                },
                {
                    "item_sku": "BRG-102",
                    "item_name": "Steel Bearing Assembly",
                    "quantity": 2,
                    "unit_cost": 45.0,
                    "line_total": 90.0,
                },
            ],
        }

    def test_create_restock_order(self, client):
        """Submitting a valid order returns the created order with metadata."""
        response = client.post("/api/restocking/orders", json=self._valid_payload())
        assert response.status_code == 200

        order = response.json()
        assert order["status"] == "Submitted"
        assert order["lead_time_days"] == 7
        assert order["order_number"].startswith("RO-")
        assert len(order["items"]) == 2

    def test_create_order_total_value_calculation(self, client):
        """total_value equals the sum of line totals."""
        payload = self._valid_payload()
        order = client.post("/api/restocking/orders", json=payload).json()
        expected = sum(i["line_total"] for i in payload["items"])
        assert abs(order["total_value"] - expected) < 0.01

    def test_create_order_lead_time_dates(self, client):
        """Expected delivery is exactly 7 days after the order date."""
        order = client.post("/api/restocking/orders", json=self._valid_payload()).json()
        order_date = datetime.strptime(order["order_date"], "%Y-%m-%d")
        expected_delivery = datetime.strptime(order["expected_delivery"], "%Y-%m-%d")
        assert (expected_delivery - order_date).days == 7

    def test_create_order_empty_items_rejected(self, client):
        """An order with no items is a client error."""
        response = client.post("/api/restocking/orders", json={"budget": 1000, "items": []})
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_create_order_missing_fields_rejected(self, client):
        """Malformed item payloads fail Pydantic validation."""
        bad = {"budget": 1000, "items": [{"item_sku": "WDG-001"}]}
        response = client.post("/api/restocking/orders", json=bad)
        assert response.status_code == 422

    def test_get_restock_orders_returns_list(self, client):
        """The list endpoint always returns an array."""
        response = client.get("/api/restocking/orders")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_submitted_order_appears_in_list_newest_first(self, client):
        """A newly submitted order is retrievable and listed first."""
        created = client.post("/api/restocking/orders", json=self._valid_payload()).json()

        listed = client.get("/api/restocking/orders").json()
        assert len(listed) > 0
        # Newest first: the order we just created is at the front
        assert listed[0]["id"] == created["id"]
        assert listed[0]["order_number"] == created["order_number"]

    def test_submitted_order_item_structure(self, client):
        """Listed orders preserve full line-item detail."""
        client.post("/api/restocking/orders", json=self._valid_payload())
        order = client.get("/api/restocking/orders").json()[0]
        for item in order["items"]:
            for key in ("item_sku", "item_name", "quantity", "unit_cost", "line_total"):
                assert key in item
