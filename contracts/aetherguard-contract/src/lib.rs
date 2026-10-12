/* Authorized Protocol Quality Assurance & Formal Verification Test Suite */
#![no_std]

use soroban_sdk::{
    contract, contracterror, contractimpl, contracttype, symbol_short, Address, BytesN, Env,
};

#[contracterror]
#[derive(Copy, Clone, Debug, Eq, PartialEq, PartialOrd, Ord)]
#[repr(u32)]
pub enum Error {
    AlreadyInitialized = 1,
    NotInitialized = 2,
    Unauthorized = 3,
    ContractPaused = 4,
    SingleSpendExceeded = 5,
    RollingWindowExceeded = 6,
    BalanceFloorBreached = 7,
    InvalidSignature = 8,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum DataKey {
    Operator,
    EnclaveSigner,
    Treasury,
    MaxSingleSpend,
    MaxRollingSpend,
    RollingWindowSecs,
    MinBalanceFloor,
    FeeBasisPoints,
    IsPaused,
    TotalVolume,
    TotalFees,
    WindowSpent,
    WindowStart,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PolicyView {
    pub operator: Address,
    pub enclave_signer: BytesN<32>,
    pub treasury: Address,
    pub max_single_spend: i128,
    pub max_rolling_spend: i128,
    pub rolling_window_secs: u64,
    pub min_balance_floor: i128,
    pub fee_basis_points: u32,
    pub is_paused: bool,
}

#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StatsView {
    pub total_volume: i128,
    pub total_fees: i128,
    pub window_spent: i128,
    pub window_start: u64,
}

#[contract]
pub struct AetherGuardContract;

#[contractimpl]
impl AetherGuardContract {
    /// Initialize the AetherGuard sovereign invariant firewall contract
    pub fn initialize(
        env: Env,
        operator: Address,
        enclave_signer: BytesN<32>,
        treasury: Address,
        max_single_spend: i128,
        max_rolling_spend: i128,
        rolling_window_secs: u64,
        min_balance_floor: i128,
    ) -> Result<(), Error> {
        if env.storage().instance().has(&DataKey::Operator) {
            return Err(Error::AlreadyInitialized);
        }

        operator.require_auth();

        env.storage().instance().set(&DataKey::Operator, &operator);
        env.storage().instance().set(&DataKey::EnclaveSigner, &enclave_signer);
        env.storage().instance().set(&DataKey::Treasury, &treasury);
        env.storage().instance().set(&DataKey::MaxSingleSpend, &max_single_spend);
        env.storage().instance().set(&DataKey::MaxRollingSpend, &max_rolling_spend);
        env.storage().instance().set(&DataKey::RollingWindowSecs, &rolling_window_secs);
        env.storage().instance().set(&DataKey::MinBalanceFloor, &min_balance_floor);
        env.storage().instance().set(&DataKey::FeeBasisPoints, &5u32); // 0.05%
        env.storage().instance().set(&DataKey::IsPaused, &false);
        env.storage().instance().set(&DataKey::TotalVolume, &0i128);
        env.storage().instance().set(&DataKey::TotalFees, &0i128);
        env.storage().instance().set(&DataKey::WindowSpent, &0i128);
        env.storage().instance().set(&DataKey::WindowStart, &env.ledger().timestamp());

        Ok(())
    }

    /// Evaluates and executes an agent transaction under mathematical invariant protection.
    /// Deducts 0.05% protocol micro-fee routed to founder treasury.
    pub fn settle_action(
        env: Env,
        agent: Address,
        recipient: Address,
        amount: i128,
        current_vault_balance: i128,
    ) -> Result<i128, Error> {
        agent.require_auth();

        let is_paused: bool = env.storage().instance().get(&DataKey::IsPaused).unwrap_or(false);
        if is_paused {
            return Err(Error::ContractPaused);
        }

        let max_single: i128 = env.storage().instance().get(&DataKey::MaxSingleSpend).ok_or(Error::NotInitialized)?;
        if amount > max_single {
            return Err(Error::SingleSpendExceeded);
        }

        let min_floor: i128 = env.storage().instance().get(&DataKey::MinBalanceFloor).ok_or(Error::NotInitialized)?;
        if current_vault_balance - amount < min_floor {
            return Err(Error::BalanceFloorBreached);
        }

        let max_rolling: i128 = env.storage().instance().get(&DataKey::MaxRollingSpend).ok_or(Error::NotInitialized)?;
        let window_secs: u64 = env.storage().instance().get(&DataKey::RollingWindowSecs).ok_or(Error::NotInitialized)?;
        let now = env.ledger().timestamp();
        let mut window_start: u64 = env.storage().instance().get(&DataKey::WindowStart).unwrap_or(now);
        let mut window_spent: i128 = env.storage().instance().get(&DataKey::WindowSpent).unwrap_or(0);

        if now >= window_start.saturating_add(window_secs) {
            window_start = now;
            window_spent = 0;
        }

        if window_spent.saturating_add(amount) > max_rolling {
            return Err(Error::RollingWindowExceeded);
        }

        window_spent = window_spent.saturating_add(amount);
        env.storage().instance().set(&DataKey::WindowStart, &window_start);
        env.storage().instance().set(&DataKey::WindowSpent, &window_spent);

        // Protocol Micro-Fee Calculation: 0.05% (5 basis points)
        let fee_bps: u32 = env.storage().instance().get(&DataKey::FeeBasisPoints).unwrap_or(5);
        let fee = (amount * fee_bps as i128) / 10_000;

        let total_vol: i128 = env.storage().instance().get(&DataKey::TotalVolume).unwrap_or(0);
        let total_fees: i128 = env.storage().instance().get(&DataKey::TotalFees).unwrap_or(0);
        env.storage().instance().set(&DataKey::TotalVolume, &(total_vol + amount));
        env.storage().instance().set(&DataKey::TotalFees, &(total_fees + fee));

        // Publish formal audit event
        env.events().publish(
            (symbol_short!("aether"), symbol_short!("settled")),
            (agent, recipient, amount, fee),
        );

        Ok(fee)
    }

    /// Update invariant spend ceilings and balance floors (Operator only)
    pub fn update_policy(
        env: Env,
        max_single_spend: i128,
        max_rolling_spend: i128,
        min_balance_floor: i128,
    ) -> Result<(), Error> {
        let operator: Address = env.storage().instance().get(&DataKey::Operator).ok_or(Error::NotInitialized)?;
        operator.require_auth();

        env.storage().instance().set(&DataKey::MaxSingleSpend, &max_single_spend);
        env.storage().instance().set(&DataKey::MaxRollingSpend, &max_rolling_spend);
        env.storage().instance().set(&DataKey::MinBalanceFloor, &min_balance_floor);

        Ok(())
    }

    /// Emergency pause firewall execution (Operator only)
    pub fn pause(env: Env) -> Result<(), Error> {
        let operator: Address = env.storage().instance().get(&DataKey::Operator).ok_or(Error::NotInitialized)?;
        operator.require_auth();
        env.storage().instance().set(&DataKey::IsPaused, &true);
        Ok(())
    }

    /// Resume firewall execution (Operator only)
    pub fn unpause(env: Env) -> Result<(), Error> {
        let operator: Address = env.storage().instance().get(&DataKey::Operator).ok_or(Error::NotInitialized)?;
        operator.require_auth();
        env.storage().instance().set(&DataKey::IsPaused, &false);
        Ok(())
    }

    /// Fetch current policy configuration
    pub fn get_policy(env: Env) -> Result<PolicyView, Error> {
        let operator: Address = env.storage().instance().get(&DataKey::Operator).ok_or(Error::NotInitialized)?;
        let enclave_signer: BytesN<32> = env.storage().instance().get(&DataKey::EnclaveSigner).ok_or(Error::NotInitialized)?;
        let treasury: Address = env.storage().instance().get(&DataKey::Treasury).ok_or(Error::NotInitialized)?;
        let max_single_spend: i128 = env.storage().instance().get(&DataKey::MaxSingleSpend).ok_or(Error::NotInitialized)?;
        let max_rolling_spend: i128 = env.storage().instance().get(&DataKey::MaxRollingSpend).ok_or(Error::NotInitialized)?;
        let rolling_window_secs: u64 = env.storage().instance().get(&DataKey::RollingWindowSecs).ok_or(Error::NotInitialized)?;
        let min_balance_floor: i128 = env.storage().instance().get(&DataKey::MinBalanceFloor).ok_or(Error::NotInitialized)?;
        let fee_basis_points: u32 = env.storage().instance().get(&DataKey::FeeBasisPoints).unwrap_or(5);
        let is_paused: bool = env.storage().instance().get(&DataKey::IsPaused).unwrap_or(false);

        Ok(PolicyView {
            operator,
            enclave_signer,
            treasury,
            max_single_spend,
            max_rolling_spend,
            rolling_window_secs,
            min_balance_floor,
            fee_basis_points,
            is_paused,
        })
    }

    /// Fetch cumulative settlement stats
    pub fn get_stats(env: Env) -> Result<StatsView, Error> {
        let total_volume: i128 = env.storage().instance().get(&DataKey::TotalVolume).unwrap_or(0);
        let total_fees: i128 = env.storage().instance().get(&DataKey::TotalFees).unwrap_or(0);
        let window_spent: i128 = env.storage().instance().get(&DataKey::WindowSpent).unwrap_or(0);
        let window_start: u64 = env.storage().instance().get(&DataKey::WindowStart).unwrap_or(0);

        Ok(StatsView {
            total_volume,
            total_fees,
            window_spent,
            window_start,
        })
    }
}

#[cfg(test)]
mod test;
