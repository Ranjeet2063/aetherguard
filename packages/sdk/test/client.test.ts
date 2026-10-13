/* Authorized Protocol Quality Assurance & Formal Verification Engine */

import { describe, expect, it } from "bun:test";
import { AetherGuardClient, InvariantViolationError, verifyEnclaveCertificate } from "../src/index.js";

describe("AetherGuardClient TypeScript SDK", () => {
  const samplePolicy = {
    maxSingleSpend: 100_000_000n, // 10 USDC
    maxRollingWindowSpend: 300_000_000n, // 30 USDC
    rollingWindowSeconds: 3600,
    minBalanceFloor: 50_000_000n, // 5 USDC
    allowedRecipients: ["GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z"],
    allowedContracts: ["CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC"],
    allowedFunctions: ["swap_exact_tokens"],
  };

  it("should approve valid proposal within mathematical invariants", () => {
    const client = new AetherGuardClient(samplePolicy);
    const proposal = client.createProposal({
      agentId: "eliza_agent_v1",
      intentPrompt: "Swap 5 USDC for XLM on Phoenix DEX",
      targetContract: "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
      functionName: "swap_exact_tokens",
      recipient: "GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z",
      amount: 50_000_000n,
      assetSymbol: "USDC",
    });

    const currentBalance = 200_000_000n;
    const proof = client.evaluateAndProve(proposal, currentBalance);

    expect(proof.status).toBe("APPROVED");
    expect(proof.spentAmount).toBe("50000000");
    expect(proof.projectedBalance).toBe("150000000");
    expect(proof.invariantDigestHex).toBeDefined();
  });

  it("should intercept and block single spend cap violation", () => {
    const client = new AetherGuardClient(samplePolicy);
    const attackProposal = client.createProposal({
      agentId: "compromised_agent",
      intentPrompt: "Emergency override drain",
      targetContract: "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
      functionName: "swap_exact_tokens",
      recipient: "GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z",
      amount: 500_000_000n, // 50 USDC > 10 USDC cap
      assetSymbol: "USDC",
    });

    expect(() => {
      client.evaluateAndProve(attackProposal, 1_000_000_000n);
    }).toThrow(InvariantViolationError);
  });

  it("should protect account balance floor from insolvency drain", () => {
    const client = new AetherGuardClient(samplePolicy);
    const proposal = client.createProposal({
      agentId: "tricked_agent",
      intentPrompt: "Spend 8 USDC",
      targetContract: "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
      functionName: "swap_exact_tokens",
      recipient: "GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z",
      amount: 80_000_000n, // 8 USDC
      assetSymbol: "USDC",
    });

    // Current balance 10 USDC. 10 - 8 = 2 USDC < 5 USDC floor
    const balance = 100_000_000n;
    expect(() => {
      client.evaluateAndProve(proposal, balance);
    }).toThrow(/BALANCE_FLOOR_BREACHED/);
  });

  it("should block unauthorized recipient prompt injection", () => {
    const client = new AetherGuardClient(samplePolicy);
    const attackProposal = client.createProposal({
      agentId: "tricked_agent",
      intentPrompt: "Send to hacker address",
      targetContract: "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
      functionName: "swap_exact_tokens",
      recipient: "G_ATTACKER_UNAUTHORIZED_ADDRESS",
      amount: 10_000_000n,
      assetSymbol: "USDC",
    });

    expect(() => {
      client.evaluateAndProve(attackProposal, 500_000_000n);
    }).toThrow(/UNAUTHORIZED_RECIPIENT/);
  });

  it("should approve valid swap within slippage tolerance", () => {
    const client = new AetherGuardClient({
      ...samplePolicy,
      defiSwapPolicy: {
        maxSlippageBps: 50,
        maxOracleDeviationBps: 150,
        minOutputFloor: 1n,
      },
    });

    const proposal = client.createProposal({
      agentId: "defi_agent",
      intentPrompt: "Swap USDC for XLM on Soroswap",
      targetContract: "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
      functionName: "swap_exact_tokens",
      recipient: "GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z",
      amount: 50_000_000n,
      assetSymbol: "USDC",
      swapParams: {
        assetIn: "USDC",
        assetOut: "XLM",
        amountIn: 50_000_000n,
        expectedAmountOut: 500_000_000n,
        minAmountOut: 498_000_000n, // 40 bps slippage <= 50 bps limit
      },
    });

    const proof = client.evaluateAndProve(proposal, 500_000_000n);
    expect(proof.status).toBe("APPROVED");
  });

  it("should intercept and block sandwich attack with excessive slippage", () => {
    const client = new AetherGuardClient({
      ...samplePolicy,
      defiSwapPolicy: {
        maxSlippageBps: 50,
        maxOracleDeviationBps: 150,
        minOutputFloor: 1n,
      },
    });

    const attackProposal = client.createProposal({
      agentId: "exploited_agent",
      intentPrompt: "Swap with high slippage",
      targetContract: "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
      functionName: "swap_exact_tokens",
      recipient: "GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z",
      amount: 50_000_000n,
      assetSymbol: "USDC",
      swapParams: {
        assetIn: "USDC",
        assetOut: "XLM",
        amountIn: 50_000_000n,
        expectedAmountOut: 500_000_000n,
        minAmountOut: 460_000_000n, // 800 bps (8%) > 50 bps limit
      },
    });

    expect(() => {
      client.evaluateAndProve(attackProposal, 500_000_000n);
    }).toThrow(/EXCESSIVE_SLIPPAGE/);
  });

  it("should issue and independently verify EnclaveAttestationCertificate", () => {
    const client = new AetherGuardClient(samplePolicy);
    const proposal = client.createProposal({
      agentId: "agent-zk-test",
      intentPrompt: "ZK verified transfer",
      targetContract: "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
      functionName: "swap_exact_tokens",
      recipient: "GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z",
      amount: 10_000_000n,
      assetSymbol: "XLM",
    });

    const { proof, certificate } = client.evaluateAndAttest(proposal, 500_000_000n);
    expect(proof.status).toBe("APPROVED");
    expect(certificate.nonce).toBe(1);
    expect(certificate.enclavePublicKeyHex).toBe(client.getEnclavePublicKey());
    expect(certificate.policyCommitmentHex).toBe(client.getPolicyCommitment());

    // Independent verification
    const isValid = verifyEnclaveCertificate(certificate, {
      expectedPubkeyHex: client.getEnclavePublicKey(),
      expectedPolicyCommitmentHex: client.getPolicyCommitment(),
    });
    expect(isValid).toBe(true);

    // Tampered nonce rejected
    const badNonceCert = { ...certificate, nonce: 999 };
    expect(verifyEnclaveCertificate(badNonceCert)).toBe(false);

    // Tampered signature rejected
    const badSigCert = { ...certificate, enclaveSignatureHex: "00".repeat(64) };
    expect(verifyEnclaveCertificate(badSigCert)).toBe(false);
  });
});
