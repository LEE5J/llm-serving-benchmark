# LLM Serving Benchmark

LLM Serving Benchmark는 vLLM, SGLang, llama.cpp 같은 LLM 서빙 프레임워크를 객관적으로 비교하기 위한 벤치마크 프로젝트입니다.

이 프로젝트의 목적은 특정 프레임워크에 유리한 단일 조건을 만드는 것이 아닙니다. 동일한 모델과 환경을 가능한 한 일원화하되, 단일 조건이 만드는 편향을 줄이기 위해 다양한 부하 유형, 입력/출력 길이, 성능 지표, 품질 벤치마크를 함께 측정하는 것을 목표로 합니다.

## 핵심 방향

서빙 프레임워크 평가는 throughput 하나로 끝나지 않습니다.

높은 token/sec를 기록하더라도 다음 문제가 있으면 실제 서비스에서는 좋은 선택이 아닐 수 있습니다.

- 첫 토큰이 너무 늦게 나온다.
- p95/p99 latency가 나쁘다.
- 동시성이 올라가면 timeout이나 OOM이 발생한다.
- 특정 길이의 prompt에서만 성능이 좋다.
- quantization이나 batching 때문에 공개 벤치마크 정확도가 떨어진다.
- chat template, tokenizer, stop sequence 차이로 응답 품질이 달라진다.

따라서 이 프로젝트는 성능과 품질을 함께 봅니다.

## SPEC 우선 원칙

코드 작성 전에 `SPEC.md`를 먼저 작성하고, 이 문서를 구현의 기준으로 삼습니다.

중요 원칙:

- `SPEC.md`가 source of truth입니다.
- Hermes Agent는 기획, 문서화, 오케스트레이션, 리뷰를 담당합니다.
- 실제 주요 코딩은 Codex CLI, Claude Code 같은 코딩 전문 에이전트에게 위임합니다.
- 어떤 코딩 에이전트가 구현하더라도 비슷한 결과물이 나오도록 SPEC을 최대한 구체적으로 유지합니다.

자세한 구현 기준은 `SPEC.md`를 보세요.

## 1차 벤치마크 유형

초기 벤치마크는 세 가지 부하 유형을 필수로 지원하는 것을 목표로 합니다.

### 1. 단일 배치 / 단일 사용자

- concurrency: 1
- 목적: 기본 응답성, framework overhead, TTFT 확인
- 주요 지표:
  - TTFT
  - TPOT
  - end-to-end latency
  - output tokens/sec
  - failure rate

### 2. 동시 사용량 10

- concurrency: 10
- 목적: 소규모 서비스 또는 내부 API 수준의 부하 확인
- 주요 지표:
  - throughput
  - latency p50/p90/p95/p99
  - TTFT p50/p90/p95/p99
  - goodput
  - failure rate
  - GPU/CPU 사용량

### 3. 동시 사용량 100

- concurrency: 100
- 목적: 고부하 상황에서 scheduler, batching, KV cache, queueing, tail latency 확인
- 주요 지표:
  - raw throughput
  - goodput
  - p99 latency
  - p99 TTFT
  - timeout/OOM/server crash 여부
  - GPU memory peak
  - cost-like metrics

## 성능 지표

최소한 다음 지표를 수집합니다.

- request throughput, req/s
- output token throughput, tokens/s
- total token throughput, input + output tokens/s
- TTFT, Time To First Token
- TPOT, Time Per Output Token
- end-to-end latency
- p50 / p90 / p95 / p99 latency
- goodput under SLO
- failure rate
- timeout rate
- GPU utilization
- GPU memory usage
- CPU utilization
- tokens/sec/GPU
- good tokens/sec/GPU
- estimated cost per 1M output tokens, optional

## 입력/출력 길이 프로파일

서빙 성능은 prompt 길이와 생성 길이에 크게 의존합니다.

초기 SPEC은 다음 프로파일을 정의합니다.

- SS: short input / short output
- SL: short input / long output
- LS: long input / short output
- LL: long input / long output
- MIXED: 실제 서비스 traffic에 가까운 혼합 profile

## 품질 벤치마크

성능만 측정하지 않습니다. 공개 데이터셋 기반으로 출력 품질 또는 correctness regression도 측정합니다.

초기 P0 후보:

- MMLU subset
  - 일반 지식 및 객관식 추론
  - exact match scoring

- GSM8K subset
  - 수학 word problem reasoning
  - final numeric answer exact match

- IFEval subset
  - instruction following
  - rule-based scoring

- Synthetic long-context retrieval
  - 긴 context에서 needle/key retrieval 성공 여부
  - exact match scoring

- KMMLU subset, 한국어 평가가 필요할 경우
  - 한국어 multiple-choice benchmark

다음 단계 후보:

- HumanEval pass@1
- MBPP
- TruthfulQA multiple-choice
- KLUE / KoBEST / KorQuAD
- RULER / LongBench / L-Eval
- MT-Bench / AlpacaEval류 judge-based benchmark

Judge 기반 평가는 비용과 비결정성 때문에 초기 hard gate가 아니라 nightly 또는 release report 용도로 분리합니다.

## 비교 대상 프레임워크

초기 대상:

- SGLang
- vLLM
- llama.cpp / llama-server

추가 후보:

- TensorRT-LLM
- Hugging Face TGI
- LMDeploy
- Ollama
- 기타 OpenAI-compatible server

## 현재 리포지토리 구조

```text
benchmark/
  bench_openai.py        # 초기 OpenAI-compatible benchmark client scaffold
configs/
  benchmark-matrix.yaml  # 초기 benchmark matrix draft
prompts/
  smoke.jsonl            # smoke prompt set
reports/
  report-template.md     # report template
servers/
  sglang.sh              # SGLang launch template
  vllm.sh                # vLLM launch template
  llama_cpp.sh           # llama.cpp launch template
SPEC.md                  # implementation-grade specification
README.md
```

향후 SPEC 기준으로 다음 구조로 확장할 예정입니다.

```text
benchmark/
  cli.py
  config.py
  openai_client.py
  workloads.py
  metrics.py
  resources.py
  reporting.py
  datasets/
  scoring/
  schemas.py
tests/
```


## Codex CLI 연동

이 리포지토리는 주요 구현을 코딩 전문 에이전트에게 위임하는 방식으로 진행합니다. 현재 Codex CLI 연동 파일은 다음과 같습니다.

- `AGENTS.md`: Codex/Claude Code 같은 코딩 에이전트가 따라야 할 repository instructions
- `docs/plans/phase-1-performance-harness.md`: Phase 1 구현 계획
- `scripts/codex_phase1.sh`: Codex CLI로 Phase 1 구현을 시작하는 스크립트

Codex CLI 실행 전 인증이 필요합니다.

```bash
# API key를 사용할 경우
export OPENAI_API_KEY=...
printf '%s' "$OPENAI_API_KEY" | codex login --with-api-key

# 또는 device auth
codex login --device-auth
```

Phase 1 구현 시작:

```bash
./scripts/codex_phase1.sh
```

주의: 이 스크립트는 실제 코드를 수정하는 코딩 에이전트를 실행합니다. 실행 전 `SPEC.md`와 `docs/plans/phase-1-performance-harness.md`를 검토하세요.

## 빠른 시작, 현재 scaffold 기준

현재 코드는 초기 scaffold입니다. SPEC의 모든 요구사항이 아직 구현된 상태는 아닙니다.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

OpenAI-compatible server가 떠 있다고 가정하고 smoke benchmark를 실행합니다.

```bash
llm-bench \
  --base-url http://127.0.0.1:8000/v1 \
  --model local_model \
  --prompts prompts/smoke.jsonl \
  --concurrency 1,10,100 \
  --max-tokens 128 \
  --out results/smoke.jsonl \
  --summary results/smoke-summary.csv
```

## 서버 실행 템플릿

```bash
bash servers/sglang.sh Qwen/Qwen2.5-7B-Instruct 8000
bash servers/vllm.sh Qwen/Qwen2.5-7B-Instruct 8001
bash servers/llama_cpp.sh /path/to/model.gguf 8002
```

실제 비교에서는 각 실행 명령, framework version, CUDA/driver, model revision, quantization, tokenizer revision을 반드시 결과 metadata에 기록해야 합니다.

## DGX / GB10 환경 메모

초기 대상 서버 환경:

- Ubuntu 24.04 aarch64
- NVIDIA GB10 / SM121
- CUDA 13.0
- 121GiB RAM

주의:

- PyTorch, SGLang, vLLM prebuilt wheel이 SM121 compatible kernel을 포함하지 않을 수 있습니다.
- 설치 가능 여부와 kernel compatibility도 벤치마크 과정에서 중요한 관찰 항목입니다.
- 단순히 “설치 실패”로 제외하지 말고 실패 조건과 로그를 기록해야 합니다.

## 결과물 목표

각 실험은 다음 산출물을 만들어야 합니다.

- raw per-request JSONL
- summary CSV/JSON
- resource usage log
- benchmark metadata
- quality benchmark score
- Markdown report
- reproduction command

## 초기 개발 계획

1. SPEC 확정
2. README 정리
3. 코딩 전문 에이전트에게 Phase 1 구현 위임
4. 성능 harness 구현
5. concurrency 1/10/100 smoke run
6. P0 품질 벤치마크 일부 구현
7. DGX에서 SGLang/vLLM/llama.cpp 순서로 검증
8. 결과 리포트 생성

## 라이선스와 데이터셋 주의사항

공개 데이터셋은 각 원본 라이선스를 확인해야 합니다.

가능하면 초기에는:

- 데이터셋을 repo에 직접 포함하지 않기
- 다운로드 스크립트 또는 dataset loader 사용
- subset manifest와 hash만 저장
- license가 명확한 synthetic dataset은 repo에 포함 가능

## 현재 상태

이 리포지토리는 초기 설계 및 scaffold 단계입니다.

가장 중요한 문서는 `SPEC.md`입니다.
구현은 이 문서를 기준으로 코딩 전문 에이전트에게 위임하는 방식으로 진행합니다.
