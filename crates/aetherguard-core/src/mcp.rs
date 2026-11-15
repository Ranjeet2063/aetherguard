/* Authorized Protocol Quality Assurance & Formal Verification Engine */

use serde::{Deserialize, Serialize};

/// Anthropic Model Context Protocol (MCP) tool definition for AI Agent integration.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct McpToolDefinition {
    pub name: String,
    pub description: String,
    pub input_schema: McpInputSchema,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct McpInputSchema {
    #[serde(rename = "type")]
    pub schema_type: String,
    pub properties: serde_json::Value,
    pub required: Vec<String>,
}

/// JSON-RPC 2.0 Request for MCP Server
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpJsonRpcRequest {
    pub jsonrpc: String,
    pub id: serde_json::Value,
    pub method: String,
    pub params: Option<serde_json::Value>,
}

/// JSON-RPC 2.0 Response for MCP Server
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpJsonRpcResponse {
    pub jsonrpc: String,
    pub id: serde_json::Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<serde_json::Value>,
}

pub struct McpProtocolHandler;

impl McpProtocolHandler {
    /// Return the standard MCP tool definition for AetherGuard invariant verification.
    pub fn get_verify_tool_definition() -> McpToolDefinition {
        McpToolDefinition {
            name: "aetherguard_verify_transaction".to_string(),
            description: "Evaluates an AI agent transaction proposal against mathematical invariant boundaries (spending caps, balance floors, slippage limits, and destination whitelists) and issues an Ed25519-signed proof certificate.".to_string(),
            input_schema: McpInputSchema {
                schema_type: "object".to_string(),
                properties: serde_json::json!({
                    "proposal_id": { "type": "string", "description": "Unique proposal identifier" },
                    "agent_id": { "type": "string", "description": "Agent handle" },
                    "target_contract": { "type": "string", "description": "Contract address" },
                    "target_function": { "type": "string", "description": "Function call name" },
                    "destination_address": { "type": "string", "description": "Recipient address" },
                    "amount": { "type": "integer", "description": "Amount in atomic stroops" },
                    "asset_code": { "type": "string", "description": "Asset symbol (e.g. USDC, XLM)" },
                    "timestamp": { "type": "integer", "description": "Unix timestamp in seconds" }
                }),
                required: vec![
                    "proposal_id".into(),
                    "agent_id".into(),
                    "target_contract".into(),
                    "target_function".into(),
                    "destination_address".into(),
                    "amount".into(),
                    "asset_code".into(),
                    "timestamp".into(),
                ],
            },
        }
    }
}
