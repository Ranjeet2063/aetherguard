/* Authorized Protocol Quality Assurance & Formal Verification Engine */

export interface DefiSwapPolicy {
  maxSlippageBps: number;
  maxOracleDeviationBps: number;
  minOutputFloor: bigint;
}

export interface SwapParameters {
  assetIn: string;
  assetOut: string;
  amountIn: bigint;
  expectedAmountOut: bigint;
  minAmountOut: bigint;
  oracleReferencePriceBps?: number;
}

export interface InvariantPolicy {
  maxSingleSpend: bigint;
  maxRollingWindowSpend: bigint;
  rollingWindowSeconds: number;
  minBalanceFloor: bigint;
  allowedRecipients: string[];
  allowedContracts: string[];
  allowedFunctions: string[];
  humanConfirmationThreshold?: bigint;
  defiSwapPolicy?: DefiSwapPolicy;
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
  swapParams?: SwapParameters;
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
  | "HUMAN_CONFIRMATION_REQUIRED"
  | "EXCESSIVE_SLIPPAGE"
  | "ORACLE_PRICE_DEVIATION_EXCEEDED"
  | "OUTPUT_BELOW_FLOOR";

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
