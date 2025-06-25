#!/usr/bin/env python3
"""
Simple import test to verify path configuration
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_imports():
    """Test all major imports"""
    print("Testing imports...")
    
    try:
        from tools.db_ops import execute_select_query
        print("✅ tools.db_ops import successful")
    except ImportError as e:
        print(f"❌ tools.db_ops import failed: {e}")
        return False
    
    try:
        from agents.orchestrator import OrchestratorAgent
        print("✅ agents.orchestrator import successful")
    except ImportError as e:
        print(f"❌ agents.orchestrator import failed: {e}")
        return False
    
    try:
        from utils.gemini_client import get_gemini_client
        print("✅ utils.gemini_client import successful")
    except ImportError as e:
        print(f"❌ utils.gemini_client import failed: {e}")
        return False
    
    try:
        from tools.impact_execution import analyze_query_impact
        print("✅ tools.impact_execution import successful")
    except ImportError as e:
        print(f"❌ tools.impact_execution import failed: {e}")
        return False
    
    print("🎉 All imports successful!")
    return True

if __name__ == "__main__":
    success = test_imports()
    if not success:
        print("❌ Import test failed")
        sys.exit(1)
    else:
        print("✅ Import test passed")
        sys.exit(0) 