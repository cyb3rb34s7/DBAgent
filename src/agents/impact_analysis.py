"""
PostgreSQL AI Agent MVP - Impact Analysis Agent
Agent 3: Risk assessment and impact analysis for destructive operations
"""

import logging
from typing import Dict, Any, List, Optional
from utils.gemini_client import get_gemini_client
from tools.db_ops import fetch_schema_context

logger = logging.getLogger(__name__)

class ImpactAnalysisAgent:
    """
    Impact Analysis Agent: Risk assessment and impact analysis specialist
    
    Responsibilities:
    - Analyze potential impact of destructive operations (UPDATE, DELETE, INSERT)
    - Estimate affected row counts using EXPLAIN queries
    - Classify risk levels (LOW, MEDIUM, HIGH, CRITICAL)
    - Generate impact reports with recommendations
    - Validate destructive operations against business rules
    - Provide rollback strategies and safety recommendations
    """
    
    def __init__(self):
        """Initialize Impact Analysis Agent"""
        self.gemini_client = get_gemini_client()
        self.risk_thresholds = {
            "LOW": 10,       # <= 10 rows affected
            "MEDIUM": 100,   # 11-100 rows affected  
            "HIGH": 1000,    # 101-1000 rows affected
            "CRITICAL": float('inf')  # > 1000 rows affected
        }
        logger.info("ImpactAnalysisAgent initialized with risk thresholds")
    
    async def analyze_query_impact(self, sql_query: str, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the potential impact of a destructive SQL query
        
        Args:
            sql_query: The SQL query to analyze (UPDATE/DELETE/INSERT)
            intent_data: Intent information from orchestrator
            
        Returns:
            Dict containing impact analysis results
        """
        try:
            logger.info(f"Analyzing impact for {intent_data.get('type', 'UNKNOWN')} query")
            
            # Step 1: Validate query type
            query_type = self._get_query_type(sql_query)
            if query_type not in ["UPDATE", "DELETE", "INSERT"]:
                return {
                    "status": "error",
                    "message": f"Impact analysis only supports destructive operations, got: {query_type}",
                    "query_type": query_type
                }
            
            # Step 2: Get schema context for the affected tables
            affected_tables = self._extract_affected_tables(sql_query, intent_data)
            schema_result = await fetch_schema_context(table_names=affected_tables)
            
            if schema_result.get("status") != "success":
                return {
                    "status": "error",
                    "message": f"Failed to fetch schema context: {schema_result.get('message')}",
                    "query_type": query_type
                }
            
            # Step 3: Estimate impact using EXPLAIN
            impact_estimate = await self._estimate_query_impact(sql_query, query_type)
            
            # Step 4: Classify risk level
            risk_classification = self._classify_risk(impact_estimate, query_type, affected_tables)
            
            # Step 5: Generate recommendations
            recommendations = await self._generate_recommendations(
                sql_query, query_type, risk_classification, schema_result.get("schema_context", {})
            )
            
            # Step 6: Create comprehensive impact report
            impact_report = {
                "status": "success",
                "query_type": query_type,
                "affected_tables": affected_tables,
                "impact_estimate": impact_estimate,
                "risk_classification": risk_classification,
                "recommendations": recommendations,
                "schema_context": schema_result.get("schema_context", {}),
                "analysis_metadata": {
                    "analyzed_at": "current_timestamp",
                    "agent": "ImpactAnalysisAgent",
                    "schema_cached": schema_result.get("cached", False)
                }
            }
            
            logger.info(f"Impact analysis completed: {risk_classification['level']} risk, {impact_estimate.get('estimated_rows', 'unknown')} rows affected")
            return impact_report
            
        except Exception as e:
            logger.error(f"Error analyzing query impact: {e}")
            return {
                "status": "error",
                "message": f"Impact analysis failed: {str(e)}",
                "query_type": "UNKNOWN",
                "error_type": "analysis_error"
            }
    
    def _get_query_type(self, sql_query: str) -> str:
        """Extract query type from SQL query"""
        query_upper = sql_query.strip().upper()
        
        if query_upper.startswith('UPDATE'):
            return "UPDATE"
        elif query_upper.startswith('DELETE'):
            return "DELETE"
        elif query_upper.startswith('INSERT'):
            return "INSERT"
        else:
            return "UNKNOWN"
    
    def _extract_affected_tables(self, sql_query: str, intent_data: Dict[str, Any]) -> List[str]:
        """
        Extract table names that will be affected by the query
        
        Args:
            sql_query: SQL query to analyze
            intent_data: Intent information
            
        Returns:
            List of affected table names
        """
        affected_tables = []
        
        # Try to get table from intent data first
        table_mentioned = intent_data.get("table_mentioned")
        if table_mentioned:
            affected_tables.append(table_mentioned)
        
        # Parse SQL for additional tables (basic parsing)
        query_upper = sql_query.upper()
        
        # For UPDATE queries: UPDATE table_name SET ...
        if query_upper.startswith('UPDATE'):
            parts = query_upper.split()
            if len(parts) > 1:
                table_name = parts[1].lower()
                if table_name not in affected_tables:
                    affected_tables.append(table_name)
        
        # For DELETE queries: DELETE FROM table_name ...
        elif query_upper.startswith('DELETE FROM'):
            parts = query_upper.split()
            if len(parts) > 2:
                table_name = parts[2].lower()
                if table_name not in affected_tables:
                    affected_tables.append(table_name)
        
        # For INSERT queries: INSERT INTO table_name ...
        elif query_upper.startswith('INSERT INTO'):
            parts = query_upper.split()
            if len(parts) > 2:
                table_name = parts[2].lower()
                if table_name not in affected_tables:
                    affected_tables.append(table_name)
        
        return affected_tables or ["unknown_table"]
    
    async def _estimate_query_impact(self, sql_query: str, query_type: str) -> Dict[str, Any]:
        """
        Estimate query impact using EXPLAIN (placeholder implementation)
        
        Args:
            sql_query: SQL query to analyze
            query_type: Type of query (UPDATE/DELETE/INSERT)
            
        Returns:
            Dict containing impact estimates
        """
        # NOTE: This is a simplified implementation for MVP
        # In production, this would use EXPLAIN ANALYZE to get actual estimates
        
        try:
            # For MVP, we'll use basic heuristics
            # In Phase 4, this will be replaced with actual EXPLAIN queries
            
            estimated_rows = self._estimate_rows_heuristic(sql_query, query_type)
            
            return {
                "method": "heuristic_estimation",  # Will be "explain_analyze" in production
                "estimated_rows": estimated_rows,
                "confidence": "low",  # Heuristic has low confidence
                "execution_time_estimate": "unknown",
                "disk_usage_impact": "unknown",
                "lock_duration_estimate": "unknown",
                "notes": "Using heuristic estimation for MVP. EXPLAIN ANALYZE will be implemented in Phase 4."
            }
            
        except Exception as e:
            logger.error(f"Error estimating query impact: {e}")
            return {
                "method": "failed",
                "estimated_rows": "unknown",
                "confidence": "none",
                "error": str(e)
            }
    
    def _estimate_rows_heuristic(self, sql_query: str, query_type: str) -> int:
        """
        Heuristic-based row estimation (MVP implementation)
        
        Args:
            sql_query: SQL query to analyze
            query_type: Type of query
            
        Returns:
            Estimated number of rows affected
        """
        query_lower = sql_query.lower()
        
        # Basic heuristics based on query patterns
        if 'where' not in query_lower:
            # No WHERE clause = potentially affects all rows
            if query_type == "DELETE":
                return 10000  # Assume large table deletion
            elif query_type == "UPDATE":
                return 5000   # Assume large table update
        else:
            # Has WHERE clause - analyze conditions
            if 'id =' in query_lower or 'id=' in query_lower:
                return 1  # Single row by ID
            elif 'limit' in query_lower:
                # Try to extract LIMIT value
                try:
                    limit_parts = query_lower.split('limit')
                    if len(limit_parts) > 1:
                        limit_value = int(limit_parts[1].strip().split()[0])
                        return min(limit_value, 100)
                except:
                    pass
                return 50  # Default for LIMIT queries
            else:
                return 100  # Default for WHERE clause queries
        
        # Default fallback
        if query_type == "INSERT":
            return 1  # INSERT typically adds one row
        
        return 50  # Conservative default
    
    def _classify_risk(self, impact_estimate: Dict[str, Any], query_type: str, affected_tables: List[str]) -> Dict[str, Any]:
        """
        Classify risk level based on impact estimate
        
        Args:
            impact_estimate: Impact estimation results
            query_type: Type of query
            affected_tables: List of affected tables
            
        Returns:
            Dict containing risk classification
        """
        estimated_rows = impact_estimate.get("estimated_rows", 0)
        
        # Determine base risk level from row count
        if isinstance(estimated_rows, str):
            risk_level = "HIGH"  # Unknown row count = high risk
            risk_score = 75
        else:
            if estimated_rows <= self.risk_thresholds["LOW"]:
                risk_level = "LOW"
                risk_score = 25
            elif estimated_rows <= self.risk_thresholds["MEDIUM"]:
                risk_level = "MEDIUM"
                risk_score = 50
            elif estimated_rows <= self.risk_thresholds["HIGH"]:
                risk_level = "HIGH"
                risk_score = 75
            else:
                risk_level = "CRITICAL"
                risk_score = 100
        
        # Adjust risk based on query type
        risk_factors = []
        
        if query_type == "DELETE":
            risk_score += 10
            risk_factors.append("DELETE operations are irreversible")
        elif query_type == "UPDATE":
            risk_factors.append("UPDATE operations modify existing data")
        elif query_type == "INSERT":
            risk_score -= 5  # INSERT is generally safer
            risk_factors.append("INSERT operations add new data")
        
        # Adjust risk based on affected tables
        critical_tables = ["users", "accounts", "payments", "orders"]  # Example critical tables
        for table in affected_tables:
            if any(critical in table.lower() for critical in critical_tables):
                risk_score += 15
                risk_factors.append(f"Critical table affected: {table}")
        
        # Re-classify based on adjusted score
        if risk_score >= 90:
            risk_level = "CRITICAL"
        elif risk_score >= 70:
            risk_level = "HIGH"
        elif risk_score >= 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            "level": risk_level,
            "score": min(risk_score, 100),
            "factors": risk_factors,
            "thresholds": self.risk_thresholds,
            "estimated_rows": estimated_rows,
            "requires_approval": risk_level in ["HIGH", "CRITICAL"]
        }
    
    async def _generate_recommendations(self, sql_query: str, query_type: str, 
                                      risk_classification: Dict[str, Any], 
                                      schema_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate safety recommendations using Gemini AI
        
        Args:
            sql_query: SQL query to analyze
            query_type: Type of query
            risk_classification: Risk classification results
            schema_context: Database schema context
            
        Returns:
            Dict containing recommendations
        """
        try:
            # Use Gemini to generate intelligent recommendations
            prompt = f"""
            Analyze this {query_type} SQL query and provide safety recommendations:
            
            Query: {sql_query}
            Risk Level: {risk_classification['level']}
            Estimated Rows: {risk_classification['estimated_rows']}
            
            Provide recommendations in JSON format:
            {{
                "safety_checks": ["check1", "check2"],
                "rollback_strategy": "strategy description",
                "testing_recommendations": ["test1", "test2"],
                "approval_justification": "why approval is needed"
            }}
            """
            
            recommendations_json = await self.gemini_client.generate_content(prompt)
            
            # Try to parse JSON response
            import json
            try:
                recommendations = json.loads(recommendations_json.strip().replace('```json', '').replace('```', ''))
            except:
                # Fallback to basic recommendations
                recommendations = self._generate_basic_recommendations(query_type, risk_classification)
            
            return {
                "status": "success",
                "recommendations": recommendations,
                "generated_by": "gemini_ai"
            }
            
        except Exception as e:
            logger.error(f"Error generating recommendations with Gemini: {e}")
            # Fallback to basic recommendations
            return {
                "status": "fallback",
                "recommendations": self._generate_basic_recommendations(query_type, risk_classification),
                "generated_by": "fallback_rules"
            }
    
    def _generate_basic_recommendations(self, query_type: str, risk_classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate basic safety recommendations (fallback)
        
        Args:
            query_type: Type of query
            risk_classification: Risk classification results
            
        Returns:
            Dict containing basic recommendations
        """
        recommendations = {
            "safety_checks": [],
            "rollback_strategy": "",
            "testing_recommendations": [],
            "approval_justification": ""
        }
        
        # Common safety checks
        recommendations["safety_checks"] = [
            "Verify WHERE clause conditions are correct",
            "Check affected row count before execution",
            "Ensure backup is available",
            "Test query on staging environment first"
        ]
        
        # Query-specific recommendations
        if query_type == "DELETE":
            recommendations["rollback_strategy"] = "No automatic rollback possible for DELETE. Restore from backup if needed."
            recommendations["testing_recommendations"] = [
                "Run SELECT with same WHERE clause first",
                "Verify row count matches expectations",
                "Test on small subset first"
            ]
        elif query_type == "UPDATE":
            recommendations["rollback_strategy"] = "Store original values before UPDATE for potential rollback."
            recommendations["testing_recommendations"] = [
                "SELECT affected rows first to verify conditions",
                "Test UPDATE on single row first",
                "Verify new values are correct"
            ]
        elif query_type == "INSERT":
            recommendations["rollback_strategy"] = "DELETE inserted rows using primary key values."
            recommendations["testing_recommendations"] = [
                "Verify data integrity constraints",
                "Check for duplicate key conflicts",
                "Validate foreign key references"
            ]
        
        # Risk-based approval justification
        risk_level = risk_classification.get("level", "UNKNOWN")
        estimated_rows = risk_classification.get("estimated_rows", "unknown")
        
        if risk_level == "CRITICAL":
            recommendations["approval_justification"] = f"CRITICAL risk: {estimated_rows} rows affected. Requires senior approval."
        elif risk_level == "HIGH":
            recommendations["approval_justification"] = f"HIGH risk: {estimated_rows} rows affected. Requires manager approval."
        elif risk_level == "MEDIUM":
            recommendations["approval_justification"] = f"MEDIUM risk: {estimated_rows} rows affected. Requires peer review."
        else:
            recommendations["approval_justification"] = f"LOW risk: {estimated_rows} rows affected. Standard approval process."
        
        return recommendations

# Global instance
impact_analysis_agent = None

def get_impact_analysis_agent() -> ImpactAnalysisAgent:
    """Get or create global ImpactAnalysisAgent instance"""
    global impact_analysis_agent
    if impact_analysis_agent is None:
        impact_analysis_agent = ImpactAnalysisAgent()
    return impact_analysis_agent 