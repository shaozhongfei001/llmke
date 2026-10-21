.PHONY: help generate check contract-all framework-test framework-verify tooling-test oracle-readonly-guard-test p0-check p0-gate p0-status security-check baseline-check rules-check trace-check mutation-probe reuse-check discovery-verify business-verify run-dev memory-check evidence-check new-loop baton-transfer
LOOP ?=
EXECUTOR ?=
PROFILE ?= L1
help:
	@python3 -c "print('framework-verify / p0-check / p0-gate / run-dev LOOP=... EXECUTOR=... / business-verify PROFILE=L1')"
generate:
	@python3 scripts/contract_generate.py
check:
	@python3 scripts/contract_check.py
contract-all:
	@$(MAKE) --no-print-directory generate
	@$(MAKE) --no-print-directory check
framework-test:
	@python3 -m pytest tests/ -q
framework-verify:
	@$(MAKE) --no-print-directory contract-all
	@$(MAKE) --no-print-directory rules-check
	@$(MAKE) --no-print-directory trace-check
	@$(MAKE) --no-print-directory p0-check
	@$(MAKE) --no-print-directory security-check
	@$(MAKE) --no-print-directory framework-test
	@$(MAKE) --no-print-directory baseline-check
tooling-test:
	@python3 -m pytest tests/test_contract_toolchain.py tests/test_installer.py -q
oracle-readonly-guard-test:
	@python3 -m pytest tests/test_readonly_guard.py -q
p0-check:
	@python3 scripts/p0_closure_check.py --mode integrity
p0-status: p0-check
p0-gate:
	@python3 scripts/p0_closure_check.py --mode strict
security-check:
	@python3 scripts/security_scan.py --all-files --tracked-sensitive
baseline-check:
	@python3 scripts/freeze_baseline.py
rules-check:
	@python3 scripts/sync_rules.py
trace-check:
	@python3 scripts/trace_check.py
mutation-probe:
	@python3 scripts/mutation_probe.py
reuse-check:
	@python3 scripts/readiness_check.py --mode inventory
discovery-verify: reuse-check p0-check trace-check
business-verify:
	@python3 scripts/p0_closure_check.py --mode strict --loop $(PROFILE)
	@python3 scripts/readiness_check.py --mode strict --loop $(PROFILE)
	@$(MAKE) --no-print-directory contract-all
	@python3 scripts/business_gate.py --profile $(PROFILE) --stage build
	@python3 scripts/business_gate.py --profile $(PROFILE) --stage test
	@python3 scripts/evaluation_dispatch.py --profile $(PROFILE)
run-dev:
	@python3 scripts/run_batch.py --loop $(LOOP) --executor $(EXECUTOR)
memory-check:
	@python3 scripts/loop_guard.py memory-check --loop $(LOOP)
evidence-check:
	@python3 scripts/loop_guard.py evidence-check --loop $(LOOP)
new-loop:
	@python3 scripts/new_loop.py $(LOOP)
baton-transfer:
	@python3 scripts/loop_guard.py baton-transfer --loop $(LOOP) --to $(TO) --executor $(EXECUTOR) --expected-revision $(REVISION)
