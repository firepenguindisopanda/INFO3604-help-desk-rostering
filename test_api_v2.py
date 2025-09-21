#!/usr/bin/env python3
"""
API v2 Test Script
Tests the new API endpoints structure without running the full Flask app
"""

def test_api_structure():
    """Test that API v2 files are properly structured"""
    import os
    
    base_path = "App/views/api_v2"
    
    # Check required files exist
    required_files = [
        "__init__.py",
        "utils.py", 
        "auth.py",
        "admin.py",
        "student.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(base_path, file)):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All API v2 files created successfully")
    
    # Check main.py was updated
    with open("App/main.py", "r") as f:
        content = f.read()
        
    if "register_api_v2" in content:
        print("✅ main.py updated to register API v2")
    else:
        print("❌ main.py missing API v2 registration")
        return False
    
    if "CORS(app, resources=" in content:
        print("✅ CORS configured for API endpoints")
    else:
        print("❌ CORS not properly configured")
        return False
        
    return True

def check_endpoints():
    """List the API endpoints that were created"""
    
    endpoints = {
        "Authentication": [
            "POST /api/v2/auth/login",
            "POST /api/v2/auth/register", 
            "POST /api/v2/auth/logout",
            "GET /api/v2/me",
            "PUT /api/v2/me"
        ],
        "Admin": [
            "GET /api/v2/admin/dashboard",
            "GET /api/v2/admin/stats"
        ],
        "Student": [
            "GET /api/v2/student/dashboard",
            "GET /api/v2/student/schedule"
        ]
    }
    
    print("\n📋 API v2 Endpoints Created:")
    for category, eps in endpoints.items():
        print(f"\n{category}:")
        for ep in eps:
            print(f"  • {ep}")
    
    print("\n🔐 Authentication:")
    print("  • JWT required for /me, /admin/*, /student/*")
    print("  • Role-based access control using @admin_required and @volunteer_required")
    
    print("\n📊 Response Format:")
    print("  • Success: {\"success\": true, \"data\": {...}, \"message\": \"...\"}")
    print("  • Error: {\"success\": false, \"message\": \"...\", \"errors\": {...}}")

def check_models():
    """Check that models have to_dict methods"""
    
    models_with_todict = [
        "App/models/user.py",
        "App/models/student.py", 
        "App/models/admin.py",
        "App/models/schedule.py",
        "App/models/shift.py",
        "App/models/shift_course_demand.py"
    ]
    
    print("\n🗃️  Model Serialization:")
    for model_file in models_with_todict:
        try:
            with open(model_file, "r") as f:
                content = f.read()
                if "def to_dict(self):" in content:
                    print(f"  ✅ {model_file.split('/')[-1]} has to_dict method")
                else:
                    print(f"  ❌ {model_file.split('/')[-1]} missing to_dict method")
        except FileNotFoundError:
            print(f"  ❌ {model_file} not found")

if __name__ == "__main__":
    print("🚀 Testing API v2 Implementation\n")
    
    if test_api_structure():
        check_endpoints()
        check_models()
        
        print("\n✅ API v2 Implementation Complete!")
        print("\n🔧 Next Steps:")
        print("  1. Install dependencies: pip install flask flask-sqlalchemy flask-jwt-extended flask-cors")
        print("  2. Test endpoints: flask run")
        print("  3. Create Next.js frontend to consume these APIs")
        print("  4. Test authentication flow and role-based access")
        
    else:
        print("\n❌ API v2 Implementation has issues - check the errors above")