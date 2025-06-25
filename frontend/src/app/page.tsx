'use client';

import { useState, useEffect, useRef } from 'react';

interface QueryResponse {
  status: string;
  message?: string;
  user_query?: string;
  sql_query?: string;
  query_type?: string;
  workflow?: string;
  data?: any[];
  metadata?: {
    rows_returned?: number;
    [key: string]: any;
  };
  approval_ticket?: {
    ticket_id: string;
  };
  approval_status?: string;
  risk_level?: string;
  orchestrator_intent?: {
    type: string;
    confidence: number;
  };
  execution_result?: any;
  impact_analysis?: any;
  human_in_the_loop?: any;
}

export default function Home() {
  const [query, setQuery] = useState('');
  const [responses, setResponses] = useState<QueryResponse[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      const ws = new WebSocket('ws://localhost:8001/ws/query');

      ws.onopen = () => {
        setIsConnected(true);
        console.log('Connected to PostgreSQL AI Agent');
      };

      ws.onmessage = (event) => {
        try {
          const response: QueryResponse = JSON.parse(event.data);
          setResponses(prev => [response, ...prev]);
          setIsLoading(false);
        } catch (error) {
          console.error('Error parsing response:', error);
          setIsLoading(false);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log('Disconnected from PostgreSQL AI Agent');
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
        setIsLoading(false);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to connect:', error);
      setIsConnected(false);
    }
  };

  const sendQuery = () => {
    if (!query.trim() || !wsRef.current || !isConnected) return;

    setIsLoading(true);
    wsRef.current.send(query);
    setQuery('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendQuery();
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'text-green-600 bg-green-50 border-green-200';
      case 'error': return 'text-red-600 bg-red-50 border-red-200';
      case 'pending_approval': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getQueryTypeColor = (type: string) => {
    switch (type?.toUpperCase()) {
      case 'SELECT': return 'bg-blue-100 text-blue-800';
      case 'UPDATE': return 'bg-orange-100 text-orange-800';
      case 'DELETE': return 'bg-red-100 text-red-800';
      case 'INSERT': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk?.toUpperCase()) {
      case 'LOW': return 'bg-green-100 text-green-800';
      case 'MEDIUM': return 'bg-yellow-100 text-yellow-800';
      case 'HIGH': return 'bg-orange-100 text-orange-800';
      case 'CRITICAL': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            PostgreSQL AI Agent
          </h1>
          <p className="text-lg text-gray-600 mb-4">
            Natural Language Database Query Interface
          </p>
          <div className="flex items-center justify-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className={`text-sm font-medium ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        {/* Query Input */}
        <div className="max-w-4xl mx-auto mb-8">
          <div className="bg-white rounded-lg shadow-lg p-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Enter your database query in natural language:
            </label>
            <div className="flex space-x-4">
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="e.g., 'show me all users', 'update user status to active', 'delete old logs'"
                className="flex-1 p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows={3}
                disabled={!isConnected || isLoading}
              />
              <button
                onClick={sendQuery}
                disabled={!query.trim() || !isConnected || isLoading}
                className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? (
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Processing...</span>
                  </div>
                ) : (
                  'Send Query'
                )}
              </button>
            </div>

            {/* Quick Examples */}
            <div className="mt-4">
              <p className="text-sm text-gray-500 mb-2">Quick examples:</p>
              <div className="flex flex-wrap gap-2">
                {[
                  'show me all tables',
                  'select version()',
                  'get current timestamp',
                  'show me users table'
                ].map((example) => (
                  <button
                    key={example}
                    onClick={() => setQuery(example)}
                    className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-full transition-colors"
                    disabled={!isConnected || isLoading}
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Responses */}
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Query Results</h2>

          {responses.length === 0 ? (
            <div className="bg-white rounded-lg shadow-lg p-8 text-center">
              <div className="text-gray-400 mb-2">
                <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2 2v-5m16 0h-3m-13 0h3m-3 0l3-3m0 0l3 3M9 21v-4a2 2 0 012-2h2a2 2 0 012 2v4" />
                </svg>
              </div>
              <p className="text-gray-500">No queries sent yet. Try sending a query above!</p>
            </div>
          ) : (
            <div className="space-y-4">
              {responses.map((response, index) => (
                <div key={index} className={`border rounded-lg p-4 ${getStatusColor(response.status)}`}>
                  {/* Response Header */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(response.status)}`}>
                        {response.status}
                      </span>
                      {response.query_type && (
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getQueryTypeColor(response.query_type)}`}>
                          {response.query_type}
                        </span>
                      )}
                      {response.risk_level && (
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getRiskColor(response.risk_level)}`}>
                          {response.risk_level} Risk
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-gray-500">
                      {new Date().toLocaleTimeString()}
                    </span>
                  </div>

                  {/* Query */}
                  {response.sql_query && (
                    <div className="mb-3">
                      <p className="text-sm font-medium text-gray-700 mb-1">SQL Query:</p>
                      <code className="text-sm bg-gray-100 px-2 py-1 rounded">{response.sql_query}</code>
                    </div>
                  )}

                  {/* Message */}
                  {response.message && (
                    <div className="mb-3">
                      <p className="text-sm">{response.message}</p>
                    </div>
                  )}

                  {/* Intent Information */}
                  {response.orchestrator_intent && (
                    <div className="mb-3">
                      <p className="text-sm font-medium text-gray-700 mb-1">AI Intent Analysis:</p>
                      <p className="text-sm">
                        Type: <span className="font-medium">{response.orchestrator_intent.type}</span>
                        {' '}(Confidence: {(response.orchestrator_intent.confidence * 100).toFixed(1)}%)
                      </p>
                    </div>
                  )}

                  {/* Approval Ticket */}
                  {response.approval_ticket && (
                    <div className="mb-3">
                      <p className="text-sm font-medium text-gray-700 mb-1">Approval Required:</p>
                      <p className="text-sm">
                        Ticket ID: <code className="bg-gray-100 px-1 rounded">{response.approval_ticket.ticket_id}</code>
                      </p>
                      <p className="text-sm">
                        Status: <span className="font-medium">{response.approval_status || 'Pending'}</span>
                      </p>
                    </div>
                  )}

                  {/* Results Table */}
                  {response.data && response.data.length > 0 && (
                    <div className="mt-3">
                      <p className="text-sm font-medium text-gray-700 mb-2">
                        Results ({response.metadata?.rows_returned || response.data?.length || 0} rows):
                      </p>
                      <div className="overflow-x-auto">
                        <table className="min-w-full text-sm border border-gray-200 rounded">
                          <thead className="bg-gray-50">
                            <tr>
                              {Object.keys(response.data?.[0] || {}).map((col) => (
                                <th key={col} className="px-3 py-2 text-left font-medium text-gray-700 border-b">
                                  {col}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {response.data?.slice(0, 10).map((row, rowIndex) => (
                              <tr key={rowIndex} className="border-b">
                                {Object.keys(response.data?.[0] || {}).map((col) => (
                                  <td key={col} className="px-3 py-2 text-gray-600">
                                    {String(row[col] ?? '')}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {(response.data?.length || 0) > 10 && (
                          <p className="text-xs text-gray-500 mt-2">
                            Showing first 10 rows of {response.data?.length || 0} total rows
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Workflow Info */}
                  {response.workflow && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <p className="text-xs text-gray-500">
                        Workflow: {response.workflow}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
