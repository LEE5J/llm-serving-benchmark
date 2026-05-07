# LLM Serving Benchmark

LLM 서빙 프레임워크(vLLM, SGLang, llama.cpp 등)를 동일한 OpenAI-compatible API 조건에서 비교하기 위한 벤치마크 리포지토리입니다.

## 목표

- 프레임워크별 설치/기동/호환성 비교
- 동일 모델, 동일 프롬프트, 동일 동시성 조건에서 성능 측정
- TTFT(Time To First Token), latency, throughput, 실패율, GPU 사용량 기록
- 재현 가능한 raw JSONL + summary CSV + Markdown report 생성

## 1차 비교 대상

- SGLang
- vLLM
- llama.cpp / llama-server

DGX 환경 메모:

- Ubuntu 24.04 aarch64
- NVIDIA GB10 / SM121
- CUDA 13.0
- PyTorch/SGLang/vLLM prebuilt wheel의 SM121 커널 호환성 확인 필요

## 빠른 시작

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

서버가 OpenAI-compatible endpoint로 떠 있다고 가정하고 벤치마크를 실행합니다.

```bash
llm-bench   --base-url http://127.0.0.1:8000/v1   --model local_model   --prompts prompts/smoke.jsonl   --concurrency 1,2,4,8   --max-tokens 128   --out results/smoke.jsonl   --summary results/smoke-summary.csv
```

## 결과 파일

- `results/*.jsonl`: 요청 단위 raw log
- `results/*-summary.csv`: 동시성별 summary
- `reports/*.md`: 사람이 읽는 비교 리포트

## 서버 실행 스크립트

`servers/` 아래 스크립트는 템플릿입니다. 모델명, 포트, CUDA 플래그는 환경에 맞게 수정합니다.

```bash
bash servers/sglang.sh Qwen/Qwen2.5-7B-Instruct 8000
bash servers/vllm.sh Qwen/Qwen2.5-7B-Instruct 8001
bash servers/llama_cpp.sh /path/to/model.gguf 8002
```

## 벤치마크 원칙

1. 같은 모델 또는 가능한 한 동등한 quant/precision 사용
2. 같은 prompt set 사용
3. warmup 후 measurement 실행
4. streaming 모드에서 TTFT 측정
5. 모든 raw result 저장
6. 실패/timeout도 결과에 포함
