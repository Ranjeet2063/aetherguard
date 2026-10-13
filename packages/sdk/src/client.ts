/* Authorized Protocol Quality Assurance & Formal Verification Engine */

import {
  createHash,
  generateKeyPairSync,
  sign,
  verify,
  createPublicKey,
  type KeyObject,
} from "node:crypto";
import {
  type AgentTransactionProposal,
  type InvariantPolicy,
  InvariantViolationError,
  type ProofOfInvariant,
  type EnclaveAttestationCertificate,
  type SwapParameters,
  computePolicyCommitment,
  computeCertificateDigest,
} from "./types.js";

interface SpendEvent {
  timestamp: number;
  amount: bigint;
}

export class AetherGuardClient {
  private policy: InvariantPolicy;
  private spendHistory: SpendEvent[] = [];
  private enclaveKeyPair: { publicKey: KeyObject; privateKey: KeyObject };
  private enclavePublicKeyHex: string;
  private nonce = 0;

  constructor(policy: InvariantPolicy) {
    this.policy = {
      ...policy,
      allowedRecipients: policy.allowedRecipients || [],
      allowedContracts: policy.allowedContracts || [],
      allowedFunctions: policy.allowedFunctions || [],
      isEmergencyPaused: policy.isEmergencyPaused ?? false,
    };
    this.enclaveKeyPair = generateKeyPairSync("ed25519");
    const spkiDer = this.enclaveKeyPair.publicKey.export({ type: "spki", format: "der" });
    this.enclavePublicKeyHex = spkiDer.subarray(spkiDer.length - 32).toString("hex");
  }

  public getPolicy(): Readonly<InvariantPolicy> {
    return this.policy;
  }

  public updatePolicy(newPolicy: Partial<InvariantPolicy>): void {
    this.policy = { ...this.policy, ...newPolicy };
  }

  public calculateWindowSpend(now: number): bigint {
    const windowStart = now - this.policy.rollingWindowSeconds;
    return this.spendHistory
      .filter((e) => e.timestamp >= windowStart && e.timestamp <= now)
      .reduce((acc, e) => acc + e.amount, 0n);
  }

  public createProposal(params: {
    agentId: string;
    intentPrompt: string;
    targetContract: string;
    functionName: string;
    recipient: string;
    amount: bigint;
    assetSymbol: string;
    swapParams?: SwapParameters;
    timestamp?: number;
  }): AgentTransactionProposal {
    const timestamp = params.timestamp ?? Math.floor(Date.now() / 1000);
    const hash = createHash("sha256")
      .update(params.agentId)
      .update(params.amount.toString())
      .update(params.recipient)
      .update(timestamp.toString())
      .digest("hex");

    return {
      proposalId: `prop_${hash.slice(0, 16)}`,
      agentId: params.agentId,
      intentPrompt: params.intentPrompt,
      targetContract: params.targetContract,
      functionName: params.functionName,
      recipient: params.recipient,
      amount: params.amount,
      assetSymbol: params.assetSymbol,
      swapParams: params.swapParams,
      timestamp,
    };
  }

  /**
   * Primary Invariant Gate.
   * Intercepts untrusted agent proposals and verifies all mathematical boundary rules.
   */
  public evaluateAndProve(
    proposal: AgentTransactionProposal,
    currentAccountBalance: bigint
  ): ProofOfInvariant {
    // 1. Emergency Pause Check
    if (this.policy.isEmergencyPaused) {
      throw new InvariantViolationError(
        "EMERGENCY_PAUSE_ACTIVE",
        `Emergency kill-switch is currently active for agent ${proposal.agentId}`
      );
    }

    // 2. Single Spend Cap Check
    if (proposal.amount > this.policy.maxSingleSpend) {
      throw new InvariantViolationError(
        "SINGLE_SPEND_CAP_EXCEEDED",
        `Attempted spend ${proposal.amount} exceeds allowed cap ${this.policy.maxSingleSpend}`,
        { attempted: proposal.amount.toString(), cap: this.policy.maxSingleSpend.toString() }
      );
    }

    // 3. Recipient Whitelist Check
    if (
      this.policy.allowedRecipients.length > 0 &&
      !this.policy.allowedRecipients.includes(proposal.recipient)
    ) {
      throw new InvariantViolationError(
        "UNAUTHORIZED_RECIPIENT",
        `Recipient '${proposal.recipient}' is not in the authorized whitelist`,
        { recipient: proposal.recipient }
      );
    }

    // 4. Contract Whitelist Check
    if (
      this.policy.allowedContracts.length > 0 &&
      !this.policy.allowedContracts.includes(proposal.targetContract)
    ) {
      throw new InvariantViolationError(
        "UNAUTHORIZED_CONTRACT",
        `Target contract '${proposal.targetContract}' is not authorized`,
        { contract: proposal.targetContract }
      );
    }

    // 5. Function Whitelist Check
    if (
      this.policy.allowedFunctions.length > 0 &&
      !this.policy.allowedFunctions.includes(proposal.functionName)
    ) {
      throw new InvariantViolationError(
        "UNAUTHORIZED_FUNCTION",
        `Function '${proposal.functionName}' is not authorized on '${proposal.targetContract}'`,
        { function: proposal.functionName }
      );
    }

    // 6. Rolling Window Limit Check
    const currentWindowSpend = this.calculateWindowSpend(proposal.timestamp);
    const projectedWindowSpend = currentWindowSpend + proposal.amount;
    if (projectedWindowSpend > this.policy.maxRollingWindowSpend) {
      throw new InvariantViolationError(
        "ROLLING_WINDOW_LIMIT_EXCEEDED",
        `Window spend (${currentWindowSpend} + ${proposal.amount}) exceeds limit ${this.policy.maxRollingWindowSpend}`,
        {
          currentSpent: currentWindowSpend.toString(),
          attempted: proposal.amount.toString(),
          windowLimit: this.policy.maxRollingWindowSpend.toString(),
        }
      );
    }

    // 7. Balance Floor Invariant Check
    if (currentAccountBalance < proposal.amount) {
      throw new InvariantViolationError(
        "BALANCE_FLOOR_BREACHED",
        `Insufficient balance: current ${currentAccountBalance} < spend ${proposal.amount}`
      );
    }

    const projectedBalance = currentAccountBalance - proposal.amount;
    if (projectedBalance < this.policy.minBalanceFloor) {
      throw new InvariantViolationError(
        "BALANCE_FLOOR_BREACHED",
        `Projected balance ${projectedBalance} breaches mandatory floor ${this.policy.minBalanceFloor}`,
        {
          currentBalance: currentAccountBalance.toString(),
          projectedBalance: projectedBalance.toString(),
          floor: this.policy.minBalanceFloor.toString(),
        }
      );
    }

    // 8. Human Escalation Check
    if (
      this.policy.humanConfirmationThreshold &&
      proposal.amount >= this.policy.humanConfirmationThreshold
    ) {
      throw new InvariantViolationError(
        "HUMAN_CONFIRMATION_REQUIRED",
        `Spend of ${proposal.amount} exceeds automated autonomy limit ${this.policy.humanConfirmationThreshold}. Human signature required.`
      );
    }

    // 9. DeFi AMM Swap & Oracle Protection Invariant Checks
    if (proposal.swapParams) {
      const swap = proposal.swapParams;
      const defiPolicy = this.policy.defiSwapPolicy || {
        maxSlippageBps: 100,
        maxOracleDeviationBps: 200,
        minOutputFloor: 1n,
      };

      // 9a. Minimum Output Floor Check
      if (swap.minAmountOut < defiPolicy.minOutputFloor) {
        throw new InvariantViolationError(
          "OUTPUT_BELOW_FLOOR",
          `Swap minimum output ${swap.minAmountOut} breaches floor ${defiPolicy.minOutputFloor}`,
          {
            minAmountOut: swap.minAmountOut.toString(),
            floor: defiPolicy.minOutputFloor.toString(),
          }
        );
      }

      // 9b. Slippage Tolerance Invariant Check
      if (swap.expectedAmountOut > 0n && swap.minAmountOut < swap.expectedAmountOut) {
        const diff = swap.expectedAmountOut - swap.minAmountOut;
        const calculatedBps = Number((diff * 10000n) / swap.expectedAmountOut);
        if (calculatedBps > defiPolicy.maxSlippageBps) {
          throw new InvariantViolationError(
            "EXCESSIVE_SLIPPAGE",
            `Swap slippage ${calculatedBps} bps exceeds maximum tolerance of ${defiPolicy.maxSlippageBps} bps`,
            {
              calculatedBps: calculatedBps.toString(),
              maxBps: defiPolicy.maxSlippageBps.toString(),
            }
          );
        }
      }

      // 9c. Oracle Price Deviation Check
      if (swap.oracleReferencePriceBps && swap.amountIn > 0n && swap.oracleReferencePriceBps > 0) {
        const impliedPriceBps = Number((swap.expectedAmountOut * 10000n) / swap.amountIn);
        const diff = Math.abs(impliedPriceBps - swap.oracleReferencePriceBps);
        const deviationBps = Math.floor((diff * 10000) / swap.oracleReferencePriceBps);
        if (deviationBps > defiPolicy.maxOracleDeviationBps) {
          throw new InvariantViolationError(
            "ORACLE_PRICE_DEVIATION_EXCEEDED",
            `Swap price deviation ${deviationBps} bps from oracle exceeds tolerance of ${defiPolicy.maxOracleDeviationBps} bps`,
            {
              calculatedDeviationBps: deviationBps.toString(),
              maxDeviationBps: defiPolicy.maxOracleDeviationBps.toString(),
            }
          );
        }
      }
    }

    // --- Invariants Verified ---
    this.spendHistory.push({
      timestamp: proposal.timestamp,
      amount: proposal.amount,
    });

    // Prune history
    const cutoff = proposal.timestamp - this.policy.rollingWindowSeconds * 2;
    this.spendHistory = this.spendHistory.filter((e) => e.timestamp >= cutoff);

    const remainingRollingBudget =
      this.policy.maxRollingWindowSpend - projectedWindowSpend;

    const digest = createHash("sha256")
      .update(proposal.proposalId)
      .update(projectedBalance.toString())
      .update(remainingRollingBudget.toString())
      .update(proposal.timestamp.toString())
      .digest("hex");

    const proofSig = sign(null, Buffer.from(digest, "hex"), this.enclaveKeyPair.privateKey).toString("hex");

    return {
      proposalId: proposal.proposalId,
      verifiedAt: proposal.timestamp,
      spentAmount: proposal.amount.toString(),
      remainingRollingBudget: remainingRollingBudget.toString(),
      projectedBalance: projectedBalance.toString(),
      invariantDigestHex: digest,
      status: "APPROVED",
      enclaveSignatureHex: proofSig,
    };
  }

  public getEnclavePublicKey(): string {
    return this.enclavePublicKeyHex;
  }

  public getPolicyCommitment(): string {
    return computePolicyCommitment(this.policy);
  }

  public evaluateAndAttest(
    proposal: AgentTransactionProposal,
    currentAccountBalance: bigint
  ): { proof: ProofOfInvariant; certificate: EnclaveAttestationCertificate } {
    const proof = this.evaluateAndProve(proposal, currentAccountBalance);
    this.nonce += 1;
    const currentNonce = this.nonce;
    const policyCommitmentHex = this.getPolicyCommitment();
    const intentPromptHash = createHash("sha256").update(proposal.intentPrompt).digest("hex");

    const certDigest = computeCertificateDigest({
      enclavePublicKeyHex: this.enclavePublicKeyHex,
      policyCommitmentHex,
      proposalId: proof.proposalId,
      intentPromptHash,
      invariantDigestHex: proof.invariantDigestHex,
      nonce: currentNonce,
      issuedAt: proof.verifiedAt,
    });

    const certSig = sign(null, certDigest, this.enclaveKeyPair.privateKey).toString("hex");

    const certificate: EnclaveAttestationCertificate = {
      enclavePublicKeyHex: this.enclavePublicKeyHex,
      policyCommitmentHex,
      proposalId: proof.proposalId,
      intentPromptHash,
      invariantDigestHex: proof.invariantDigestHex,
      nonce: currentNonce,
      issuedAt: proof.verifiedAt,
      enclaveSignatureHex: certSig,
    };

    return { proof, certificate };
  }
}

export function verifyEnclaveCertificate(
  cert: EnclaveAttestationCertificate,
  options?: {
    expectedPubkeyHex?: string;
    expectedPolicyCommitmentHex?: string;
  }
): boolean {
  if (options?.expectedPubkeyHex && cert.enclavePublicKeyHex !== options.expectedPubkeyHex) {
    return false;
  }
  if (
    options?.expectedPolicyCommitmentHex &&
    cert.policyCommitmentHex !== options.expectedPolicyCommitmentHex
  ) {
    return false;
  }

  try {
    const certDigest = computeCertificateDigest({
      enclavePublicKeyHex: cert.enclavePublicKeyHex,
      policyCommitmentHex: cert.policyCommitmentHex,
      proposalId: cert.proposalId,
      intentPromptHash: cert.intentPromptHash,
      invariantDigestHex: cert.invariantDigestHex,
      nonce: cert.nonce,
      issuedAt: cert.issuedAt,
    });

    const rawPub = Buffer.from(cert.enclavePublicKeyHex, "hex");
    const spki = Buffer.concat([Buffer.from("302a300506032b6570032100", "hex"), rawPub]);
    const pubKeyObj = createPublicKey({ key: spki, format: "der", type: "spki" });
    const sigBytes = Buffer.from(cert.enclaveSignatureHex, "hex");

    return verify(null, certDigest, pubKeyObj, sigBytes);
  } catch {
    return false;
  }
}
