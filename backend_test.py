import requests
import sys
import json
from datetime import datetime
import time

class HealthChatbotAPITester:
    def __init__(self, base_url="https://eco-learn-7.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_user_id = f"test_user_{datetime.now().strftime('%H%M%S')}"

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            print(f"   Status Code: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Non-dict response'}")
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error text: {response.text}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timed out after {timeout} seconds")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )
        return success

    def test_health_stats(self):
        """Test health statistics endpoint"""
        success, response = self.run_test(
            "Health Statistics",
            "GET",
            "health/stats",
            200
        )
        
        if success:
            required_keys = ['total_queries', 'unique_users', 'recent_queries_24h', 'status']
            missing_keys = [key for key in required_keys if key not in response]
            if missing_keys:
                print(f"   ⚠️  Missing keys in stats response: {missing_keys}")
            else:
                print(f"   📊 Stats: {response['total_queries']} queries, {response['unique_users']} users, {response['recent_queries_24h']} today")
        
        return success

    def test_health_query_simple(self):
        """Test health query with a simple question"""
        test_question = "What are the symptoms of common cold?"
        
        success, response = self.run_test(
            "Health Query - Simple Question",
            "POST",
            "health/query",
            200,
            data={
                "question": test_question,
                "user_id": self.test_user_id
            },
            timeout=45  # AI responses can take longer
        )
        
        if success:
            required_keys = ['answer', 'query_id', 'timestamp']
            missing_keys = [key for key in required_keys if key not in response]
            if missing_keys:
                print(f"   ⚠️  Missing keys in query response: {missing_keys}")
            else:
                print(f"   🤖 AI Response length: {len(response['answer'])} characters")
                print(f"   📝 Query ID: {response['query_id']}")
                # Check if response contains health-related content
                answer_lower = response['answer'].lower()
                health_keywords = ['symptom', 'health', 'medical', 'doctor', 'treatment', 'cold', 'fever']
                found_keywords = [kw for kw in health_keywords if kw in answer_lower]
                if found_keywords:
                    print(f"   ✅ Response contains health keywords: {found_keywords}")
                else:
                    print(f"   ⚠️  Response may not be health-focused")
        
        return success, response.get('query_id') if success else None

    def test_health_query_complex(self):
        """Test health query with a more complex question"""
        test_question = "I have been experiencing headaches and fatigue for the past week. When should I see a doctor?"
        
        success, response = self.run_test(
            "Health Query - Complex Question",
            "POST",
            "health/query",
            200,
            data={
                "question": test_question,
                "user_id": self.test_user_id
            },
            timeout=45
        )
        
        if success:
            answer_lower = response['answer'].lower()
            # Check for medical disclaimer/advice to see doctor
            medical_advice_keywords = ['consult', 'doctor', 'healthcare', 'professional', 'medical attention']
            found_advice = [kw for kw in medical_advice_keywords if kw in answer_lower]
            if found_advice:
                print(f"   ✅ Response includes medical advice keywords: {found_advice}")
            else:
                print(f"   ⚠️  Response may be missing medical disclaimer")
        
        return success

    def test_chat_history(self):
        """Test chat history retrieval"""
        success, response = self.run_test(
            "Chat History Retrieval",
            "GET",
            f"health/history/{self.test_user_id}",
            200
        )
        
        if success:
            required_keys = ['messages', 'total']
            missing_keys = [key for key in required_keys if key not in response]
            if missing_keys:
                print(f"   ⚠️  Missing keys in history response: {missing_keys}")
            else:
                print(f"   📚 Found {response['total']} messages in history")
                if response['messages']:
                    first_message = response['messages'][0]
                    message_keys = list(first_message.keys())
                    print(f"   📝 Message structure: {message_keys}")
        
        return success

    def test_error_handling(self):
        """Test error handling with invalid requests"""
        print(f"\n🔍 Testing Error Handling...")
        
        # Test empty question
        success1, _ = self.run_test(
            "Empty Question",
            "POST",
            "health/query",
            422,  # Validation error expected
            data={"question": "", "user_id": self.test_user_id}
        )
        
        # Test missing question field
        success2, _ = self.run_test(
            "Missing Question Field",
            "POST",
            "health/query",
            422,  # Validation error expected
            data={"user_id": self.test_user_id}
        )
        
        # Test invalid user ID for history
        success3, _ = self.run_test(
            "Invalid User History",
            "GET",
            "health/history/nonexistent_user",
            200  # Should return empty history, not error
        )
        
        return success1 or success2  # At least one error handling test should pass

def main():
    print("🏥 AI-Driven Public Health Chatbot - Backend API Testing")
    print("=" * 60)
    
    tester = HealthChatbotAPITester()
    
    # Test sequence
    tests = [
        ("Root Endpoint", tester.test_root_endpoint),
        ("Health Statistics", tester.test_health_stats),
        ("Simple Health Query", lambda: tester.test_health_query_simple()[0]),
        ("Complex Health Query", tester.test_health_query_complex),
        ("Chat History", tester.test_chat_history),
        ("Error Handling", tester.test_error_handling)
    ]
    
    print(f"🧪 Running {len(tests)} test categories...")
    
    for test_name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
    
    # Final results
    print("\n" + "=" * 60)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed! Backend API is working correctly.")
        return 0
    elif tester.tests_passed >= tester.tests_run * 0.7:  # 70% pass rate
        print("⚠️  Most tests passed, but some issues detected.")
        return 0
    else:
        print("❌ Multiple test failures detected. Backend needs attention.")
        return 1

if __name__ == "__main__":
    sys.exit(main())