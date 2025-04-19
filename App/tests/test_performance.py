from locust import HttpUser, task, between

class PerformanceTests(HttpUser):
    wait_time = between(1, 2)

    @task
    def test_homepage(self):
        response = self.client.get("/")
        assert response.elapsed.total_seconds() < 5, f"Homepage took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_authentication_admin(self):
        response = self.client.post('/login', json={
            "username": "a",
            "password": "123"
        })
        assert response.elapsed.total_seconds() < 5, f"Authentication took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_schedule_generation(self):
        response = self.client.post("/api/schedule/generate", json={})
        assert response.elapsed.total_seconds() < 5, f"Schedule generation took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_get_schedule(self):
        response = self.client.get("/api/schedule")
        assert response.elapsed.total_seconds() < 5, f"Schedule retrieval took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_get_user_profile(self):
        response = self.client.get("/api/profile")
        assert response.elapsed.total_seconds() < 5, f"User profile retrieval took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_create_request(self):
        response = self.client.post("/api/requests", json={
            "request_type": "example",
            "details": "Performance test request"
        })
        assert response.elapsed.total_seconds() < 5, f"Request creation took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_list_requests(self):
        response = self.client.get("/api/requests")
        assert response.elapsed.total_seconds() < 5, f"Request listing took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_get_tracking_data(self):
        response = self.client.get("/api/tracking")
        assert response.elapsed.total_seconds() < 5, f"Tracking data retrieval took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_admin_dashboard(self):
        response = self.client.get("/api/admin/dashboard")
        assert response.elapsed.total_seconds() < 5, f"Admin dashboard took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_volunteer_dashboard(self):
        response = self.client.get("/api/volunteer/dashboard")
        assert response.elapsed.total_seconds() < 5, f"Volunteer dashboard took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_get_notifications(self):
        response = self.client.get("/api/notifications")
        assert response.elapsed.total_seconds() < 5, f"Notifications retrieval took too long to respond, response time: {response.elapsed.total_seconds()} seconds"
