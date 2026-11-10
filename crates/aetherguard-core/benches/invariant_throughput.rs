/* Authorized Protocol Quality Assurance & Formal Invariant Verification */
//! Benchmark: AetherGuard Mathematical Invariant Throughput
//!
//! Measures the core firewall engine's performance across three key operations:
//! - Single invariant evaluation latency
//! - Rolling-window spend calculation at scale  
//! - Batch transaction screening throughput

use aetherguard_core::{
    crypto::EnclaveKeyVault,
    engine::AetherGuardEngine,
    invariants::InvariantPolicy,
    proposals::AgentTransactionProposal,
};
use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};

const RECIPIENT: &str = "GDQRQ6BKGA7XUQHXPZ3JNMUMXMRQJBJSZHMVKTQEQPUVDYPC7CJNBFF";
const CONTRACT: &str = "CCWAMYJME4H46SE7GBK4ACMVIZPBC7GHYZIX37JQRD2YSEA3EDLV3ECO";

fn build_policy() -> InvariantPolicy {
    InvariantPolicy::builder()
        .max_single_spend(100_000_000)
        .max_rolling_window(500_000_000, 3600)
        .min_balance_floor(10_000_000)
        .allow_recipient(RECIPIENT)
        .allow_contract(CONTRACT)
        .allow_function("swap")
        .build()
}

fn build_proposal(agent_id: &str, amount: u128, timestamp: i64) -> AgentTransactionProposal {
    AgentTransactionProposal::new(
        agent_id,
        "benchmark invariant check",
        CONTRACT,
        "swap",
        RECIPIENT,
        amount,
        "USDC",
        timestamp,
    )
}

/// Benchmark 1: Single invariant evaluation latency (ns/op)
fn bench_single_evaluation(c: &mut Criterion) {
    let proposal = build_proposal("bench-agent-001", 50_000_000, 1_700_000_000);

    c.bench_function("single_invariant_eval", |b| {
        b.iter(|| {
            let policy = build_policy();
            let vault = EnclaveKeyVault::generate();
            let mut engine = AetherGuardEngine::new(policy, vault);
            black_box(engine.evaluate_and_prove(black_box(&proposal), 1_000_000_000))
        })
    });
}

/// Benchmark 2: Rolling-window spend calculation at various history sizes
fn bench_rolling_window(c: &mut Criterion) {
    let mut group = c.benchmark_group("rolling_window_at_scale");

    for history_size in [100usize, 1_000, 10_000] {
        group.throughput(Throughput::Elements(history_size as u64));
        group.bench_with_input(
            BenchmarkId::from_parameter(history_size),
            &history_size,
            |b, &size| {
                // Pre-build engine with spend history
                let policy = build_policy();
                let vault = EnclaveKeyVault::generate();
                let mut engine = AetherGuardEngine::new(policy, vault);
                for i in 0..size {
                    let p = build_proposal(
                        &format!("warmup-{}", i),
                        1_000,
                        1_700_000_000 - i as i64,
                    );
                    let _ = engine.evaluate_and_prove(&p, 1_000_000_000_000);
                }

                b.iter(|| {
                    black_box(engine.calculate_window_spend(black_box(1_700_000_000i64)))
                })
            },
        );
    }
    group.finish();
}

/// Benchmark 3: Batch screening throughput (proposals/second)
fn bench_batch_screening(c: &mut Criterion) {
    let mut group = c.benchmark_group("batch_screening_throughput");

    for batch_size in [10u64, 100, 1_000] {
        group.throughput(Throughput::Elements(batch_size));
        group.bench_with_input(
            BenchmarkId::from_parameter(batch_size),
            &batch_size,
            |b, &size| {
                let proposals: Vec<AgentTransactionProposal> = (0..size)
                    .map(|i| build_proposal(
                        &format!("agent-{}", i),
                        10_000,
                        1_700_000_000 + i as i64,
                    ))
                    .collect();

                b.iter(|| {
                    let policy = build_policy();
                    let mut engine = AetherGuardEngine::new(policy, EnclaveKeyVault::generate());
                    for p in black_box(&proposals) {
                        let _ = engine.evaluate_and_prove(p, 10_000_000_000);
                    }
                })
            },
        );
    }
    group.finish();
}

criterion_group!(
    benches,
    bench_single_evaluation,
    bench_rolling_window,
    bench_batch_screening,
);
criterion_main!(benches);
