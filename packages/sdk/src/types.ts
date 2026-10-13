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

export interface EnclaveAttestationCertificate {
  enclavePublicKeyHex: string;
  policyCommitmentHex: string;
  proposalId: string;
  intentPromptHash: string;
  invariantDigestHex: string;
  nonce: number;
  issuedAt: number;
  enclaveSignatureHex: string;
}

export function computePolicyCommitment(policy: InvariantPolicy): string {
  const { createHash } = require("node:crypto");
  const hasher = createHash("sha256");
  hasher.update("AETHERGUARD_ZK_POLICY_V1");

  const bigintTo16Bytes = (v: bigint): Buffer => {
    const buf = Buffer.alloc(16);
    let val = v;
    for (let i = 15; i >= 0; i--) {
      buf[i] = Number(val & 0xffn);
      val >>= 8n;
    }
    return buf;
  };

  hasher.update(bigintTo16Bytes(policy.maxSingleSpend));
  hasher.update(bigintTo16Bytes(policy.maxRollingWindowSpend));

  const secondsBuf = Buffer.alloc(8);
  secondsBuf.writeBigInt64BE(BigInt(policy.rollingWindowSeconds));
  hasher.update(secondsBuf);

  hasher.update(bigintTo16Bytes(policy.minBalanceFloor));

  const recipients = [...(policy.allowedRecipients || [])].sort();
  for (const r of recipients) {
    hasher.update(Buffer.from(r, "utf-8"));
  }

  const contracts = [...(policy.allowedContracts || [])].sort();
  for (const c of contracts) {
    hasher.update(Buffer.from(c, "utf-8"));
  }

  if (policy.defiSwapPolicy) {
    const slipBuf = Buffer.alloc(4);
    slipBuf.writeUInt32BE(policy.defiSwapPolicy.maxSlippageBps);
    hasher.update(slipBuf);

    const devBuf = Buffer.alloc(4);
    devBuf.writeUInt32BE(policy.defiSwapPolicy.maxOracleDeviationBps);
    hasher.update(devBuf);

    hasher.update(bigintTo16Bytes(policy.defiSwapPolicy.minOutputFloor));
  }

  return hasher.digest("hex");
}

export function computeCertificateDigest(params: {
  enclavePublicKeyHex: string;
  policyCommitmentHex: string;
  proposalId: string;
  intentPromptHash: string;
  invariantDigestHex: string;
  nonce: number;
  issuedAt: number;
}): Buffer {
  const { createHash } = require("node:crypto");
  const hasher = createHash("sha256");
  hasher.update("AETHERGUARD_ENCLAVE_CERT_V1");
  hasher.update(Buffer.from(params.enclavePublicKeyHex, "utf-8"));
  hasher.update(Buffer.from(params.policyCommitmentHex, "utf-8"));
  hasher.update(Buffer.from(params.proposalId, "utf-8"));
  hasher.update(Buffer.from(params.intentPromptHash, "utf-8"));
  hasher.update(Buffer.from(params.invariantDigestHex, "utf-8"));

  const nonceBuf = Buffer.alloc(8);
  nonceBuf.writeBigUInt64BE(BigInt(params.nonce));
  hasher.update(nonceBuf);

  const issuedAtBuf = Buffer.alloc(8);
  issuedAtBuf.writeBigInt64BE(BigInt(params.issuedAt));
  hasher.update(issuedAtBuf);

  return hasher.digest();
}
