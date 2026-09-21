---
type: Repository Guide
title: Quantum AI Trading Bot guide
description: Entry point for the paper-trading bot source tree, its decision and execution boundaries, data adapters, quantum modules, and operational scripts.
tags: [trading, paper-trading, ibkr, quantum]
openwiki:
  roles: [repository, architecture]
  source_paths: [pyproject.toml, README.md, bin/vpa_executor.py, engine/model_orchestrator.py]
  validation_commands: [python -m pytest tests/test_futures_adapter.py -q]
---

# Quantum AI Trading Bot

This repository is a Python trading-system archive whose current source contains two related execution paths: a model-zoo pipeline that creates a verifiable prediction artifact (VPA), and operational scripts that send VPA intents through paper-only IBKR guardrails. It also contains a standalone unified quantum bot and quantum-inspired analysis/ML modules. The package metadata names the project `quantum-ai-trading-bot`; it requires Python 3.8+ and declares `ib_insync`, market-data, numerical, and YAML dependencies in `pyproject.toml`.

Start with the system that owns the change rather than assuming every historical script is a current entrypoint. The canonical safety boundary is [execution safety gates](execution/safety-gates.md); the canonical decision contract is the [decision pipeline](architecture/decision-pipeline.md).

## Map of the wiki

- [Decision pipeline](architecture/decision-pipeline.md) — model interfaces, registry wiring, fallback-to-HOLD behavior, VPA artifacts, and append-only learning records.
- [Execution safety gates](execution/safety-gates.md) — VPA parsing, paper-only constraints, authority/whitelist/risk checks, futures contracts, receipts, and idempotency.
- [Market data](data/market-data.md) — asynchronous Yahoo Finance/CoinGecko normalization, routing, cache behavior, and scope boundary.
- [Quantum stack](models/quantum-stack.md) — quantum-inspired analysis, quantum ML, the enhanced LSTM, and the separate unified-bot integration.
- [Paper runtime](operations/paper-runtime.md) — shell runner preflight, broker gateway dependency, and systemd service files.

## Task routing

| Change area or user intent | Relevant wiki page | Exact source entry points | Important symbols or types | Focused tests | Minimal validation command |
| --- | --- | --- | --- | --- | --- |
| Change forecast, signal, allocation, or execution-policy behavior | [Decision pipeline](architecture/decision-pipeline.md) | `engine/model_orchestrator.py`, `models/interfaces.py`, `models/registry.py` | `ModelOrchestrator.run_decision_cycle`, `ForecastResult`, `SignalResult`, `AllocationResult`, `ExecutionPolicy` | No dedicated orchestrator test was found; use a narrow new test near `tests/` for the changed fallback/contract | `python -m pytest tests/test_decision_plan_futures_schema.py -q` when the plan schema is affected |
| Add or change a registry model | [Decision pipeline](architecture/decision-pipeline.md) | `models/registry.py`, `models/baseline_*.py`, `config/model_zoo.yaml` | `register_custom_model`, `ModelRegistry.create_*_model` | No registry-specific test was found | `python -c "from models.registry import get_registry; print(get_registry().get_model_info())"` |
| Change VPA parsing, order construction, or paper-order gating | [Execution safety gates](execution/safety-gates.md) | `bin/vpa_executor.py`, `engine/execution_authority.py`, `engine/risk_manager.py`, `engine/whitelist.py` | `ExecutionIntent`, `VPAExecutor.enforce_autonomous_safety_gates`, `ExecutionAuthority.check`, `PortfolioRiskManager.check_order` | `tests/test_decision_plan_futures_schema.py`, `tests/test_safety.py` | `python -m pytest tests/test_decision_plan_futures_schema.py -q` |
| Add a futures instrument or roll an expiry | [Execution safety gates](execution/safety-gates.md) | `config/instruments.yaml`, `instruments/spec.py`, `instruments/ibkr_futures_adapter.py` | `FutureSpec`, `IBKRFutureAdapter.load_spec_from_config`, `create_spec_from_dict` | `tests/test_futures_adapter.py` | `python -m pytest tests/test_futures_adapter.py -q` |
| Change portfolio limits, authority windows, or whitelist phase | [Execution safety gates](execution/safety-gates.md) | `config/risk_limits.yaml`, `config/execution_authority.yaml`, `config/whitelists/*.yaml` | `ExecutionAuthority`, `WhitelistManager`, `PortfolioRiskManager` | `tests/test_safety.py` exercises general safety defaults but not these classes directly | `python engine/execution_authority.py --override-time 2026-01-26T10:00:00+00:00` |
| Change Yahoo Finance/CoinGecko data routing or normalized fields | [Market data](data/market-data.md) | `data/unified_data_manager.py`, `data/yahoo_finance_provider.py`, `data/coingecko_provider.py` | `UnifiedDataManager`, `UnifiedMarketData`, `get_market_data` | Provider scripts under `data/test_*.py` are integration-oriented | `python -m py_compile data/unified_data_manager.py` |
| Change quantum signal or ML algorithms | [Quantum stack](models/quantum-stack.md) | `quantum_signal_generation/`, `quantum_machine_learning/`, `ml/enhanced_quantum_lstm.py` | factory functions such as `create_qft_analyzer`, `create_ensemble_predictor`, `create_enhanced_quantum_lstm` | `tests/test_quantum_algorithms.py`, `ml/test_enhanced_quantum_lstm.py` | `python tests/test_quantum_algorithms.py` |
| Change service startup, reconnect behavior, or paper-run sequencing | [Paper runtime](operations/paper-runtime.md) | `bin/run_paper_production.sh`, `bin/quantum_bot_with_autoreconnect.py`, `ops/systemd/*.service` | `run_one_cycle`, `execute_vpa` | `tests/test_gateway_api.sh` requires a configured gateway | `bash -n bin/run_paper_production.sh` |

The commands above are focused checks, not proof that a broker-connected system is safe to run. Integration with IBKR, `ib_insync`, configured environment files, and a running gateway is conditional and should be used only when the change crosses that boundary.

## Repository reality and boundaries

- `bin/`, `engine/`, `models/`, `data/`, `learning/`, `instruments/`, and the quantum directories are importable source trees placed at the repository root. Several modules hard-code `/home/davidsanker/platform` or add absolute paths to `sys.path`; do not treat this checkout as a relocatable packaged application without verifying that path behavior.
- `config/quantum_runtime.env` is a runtime environment file and is intentionally not documented here. Do not put credentials in the repository or generated wiki. The source safety checks require paper mode and reject `ALLOW_LIVE=true`.
- `bin/archive/` and many root Markdown reports are historical/support material, not the canonical behavior described here. Consult them for operational history only after checking the source file that currently owns a behavior.

## Backlog

- `pyproject.toml` declares `qbot-cycle`, `qbot-paper-prod`, and `qbot-status` under `quantum_trading_bot.cli`, but the latest production sync records `src/quantum_trading_bot/cli.py` as deleted. The console-script surface cannot be documented as working until the package layout and entrypoint are reconciled.
