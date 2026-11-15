/* Authorized Protocol Quality Assurance & Formal Verification Engine */

use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Real-time metrics and latency telemetry for AetherGuard invariant verification.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineTelemetryMetrics {
    pub total_proposals_evaluated: u64,
    pub total_proposals_passed: u64,
    pub total_proposals_rejected: u64,
    pub total_verification_time_micros: u64,
    pub total_amount_guarded: u128,
}

impl Default for EngineTelemetryMetrics {
    fn default() -> Self {
        Self::new()
    }
}

impl EngineTelemetryMetrics {
    pub fn new() -> Self {
        Self {
            total_proposals_evaluated: 0,
            total_proposals_passed: 0,
            total_proposals_rejected: 0,
            total_verification_time_micros: 0,
            total_amount_guarded: 0,
        }
    }

    pub fn record_success(&mut self, duration: Duration, amount: u128) {
        self.total_proposals_evaluated += 1;
        self.total_proposals_passed += 1;
        self.total_verification_time_micros += duration.as_micros() as u64;
        self.total_amount_guarded += amount;
    }

    pub fn record_failure(&mut self, duration: Duration) {
        self.total_proposals_evaluated += 1;
        self.total_proposals_rejected += 1;
        self.total_verification_time_micros += duration.as_micros() as u64;
    }

    pub fn average_latency_micros(&self) -> f64 {
        if self.total_proposals_evaluated == 0 {
            0.0
        } else {
            self.total_verification_time_micros as f64 / self.total_proposals_evaluated as f64
        }
    }

    pub fn pass_rate_percentage(&self) -> f64 {
        if self.total_proposals_evaluated == 0 {
            100.0
        } else {
            (self.total_proposals_passed as f64 / self.total_proposals_evaluated as f64) * 100.0
        }
    }
}
