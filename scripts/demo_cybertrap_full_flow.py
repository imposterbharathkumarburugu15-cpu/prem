#!/usr/bin/env python3
"""
PRAMAN CyberTrap — 13-Step Judge-Ready Demonstration Script
Demonstrates:
  Detect -> Analyse -> Learn -> Recommend -> Approve -> Validate -> Improve -> Ledger Audit
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app

def log(msg=""):
    print(msg, flush=True)

def run_judge_demo():
    log("=" * 70)
    log("🛡️  PRAMAN CyberTrap — Adaptive Agricultural Cyber Defense")
    log("    Judge-Ready 13-Step Automated Verification")
    log("=" * 70)

    log("\n[Step 1] Initializing TestClient & Verifying Platform Health...")
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    log(f" -> Result: 200 OK | Platform Service: {r.json().get('service')}")

    # Step 2: Verify Isolated CyberTrap Module Active
    log("\n[Step 2] Verifying Isolated CyberTrap Honeypot Module...")
    r = client.get("/api/v1/cybertrap/decoys/batches")
    assert r.status_code == 200, f"Decoy catalog failed: {r.text}"
    decoys = r.json()
    log(f" -> Result: 200 OK | Synthetic Honey-Batches Active: {decoys.get('total')}")

    # Step 3 & 4: Run Local Attacker Simulator (Decoy Probe with Canary Trigger)
    log("\n[Step 3 & 4] Attacker accesses synthetic honey-batch through decoy endpoint...")
    honey_batch_id = "BATCH-HONEY-SAFFRON-001"
    r = client.get(
        f"/api/v1/cybertrap/decoys/batches/{honey_batch_id}",
        headers={"X-Canary-Secret": "prm_canary_saffron_secret_9981"}
    )
    assert r.status_code == 200, f"Honey-batch probe failed: {r.text}"
    log(f" -> Result: 200 OK | Decoy Batch Returned: {r.json().get('batch_id')} (Honeytoken Armed)")

    # Step 5: Display Detected Decoy Interaction
    log("\n[Step 5] Ingesting & Displaying Captured Interaction Telemetry...")
    r = client.get("/api/v1/cybertrap/intel/events?limit=5")
    assert r.status_code == 200
    events = r.json().get("items", [])
    log(f" -> Result: {len(events)} Events Logged | Latest Event: {events[0]['decoy_type']} at {events[0]['request_path']}")

    # Step 6: Explain Threat Classification
    log("\n[Step 6] Running Deterministic Threat Classification Engine...")
    r = client.post("/api/v1/cybertrap/intel/analyse")
    assert r.status_code == 200
    analysis = r.json().get("analysis", {})
    log(f" -> Result: Analyzed {analysis.get('events_analyzed')} events | Incidents Promoted: {analysis.get('incidents_created')}")

    # Step 7: Generate Administrator Alert / Fetch Incidents
    log("\n[Step 7] Generating Incident Intelligence Alert...")
    r = client.get("/api/v1/cybertrap/intel/incidents")
    assert r.status_code == 200
    incidents = r.json().get("items", [])
    assert len(incidents) > 0, "Expected at least 1 incident"
    target_inc = incidents[0]
    log(f" -> Result: Incident '{target_inc['id']}' | Category: {target_inc['category']} | Risk: {target_inc['risk_level']}")
    log(f"    Explainable Rationale: {target_inc['explanation'].get('primary_rule', 'N/A')}")

    # Step 8: Propose Defensive Security Rule
    log("\n[Step 8] Adaptive Engine Recommends Defensive Rule Proposal...")
    r = client.post("/api/v1/cybertrap/feedback/rules/generate")
    assert r.status_code == 200
    r = client.get("/api/v1/cybertrap/feedback/rules")
    rules = r.json().get("items", [])
    assert len(rules) > 0, "Expected at least 1 rule"
    target_rule = rules[0]
    log(f" -> Result: Rule '{target_rule['id']}' Proposed: {target_rule['rule_type']} on {target_rule['target_value']}")
    log(f"    Parameters: {target_rule['parameters']}")

    # Step 9: Approve Rule as Cybersecurity Administrator
    log("\n[Step 9] Cybersecurity Administrator (Dr. K. Rao) Formally Approves Rule...")
    r = client.post(
        f"/api/v1/cybertrap/feedback/rules/{target_rule['id']}/approve",
        json={"approved_by": "Cybersecurity Administrator (Dr. K. Rao)"}
    )
    assert r.status_code == 200
    log(f" -> Result: Status transitioned to {r.json().get('new_status')} (Human Authorized)")

    # Step 10: Validate in Staging
    log("\n[Step 10] Dry-Run Validation in Staging Environment...")
    r = client.post(f"/api/v1/cybertrap/feedback/rules/{target_rule['id']}/validate-staging")
    assert r.status_code == 200
    val_report = r.json().get("validation_results", {})
    log(f" -> Result: Status transitioned to {r.json().get('new_status')} | Validation Decision: {val_report.get('validation_decision')}")

    # Deploy Rule
    r = client.post(f"/api/v1/cybertrap/feedback/rules/{target_rule['id']}/deploy")
    assert r.status_code == 200
    log(f" -> Rule Deployed to Production Enforcement (Status: {r.json().get('new_status')}, Version: {r.json().get('version')})")

    # Step 11: Run Attacker Simulator Again & Show Validated Defensive Response
    log("\n[Step 11] Running Attacker Simulation Again — Verifying Active Defensive Response...")
    r = client.post("/api/v1/cybertrap/feedback/check", json={"source_ip": target_rule["target_value"]})
    assert r.status_code == 200
    check_res = r.json()
    assert check_res["allowed"] is False, "Expected IP to be blocked"
    log(f" -> Result: BLOCKED! Enforcement Action: {check_res['enforcement']['action']} | Reason: {check_res['enforcement']['reason']}")

    # Step 12: Generate Incident Report Hash
    log("\n[Step 12] Generating Cryptographic SHA-256 Digest of Incident Report...")
    r = client.post(f"/api/v1/cybertrap/audit/incidents/{target_inc['id']}/anchor")
    assert r.status_code == 200
    receipt = r.json()
    log(f" -> Result: ANCHORED | Canonical SHA-256 Digest: {receipt.get('canonical_report_hash')}")
    log(f"    Ledger Checkpoint Block ID: {receipt.get('ledger_checkpoint_id')}")

    # Step 13: Verify Blockchain Audit Record
    log("\n[Step 13] Verifying Blockchain Ledger Record Integrity...")
    r = client.get(f"/api/v1/cybertrap/audit/incidents/{target_inc['id']}/verify")
    assert r.status_code == 200
    verify = r.json()
    assert verify.get("is_intact") is True, f"Integrity check failed: {verify}"
    log(f" -> Result: {verify.get('status')} | Cryptographic Proof: Intact ({verify.get('verification_note')})")

    log("\n" + "=" * 70)
    log("✅ PRAMAN CYBERTRAP 13-STEP DEMONSTRATION PASSED WITH 100% SUCCESS!")
    log("=" * 70)

if __name__ == "__main__":
    run_judge_demo()
