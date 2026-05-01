# Project 2 Ablation Summary

- 总记录: 150（149 成功 / 1 失败）

## Weighted Quality by Config

| Config | N | Faithfulness | Coverage | Citation Acc. | Structure | Weighted Avg | Avg Time |
|---|---|---|---|---|---|---|---|
| baseline | 30 | 0.667±0.25 | 0.677±0.10 | 0.993±0.04 | 0.710±0.14 | **0.759**±0.10 | 183.6s |
| multisource | 30 | 0.543±0.24 | 0.653±0.18 | 0.933±0.25 | 0.690±0.21 | **0.698**±0.20 | 71.7s |
| debate_1round | 29 | 0.497±0.12 | 0.700±0.00 | 0.807±0.29 | 0.638±0.15 | **0.653**±0.09 | 429.0s |
| debate_2round | 30 | 0.467±0.13 | 0.680±0.08 | 0.783±0.27 | 0.720±0.16 | **0.650**±0.10 | 656.1s |
| full | 30 | 0.467±0.13 | 0.680±0.08 | 0.637±0.37 | 0.697±0.23 | **0.609**±0.15 | 828.1s |

## Key Deltas: full vs baseline

- **Faithfulness**: 0.667 → 0.467 (-0.200, -30.0%)
- **Coverage**: 0.677 → 0.680 (+0.003, +0.5%)
- **Citation Acc.**: 0.993 → 0.637 (-0.357, -35.9%)
- **Structure**: 0.710 → 0.697 (-0.013, -1.9%)

## Key Deltas: debate_2round vs baseline (debate-only contribution)

- **Faithfulness**: 0.667 → 0.467 (-0.200, -30.0%)
- **Coverage**: 0.677 → 0.680 (+0.003, +0.5%)
- **Citation Acc.**: 0.993 → 0.783 (-0.210, -21.1%)
- **Structure**: 0.710 → 0.720 (+0.010, +1.4%)
