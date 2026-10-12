/* Authorized Protocol Quality Assurance & Formal Verification Engine */

import { AetherGuardClient, type InvariantPolicy, InvariantViolationError } from "@aetherguard/sdk";

export interface ElizaPluginAction {
  name: string;
  similes: string[];
  description: string;
  validate: (runtime: any, message: any) => Promise<boolean>;
  handler: (runtime: any, message: any, state?: any, options?: any, callback?: any) => Promise<boolean>;
  examples: any[];
}

export interface ElizaPlugin {
  name: string;
  description: string;
  actions: ElizaPluginAction[];
  evaluators: any[];
  providers: any[];
}

/**
 * Creates the official AetherGuard ElizaOS plugin configured with a mathematical invariant policy.
 */
export function createAetherGuardPlugin(policy: InvariantPolicy): ElizaPlugin {
  const guard = new AetherGuardClient(policy);

  const safeTransferAction: ElizaPluginAction = {
    name: "AETHERGUARD_SAFE_TRANSFER",
    similes: ["SAFE_SEND", "GUARDED_TRANSFER", "SECURE_PAYMENT", "CHECK_INVARIANTS_AND_SEND"],
    description: "Evaluates mathematical invariants (spend velocity, recipient whitelists, balance floor) before executing a transaction.",
    validate: async (_runtime, message) => {
      const text = message.content?.text || "";
      return Boolean(text && (text.includes("send") || text.includes("transfer") || text.includes("swap")));
    },
    handler: async (runtime, message, _state, _options, callback) => {
      try {
        const amount = BigInt(message.content?.amount || 0);
        const recipient = message.content?.recipient || "";
        const targetContract = message.content?.targetContract || "DEFAULT_STOKEN_CONTRACT";
        const functionName = message.content?.functionName || "transfer";
        const assetSymbol = message.content?.asset || "USDC";

        const currentBalance = BigInt(message.content?.currentBalance || 1_000_000_000n);

        const proposal = guard.createProposal({
          agentId: runtime?.agentId || "eliza_agent",
          intentPrompt: message.content?.text || "Transfer request",
          targetContract,
          functionName,
          recipient,
          amount,
          assetSymbol,
        });

        const proof = guard.evaluateAndProve(proposal, currentBalance);

        if (callback) {
          callback({
            text: `[AetherGuard APPROVED] Invariants verified mathematically. Proof Digest: ${proof.invariantDigestHex.slice(0, 16)}... Ready for on-chain broadcast.`,
            content: { proof },
          });
        }
        return true;
      } catch (err) {
        if (err instanceof InvariantViolationError) {
          if (callback) {
            callback({
              text: `[AetherGuard BLOCKED] Security Invariant Violation: ${err.message}. Transaction aborted pre-broadcast. Zero funds lost.`,
              error: err.reason,
            });
          }
          return false;
        }
        throw err;
      }
    },
    examples: [
      [
        {
          user: "{{user1}}",
          content: { text: "Send 50 USDC to GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z" },
        },
        {
          user: "{{agentName}}",
          content: {
            text: "[AetherGuard APPROVED] Invariants verified mathematically. Zero prompt injection detected.",
            action: "AETHERGUARD_SAFE_TRANSFER",
          },
        },
      ],
    ],
  };

  return {
    name: "aetherguard",
    description: "High-Performance Mathematical Invariant Firewall & Prompt-Injection Defense for Autonomous Agents",
    actions: [safeTransferAction],
    evaluators: [],
    providers: [],
  };
}

export const aetherguardPlugin = createAetherGuardPlugin({
  maxSingleSpend: 100_000_000n, // 10 USDC default
  maxRollingWindowSpend: 500_000_000n, // 50 USDC default
  rollingWindowSeconds: 3600,
  minBalanceFloor: 50_000_000n, // 5 USDC floor
  allowedRecipients: [],
  allowedContracts: [],
  allowedFunctions: ["transfer", "swap_exact_tokens"],
});
