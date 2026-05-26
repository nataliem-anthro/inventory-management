"""
Tests for the to-do tasks API endpoints (list, create, toggle, delete).

The tasks store is an in-memory list seeded from data/tasks.json and mutated
during the server session, so these tests use relative assertions and clean up
the tasks they create rather than asserting on exact counts.
"""
import pytest


VALID_PRIORITIES = {"high", "medium", "low"}
VALID_STATUSES = {"pending", "completed"}


def _make_task(client, title="Test task", priority="medium", due_date="2026-06-01"):
    """Create a task and return its JSON body."""
    response = client.post(
        "/api/tasks",
        json={"title": title, "priority": priority, "dueDate": due_date},
    )
    assert response.status_code == 201
    return response.json()


class TestGetTasks:
    """Test suite for GET /api/tasks."""

    def test_get_all_tasks(self, client):
        """Returns a non-empty list (seeded) of well-structured tasks."""
        response = client.get("/api/tasks")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first = data[0]
        for key in ("id", "title", "priority", "dueDate", "status"):
            assert key in first

    def test_task_field_types(self, client):
        """Every task field is a string."""
        data = client.get("/api/tasks").json()
        for task in data:
            assert isinstance(task["id"], str)
            assert isinstance(task["title"], str)
            assert isinstance(task["priority"], str)
            assert isinstance(task["dueDate"], str)
            assert isinstance(task["status"], str)

    def test_task_priority_values(self, client):
        """Every task has a valid priority."""
        data = client.get("/api/tasks").json()
        for task in data:
            assert task["priority"] in VALID_PRIORITIES

    def test_task_status_values(self, client):
        """Every task has a valid status."""
        data = client.get("/api/tasks").json()
        for task in data:
            assert task["status"] in VALID_STATUSES


class TestCreateTask:
    """Test suite for POST /api/tasks."""

    def test_create_task_returns_201_and_task(self, client):
        """A valid create returns 201 with the new task, defaulting to pending."""
        task = _make_task(client, title="Review supplier contracts", priority="high",
                           due_date="2026-07-01")
        assert task["title"] == "Review supplier contracts"
        assert task["priority"] == "high"
        assert task["dueDate"] == "2026-07-01"
        assert task["status"] == "pending"
        assert isinstance(task["id"], str) and task["id"]
        # cleanup
        client.delete(f"/api/tasks/{task['id']}")

    def test_create_task_trims_title(self, client):
        """Leading/trailing whitespace is stripped from the title."""
        task = _make_task(client, title="   Padded title   ")
        assert task["title"] == "Padded title"
        client.delete(f"/api/tasks/{task['id']}")

    def test_create_task_default_priority(self, client):
        """Omitting priority defaults to medium."""
        response = client.post("/api/tasks", json={"title": "No priority", "dueDate": "2026-06-15"})
        assert response.status_code == 201
        task = response.json()
        assert task["priority"] == "medium"
        client.delete(f"/api/tasks/{task['id']}")

    def test_create_task_appears_newest_first(self, client):
        """A newly created task is listed at the front."""
        task = _make_task(client, title="Front of list")
        listed = client.get("/api/tasks").json()
        assert listed[0]["id"] == task["id"]
        assert listed[0]["title"] == "Front of list"
        client.delete(f"/api/tasks/{task['id']}")

    def test_create_task_generates_unique_ids(self, client):
        """Two creates yield distinct ids."""
        a = _make_task(client, title="A")
        b = _make_task(client, title="B")
        assert a["id"] != b["id"]
        client.delete(f"/api/tasks/{a['id']}")
        client.delete(f"/api/tasks/{b['id']}")

    def test_create_task_invalid_priority_rejected(self, client):
        """An unknown priority is a client error (400)."""
        response = client.post(
            "/api/tasks",
            json={"title": "Bad priority", "priority": "urgent", "dueDate": "2026-06-01"},
        )
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_create_task_empty_title_rejected(self, client):
        """A blank title is a client error (400)."""
        response = client.post(
            "/api/tasks",
            json={"title": "   ", "priority": "low", "dueDate": "2026-06-01"},
        )
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_create_task_missing_due_date_rejected(self, client):
        """A missing required field fails Pydantic validation (422)."""
        response = client.post("/api/tasks", json={"title": "No due date", "priority": "low"})
        assert response.status_code == 422


class TestToggleTask:
    """Test suite for PATCH /api/tasks/{id}."""

    def test_toggle_flips_status(self, client):
        """Toggling moves pending -> completed -> pending."""
        task = _make_task(client, title="Toggle me")
        assert task["status"] == "pending"

        toggled = client.patch(f"/api/tasks/{task['id']}")
        assert toggled.status_code == 200
        assert toggled.json()["status"] == "completed"

        toggled_back = client.patch(f"/api/tasks/{task['id']}")
        assert toggled_back.status_code == 200
        assert toggled_back.json()["status"] == "pending"

        client.delete(f"/api/tasks/{task['id']}")

    def test_toggle_nonexistent_task(self, client):
        """Toggling an unknown id returns 404."""
        response = client.patch("/api/tasks/does-not-exist")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestDeleteTask:
    """Test suite for DELETE /api/tasks/{id}."""

    def test_delete_removes_task(self, client):
        """A deleted task is gone and no longer toggleable."""
        task = _make_task(client, title="Delete me")
        task_id = task["id"]

        response = client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == task_id
        assert body["deleted"] is True

        # It should no longer exist
        assert client.patch(f"/api/tasks/{task_id}").status_code == 404
        ids = [t["id"] for t in client.get("/api/tasks").json()]
        assert task_id not in ids

    def test_delete_nonexistent_task(self, client):
        """Deleting an unknown id returns 404."""
        response = client.delete("/api/tasks/does-not-exist")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestTaskLifecycle:
    """End-to-end create -> toggle -> delete flow."""

    def test_full_lifecycle(self, client):
        """Create, complete, then delete a task."""
        task = _make_task(client, title="Lifecycle task", priority="high", due_date="2026-08-01")
        task_id = task["id"]

        completed = client.patch(f"/api/tasks/{task_id}").json()
        assert completed["status"] == "completed"

        assert client.delete(f"/api/tasks/{task_id}").status_code == 200
        assert client.delete(f"/api/tasks/{task_id}").status_code == 404
