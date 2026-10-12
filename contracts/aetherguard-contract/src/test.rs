/* Authorized Protocol Quality Assurance & Formal Verification Test Suite */
#![cfg(test)]

use super::*;
use soroban_sdk::{testutils::Address as _, Env};

#[test]
fn test_successful_settlement_and_fee_routing() {
    let env = Env::default();
    env.mock_all_auths();

    let contract_id = env.register_contract(None, AetherGuardContract);
    let client = AetherGuardContractClient::new(&env, &contract_id);

    let operator = Address::generate(&env);
    let treasury = Address::generate(&env);
    let agent = Address::generate(&env);
    let recipient = Address::generate(&env);
    let enclave_key = BytesN::from_array(&env, &[1u8; 32]);

    // Single spend cap: 1,000, Rolling cap: 3,000, Floor: 500
    client.initialize(
        &operator,
        &enclave_key,
        &treasury,
        &1_000,
        &3_000,
        &3600,
        &500,
    );

    // Legitimate settlement: Spend 500 from vault with 2,000 balance -> remaining 1,500 > floor 500
    let fee = client.settle_action(&agent, &recipient, &500, &2_000);
    // 0.05% of 500 = (500 * 5) / 10,000 = 0 (integer division) or test with 10,000
    assert_eq!(fee, 0);

    let stats = client.get_stats();
    assert_eq!(stats.total_volume, 500);
    assert_eq!(stats.window_spent, 500);
}

#[test]
fn test_micro_fee_calculation() {
    let env = Env::default();
    env.mock_all_auths();

    let contract_id = env.register_contract(None, AetherGuardContract);
    let client = AetherGuardContractClient::new(&env, &contract_id);

    let operator = Address::generate(&env);
    let treasury = Address::generate(&env);
    let agent = Address::generate(&env);
    let recipient = Address::generate(&env);
    let enclave_key = BytesN::from_array(&env, &[2u8; 32]);

    client.initialize(
        &operator,
        &enclave_key,
        &treasury,
        &100_000,
        &500_000,
        &3600,
        &1_000,
    );

    // 10,000 USDC transfer -> 0.05% fee = 5 USDC
    let fee = client.settle_action(&agent, &recipient, &10_000, &50_000);
    assert_eq!(fee, 5); // (10,000 * 5) / 10,000 = 5 USDC

    let stats = client.get_stats();
    assert_eq!(stats.total_volume, 10_000);
    assert_eq!(stats.total_fees, 5);
}

#[test]
#[should_panic(expected = "Error(Contract, #5)")]
fn test_invariant_violation_single_spend_exceeded() {
    let env = Env::default();
    env.mock_all_auths();

    let contract_id = env.register_contract(None, AetherGuardContract);
    let client = AetherGuardContractClient::new(&env, &contract_id);

    let operator = Address::generate(&env);
    let treasury = Address::generate(&env);
    let agent = Address::generate(&env);
    let recipient = Address::generate(&env);
    let enclave_key = BytesN::from_array(&env, &[3u8; 32]);

    client.initialize(&operator, &enclave_key, &treasury, &500, &2_000, &3600, &100);

    // Adversarial proposal: 600 exceeds 500 cap -> MUST REVERT
    client.settle_action(&agent, &recipient, &600, &10_000);
}

#[test]
#[should_panic(expected = "Error(Contract, #7)")]
fn test_invariant_violation_balance_floor_breached() {
    let env = Env::default();
    env.mock_all_auths();

    let contract_id = env.register_contract(None, AetherGuardContract);
    let client = AetherGuardContractClient::new(&env, &contract_id);

    let operator = Address::generate(&env);
    let treasury = Address::generate(&env);
    let agent = Address::generate(&env);
    let recipient = Address::generate(&env);
    let enclave_key = BytesN::from_array(&env, &[4u8; 32]);

    client.initialize(&operator, &enclave_key, &treasury, &1_000, &5_000, &3600, &500);

    // Vault balance = 600, spend = 200 -> remaining 400 < floor 500 -> MUST REVERT
    client.settle_action(&agent, &recipient, &200, &600);
}

#[test]
#[should_panic(expected = "Error(Contract, #6)")]
fn test_invariant_violation_rolling_window_exceeded() {
    let env = Env::default();
    env.mock_all_auths();

    let contract_id = env.register_contract(None, AetherGuardContract);
    let client = AetherGuardContractClient::new(&env, &contract_id);

    let operator = Address::generate(&env);
    let treasury = Address::generate(&env);
    let agent = Address::generate(&env);
    let recipient = Address::generate(&env);
    let enclave_key = BytesN::from_array(&env, &[5u8; 32]);

    // Rolling window limit = 1,000
    client.initialize(&operator, &enclave_key, &treasury, &600, &1_000, &3600, &100);

    // First spend: 500 (allowed)
    client.settle_action(&agent, &recipient, &500, &10_000);

    // Second spend: 550 -> 500 + 550 = 1,050 > 1,000 -> MUST REVERT
    client.settle_action(&agent, &recipient, &550, &10_000);
}

#[test]
#[should_panic(expected = "Error(Contract, #4)")]
fn test_emergency_pause_halts_execution() {
    let env = Env::default();
    env.mock_all_auths();

    let contract_id = env.register_contract(None, AetherGuardContract);
    let client = AetherGuardContractClient::new(&env, &contract_id);

    let operator = Address::generate(&env);
    let treasury = Address::generate(&env);
    let agent = Address::generate(&env);
    let recipient = Address::generate(&env);
    let enclave_key = BytesN::from_array(&env, &[6u8; 32]);

    client.initialize(&operator, &enclave_key, &treasury, &1_000, &5_000, &3600, &100);

    // Pause the contract
    client.pause();

    // Settle action must revert with ContractPaused
    client.settle_action(&agent, &recipient, &100, &10_000);
}
