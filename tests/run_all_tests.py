#!/usr/bin/env python3
"""
PostgreSQL AI Agent MVP - Test Runner
Executes all test scripts in sequence with comprehensive reporting
"""

import subprocess
import sys
import time
from pathlib import Path

# Test scripts in recommended execution order
TEST_SCRIPTS = [
    # Import tests
    "test_imports.py",
    
    # Unit tests for tools (P4.T2.1)
    "test_rollback_operation.py",
    "test_global_exception_handler.py",
    
    # Core functionality tests
    "test_gemini.py",
    "test_gemini_client.py", 
    "test_db_ops.py",
    "test_redis_caching.py",
    
    # Component tests
    "test_schema_context.py",
    "test_orchestrator.py",
    "test_query_builder.py",
    "test_websocket.py",
    "test_langgraph_workflow.py",
    
    # Advanced functionality tests
    "test_impact_analysis.py",
    "test_approval_workflow.py", 
    "test_safe_execution.py",
    
    # End-to-end tests
    "test_enhanced_workflow.py"
]

def run_test(script_name):
    """Run a single test script and return results"""
    print(f"\n{'='*60}")
    print(f"🧪 Running: {script_name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Run the test script
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result.returncode == 0:
            print(f"✅ PASSED - {script_name} ({duration:.2f}s)")
            if result.stdout:
                print("📤 Output:")
                print(result.stdout)
            return True, duration, None
        else:
            print(f"❌ FAILED - {script_name} ({duration:.2f}s)")
            print("📤 STDOUT:")
            print(result.stdout)
            print("📤 STDERR:")
            print(result.stderr)
            return False, duration, result.stderr
            
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT - {script_name} (exceeded 5 minutes)")
        return False, 300, "Test timed out after 5 minutes"
    except Exception as e:
        print(f"💥 ERROR - {script_name}: {e}")
        return False, 0, str(e)

def main():
    """Run all tests and generate report"""
    print("🚀 PostgreSQL AI Agent MVP - Test Suite Runner")
    print("=" * 60)
    
    # Change to tests directory
    tests_dir = Path(__file__).parent
    original_dir = Path.cwd()
    
    try:
        # Change to tests directory for test execution
        import os
        os.chdir(tests_dir)
        
        # Add src directory to Python path for imports
        src_path = str(tests_dir.parent / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        
        results = []
        total_start_time = time.time()
        
        for script in TEST_SCRIPTS:
            script_path = tests_dir / script
            if script_path.exists():
                success, duration, error = run_test(script)
                results.append({
                    'script': script,
                    'success': success,
                    'duration': duration,
                    'error': error
                })
            else:
                print(f"⚠️  SKIPPED - {script} (file not found)")
                results.append({
                    'script': script,
                    'success': False,
                    'duration': 0,
                    'error': 'File not found'
                })
        
        total_end_time = time.time()
        total_duration = total_end_time - total_start_time
        
        # Generate summary report
        print(f"\n{'='*60}")
        print("📊 TEST SUMMARY REPORT")
        print(f"{'='*60}")
        
        passed = sum(1 for r in results if r['success'])
        failed = len(results) - passed
        total_time = sum(r['duration'] for r in results)
        
        print(f"📈 Overall Results:")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📊 Total Tests: {len(results)}")
        print(f"   ⏱️  Total Time: {total_duration:.2f}s")
        print(f"   🎯 Success Rate: {(passed/len(results)*100):.1f}%")
        
        print(f"\n📋 Detailed Results:")
        for result in results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"   {status} {result['script']:<30} ({result['duration']:.2f}s)")
            if not result['success'] and result['error']:
                print(f"        Error: {result['error'][:100]}...")
        
        if failed > 0:
            print(f"\n⚠️  {failed} test(s) failed. Check the detailed output above.")
            print("💡 Common issues:")
            print("   - Database connection not available")
            print("   - Redis server not running") 
            print("   - Missing .env file or API keys")
            print("   - FastAPI server not running (for endpoint tests)")
            
        print(f"\n🎉 Test run completed in {total_duration:.2f} seconds")
        
        # Return appropriate exit code
        return 0 if failed == 0 else 1
        
    finally:
        # Change back to original directory
        os.chdir(original_dir)

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 