"""
Test script for Gemini API integration
"""

import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_gemini_api():
    """Test Gemini API connection and basic functionality"""
    print("🧪 Testing Gemini API Integration")
    print("=" * 50)
    
    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment variables")
        print("   Please add GEMINI_API_KEY to your .env file")
        return False
    
    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Create model instance - using gemini-2.0-flash as per user's API endpoint
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Test basic generation
        print("\n📤 Test 1: Basic text generation")
        response = model.generate_content("What is PostgreSQL? Give a brief one-sentence answer.")
        print(f"✅ Response: {response.text}")
        
        # Test JSON-structured response
        print("\n📤 Test 2: JSON structured response")
        prompt = """
        Analyze this query and return a JSON object with the following structure:
        {
            "intent": "SELECT|UPDATE|DELETE|INSERT",
            "confidence": 0.0-1.0,
            "keywords": ["list", "of", "keywords"],
            "table_mentioned": "table_name or null"
        }
        
        Query: "show me all users from the database"
        """
        response = model.generate_content(prompt)
        print(f"✅ Response: {response.text}")
        
        print("\n🎉 Gemini API integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Gemini API: {e}")
        return False

if __name__ == "__main__":
    success = test_gemini_api()
    if not success:
        print("\n⚠️  Make sure:")
        print("   1. You have added GEMINI_API_KEY to your .env file")
        print("   2. Your API key is valid and active")
        print("   3. You have internet connectivity")
        print("   4. The model 'gemini-2.0-flash' is available for your API key") 