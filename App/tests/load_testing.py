"""
Load testing configuration for Help Desk Rostering system
Tests scheduling performance under various load conditions
"""
from locust import HttpUser, task, between
import json
import random
from datetime import datetime, timedelta


class SchedulingLoadTest(HttpUser):
    """Load test for scheduling operations"""
    wait_time = between(1, 3)
    
    def on_start(self):
        """Setup - login and get auth token"""
        self.login()
        self.setup_test_data()
    
    def login(self):
        """Login as admin user"""
        response = self.client.post("/api/v2/auth/login", json={
            "username": "admin",
            "password": "password"  # Use test credentials
        })
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                self.token = data['data']['access_token']
                self.headers = {'Authorization': f'Bearer {self.token}'}
            else:
                self.headers = {}
        else:
            self.headers = {}
    
    def setup_test_data(self):
        """Setup test data for scheduling"""
        self.test_schedules = [
            {
                'name': f'Load Test Schedule {i}',
                'start_date': (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'),
                'end_date': (datetime.now() + timedelta(days=i+7)).strftime('%Y-%m-%d'),
                'type': 'helpdesk'
            }
            for i in range(5)
        ]
    
    @task(3)
    def get_schedules(self):
        """Test schedule listing performance"""
        self.client.get("/api/v2/schedules", headers=self.headers)
    
    @task(2)
    def get_assistants(self):
        """Test assistant listing performance"""
        self.client.get("/api/v2/assistants", headers=self.headers)
    
    @task(2)
    def get_courses(self):
        """Test course listing performance"""
        self.client.get("/api/v2/courses", headers=self.headers)
    
    @task(1)
    def generate_schedule(self):
        """Test schedule generation performance - most intensive operation"""
        schedule_data = random.choice(self.test_schedules)
        
        with self.client.post("/api/v2/schedules/generate", 
                             json=schedule_data, 
                             headers=self.headers,
                             catch_response=True) as response:
            
            # Schedule generation may take longer, so be more lenient
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code in [400, 422]:
                # Expected validation errors don't count as failures
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(1)
    def test_schedule_optimization(self):
        """Test schedule optimization endpoint"""
        optimization_data = {
            'schedule_id': 1,
            'optimization_type': 'fairness',
            'constraints': {
                'max_hours_per_assistant': 20,
                'min_hours_per_assistant': 8
            }
        }
        
        self.client.post("/api/v2/schedules/optimize",
                        json=optimization_data,
                        headers=self.headers)


class VolunteerLoadTest(HttpUser):
    """Load test simulating multiple volunteers accessing the system"""
    wait_time = between(2, 5)
    
    def on_start(self):
        """Login as student/volunteer"""
        self.student_login()
    
    def student_login(self):
        """Login as student user"""
        # Create different student credentials for load testing
        student_id = random.randint(1000, 9999)
        response = self.client.post("/api/v2/auth/login", json={
            "username": f"student{student_id}",
            "password": "password"
        })
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                self.token = data['data']['access_token']
                self.headers = {'Authorization': f'Bearer {self.token}'}
            else:
                self.headers = {}
        else:
            self.headers = {}
    
    @task(3)
    def view_profile(self):
        """Test volunteer profile viewing"""
        self.client.get("/api/v2/volunteer/profile", headers=self.headers)
    
    @task(2)
    def update_availability(self):
        """Test availability updates"""
        availability_data = {
            'availability': [
                {
                    'day_of_week': random.randint(0, 6),
                    'start_time': f"{random.randint(8, 12):02d}:00",
                    'end_time': f"{random.randint(13, 18):02d}:00"
                }
                for _ in range(random.randint(2, 5))
            ]
        }
        
        self.client.post("/api/v2/volunteer/availability",
                        json=availability_data,
                        headers=self.headers)
    
    @task(1)
    def submit_application(self):
        """Test application submission"""
        application_data = {
            'courses': [f"COMP{random.randint(1000, 4000)}" for _ in range(random.randint(2, 4))],
            'experience': random.choice(['beginner', 'intermediate', 'advanced']),
            'preferred_hours': random.randint(8, 20)
        }
        
        self.client.post("/api/v2/volunteer/apply",
                        json=application_data,
                        headers=self.headers)


class AdminLoadTest(HttpUser):
    """Load test for admin operations"""
    wait_time = between(1, 4)
    
    def on_start(self):
        """Login as admin"""
        response = self.client.post("/api/v2/auth/login", json={
            "username": "admin",
            "password": "password"
        })
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                self.token = data['data']['access_token']
                self.headers = {'Authorization': f'Bearer {self.token}'}
            else:
                self.headers = {}
        else:
            self.headers = {}
    
    @task(2)
    def manage_assistants(self):
        """Test assistant management operations"""
        self.client.get("/api/v2/assistants", headers=self.headers)
    
    @task(2)
    def manage_courses(self):
        """Test course management"""
        self.client.get("/api/v2/courses", headers=self.headers)
    
    @task(1)
    def create_course(self):
        """Test course creation"""
        course_data = {
            'code': f"TEST{random.randint(1000, 9999)}",
            'name': f"Test Course {random.randint(1, 100)}",
            'credits': random.choice([3, 4, 6])
        }
        
        self.client.post("/api/v2/courses",
                        json=course_data,
                        headers=self.headers)
    
    @task(1)
    def export_schedule(self):
        """Test schedule export performance"""
        export_data = {
            'schedule_id': 1,
            'format': random.choice(['pdf', 'csv', 'excel'])
        }
        
        self.client.post("/api/v2/schedules/export",
                        json=export_data,
                        headers=self.headers)


# Performance benchmark targets
class PerformanceBenchmarks:
    """Define performance targets for load testing"""
    
    # Response time targets (in milliseconds)
    RESPONSE_TIME_TARGETS = {
        'api_read_operations': 500,      # GET requests should be under 500ms
        'api_write_operations': 1000,    # POST/PUT should be under 1s
        'schedule_generation': 30000,    # Schedule generation under 30s
        'file_exports': 5000            # File exports under 5s
    }
    
    # Throughput targets
    THROUGHPUT_TARGETS = {
        'concurrent_users': 20,          # Support 20 concurrent users
        'requests_per_second': 50,       # Handle 50 requests/second
        'schedule_generations_per_hour': 10  # 10 schedule generations/hour
    }
    
    # Error rate targets
    ERROR_RATE_TARGETS = {
        'max_error_rate': 0.05,         # Less than 5% error rate
        'max_timeout_rate': 0.01        # Less than 1% timeout rate
    }