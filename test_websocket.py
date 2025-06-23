"""
Simple WebSocket Test Client for PostgreSQL AI Agent MVP
Run this script to test the WebSocket endpoint
"""

import asyncio
import websockets
import json

async def test_websocket():
    """Test the WebSocket endpoint"""
    uri = "ws://localhost:8001/ws/query"
    
    try:
        print("🔗 Connecting to WebSocket...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            
            # Test queries to send
            test_queries = [
                "show me all users",
                "select * from products where price > 100",
                "update users set status = 'active'"
            ]
            
            for i, query in enumerate(test_queries, 1):
                print(f"\n📤 Sending test query {i}: {query}")
                await websocket.send(query)
                
                print("📥 Waiting for response...")
                response = await websocket.recv()
                
                try:
                    response_data = json.loads(response)
                    print("✅ Response received:")
                    print(f"   Status: {response_data.get('status')}")
                    print(f"   Query: {response_data.get('query')}")
                    print(f"   Message: {response_data.get('message')}")
                except json.JSONDecodeError:
                    print(f"✅ Raw response: {response}")
                
                # Wait a bit between queries
                await asyncio.sleep(1)
            
            print("\n🎉 WebSocket test completed successfully!")
            
    except ConnectionRefusedError:
        print("❌ Connection refused. Make sure the FastAPI server is running on port 8001")
        print("   Run: python src/main.py")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 WebSocket Test Client")
    print("=" * 50)
    asyncio.run(test_websocket()) 