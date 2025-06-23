# PostgreSQL AI Agent MVP

A sophisticated AI-powered natural language to SQL agent with comprehensive safety controls, impact analysis, and approval workflows for destructive database operations.

## 🚀 Features

### Core Capabilities
- **Natural Language to SQL**: Convert plain English queries to SQL using Gemini AI
- **Intelligent Schema Understanding**: Automatic database schema inspection with Redis caching
- **Real-time Query Processing**: WebSocket-based real-time communication
- **Comprehensive Safety Layer**: Impact analysis and approval workflows for destructive operations

### Safety & Security
- **Impact Analysis**: Risk assessment for UPDATE, DELETE, and INSERT operations
- **Approval Workflow**: Human-in-the-loop approval system with Redis-backed ticket management
- **Transaction Safety**: All destructive queries wrapped in transactions with automatic rollback
- **Query Validation**: Syntax validation, security checks, and optimization suggestions

### Advanced Features
- **Multi-Agent Architecture**: Specialized agents for orchestration, query building, and impact analysis
- **LangGraph Workflow**: Sophisticated state management and conditional routing
- **Schema Intelligence**: 45-58x performance improvement with Redis caching
- **Risk Classification**: Automatic risk scoring (LOW/MEDIUM/HIGH/CRITICAL) with approval thresholds

## 🏗️ Architecture

The system follows a multi-agent architecture with three specialized agents:

1. **OrchestratorAgent**: Routes queries and manages the overall workflow
2. **QueryBuilderAgent**: Generates SQL from natural language using Gemini AI
3. **ImpactAnalysisAgent**: Analyzes risk and impact of destructive operations

### Technology Stack
- **Backend**: Python, FastAPI, LangGraph
- **Database**: PostgreSQL
- **Caching**: Redis
- **AI Provider**: Google Gemini API
- **WebSocket**: Real-time communication
- **Testing**: Comprehensive test suite

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL database
- Redis server
- Google Gemini API key

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd DBAGENT
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

If `requirements.txt` doesn't exist, install manually:
```bash
pip install langgraph fastapi uvicorn psycopg2-binary redis python-dotenv google-generativeai requests
```

### 4. Environment Configuration
Create a `.env` file in the project root:
```env
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
REDIS_URL=redis://localhost:6379/0
GEMINI_API_KEY=your_gemini_api_key_here
DEBUG=False
```

### 5. Database Setup
Ensure your PostgreSQL database is running and accessible. The system will automatically inspect the schema.

### 6. Redis Setup
Ensure Redis server is running:
```bash
# Windows (if Redis is installed)
redis-server

# Linux/Mac
redis-server

# Or using Docker
docker run -d -p 6379:6379 redis:alpine
```

## 🚀 Running the Application

### Start the FastAPI Server
```bash
python src/main.py
```

The server will start on `http://localhost:8001`

### Available Endpoints

#### Core Endpoints
- `GET /health` - Health check
- `WebSocket /ws/query` - Real-time query processing

#### Approval Workflow Endpoints
- `GET /approve/{ticket_id}?approver=name&comments=text` - Approve a request
- `GET /reject/{ticket_id}?approver=name&comments=text` - Reject a request  
- `GET /status/{ticket_id}` - Check approval status

## 📊 Usage Examples

### 1. Simple SELECT Query via WebSocket
```python
import asyncio
import websockets
import json

async def test_query():
    uri = "ws://localhost:8001/ws/query"
    async with websockets.connect(uri) as websocket:
        # Send natural language query
        await websocket.send("show me all active users")
        
        # Receive SQL results
        response = await websocket.recv()
        print(json.loads(response))

asyncio.run(test_query())
```

### 2. Destructive Query (Requires Approval)
```python
# Send via WebSocket
query = "update all users to set their status as inactive"

# This will:
# 1. Analyze impact and risk
# 2. Create approval request
# 3. Return ticket ID for approval
# 4. Wait for human approval
# 5. Execute safely with transaction
```

### 3. Approval Workflow
```bash
# Check status
curl http://localhost:8001/status/ticket-id-here

# Approve request
curl "http://localhost:8001/approve/ticket-id-here?approver=manager&comments=Approved"

# Reject request  
curl "http://localhost:8001/reject/ticket-id-here?approver=security&comments=Rejected"
```

## 🧪 Testing

### Run All Tests
```bash
# Move to tests directory
cd tests

# Run individual test suites
python test_impact_analysis.py
python test_approval_workflow.py
python test_safe_execution.py
python test_enhanced_workflow.py
```

### Test Coverage
- **Impact Analysis**: Risk assessment, EXPLAIN analysis, recommendations
- **Approval Workflow**: Ticket creation, status tracking, Redis operations
- **Safe Execution**: Transaction safety, rollback testing, security validation
- **End-to-End**: Complete natural language to SQL pipeline

## 🔄 Workflow Overview

### SELECT Query Flow
1. User sends natural language query via WebSocket
2. OrchestratorAgent extracts intent using Gemini AI
3. System fetches schema context (cached in Redis)
4. QueryBuilderAgent generates SQL using schema + intent
5. Query validation and optimization
6. Safe execution and results returned

### Destructive Query Flow (UPDATE/DELETE/INSERT)
1. Intent extraction identifies destructive operation
2. ImpactAnalysisAgent analyzes risk and impact
3. If HIGH/CRITICAL risk, approval request created
4. Human approver reviews via endpoints
5. Once approved, safe execution with transaction wrapping
6. Automatic rollback on any errors

## 📈 Performance

- **Schema Caching**: 45-58x performance improvement with Redis
- **Real-time Processing**: WebSocket-based instant responses
- **Concurrent Handling**: FastAPI async support
- **Efficient Routing**: LangGraph conditional workflows

## 🔒 Security Features

### Query Validation
- SQL injection prevention
- Dangerous operation blocking
- Syntax validation
- Security pattern detection

### Approval Controls
- Risk-based approval requirements
- Ticket expiration (24 hours)
- Approval history tracking
- Multi-level approval support

### Transaction Safety
- Automatic BEGIN/COMMIT/ROLLBACK
- Error handling with rollback
- Connection management
- Execution logging

## 🏗️ Project Structure

```
DBAGENT/
├── src/
│   ├── agents/
│   │   ├── orchestrator.py      # Main orchestration agent
│   │   ├── query_builder.py     # SQL generation agent
│   │   └── impact_analysis.py   # Risk assessment agent
│   ├── tools/
│   │   ├── db_ops.py           # Database operations (MCP Server 1)
│   │   └── impact_execution.py # Impact & execution (MCP Server 2)
│   ├── utils/
│   │   ├── gemini_client.py    # Gemini AI integration
│   │   └── redis_client.py     # Redis connection management
│   ├── workflows/
│   │   └── select_query_flow.py # LangGraph workflow
│   └── main.py                 # FastAPI application
├── tests/
│   ├── test_impact_analysis.py
│   ├── test_approval_workflow.py
│   ├── test_safe_execution.py
│   └── test_enhanced_workflow.py
├── docs/
│   ├── flow.md                 # Workflow diagrams
│   └── PRD.md                  # Product requirements
├── .env.example                # Environment template
├── .gitignore
├── README.md
├── tasklist.md                 # Development tracker
└── context.md                  # Development context
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the existing code structure
4. Add comprehensive tests
5. Update documentation
6. Submit a pull request

## 📝 Development Notes

- Uses Gemini AI instead of OpenAI for cost efficiency
- Redis caching dramatically improves performance
- Comprehensive error handling and logging
- Phase-by-phase development approach
- Extensive testing coverage

## 🚨 Important Notes

### Production Considerations
- Configure proper database credentials
- Set up Redis clustering for high availability
- Implement proper authentication/authorization
- Add rate limiting and monitoring
- Configure CORS appropriately
- Use environment-specific configurations

### Security Warnings
- Never commit `.env` files
- Rotate API keys regularly
- Monitor approval workflows
- Review destructive operations carefully
- Implement proper backup strategies

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the test scripts for usage examples
2. Review the tasklist.md for implementation details
3. Check logs for debugging information
4. Ensure all dependencies are properly installed

## 🔮 Future Enhancements

- Web UI for approval management
- Advanced query optimization
- Multi-database support
- Enhanced monitoring and metrics
- Role-based access control
- Query history and analytics 