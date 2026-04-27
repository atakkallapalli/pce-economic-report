"""
Load testing with Locust.

Run with: locust -f tests/load/locustfile.py --host=http://localhost:8000
Target: 10,000 concurrent users, p95 < 100ms
"""

import uuid

from locust import HttpUser, between, task


class TaskAPIUser(HttpUser):
    wait_time = between(1, 3)
    token: str = ""
    user_id: str = ""

    def on_start(self):
        email = f"loadtest_{uuid.uuid4().hex[:8]}@test.com"
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "LoadTest1",
                "full_name": "Load Test User",
            },
        )
        if response.status_code == 201:
            data = response.json()
            self.token = data["tokens"]["access_token"]
            self.user_id = data["user"]["id"]

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def list_tasks(self):
        self.client.get("/api/v1/tasks", headers=self.headers)

    @task(2)
    def create_task(self):
        self.client.post(
            "/api/v1/tasks",
            headers=self.headers,
            json={
                "title": f"Load Test Task {uuid.uuid4().hex[:8]}",
                "description": "Created during load testing",
                "priority": "MEDIUM",
            },
        )

    @task(1)
    def health_check(self):
        self.client.get("/health")

    @task(1)
    def search_tasks(self):
        self.client.get(
            "/api/v1/tasks/search?q=load test",
            headers=self.headers,
        )
