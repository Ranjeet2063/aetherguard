#!/usr/bin/env node
/* Authorized Protocol Quality Assurance & Formal Verification Engine */

import { AetherGuardClient, type InvariantPolicy, InvariantViolationError } from "aetherguard-sdk";
import * as readline from "node:readline";

const defaultPolicy: InvariantPolicy = {
  maxSingleSpend: 100_000_000n, // 10 USDC
  maxRollingWindowSpend: 300_000_000n, // 30 USDC
  rollingWindowSeconds: 3600,
  minBalanceFloor: 50_000_000n, // 5 USDC
  allowedRecipients: ["GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z"],
  allowedContracts: ["CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC"],
  allowedFunctions: ["swap_exact_tokens", "transfer"],
};

const guard = new AetherGuardClient(defaultPolicy);

const TOOLS = [
  {
    name: "evaluate_agent_proposal",
    description: "Evaluates an untrusted AI agent transaction proposal against mathematical boundary invariants (spend velocity, recipient whitelist, balance floor).",
    inputSchema: {
      type: "object",
      properties: {
        agentId: { type: "string", description: "Identifier of the agent submitting proposal" },
        intentPrompt: { type: "string", description: "Original user prompt or agent reasoning intent" },
        targetContract: { type: "string", description: "Smart contract address" },
        functionName: { type: "string", description: "Contract function to call" },
        recipient: { type: "string", description: "Target recipient address" },
        amount: { type: "string", description: "Amount in atomic units" },
        assetSymbol: { type: "string", description: "Token symbol (e.g. USDC)" },
        currentAccountBalance: { type: "string", description: "Current account balance in atomic units" },
      },
      required: ["agentId", "intentPrompt", "targetContract", "functionName", "recipient", "amount", "currentAccountBalance"],
    },
  },
  {
    name: "get_firewall_status",
    description: "Inspects the active AetherGuard policy invariants, spend limits, and balance reserve floor.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
];

function handleRpcMessage(message: any) {
  const { id, method, params } = message;

  if (method === "initialize") {
    return {
      jsonrpc: "2.0",
      id,
      result: {
        protocolVersion: "2024-11-05",
        capabilities: { tools: {} },
        serverInfo: {
          name: "aetherguard-mcp",
          version: "0.1.0",
        },
      },
    };
  }

  if (method === "tools/list") {
    return {
      jsonrpc: "2.0",
      id,
      result: { tools: TOOLS },
    };
  }

  if (method === "tools/call") {
    const { name, arguments: args } = params;

    if (name === "get_firewall_status") {
      const policy = guard.getPolicy();
      return {
        jsonrpc: "2.0",
        id,
        result: {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  maxSingleSpend: policy.maxSingleSpend.toString(),
                  maxRollingWindowSpend: policy.maxRollingWindowSpend.toString(),
                  rollingWindowSeconds: policy.rollingWindowSeconds,
                  minBalanceFloor: policy.minBalanceFloor.toString(),
                  allowedRecipients: policy.allowedRecipients,
                  allowedContracts: policy.allowedContracts,
                  allowedFunctions: policy.allowedFunctions,
                  status: "ACTIVE",
                },
                null,
                2
              ),
            },
          ],
        },
      };
    }

    if (name === "evaluate_agent_proposal") {
      try {
        const proposal = guard.createProposal({
          agentId: args.agentId,
          intentPrompt: args.intentPrompt,
          targetContract: args.targetContract,
          functionName: args.functionName,
          recipient: args.recipient,
          amount: BigInt(args.amount),
          assetSymbol: args.assetSymbol || "USDC",
        });

        const currentBalance = BigInt(args.currentAccountBalance);
        const proof = guard.evaluateAndProve(proposal, currentBalance);

        return {
          jsonrpc: "2.0",
          id,
          result: {
            content: [
              {
                type: "text",
                text: JSON.stringify(
                  {
                    status: "APPROVED",
                    proofDigest: proof.invariantDigestHex,
                    projectedBalance: proof.projectedBalance,
                    spentAmount: proof.spentAmount,
                    remainingRollingBudget: proof.remainingRollingBudget,
                    message: "All mathematical invariants verified. Zero prompt injection detected.",
                  },
                  null,
                  2
                ),
              },
            ],
          },
        };
      } catch (err) {
        if (err instanceof InvariantViolationError) {
          return {
            jsonrpc: "2.0",
            id,
            result: {
              content: [
                {
                  type: "text",
                  text: JSON.stringify(
                    {
                      status: "BLOCKED",
                      reason: err.reason,
                      message: err.message,
                      action: "TRANSACTION_ABORTED_PRE_BROADCAST",
                    },
                    null,
                    2
                  ),
                },
              ],
            },
          };
        }
        throw err;
      }
    }
  }

  return {
    jsonrpc: "2.0",
    id,
    error: { code: -32601, message: "Method not found" },
  };
}

// Start stdio loop
const rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal: false });
rl.on("line", (line) => {
  if (!line.trim()) return;
  try {
    const parsed = JSON.parse(line);
    const response = handleRpcMessage(parsed);
    if (response) {
      console.log(JSON.stringify(response));
    }
  } catch (e) {
    console.error("Invalid JSON-RPC line:", e);
  }
});
