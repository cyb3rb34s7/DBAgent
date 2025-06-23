# Test Suite - PostgreSQL AI Agent MVP

This directory contains comprehensive tests for all components of the PostgreSQL AI Agent MVP.

## 🧪 Running Tests

### Run All Tests
```bash
# From project root
cd tests
python run_all_tests.py
```

### Run Individual Tests
```bash
# Core functionality
python test_gemini.py
python test_gemini_client.py
python test_db_ops.py
python test_redis_caching.py

# Component tests
python test_schema_context.py
python test_orchestrator.py
python test_query_builder.py
python test_websocket.py
python test_langgraph_workflow.py

# Advanced functionality
python test_impact_analysis.py
python test_approval_workflow.py
python test_safe_execution.py

# End-to-end tests
python test_enhanced_workflow.py
```

## 📋 Test Categories

### Core Functionality Tests
- **test_gemini.py**: Basic Gemini AI API connectivity
- **test_gemini_client.py**: Gemini client utility functions
- **test_db_ops.py**: Database operations and connections
- **test_redis_caching.py**: Redis caching functionality

### Component Tests  
- **test_schema_context.py**: Schema intelligence and caching
- **test_orchestrator.py**: Orchestrator agent functionality
- **test_query_builder.py**: Query builder agent with Gemini AI
- **test_websocket.py**: WebSocket communication
- **test_langgraph_workflow.py**: LangGraph workflow execution

### Advanced Functionality Tests
- **test_impact_analysis.py**: Impact analysis agent and risk assessment
- **test_approval_workflow.py**: Approval workflow with Redis tickets
- **test_safe_execution.py**: Safe execution with transaction wrapping

### End-to-End Tests
- **test_enhanced_workflow.py**: Complete natural language to SQL pipeline

## 🔧 Prerequisites

Before running tests, ensure:

1. **Environment Setup**:
   ```bash
   # Virtual environment activated
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   
   # Dependencies installed
   pip install -r requirements.txt
   ```

2. **Services Running**:
   - PostgreSQL database accessible
   - Redis server running
   - `.env` file configured with:
     - `DATABASE_URL`
     - `REDIS_URL` 
     - `GEMINI_API_KEY`

3. **Optional for Full Testing**:
   - FastAPI server running (`python src/main.py`) for endpoint tests

## 📊 Test Results

The test runner provides comprehensive reporting:
- ✅ Pass/Fail status for each test
- ⏱️ Execution time per test
- 📈 Overall success rate
- 🔍 Detailed error messages for failures

## 🚨 Common Issues

### Database Connection Errors
- Verify PostgreSQL is running
- Check `DATABASE_URL` in `.env`
- Ensure database is accessible

### Redis Connection Errors  
- Verify Redis server is running
- Check `REDIS_URL` in `.env`
- Try: `redis-server` or `docker run -d -p 6379:6379 redis:alpine`

### Gemini API Errors
- Verify `GEMINI_API_KEY` in `.env`
- Check API key validity
- Ensure internet connectivity

### Import Errors
- Verify virtual environment is activated
- Check all dependencies are installed
- Ensure `src/` directory is in Python path

## 💡 Test Development

When adding new tests:
1. Follow existing test patterns
2. Add proper error handling
3. Include comprehensive assertions
4. Update `run_all_tests.py` if needed
5. Document test purpose and requirements 