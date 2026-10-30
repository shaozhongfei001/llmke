.PHONY: help generate check contract-all contract-v2-check framework-test framework-verify tooling-test oracle-readonly-guard-test p0-check p0-gate p0-status security-check baseline-check rules-check trace-check mutation-probe reuse-check discovery-verify business-verify run-dev memory-check evidence-check new-loop baton-transfer module-test python-info
LOOP ?=
EXECUTOR ?=
PROFILE ?= L1
# W-05 解释器唯一来源：优先 LLMKE_PYTHON，其次仓库内 .venv，最后回退 PATH。
# 为什么：Makefile 内所有 python3 都从 PATH 取；conda/系统 shell 下会取到缺依赖的解释器，
# 表现为"门禁莫名红"（R-02 已发生 3 次，其中一次是 run_batch 内部 spawn make）。
LLMKE_PYTHON ?= $(shell [ -x .venv/bin/python3 ] && echo .venv/bin/python3 || echo python3)
PY := $(LLMKE_PYTHON)
help:
	@$(PY) -c "print('framework-verify / p0-check / p0-gate / run-dev LOOP=... EXECUTOR=... / business-verify PROFILE=L1')"
generate:
	@$(PY) scripts/contract_generate.py
check:
	@$(PY) scripts/contract_check.py
contract-all:
	@$(MAKE) --no-print-directory generate
	@$(MAKE) --no-print-directory check
framework-test:
	@$(PY) -m pytest tests/ modules/ -q
module-test:
	@$(PY) -m pytest modules/ -q
# V2 文档管线合同自查（仓内解析、离线、不替代 contract-all）
# 为什么单列：这两个脚本覆盖 V2 新增的 schema/API/来源/规则/验收合同与合成样例，
# 而通用 contract_toolchain 只做 registry 驱动的语义+联动，不校验样例一致性。
ingest-slice-test:
	@$(PY) -m pytest tests/test_parse_artifact_store.py tests/test_doc2md_adapter.py tests/test_rag_projection.py -q
contract-v2-check:
	@$(PY) scripts/document_pipeline_v2_offline_check.py
	@$(PY) scripts/document_pipeline_v2_validate.py
	@$(PY) -m pytest tests/test_contract_semantics.py tests/test_document_pipeline_v2_contracts.py -q
framework-verify:
	@$(MAKE) --no-print-directory contract-all
	@$(MAKE) --no-print-directory rules-check
	@$(MAKE) --no-print-directory trace-check
	@$(MAKE) --no-print-directory p0-check
	@$(MAKE) --no-print-directory security-check
	@$(MAKE) --no-print-directory framework-test
	@$(MAKE) --no-print-directory baseline-check
tooling-test:
	@$(PY) -m pytest tests/test_contract_toolchain.py tests/test_installer.py -q
oracle-readonly-guard-test:
	@$(PY) -m pytest tests/test_readonly_guard.py -q
p0-check:
	@$(PY) scripts/p0_closure_check.py --mode integrity
p0-status: p0-check
p0-gate:
	@$(PY) scripts/p0_closure_check.py --mode strict
security-check:
	@$(PY) scripts/security_scan.py --all-files --tracked-sensitive
baseline-check:
	@$(PY) scripts/freeze_baseline.py
rules-check:
	@$(PY) scripts/sync_rules.py
trace-check:
	@$(PY) scripts/trace_check.py
mutation-probe:
	@$(PY) scripts/mutation_probe.py
reuse-check:
	@$(PY) scripts/readiness_check.py --mode inventory
discovery-verify: reuse-check p0-check trace-check
business-verify:
	@$(PY) scripts/p0_closure_check.py --mode strict --loop $(PROFILE)
	@$(PY) scripts/readiness_check.py --mode strict --loop $(PROFILE)
	@$(MAKE) --no-print-directory contract-all
	@$(PY) scripts/business_gate.py --profile $(PROFILE) --stage build
	@$(PY) scripts/business_gate.py --profile $(PROFILE) --stage test
	@$(PY) scripts/evaluation_dispatch.py --profile $(PROFILE)
run-dev:
	@$(PY) scripts/run_batch.py --loop $(LOOP) --executor $(EXECUTOR)
memory-check:
	@$(PY) scripts/loop_guard.py memory-check --loop $(LOOP)
evidence-check:
	@$(PY) scripts/loop_guard.py evidence-check --loop $(LOOP)
new-loop:
	@$(PY) scripts/new_loop.py $(LOOP)
baton-transfer:
	@$(PY) scripts/loop_guard.py baton-transfer --loop $(LOOP) --to $(TO) --executor $(EXECUTOR) --expected-revision $(REVISION)
python-info:
	@$(PY) -c "import sys;print('make sees:',sys.executable)"
