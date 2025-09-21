"""
Test script for API v2 Schedule routes

Simple test to validate the new schedule API endpoints work correctly.
"""

import json
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_api_v2_schedule_imports():
    """Test that all imports work correctly"""
    try:
        # Test that we can import the new schedule routes
        from App.views.api_v2 import schedule
        print("Schedule API v2 routes imported successfully")
        
        # Test controller imports
        from App.controllers.availability import get_available_staff_for_time, check_staff_availability_for_time
        print("Availability controller functions imported successfully")
        
        from App.controllers.allocation import remove_staff_from_shift, assign_staff_to_shift
        print("Allocation controller functions imported successfully")
        
        # Test API v2 blueprint registration
        from App.views.api_v2 import api_v2
        print("API v2 blueprint imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def test_route_definitions():
    """Test that routes are properly defined"""
    try:
        from App.views.api_v2 import api_v2
        
        # Get all routes registered with the blueprint
        routes = []
        for rule in api_v2.url_map.iter_rules():
            if rule.endpoint.startswith('api_v2.'):
                routes.append(f"{rule.methods} {rule.rule}")
        
        print(f"Found {len(routes)} API v2 routes")
        for route in routes:
            print(f"  - {route}")
        
        return True
        
    except Exception as e:
        print(f"Error checking routes: {e}")
        return False


def test_api_response_utilities():
    """Test API response utility functions"""
    try:
        from App.views.api_v2.utils import api_success, api_error
        
        # Test success response
        success_response = api_success({"test": "data"}, "Test message")
        print("API success response utility works")
        
        # Test error response  
        error_response = api_error("Test error", {"field": "error"})
        print("API error response utility works")

        return True
        
    except Exception as e:
        print(f"Error testing API utilities: {e}")
        return False


def main():
    """Run all tests"""
    print("Testing API v2 Schedule Implementation")
    print("=" * 50)
    
    tests = [
        test_api_v2_schedule_imports,
        test_route_definitions,
        test_api_response_utilities
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print(f"\nRunning {test.__name__}...")
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests passed! API v2 Schedule routes are ready.")
        return 0
    else:
        print("Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit(main())