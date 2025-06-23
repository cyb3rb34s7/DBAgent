"""
Test script for Approval Workflow
"""

import asyncio
import sys
import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from tools.impact_execution import (
    create_approval_request, 
    check_approval_status, 
    update_approval_status,
    analyze_query_impact
)

async def test_approval_workflow():
    """Test the complete approval workflow"""
    print("🧪 Testing Approval Workflow")
    print("=" * 60)
    
    # Test 1: Create approval requests
    print("\n📤 Test 1: Create Approval Requests")
    
    # First, create an impact analysis for a destructive query
    test_sql = "UPDATE users SET status = 'inactive' WHERE last_login < '2023-01-01'"
    test_intent = {
        "type": "UPDATE",
        "table_mentioned": "users",
        "confidence": 0.9,
        "keywords": ["update", "users", "inactive"]
    }
    
    try:
        print("   Step 1.1: Analyzing query impact...")
        impact_result = await analyze_query_impact(test_sql, test_intent)
        print(f"   Impact Analysis Status: {impact_result.get('status')}")
        
        if impact_result.get('status') == 'success':
            risk_level = impact_result.get('risk_classification', {}).get('level', 'UNKNOWN')
            estimated_rows = impact_result.get('impact_estimate', {}).get('estimated_rows', 'unknown')
            print(f"   Risk Level: {risk_level}, Estimated Rows: {estimated_rows}")
            
            print("   Step 1.2: Creating approval request...")
            requester_info = {
                "user_id": "test_user",
                "email": "test@example.com",
                "role": "developer"
            }
            
            approval_result = await create_approval_request(test_sql, impact_result, requester_info)
            print(f"   Approval Request Status: {approval_result.get('status')}")
            
            if approval_result.get('status') == 'success':
                ticket_id = approval_result.get('ticket_id')
                print(f"   ✅ Ticket Created: {ticket_id}")
                print(f"   Expires in: {approval_result.get('expires_in_hours')} hours")
                
                # Store ticket ID for further tests
                global test_ticket_id
                test_ticket_id = ticket_id
            else:
                print(f"   ❌ Error: {approval_result.get('message')}")
                return
        else:
            print(f"   ❌ Impact analysis failed: {impact_result.get('message')}")
            return
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Test 2: Check approval status
    print("\n📤 Test 2: Check Approval Status")
    
    try:
        status_result = await check_approval_status(test_ticket_id)
        print(f"   Status Check Result: {status_result.get('status')}")
        
        if status_result.get('status') == 'found':
            approval_status = status_result.get('approval_status')
            print(f"   ✅ Current Status: {approval_status}")
            print(f"   Time Remaining: {status_result.get('time_remaining')}")
            print(f"   Is Approved: {status_result.get('is_approved')}")
            print(f"   Is Rejected: {status_result.get('is_rejected')}")
        else:
            print(f"   ❌ Error: {status_result.get('message')}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Update approval status (simulate approval)
    print("\n📤 Test 3: Update Approval Status")
    
    try:
        approver_info = {
            "approver_id": "manager_001",
            "department": "engineering",
            "approval_level": "senior"
        }
        
        update_result = await update_approval_status(
            test_ticket_id, 
            "APPROVED", 
            approver_info, 
            "Approved after review - low risk operation"
        )
        
        print(f"   Update Status: {update_result.get('status')}")
        
        if update_result.get('status') == 'success':
            print(f"   ✅ Status Updated: {update_result.get('old_status')} → {update_result.get('new_status')}")
            
            # Verify the update
            verify_result = await check_approval_status(test_ticket_id)
            if verify_result.get('status') == 'found':
                print(f"   ✅ Verified Status: {verify_result.get('approval_status')}")
                print(f"   Is Approved: {verify_result.get('is_approved')}")
                
                # Show approval history
                approval_request = verify_result.get('approval_request', {})
                history = approval_request.get('approval_history', [])
                print(f"   Approval History: {len(history)} entries")
                if history:
                    latest = history[-1]
                    print(f"     Latest: {latest.get('old_status')} → {latest.get('new_status')} by {latest.get('approver_info', {}).get('approver_id')}")
            else:
                print(f"   ❌ Verification failed: {verify_result.get('message')}")
        else:
            print(f"   ❌ Update failed: {update_result.get('message')}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Test FastAPI endpoints (if server is running)
    print("\n📤 Test 4: FastAPI Endpoints")
    
    try:
        base_url = "http://localhost:8001"
        
        # Test health endpoint first
        health_response = requests.get(f"{base_url}/health", timeout=5)
        if health_response.status_code == 200:
            print("   ✅ FastAPI server is running")
            
            # Test status endpoint
            status_response = requests.get(f"{base_url}/status/{test_ticket_id}", timeout=5)
            print(f"   Status Endpoint: {status_response.status_code}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"   ✅ Ticket Status: {status_data.get('approval_status')}")
            
            # Create a new ticket for rejection test
            print("   Creating new ticket for rejection test...")
            new_impact = await analyze_query_impact(
                "DELETE FROM temp_logs WHERE created_at < NOW() - INTERVAL '30 days'",
                {"type": "DELETE", "table_mentioned": "temp_logs"}
            )
            
            if new_impact.get('status') == 'success':
                new_approval = await create_approval_request(
                    "DELETE FROM temp_logs WHERE created_at < NOW() - INTERVAL '30 days'",
                    new_impact,
                    {"user_id": "test_user_2"}
                )
                
                if new_approval.get('status') == 'success':
                    new_ticket_id = new_approval.get('ticket_id')
                    print(f"   New Ticket Created: {new_ticket_id}")
                    
                    # Test rejection endpoint
                    reject_response = requests.get(
                        f"{base_url}/reject/{new_ticket_id}",
                        params={"approver": "security_team", "comments": "Rejected - insufficient justification"},
                        timeout=5
                    )
                    
                    print(f"   Reject Endpoint: {reject_response.status_code}")
                    if reject_response.status_code == 200:
                        reject_data = reject_response.json()
                        print(f"   ✅ Rejection Status: {reject_data.get('status')}")
                        print(f"   Rejection Message: {reject_data.get('message')}")
            
        else:
            print(f"   ⚠️  FastAPI server not running (status: {health_response.status_code})")
            
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️  FastAPI server not accessible: {e}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Edge cases
    print("\n📤 Test 5: Edge Cases")
    
    try:
        # Test with non-existent ticket
        fake_ticket = "non-existent-ticket-id"
        fake_result = await check_approval_status(fake_ticket)
        print(f"   Non-existent ticket: {fake_result.get('status')} - {fake_result.get('message')[:50]}...")
        
        # Test Redis connection
        from utils.redis_client import get_redis_client
        redis_client = get_redis_client()
        print(f"   Redis Connected: {redis_client.is_connected()}")
        
        if redis_client.is_connected():
            # Test direct Redis operations
            test_key = "test_approval_workflow"
            redis_client.redis_client.setex(test_key, 60, "test_value")
            retrieved = redis_client.redis_client.get(test_key)
            print(f"   Redis Test: {retrieved == 'test_value'}")
            redis_client.redis_client.delete(test_key)
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n🎉 Approval workflow testing completed!")

if __name__ == "__main__":
    asyncio.run(test_approval_workflow()) 