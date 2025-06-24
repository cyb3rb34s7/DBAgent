# PostgreSQL AI Agent MVP - System Flow Documentation

This document provides comprehensive flow diagrams for the PostgreSQL AI Agent MVP system, showing the agentic architecture, LangGraph workflows, and data pathways.

## 🏗️ System Architecture Overview

```mermaid
flowchart TD
    subgraph "Client Layer"
        WS["WebSocket Client"]
        API["REST API Client"]
    end

    subgraph "FastAPI Server"
        HEALTH["health endpoint"]
        WSE["WebSocket /ws/query"]
        APPROVE["/approve/{ticket_id}"]
        REJECT["/reject/{ticket_id}"]
        STATUS["/status/{ticket_id}"]
    end

    subgraph "Agent Layer"
        ORCH["OrchestratorAgent"]
        QB["QueryBuilderAgent"]
        IA["ImpactAnalysisAgent"]
    end

    subgraph "Tool Layer (MCP Servers)"
        MCP1["MCP Server 1 - Database Operations"]
        MCP2["MCP Server 2 - Impact & Execution"]
    end

    subgraph "LangGraph Workflow"
        LG["LangGraph StateGraph"]
    end

    subgraph "External Services"
        GEMINI["Gemini AI API"]
        PG["PostgreSQL Database"]
        REDIS["Redis Cache"]
    end

    WS --> WSE
    API --> APPROVE
    API --> REJECT
    API --> STATUS

    WSE --> ORCH
    APPROVE --> MCP2
    REJECT --> MCP2
    STATUS --> MCP2

    ORCH --> LG
    LG --> QB
    LG --> IA
    LG --> MCP1
    LG --> MCP2

    QB --> GEMINI
    IA --> GEMINI
    MCP1 --> PG
    MCP1 --> REDIS
    MCP2 --> PG
    MCP2 --> REDIS

```

## 🔄 Complete Query Processing Flow

```mermaid
flowchart TD
    START([User Query Input]) --> INTENT{Query Type?}
    
    INTENT -->|SELECT| SELECT_FLOW[SELECT Query Flow]
    INTENT -->|UPDATE/DELETE/INSERT| DESTRUCTIVE_FLOW[Destructive Query Flow]
    
    subgraph "SELECT Query Flow"
        SELECT_FLOW --> EXTRACT[Extract Intent<br/>Gemini AI]
        EXTRACT --> SCHEMA[Fetch Schema Context<br/>Redis Cached]
        SCHEMA --> BUILD[Build SQL Query<br/>Gemini AI]
        BUILD --> VALIDATE[Validate Query<br/>Security Checks]
        VALIDATE --> EXECUTE[Execute SELECT<br/>PostgreSQL]
        EXECUTE --> RESULTS[Return Results]
    end
    
    subgraph "Destructive Query Flow"
        DESTRUCTIVE_FLOW --> EXTRACT2[Extract Intent<br/>Gemini AI]
        EXTRACT2 --> IMPACT[Analyze Impact<br/>Risk Assessment]
        IMPACT --> RISK{Risk Level?}
        
        RISK -->|LOW/MEDIUM| AUTO_APPROVE[Auto Approve]
        RISK -->|HIGH/CRITICAL| APPROVAL[Create Approval Request<br/>Redis Ticket]
        
        APPROVAL --> WAIT[Wait for Human Approval]
        WAIT --> CHECK{Approved?}
        CHECK -->|No| REJECTED[Query Rejected]
        CHECK -->|Yes| APPROVED[Query Approved]
        
        AUTO_APPROVE --> SAFE_EXEC
        APPROVED --> SAFE_EXEC[Safe Execution<br/>Transaction Wrapped]
        
        SAFE_EXEC --> COMMIT{Success?}
        COMMIT -->|Yes| COMMIT_TX[COMMIT Transaction]
        COMMIT -->|No| ROLLBACK[ROLLBACK Transaction]
        
        COMMIT_TX --> SUCCESS[Execution Success]
        ROLLBACK --> ERROR[Execution Failed]
    end
    
    RESULTS --> END([Response to User])
    SUCCESS --> END
    ERROR --> END
    REJECTED --> END
```

## 🤖 Agent Interaction Flow

```mermaid
sequenceDiagram
    participant User
    participant WS as WebSocket
    participant Orch as OrchestratorAgent
    participant QB as QueryBuilderAgent
    participant IA as ImpactAnalysisAgent
    participant LG as LangGraph
    participant DB as Database
    participant Redis
    participant Gemini as Gemini AI
    
    User->>WS: Natural Language Query
    WS->>Orch: process_query()
    
    Orch->>Gemini: extract_intent()
    Gemini-->>Orch: Intent JSON
    
    alt SELECT Query
        Orch->>LG: Start SELECT workflow
        LG->>Redis: fetch_schema_context()
        Redis-->>LG: Schema (cached)
        LG->>QB: build_sql_query()
        QB->>Gemini: Generate SQL
        Gemini-->>QB: SQL Query
        QB-->>LG: Validated SQL
        LG->>DB: execute_select_query()
        DB-->>LG: Results
        LG-->>Orch: Final Results
    else Destructive Query
        Orch->>LG: Start Destructive workflow
        LG->>IA: analyze_query_impact()
        IA->>Gemini: Generate recommendations
        Gemini-->>IA: Safety recommendations
        IA->>DB: EXPLAIN analysis
        DB-->>IA: Impact estimates
        IA-->>LG: Risk assessment
        
        alt High Risk
            LG->>Redis: create_approval_request()
            Redis-->>LG: Ticket ID
            LG-->>Orch: Approval Required
        else Low Risk
            LG->>DB: execute_approved_query()
            DB-->>LG: Execution results
            LG-->>Orch: Success/Error
        end
    end
    
    Orch-->>WS: Response
    WS-->>User: Results/Status
```

## 🔀 LangGraph State Management

```mermaid
stateDiagram-v2
    [*] --> START
    
    START --> extract_intent : User Query
    
    state extract_intent {
        [*] --> gemini_extraction
        gemini_extraction --> intent_parsed
        intent_parsed --> [*]
    }
    
    extract_intent --> route_decision : Intent Available
    
    state route_decision {
        [*] --> check_query_type
        check_query_type --> select_route : SELECT
        check_query_type --> destructive_route : UPDATE/DELETE/INSERT
    }
    
    route_decision --> fetch_schema : SELECT Route
    route_decision --> analyze_impact : Destructive Route
    
    state fetch_schema {
        [*] --> redis_lookup
        redis_lookup --> cache_hit : Found
        redis_lookup --> db_query : Not Found
        db_query --> cache_store
        cache_store --> schema_ready
        cache_hit --> schema_ready
        schema_ready --> [*]
    }
    
    fetch_schema --> build_query
    
    state build_query {
        [*] --> gemini_sql_generation
        gemini_sql_generation --> sql_validation
        sql_validation --> query_optimization
        query_optimization --> [*]
    }
    
    build_query --> validate_query
    
    state validate_query {
        [*] --> syntax_check
        syntax_check --> security_check
        security_check --> complexity_analysis
        complexity_analysis --> [*]
    }
    
    validate_query --> execute_select
    
    state execute_select {
        [*] --> db_connection
        db_connection --> query_execution
        query_execution --> result_formatting
        result_formatting --> [*]
    }
    
    execute_select --> END
    
    state analyze_impact {
        [*] --> heuristic_analysis
        heuristic_analysis --> explain_analysis
        explain_analysis --> risk_classification
        risk_classification --> recommendation_generation
        recommendation_generation --> [*]
    }
    
    analyze_impact --> approval_decision : Impact Complete
    
    state approval_decision {
        [*] --> check_risk_level
        check_risk_level --> auto_approve : LOW/MEDIUM
        check_risk_level --> require_approval : HIGH/CRITICAL
    }
    
    approval_decision --> execute_approved : Auto Approved
    approval_decision --> create_ticket : Approval Required
    
    state create_ticket {
        [*] --> generate_ticket_id
        generate_ticket_id --> store_in_redis
        store_in_redis --> notify_approvers
        notify_approvers --> [*]
    }
    
    create_ticket --> wait_approval
    
    state wait_approval {
        [*] --> check_status
        check_status --> still_pending : PENDING
        check_status --> approved : APPROVED
        check_status --> rejected : REJECTED
        still_pending --> check_status
    }
    
    wait_approval --> execute_approved : Approved
    wait_approval --> END : Rejected
    
    state execute_approved {
        [*] --> verify_approval
        verify_approval --> begin_transaction
        begin_transaction --> execute_query
        execute_query --> commit_success : Success
        execute_query --> rollback_error : Error
        commit_success --> update_ticket_executed
        rollback_error --> update_ticket_failed
        update_ticket_executed --> [*]
        update_ticket_failed --> [*]
    }
    
    execute_approved --> END
    
    END --> [*]
```

## 🗄️ Data Flow Architecture

```mermaid
graph LR
    subgraph "Input Layer"
        NLQ[Natural Language Query]
        REST[REST API Calls]
    end
    
    subgraph "Processing Layer"
        subgraph "State Management"
            STATE[LangGraph State]
            METADATA[Query Metadata]
            CONTEXT[Execution Context]
        end
        
        subgraph "AI Processing"
            INTENT_AI[Intent Extraction<br/>Gemini]
            SQL_AI[SQL Generation<br/>Gemini]
            REC_AI[Recommendations<br/>Gemini]
        end
        
        subgraph "Data Operations"
            SCHEMA_OPS[Schema Operations]
            QUERY_OPS[Query Operations]
            IMPACT_OPS[Impact Operations]
        end
    end
    
    subgraph "Storage Layer"
        subgraph "Primary Storage"
            PG_DATA[PostgreSQL<br/>Primary Data]
            PG_META[PostgreSQL<br/>Metadata Tables]
        end
        
        subgraph "Cache Layer"
            REDIS_SCHEMA[Redis<br/>Schema Cache]
            REDIS_TICKETS[Redis<br/>Approval Tickets]
            REDIS_SESSION[Redis<br/>Session Data]
        end
    end
    
    subgraph "Output Layer"
        JSON_RESP[JSON Responses]
        WS_RESP[WebSocket Messages]
        APPROVAL_UI[Approval Interface]
    end
    
    NLQ --> STATE
    REST --> METADATA
    
    STATE --> INTENT_AI
    INTENT_AI --> SQL_AI
    SQL_AI --> QUERY_OPS
    
    METADATA --> IMPACT_OPS
    IMPACT_OPS --> REC_AI
    
    SCHEMA_OPS <--> REDIS_SCHEMA
    SCHEMA_OPS <--> PG_META
    
    QUERY_OPS <--> PG_DATA
    
    IMPACT_OPS <--> REDIS_TICKETS
    IMPACT_OPS <--> PG_DATA
    
    CONTEXT --> JSON_RESP
    CONTEXT --> WS_RESP
    METADATA --> APPROVAL_UI
```

## 🔐 Security & Approval Flow

```mermaid
flowchart TD
    QUERY[Incoming Query] --> CLASSIFY[Classify Query Type]
    
    CLASSIFY --> SELECT_TYPE{Query Type}
    
    SELECT_TYPE -->|SELECT| SAFE_PATH[Safe Execution Path]
    SELECT_TYPE -->|INSERT/UPDATE/DELETE| DANGER_PATH[Destructive Query Path]
    
    subgraph "Safe Execution Path"
        SAFE_PATH --> VALIDATE_SAFE[Validate Query]
        VALIDATE_SAFE --> CHECK_INJECTION[Check SQL Injection]
        CHECK_INJECTION --> EXECUTE_SAFE[Execute Directly]
        EXECUTE_SAFE --> RETURN_SAFE[Return Results]
    end
    
    subgraph "Destructive Query Path"
        DANGER_PATH --> ANALYZE[Impact Analysis]
        ANALYZE --> ESTIMATE[Estimate Affected Rows]
        ESTIMATE --> CLASSIFY_RISK[Classify Risk Level]
        
        CLASSIFY_RISK --> RISK_DECISION{Risk Level}
        
        RISK_DECISION -->|LOW ≤10 rows| LOW_RISK[Low Risk Path]
        RISK_DECISION -->|MEDIUM ≤100 rows| MEDIUM_RISK[Medium Risk Path]
        RISK_DECISION -->|HIGH ≤1000 rows| HIGH_RISK[High Risk Path]
        RISK_DECISION -->|CRITICAL >1000 rows| CRITICAL_RISK[Critical Risk Path]
        
        LOW_RISK --> AUTO_APPROVE[Auto Approve]
        MEDIUM_RISK --> PEER_REVIEW[Require Peer Review]
        HIGH_RISK --> MANAGER_APPROVAL[Require Manager Approval]
        CRITICAL_RISK --> SENIOR_APPROVAL[Require Senior Approval]
        
        AUTO_APPROVE --> SAFE_EXECUTE
        PEER_REVIEW --> APPROVAL_FLOW
        MANAGER_APPROVAL --> APPROVAL_FLOW
        SENIOR_APPROVAL --> APPROVAL_FLOW
        
        subgraph "Approval Workflow"
            APPROVAL_FLOW --> CREATE_TICKET[Create Approval Ticket]
            CREATE_TICKET --> STORE_REDIS[Store in Redis]
            STORE_REDIS --> NOTIFY[Notify Approvers]
            NOTIFY --> WAIT[Wait for Decision]
            
            WAIT --> CHECK_STATUS{Check Status}
            CHECK_STATUS -->|Approved| APPROVED_STATUS[Approved]
            CHECK_STATUS -->|Rejected| REJECTED_STATUS[Rejected]
            CHECK_STATUS -->|Pending| WAIT
            CHECK_STATUS -->|Expired| EXPIRED_STATUS[Expired]
            
            APPROVED_STATUS --> SAFE_EXECUTE
            REJECTED_STATUS --> REJECT_QUERY[Reject Query]
            EXPIRED_STATUS --> REJECT_QUERY
        end
        
        subgraph "Safe Execution"
            SAFE_EXECUTE --> BEGIN_TX[BEGIN Transaction]
            BEGIN_TX --> FINAL_VALIDATE[Final Validation]
            FINAL_VALIDATE --> EXECUTE_QUERY[Execute Query]
            
            EXECUTE_QUERY --> SUCCESS_CHECK{Execution Success?}
            SUCCESS_CHECK -->|Yes| COMMIT_TX[COMMIT Transaction]
            SUCCESS_CHECK -->|No| ROLLBACK_TX[ROLLBACK Transaction]
            
            COMMIT_TX --> UPDATE_SUCCESS[Update Ticket: EXECUTED]
            ROLLBACK_TX --> UPDATE_FAILED[Update Ticket: FAILED]
            
            UPDATE_SUCCESS --> RETURN_SUCCESS[Return Success]
            UPDATE_FAILED --> RETURN_ERROR[Return Error]
        end
    end
    
    RETURN_SAFE --> END[End]
    RETURN_SUCCESS --> END
    RETURN_ERROR --> END
    REJECT_QUERY --> END
```

## 📊 Performance & Caching Strategy

```mermaid
graph TD
    subgraph "Request Flow"
        REQ[Incoming Request]
        CACHE_CHECK{Cache Check}
        CACHE_HIT[Cache Hit<br/>45-58x Faster]
        CACHE_MISS[Cache Miss<br/>Database Query]
    end
    
    subgraph "Redis Cache Layers"
        SCHEMA_CACHE[Schema Cache<br/>TTL: 1 hour]
        TICKET_CACHE[Approval Tickets<br/>TTL: 24 hours]
        SESSION_CACHE[Session Data<br/>TTL: 30 minutes]
    end
    
    subgraph "Database Operations"
        SCHEMA_QUERY[Schema Query<br/>PostgreSQL Catalogs]
        DATA_QUERY[Data Query<br/>User Tables]
        META_QUERY[Metadata Query<br/>System Tables]
    end
    
    subgraph "Performance Metrics"
        FAST[Schema: ~2ms<br/>with cache]
        SLOW[Schema: ~100ms<br/>without cache]
        APPROVAL[Ticket: ~5ms<br/>Redis lookup]
    end
    
    REQ --> CACHE_CHECK
    CACHE_CHECK -->|Hit| CACHE_HIT
    CACHE_CHECK -->|Miss| CACHE_MISS
    
    CACHE_HIT --> SCHEMA_CACHE
    CACHE_MISS --> SCHEMA_QUERY
    
    SCHEMA_QUERY --> SCHEMA_CACHE
    SCHEMA_CACHE --> FAST
    SCHEMA_QUERY --> SLOW
    
    TICKET_CACHE --> APPROVAL
    SESSION_CACHE --> FAST
```

## 🔧 Error Handling & Recovery

```mermaid
flowchart TD
    ERROR[Error Occurred] --> CLASSIFY_ERROR{Error Type}
    
    CLASSIFY_ERROR -->|Database Error| DB_ERROR[Database Error Handler]
    CLASSIFY_ERROR -->|Redis Error| REDIS_ERROR[Redis Error Handler]
    CLASSIFY_ERROR -->|Gemini API Error| AI_ERROR[AI Error Handler]
    CLASSIFY_ERROR -->|Validation Error| VAL_ERROR[Validation Error Handler]
    CLASSIFY_ERROR -->|System Error| SYS_ERROR[System Error Handler]
    
    subgraph "Database Error Recovery"
        DB_ERROR --> CHECK_CONNECTION[Check Connection]
        CHECK_CONNECTION --> RETRY_DB{Retry?}
        RETRY_DB -->|Yes| RECONNECT[Reconnect & Retry]
        RETRY_DB -->|No| FALLBACK_DB[Use Fallback]
        RECONNECT --> SUCCESS_DB[Success]
        FALLBACK_DB --> DEGRADED_DB[Degraded Mode]
    end
    
    subgraph "Redis Error Recovery"
        REDIS_ERROR --> CHECK_REDIS[Check Redis Connection]
        CHECK_REDIS --> RETRY_REDIS{Retry?}
        RETRY_REDIS -->|Yes| RECONNECT_REDIS[Reconnect Redis]
        RETRY_REDIS -->|No| NO_CACHE[Continue Without Cache]
        RECONNECT_REDIS --> SUCCESS_REDIS[Success]
        NO_CACHE --> DEGRADED_REDIS[Performance Degraded]
    end
    
    subgraph "AI Error Recovery"
        AI_ERROR --> CHECK_API[Check API Status]
        CHECK_API --> RETRY_AI{Retry?}
        RETRY_AI -->|Yes| RETRY_REQUEST[Retry API Request]
        RETRY_AI -->|No| FALLBACK_AI[Use Fallback Logic]
        RETRY_REQUEST --> SUCCESS_AI[Success]
        FALLBACK_AI --> BASIC_RULES[Basic Rule-Based Logic]
    end
    
    subgraph "Transaction Recovery"
        TRANSACTION_ERROR[Transaction Error] --> ROLLBACK_AUTO[Auto Rollback]
        ROLLBACK_AUTO --> LOG_ERROR[Log Error Details]
        LOG_ERROR --> UPDATE_TICKET[Update Ticket Status]
        UPDATE_TICKET --> NOTIFY_USER[Notify User]
    end
    
    SUCCESS_DB --> CONTINUE[Continue Processing]
    SUCCESS_REDIS --> CONTINUE
    SUCCESS_AI --> CONTINUE
    DEGRADED_DB --> CONTINUE
    DEGRADED_REDIS --> CONTINUE
    BASIC_RULES --> CONTINUE
    NOTIFY_USER --> CONTINUE
    
    CONTINUE --> RESPONSE[Send Response to User]
```

This comprehensive flow documentation provides a complete view of the PostgreSQL AI Agent MVP system architecture, showing how the various components interact, the decision pathways, and the safety mechanisms in place. 
