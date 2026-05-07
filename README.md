# LLM Serving Benchmark

LLM Serving Benchmark는 vLLM, SGLang, llama.cpp 같은 LLM 서빙 프레임워크를 사용자의 하드웨어와 실행 환경에서 비교하기 위한 벤치마크 도구입니다.

이 프로젝트의 목적은 특정 프레임워크가 좋아 보이는 단일 숫자를 만드는 것이 아닙니다. 같은 모델, 같은 요청 형식, 같은 측정 기준을 사용하되, 하드웨어와 실행 환경은 결과 해석에 필요한 메타데이터로 남기는 것이 목적입니다.

- 첫 토큰이 얼마나 빨리 나오는가
- 동시 요청이 늘어날 때 p95/p99 latency가 어떻게 변하는가
- throughput이 높아도 SLO를 만족하는 goodput은 충분한가
- timeout, OOM, server crash, invalid response가 얼마나 발생하는가
- prompt 길이와 생성 길이가 달라져도 결과가 일관적인가
- quantization, tokenizer, chat template, stop sequence 차이로 품질이 흔들리지 않는가

## 왜 만들었나

LLM serving 성능은 하나의 `tokens/sec` 값으로 설명되지 않습니다.

예를 들어 어떤 프레임워크는 높은 동시성에서 output token throughput은 좋지만 첫 토큰이 늦을 수 있습니다. 어떤 설정은 짧은 prompt에서는 빠르지만 긴 context에서는 KV cache 압박이나 queueing 때문에 tail latency가 급격히 나빠질 수 있습니다. quantization이나 framework-specific optimization은 성능을 높이는 대신 품질 회귀를 만들 수도 있습니다.

이 프로젝트는 이런 차이를 숨기지 않고 기록합니다. 결과에는 raw per-request artifact, summary metric, 환경 metadata, 재현 명령을 남겨 나중에 같은 조건으로 다시 확인할 수 있게 합니다.

## 현재 상태

현재 리포지토리는 초기 scaffold 단계입니다.

구현 계약은 `SPEC.md`에 정의되어 있으며, 계획 과정의 의도와 설계 판단은 `PLANNING.md`에 정리되어 있습니다. README는 사용자 관점에서 목적과 실행 방법만 설명합니다.

현재 제공되는 코드는 OpenAI-compatible `/chat/completions` 서버에 요청을 보내는 초기 벤치마크 harness입니다. `SPEC.md`의 모든 요구사항이 아직 구현된 상태는 아닙니다.

## 설치

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

설치 후 `llm-bench` 명령을 사용할 수 있습니다.

```bash
llm-bench --help
```

## 빠른 실행

OpenAI-compatible server가 이미 떠 있다고 가정합니다.

```bash
llm-bench \
  --base-url http://127.0.0.1:8000/v1 \
  --model local_model \
  --prompts prompts/smoke.jsonl \
  --concurrency 1,10,100 \
  --requests 100 \
  --warmup 10 \
  --max-tokens 128 \
  --temperature 0 \
  --out results/smoke.jsonl \
  --summary results/smoke-summary.csv
```

현재 scaffold는 raw JSONL과 summary CSV를 생성합니다. 향후 현재 구현 범위가 완료되면 summary JSON, 더 명확한 schema, goodput, failure category, resource metric이 확장됩니다.

## 서버 실행 예시

서버 실행 스크립트는 템플릿입니다. 실제 환경에 맞게 모델 경로, 포트, dtype, quantization, tensor parallel 설정을 조정해야 합니다.

```bash
bash servers/sglang.sh Qwen/Qwen2.5-7B-Instruct 8000
bash servers/vllm.sh Qwen/Qwen2.5-7B-Instruct 8001
bash servers/llama_cpp.sh /path/to/model.gguf 8002
```

벤치마크 결과를 비교할 때는 서버 실행 명령, framework version, 하드웨어, CUDA/driver, model revision, tokenizer revision, dtype, quantization 설정을 함께 기록해야 합니다.

## 입력 프롬프트

프롬프트 파일은 JSONL 형식입니다. 각 줄은 하나의 요청 입력입니다.

`prompt` 필드를 사용할 수 있습니다.

```json
{"id":"hello","prompt":"Explain what an LLM serving benchmark measures."}
```

또는 OpenAI chat 형식의 `messages` 필드를 사용할 수 있습니다.

```json
{"id":"chat-1","messages":[{"role":"user","content":"Write a short summary of GPU batching."}]}
```

현재 smoke 예시는 `prompts/smoke.jsonl`에 있습니다.

## 주요 지표

이 프로젝트가 최종적으로 중요하게 보는 지표는 다음과 같습니다.

- request throughput
- output token throughput
- total token throughput
- TTFT, Time To First Token
- TPOT, Time Per Output Token
- end-to-end latency p50/p90/p95/p99
- goodput under SLO
- failure rate and timeout rate
- GPU/CPU/RAM resource usage
- cost-like efficiency metrics
- quality/correctness regression score

현재 구현 범위는 성능 harness에 집중합니다. 품질 벤치마크는 성능 harness가 정리된 뒤 추가됩니다.

## 결과 파일

벤치마크 실행 결과는 기본적으로 `results/` 아래에 저장합니다.

- raw JSONL: 요청별 latency, token count, 성공/실패 정보
- summary CSV/JSON: concurrency 또는 workload별 집계 지표
- report: 환경, 설정, 주요 결과, 재현 명령을 담은 Markdown 문서

`results/`에 생성되는 실제 벤치마크 결과 파일은 일반적으로 git에 커밋하지 않습니다.

## 비교 대상

초기 대상은 다음 OpenAI-compatible serving framework입니다.

- vLLM
- SGLang
- llama.cpp / llama-server

이후 필요에 따라 TensorRT-LLM, Hugging Face TGI, LMDeploy, Ollama 등을 추가할 수 있습니다.

## 주의사항

서버와 클라이언트를 같은 머신에서 실행하면 client overhead와 resource measurement가 결과에 영향을 줄 수 있습니다.

프레임워크별 기본값은 서로 다를 수 있으므로, decoding parameter, max context length, batching 관련 설정, quantization, dtype을 반드시 함께 기록해야 합니다.

공개 데이터셋을 사용하는 품질 벤치마크는 원본 라이선스를 확인해야 합니다. 데이터셋 원문을 저장소에 직접 포함하기보다 runtime downloader, subset manifest, hash를 사용하는 방식을 선호합니다.
