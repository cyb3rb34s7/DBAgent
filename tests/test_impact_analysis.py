"""
Test script for Impact Analysis Agent and Tools
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from agents.impact_analysis import get_impact_analysis_agent
from tools.impact_execution import analyze_query_impact, test_impact_connection

async def test_impact_analysis():
    """Test the Impact Analysis Agent and tools"""
    print("🧪 Testing Impact Analysis Agent and Tools")
    print("=" * 60)
    
    impact_agent = get_impact_analysis_agent()
    
    # Test 1: Impact Analysis Agent initialization
    print("\n📤 Test 1: Impact Analysis Agent Initialization")
    print(f"✅ Agent initialized with risk thresholds: {impact_agent.risk_thresholds}")
    
    # Test 2: Database connection test
    print("\n📤 Test 2: Database Connection Test")
    try:
        connection_result = await test_impact_connection()
        print(f"✅ Status: {connection_result.get('status')}")
        if connection_result.get('status') == 'success':
            print(f"   Message: {connection_result.get('message')}")
        else:
            print(f"   Error: {connection_result.get('message')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Impact analysis for different query types
    print("\n📤 Test 3: Impact Analysis for Different Query Types")
    
    test_queries = [
        {
            "sql": "UPDATE users SET status = 'inactive' WHERE id = 123",
            "intent": {
                "type": "UPDATE",
                "table_mentioned": "users",
                "confidence": 0.9,
                "keywords": ["update", "users", "status"]
            }
        },
        {
            "sql": "DELETE FROM audit_logs WHERE created_at < '2023-01-01'",
            "intent": {
                "type": "DELETE", 
                "table_mentioned": "audit_logs",
                "confidence": 0.85,
                "keywords": ["delete", "audit_logs", "old"]
            }
        },
        {
            "sql": "INSERT INTO notifications (user_id, message) VALUES (1, 'Test notification')",
            "intent": {
                "type": "INSERT",
                "table_mentioned": "notifications", 
                "confidence": 0.8,
                "keywords": ["insert", "notifications"]
            }
        },
        {
            "sql": "UPDATE users SET last_login = NOW()",
            "intent": {
                "type": "UPDATE",
                "table_mentioned": "users",
                "confidence": 0.9,
                "keywords": ["update", "users", "all"]
            }
        },
        {
            "sql": "DELETE FROM trades",
            "intent": {
                "type": "DELETE",
                "table_mentioned": "trades",
                "confidence": 0.95,
                "keywords": ["delete", "trades", "all"]
            }
        }
    ]
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n   Test 3.{i}: {test_case['intent']['type']} query")
        print(f"      SQL: {test_case['sql'][:60]}...")
        
        try:
            # Test with Impact Analysis Agent directly
            agent_result = await impact_agent.analyze_query_impact(test_case['sql'], test_case['intent'])
            print(f"      Agent Status: {agent_result.get('status')}")
            
            if agent_result.get('status') == 'success':
                risk = agent_result.get('risk_classification', {})
                impact = agent_result.get('impact_estimate', {})
                
                print(f"      Risk Level: {risk.get('level')} (Score: {risk.get('score')})")
                print(f"      Estimated Rows: {impact.get('estimated_rows')}")
                print(f"      Affected Tables: {agent_result.get('affected_tables')}")
                print(f"      Requires Approval: {risk.get('requires_approval')}")
                
                # Show some recommendations
                recommendations = agent_result.get('recommendations', {}).get('recommendations', {})
                if recommendations.get('safety_checks'):
                    print(f"      Safety Checks: {len(recommendations['safety_checks'])} items")
            else:
                print(f"      Error: {agent_result.get('message')}")
            
            # Test with combined tool (includes EXPLAIN analysis)
            print(f"      Testing combined analysis...")
            tool_result = await analyze_query_impact(test_case['sql'], test_case['intent'])
            print(f"      Tool Status: {tool_result.get('status')}")
            
            if tool_result.get('status') == 'success':
                explain = tool_result.get('explain_analysis', {})
                if explain.get('status') == 'success':
                    print(f"      EXPLAIN Rows: {explain.get('estimated_rows')}")
                    print(f"      EXPLAIN Cost: {explain.get('estimated_cost')}")
                else:
                    print(f"      EXPLAIN: {explain.get('message', 'Not available')}")
            
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    # Test 4: Risk classification edge cases
    print("\n📤 Test 4: Risk Classification Edge Cases")
    
    edge_cases = [
        {
            "name": "Single row by ID",
            "sql": "UPDATE users SET email = 'new@email.com' WHERE id = 1",
            "intent": {"type": "UPDATE", "table_mentioned": "users"}
        },
        {
            "name": "No WHERE clause (dangerous)",
            "sql": "DELETE FROM temp_table",
            "intent": {"type": "DELETE", "table_mentioned": "temp_table"}
        },
        {
            "name": "Critical table affected",
            "sql": "UPDATE users SET password = 'reset' WHERE status = 'inactive'",
            "intent": {"type": "UPDATE", "table_mentioned": "users"}
        }
    ]
    
    for i, case in enumerate(edge_cases, 1):
        print(f"\n   Test 4.{i}: {case['name']}")
        try:
            result = await impact_agent.analyze_query_impact(case['sql'], case['intent'])
            if result.get('status') == 'success':
                risk = result.get('risk_classification', {})
                print(f"      Risk Level: {risk.get('level')}")
                print(f"      Risk Score: {risk.get('score')}")
                print(f"      Risk Factors: {len(risk.get('factors', []))}")
                for factor in risk.get('factors', [])[:2]:  # Show first 2 factors
                    print(f"        - {factor}")
            else:
                print(f"      Error: {result.get('message')}")
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    # Test 5: Recommendations generation
    print("\n📤 Test 5: Recommendations Generation")
    test_sql = "UPDATE users SET status = 'archived' WHERE last_login < '2023-01-01'"
    test_intent = {"type": "UPDATE", "table_mentioned": "users"}
    
    try:
        result = await impact_agent.analyze_query_impact(test_sql, test_intent)
        if result.get('status') == 'success':
            recommendations = result.get('recommendations', {}).get('recommendations', {})
            print(f"✅ Recommendations generated by: {result.get('recommendations', {}).get('generated_by')}")
            
            if recommendations.get('safety_checks'):
                print(f"   Safety Checks ({len(recommendations['safety_checks'])}):")
                for check in recommendations['safety_checks'][:3]:
                    print(f"     - {check}")
            
            if recommendations.get('rollback_strategy'):
                print(f"   Rollback Strategy: {recommendations['rollback_strategy'][:80]}...")
            
            if recommendations.get('approval_justification'):
                print(f"   Approval Justification: {recommendations['approval_justification'][:80]}...")
        else:
            print(f"❌ Error: {result.get('message')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n🎉 Impact Analysis testing completed!")

if __name__ == "__main__":
    asyncio.run(test_impact_analysis()) 