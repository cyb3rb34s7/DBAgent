"""
Test script for Safe Execution functionality
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from tools.impact_execution import (
    analyze_query_impact,
    create_approval_request, 
    update_approval_status,
    execute_approved_query
)

async def test_safe_execution():
    """Test the complete safe execution workflow"""
    print("🧪 Testing Safe Execution Workflow")
    print("=" * 60)
    
    # Test 1: Create and approve a safe UPDATE query
    print("\n📤 Test 1: Safe UPDATE Query Execution")
    
    # Use a simple UPDATE that won't break if the column doesn't exist
    test_sql = "UPDATE users SET updated_at = NOW() WHERE id = 999999"  # Non-existent ID
    test_intent = {
        "type": "UPDATE",
        "table_mentioned": "users",
        "confidence": 0.9,
        "keywords": ["update", "users", "timestamp"]
    }
    
    try:
        print("   Step 1.1: Analyzing query impact...")
        impact_result = await analyze_query_impact(test_sql, test_intent)
        print(f"   Impact Analysis: {impact_result.get('status')}")
        
        if impact_result.get('status') != 'success':
            print(f"   ❌ Impact analysis failed: {impact_result.get('message')}")
            return
        
        print("   Step 1.2: Creating approval request...")
        approval_result = await create_approval_request(
            test_sql, 
            impact_result, 
            {"user_id": "test_executor", "role": "admin"}
        )
        
        if approval_result.get('status') != 'success':
            print(f"   ❌ Approval request failed: {approval_result.get('message')}")
            return
        
        ticket_id = approval_result.get('ticket_id')
        print(f"   ✅ Ticket Created: {ticket_id}")
        
        print("   Step 1.3: Approving the request...")
        approve_result = await update_approval_status(
            ticket_id,
            "APPROVED",
            {"approver_id": "security_admin", "department": "security"},
            "Safe UPDATE operation approved"
        )
        
        if approve_result.get('status') != 'success':
            print(f"   ❌ Approval failed: {approve_result.get('message')}")
            return
        
        print(f"   ✅ Request Approved")
        
        print("   Step 1.4: Executing approved query...")
        execution_result = await execute_approved_query(
            ticket_id,
            {"executor_id": "system_admin", "execution_method": "automated"}
        )
        
        print(f"   Execution Status: {execution_result.get('status')}")
        
        if execution_result.get('status') == 'success':
            print(f"   ✅ Query Executed Successfully")
            print(f"   Rows Affected: {execution_result.get('rows_affected')}")
            print(f"   Transaction Status: {execution_result.get('transaction_status')}")
            print(f"   Execution Method: {execution_result.get('execution_method')}")
        else:
            print(f"   ⚠️  Execution Result: {execution_result.get('message')}")
            print(f"   Transaction Status: {execution_result.get('transaction_status', 'unknown')}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Try to execute without approval
    print("\n📤 Test 2: Execution Without Approval (Should Fail)")
    
    try:
        print("   Step 2.1: Creating unapproved request...")
        test_sql_2 = "DELETE FROM audit_logs WHERE created_at < '2020-01-01'"
        impact_result_2 = await analyze_query_impact(
            test_sql_2, 
            {"type": "DELETE", "table_mentioned": "audit_logs"}
        )
        
        if impact_result_2.get('status') == 'success':
            approval_result_2 = await create_approval_request(
                test_sql_2, 
                impact_result_2, 
                {"user_id": "test_user"}
            )
            
            if approval_result_2.get('status') == 'success':
                unapproved_ticket = approval_result_2.get('ticket_id')
                print(f"   Unapproved Ticket: {unapproved_ticket}")
                
                print("   Step 2.2: Attempting execution without approval...")
                execution_result_2 = await execute_approved_query(
                    unapproved_ticket,
                    {"executor_id": "unauthorized_user"}
                )
                
                print(f"   Execution Status: {execution_result_2.get('status')}")
                
                if execution_result_2.get('status') == 'error':
                    print(f"   ✅ Correctly Blocked: {execution_result_2.get('message')}")
                    print(f"   Error Type: {execution_result_2.get('error_type')}")
                else:
                    print(f"   ❌ Security Failure: Unapproved query was executed!")
            else:
                print(f"   ❌ Approval request failed: {approval_result_2.get('message')}")
        else:
            print(f"   ❌ Impact analysis failed: {impact_result_2.get('message')}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Transaction rollback on error
    print("\n📤 Test 3: Transaction Rollback on Error")
    
    try:
        print("   Step 3.1: Creating request with invalid SQL...")
        # This query should fail due to syntax error, testing rollback
        invalid_sql = "UPDATE non_existent_table SET invalid_column = 'test' WHERE id = 1"
        
        impact_result_3 = await analyze_query_impact(
            invalid_sql,
            {"type": "UPDATE", "table_mentioned": "non_existent_table"}
        )
        
        if impact_result_3.get('status') == 'success':
            approval_result_3 = await create_approval_request(
                invalid_sql,
                impact_result_3,
                {"user_id": "test_rollback"}
            )
            
            if approval_result_3.get('status') == 'success':
                rollback_ticket = approval_result_3.get('ticket_id')
                
                print("   Step 3.2: Approving invalid query...")
                await update_approval_status(
                    rollback_ticket,
                    "APPROVED",
                    {"approver_id": "test_approver"},
                    "Testing rollback functionality"
                )
                
                print("   Step 3.3: Executing invalid query (should rollback)...")
                execution_result_3 = await execute_approved_query(
                    rollback_ticket,
                    {"executor_id": "rollback_tester"}
                )
                
                print(f"   Execution Status: {execution_result_3.get('status')}")
                
                if execution_result_3.get('status') == 'error':
                    print(f"   ✅ Error Handled: {execution_result_3.get('message')[:80]}...")
                    print(f"   Transaction Status: {execution_result_3.get('transaction_status')}")
                    print(f"   Error Type: {execution_result_3.get('error_type')}")
                    
                    if execution_result_3.get('transaction_status') == 'rolled_back':
                        print("   ✅ Transaction Correctly Rolled Back")
                    else:
                        print(f"   ⚠️  Transaction Status: {execution_result_3.get('transaction_status')}")
                else:
                    print(f"   ❌ Expected error but got success: {execution_result_3}")
            else:
                print(f"   ❌ Approval request failed: {approval_result_3.get('message')}")
        else:
            print(f"   ❌ Impact analysis failed: {impact_result_3.get('message')}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Invalid query types
    print("\n📤 Test 4: Invalid Query Types (Should Fail)")
    
    try:
        print("   Step 4.1: Testing SELECT query execution...")
        
        # Create an approval for a SELECT query (should be rejected by execute_approved_query)
        select_sql = "SELECT * FROM users LIMIT 5"
        select_impact = await analyze_query_impact(
            select_sql,
            {"type": "SELECT", "table_mentioned": "users"}
        )
        
        if select_impact.get('status') == 'success':
            select_approval = await create_approval_request(
                select_sql,
                select_impact,
                {"user_id": "select_tester"}
            )
            
            if select_approval.get('status') == 'success':
                select_ticket = select_approval.get('ticket_id')
                
                # Approve it
                await update_approval_status(
                    select_ticket,
                    "APPROVED",
                    {"approver_id": "test_approver"},
                    "Testing SELECT rejection"
                )
                
                # Try to execute (should fail)
                select_execution = await execute_approved_query(
                    select_ticket,
                    {"executor_id": "select_executor"}
                )
                
                print(f"   SELECT Execution Status: {select_execution.get('status')}")
                
                if select_execution.get('status') == 'error':
                    print(f"   ✅ SELECT Correctly Rejected: {select_execution.get('message')}")
                    print(f"   Error Type: {select_execution.get('error_type')}")
                else:
                    print(f"   ❌ SELECT should have been rejected but was executed")
            else:
                print(f"   ❌ SELECT approval failed: {select_approval.get('message')}")
        else:
            print(f"   ❌ SELECT impact analysis failed: {select_impact.get('message')}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Non-existent ticket
    print("\n📤 Test 5: Non-existent Ticket (Should Fail)")
    
    try:
        fake_ticket = "fake-ticket-id-12345"
        fake_execution = await execute_approved_query(
            fake_ticket,
            {"executor_id": "fake_executor"}
        )
        
        print(f"   Fake Ticket Execution: {fake_execution.get('status')}")
        
        if fake_execution.get('status') == 'error':
            print(f"   ✅ Non-existent Ticket Correctly Rejected: {fake_execution.get('message')}")
            print(f"   Error Type: {fake_execution.get('error_type')}")
        else:
            print(f"   ❌ Non-existent ticket should have been rejected")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n🎉 Safe execution testing completed!")

if __name__ == "__main__":
    asyncio.run(test_safe_execution()) 