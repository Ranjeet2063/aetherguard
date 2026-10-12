/* Authorized Protocol Quality Assurance & Formal Verification Engine */

export interface InvariantPolicy {
  maxSingleSpend: bigint;
  maxRollingWindowSpend: bigint;
  rollingWindowSeconds: number;
  minBalanceFloor: bigint;
  allowedRecipients: string[];
  allowedContracts: string[];
  allowedFunctions: string[];
  humanConfirmationThreshold?: bigint;
  isEmergencyPaused?: boolean;
}

export interface AgentTransactionProposal {
  proposalId: string;
  agentId: string;
  intentPrompt: string;
  targetContract: string;
  functionName: string;
  recipient: string;
  amount: bigint;
  assetSymbol: string;
  timestamp: number;
}

export interface ProofOfInvariant {
  proposalId: string;
  verifiedAt: number;
  spentAmount: string;
  remainingRollingBudget: string;
  projectedBalance: string;
  invariantDigestHex: string;
  enclaveSignatureHex?: string;
  status: "APPROVED";
}

export type InvariantFailureReason =
  | "SINGLE_SPEND_CAP_EXCEEDED"
  | "ROLLING_WINDOW_LIMIT_EXCEEDED"
  | "BALANCE_FLOOR_BREACHED"
  | "UNAUTHORIZED_RECIPIENT"
  | "UNAUTHORIZED_CONTRACT"
  | "UNAUTHORIZED_FUNCTION"
  | "EMERGENCY_PAUSE_ACTIVE"
  | "HUMAN_CONFIRMATION_REQUIRED";

export class InvariantViolationError extends Error {
  constructor(
    public readonly reason: InvariantFailureReason,
    message: string,
    public readonly details?: Record<string, unknown>
  ) {
    super(`[AetherGuard] Mathematical Invariant Violation (${reason}): ${message}`);
    this.name = "InvariantViolationError";
  }
}
