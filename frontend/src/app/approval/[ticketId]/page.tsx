'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';

interface ApprovalRequest {
    ticket_id: string;
    status: string;
    sql_query: string;
    impact_analysis: {
        query_type: string;
        affected_tables: string[];
        risk_classification: {
            level: string;
            score: number;
            factors: string[];
            requires_approval: boolean;
            estimated_rows: number;
        };
        impact_estimate: {
            estimated_rows: number;
            method: string;
            confidence: string;
        };
        recommendations: {
            recommendations: {
                safety_checks: string[];
                rollback_strategy: string;
                testing_recommendations: string[];
                approval_justification: string;
            };
        };
    };
    created_at: string;
    expires_at: string;
    metadata: {
        risk_level: string;
        estimated_rows: number | string;
        affected_tables: string[];
    };
}

interface ApprovalResponse {
    status: string;
    message: string;
    ticket_id: string;
    approver?: string;
}

export default function ApprovalPage() {
    const params = useParams();
    const router = useRouter();
    const ticketId = params.ticketId as string;

    const [approvalRequest, setApprovalRequest] = useState<ApprovalRequest | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [processing, setProcessing] = useState(false);
    const [approverName, setApproverName] = useState('');
    const [comments, setComments] = useState('');

    useEffect(() => {
        if (ticketId) {
            fetchApprovalRequest();
        }
    }, [ticketId]);

    const fetchApprovalRequest = async () => {
        try {
            setLoading(true);
            const response = await fetch(`http://localhost:8001/status/${ticketId}`);
            const data = await response.json();

            if (data.status === 'success') {
                setApprovalRequest(data.request_details);
            } else {
                setError(data.message || 'Failed to fetch approval request');
            }
        } catch (err) {
            setError('Failed to connect to the server. Make sure the FastAPI server is running.');
        } finally {
            setLoading(false);
        }
    };

    const handleApproval = async (action: 'approve' | 'reject') => {
        if (!approverName.trim()) {
            alert('Please enter your name as the approver');
            return;
        }

        setProcessing(true);
        try {
            const endpoint = action === 'approve' ? 'approve' : 'reject';
            const url = `http://localhost:8001/${endpoint}/${ticketId}?approver=${encodeURIComponent(approverName)}&comments=${encodeURIComponent(comments)}`;

            const response = await fetch(url, { method: 'GET' });
            const data: ApprovalResponse = await response.json();

            if (data.status === 'success') {
                alert(`Request ${action}ed successfully!`);
                // Refresh the approval request to show updated status
                await fetchApprovalRequest();
            } else {
                alert(`Failed to ${action} request: ${data.message}`);
            }
        } catch (err) {
            alert(`Error ${action}ing request. Please try again.`);
        } finally {
            setProcessing(false);
        }
    };

    const getRiskColor = (risk: string) => {
        switch (risk?.toUpperCase()) {
            case 'LOW': return 'bg-green-100 text-green-800 border-green-200';
            case 'MEDIUM': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            case 'HIGH': return 'bg-orange-100 text-orange-800 border-orange-200';
            case 'CRITICAL': return 'bg-red-100 text-red-800 border-red-200';
            default: return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    const getStatusColor = (status: string) => {
        switch (status?.toUpperCase()) {
            case 'PENDING_APPROVAL': return 'bg-yellow-100 text-yellow-800';
            case 'APPROVED': return 'bg-green-100 text-green-800';
            case 'REJECTED': return 'bg-red-100 text-red-800';
            case 'EXPIRED': return 'bg-gray-100 text-gray-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
                <div className="bg-white rounded-lg shadow-lg p-8 text-center">
                    <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-gray-600">Loading approval request...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
                <div className="bg-white rounded-lg shadow-lg p-8 text-center max-w-md">
                    <div className="text-red-500 mb-4">
                        <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                        </svg>
                    </div>
                    <h2 className="text-xl font-bold text-gray-900 mb-2">Error</h2>
                    <p className="text-gray-600 mb-4">{error}</p>
                    <button
                        onClick={() => router.push('/')}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                    >
                        Go Back to Home
                    </button>
                </div>
            </div>
        );
    }

    if (!approvalRequest) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
                <div className="bg-white rounded-lg shadow-lg p-8 text-center">
                    <p className="text-gray-600">Approval request not found</p>
                </div>
            </div>
        );
    }

    const isExpired = new Date() > new Date(approvalRequest.expires_at);
    const isPending = approvalRequest.status === 'PENDING_APPROVAL' && !isExpired;
    const timeRemaining = new Date(approvalRequest.expires_at).getTime() - new Date().getTime();
    const hoursRemaining = Math.max(0, Math.floor(timeRemaining / (1000 * 60 * 60)));

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
            <div className="container mx-auto px-4 py-8">
                {/* Header */}
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-bold text-gray-900 mb-2">
                        Query Approval Request
                    </h1>
                    <p className="text-lg text-gray-600">
                        Review and approve/reject destructive database operations
                    </p>
                </div>

                <div className="max-w-4xl mx-auto">
                    {/* Status Card */}
                    <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
                        <div className="flex items-center justify-between mb-4">
                            <div>
                                <h2 className="text-xl font-bold text-gray-900">Ticket #{ticketId.slice(-8)}</h2>
                                <p className="text-sm text-gray-500">Created: {new Date(approvalRequest.created_at).toLocaleString()}</p>
                            </div>
                            <div className="text-right">
                                <span className={`px-3 py-1 text-sm font-medium rounded-full ${getStatusColor(approvalRequest.status)}`}>
                                    {approvalRequest.status.replace('_', ' ')}
                                </span>
                                {isPending && (
                                    <p className="text-sm text-gray-500 mt-1">
                                        Expires in {hoursRemaining}h
                                    </p>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Query Details */}
                    <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
                        <h3 className="text-lg font-bold text-gray-900 mb-4">Query Details</h3>

                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-2">SQL Query:</label>
                            <div className="bg-gray-50 p-4 rounded-md border">
                                <code className="text-sm text-gray-800 font-mono">{approvalRequest.sql_query}</code>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Query Type:</label>
                                <span className="inline-block px-2 py-1 text-sm bg-blue-100 text-blue-800 rounded">
                                    {approvalRequest.impact_analysis.query_type}
                                </span>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Affected Tables:</label>
                                <p className="text-sm text-gray-600">
                                    {approvalRequest.impact_analysis.affected_tables.join(', ') || 'Unknown'}
                                </p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Estimated Rows:</label>
                                <p className="text-sm text-gray-600">
                                    {approvalRequest.impact_analysis.impact_estimate.estimated_rows}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Risk Analysis */}
                    <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
                        <h3 className="text-lg font-bold text-gray-900 mb-4">Risk Analysis</h3>

                        <div className={`p-4 rounded-lg border-2 mb-4 ${getRiskColor(approvalRequest.impact_analysis.risk_classification.level)}`}>
                            <div className="flex items-center justify-between mb-2">
                                <span className="font-bold text-lg">
                                    {approvalRequest.impact_analysis.risk_classification.level} RISK
                                </span>
                                <span className="text-sm">
                                    Score: {approvalRequest.impact_analysis.risk_classification.score}/100
                                </span>
                            </div>

                            {approvalRequest.impact_analysis.risk_classification.factors.length > 0 && (
                                <div>
                                    <p className="text-sm font-medium mb-2">Risk Factors:</p>
                                    <ul className="text-sm space-y-1">
                                        {approvalRequest.impact_analysis.risk_classification.factors.map((factor, index) => (
                                            <li key={index} className="flex items-start">
                                                <span className="text-red-500 mr-2">•</span>
                                                {factor}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Safety Recommendations */}
                    {approvalRequest.impact_analysis.recommendations?.recommendations && (
                        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
                            <h3 className="text-lg font-bold text-gray-900 mb-4">Safety Recommendations</h3>

                            {approvalRequest.impact_analysis.recommendations.recommendations.safety_checks?.length > 0 && (
                                <div className="mb-4">
                                    <h4 className="font-medium text-gray-900 mb-2">Safety Checks:</h4>
                                    <ul className="text-sm text-gray-600 space-y-1">
                                        {approvalRequest.impact_analysis.recommendations.recommendations.safety_checks.map((check, index) => (
                                            <li key={index} className="flex items-start">
                                                <span className="text-blue-500 mr-2">✓</span>
                                                {check}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {approvalRequest.impact_analysis.recommendations.recommendations.rollback_strategy && (
                                <div className="mb-4">
                                    <h4 className="font-medium text-gray-900 mb-2">Rollback Strategy:</h4>
                                    <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded">
                                        {approvalRequest.impact_analysis.recommendations.recommendations.rollback_strategy}
                                    </p>
                                </div>
                            )}

                            {approvalRequest.impact_analysis.recommendations.recommendations.approval_justification && (
                                <div>
                                    <h4 className="font-medium text-gray-900 mb-2">Approval Justification:</h4>
                                    <p className="text-sm text-gray-600 bg-yellow-50 p-3 rounded border border-yellow-200">
                                        {approvalRequest.impact_analysis.recommendations.recommendations.approval_justification}
                                    </p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Approval Actions */}
                    {isPending && (
                        <div className="bg-white rounded-lg shadow-lg p-6">
                            <h3 className="text-lg font-bold text-gray-900 mb-4">Approval Decision</h3>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Approver Name: <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={approverName}
                                        onChange={(e) => setApproverName(e.target.value)}
                                        placeholder="Enter your name"
                                        className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Comments (optional):
                                    </label>
                                    <textarea
                                        value={comments}
                                        onChange={(e) => setComments(e.target.value)}
                                        placeholder="Add any comments about your decision..."
                                        rows={3}
                                        className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                                    />
                                </div>

                                <div className="flex space-x-4">
                                    <button
                                        onClick={() => handleApproval('approve')}
                                        disabled={processing || !approverName.trim()}
                                        className="flex-1 px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        {processing ? (
                                            <div className="flex items-center justify-center space-x-2">
                                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                                <span>Processing...</span>
                                            </div>
                                        ) : (
                                            '✓ Approve Query'
                                        )}
                                    </button>

                                    <button
                                        onClick={() => handleApproval('reject')}
                                        disabled={processing || !approverName.trim()}
                                        className="flex-1 px-6 py-3 bg-red-600 text-white rounded-md hover:bg-red-700 focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        {processing ? (
                                            <div className="flex items-center justify-center space-x-2">
                                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                                <span>Processing...</span>
                                            </div>
                                        ) : (
                                            '✗ Reject Query'
                                        )}
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Already Processed */}
                    {!isPending && (
                        <div className="bg-white rounded-lg shadow-lg p-6 text-center">
                            <div className="text-gray-400 mb-4">
                                <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                            </div>
                            <h3 className="text-lg font-bold text-gray-900 mb-2">
                                {isExpired ? 'Request Expired' : 'Request Already Processed'}
                            </h3>
                            <p className="text-gray-600 mb-4">
                                {isExpired
                                    ? 'This approval request has expired and can no longer be processed.'
                                    : `This request has already been ${approvalRequest.status.toLowerCase().replace('_', ' ')}.`
                                }
                            </p>
                            <button
                                onClick={() => router.push('/')}
                                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                            >
                                Return to Home
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
} 