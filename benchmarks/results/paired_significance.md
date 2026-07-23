# Paired significance vs baseline

Source: `benchmarks/results/zhipu_archive/ablation_20260430_062537.json` — 149 ok records, configs: {'baseline': 30, 'multisource': 30, 'debate_1round': 29, 'debate_2round': 30, 'full': 30}

Positive delta = better than baseline. CI excluding 0 = significant.

## debate_1round vs baseline

| dimension | n | mean delta | CI95 | verdict |
|---|---|---|---|---|
| faithfulness | 29 | -0.176 | [-0.255, -0.090] | **significant** |
| coverage | 29 | +0.024 | [-0.010, +0.062] | n.s. |
| citation_accuracy | 29 | -0.186 | [-0.303, -0.090] | **significant** |
| structure_coherence | 29 | -0.072 | [-0.145, -0.007] | **significant** |
| weighted_average | 29 | -0.108 | [-0.147, -0.064] | **significant** |

## debate_2round vs baseline

| dimension | n | mean delta | CI95 | verdict |
|---|---|---|---|---|
| faithfulness | 30 | -0.200 | [-0.287, -0.103] | **significant** |
| coverage | 30 | +0.003 | [-0.033, +0.040] | n.s. |
| citation_accuracy | 30 | -0.210 | [-0.312, -0.122] | **significant** |
| structure_coherence | 30 | +0.010 | [-0.057, +0.073] | n.s. |
| weighted_average | 30 | -0.110 | [-0.156, -0.063] | **significant** |

## full vs baseline

| dimension | n | mean delta | CI95 | verdict |
|---|---|---|---|---|
| faithfulness | 30 | -0.200 | [-0.287, -0.103] | **significant** |
| coverage | 30 | +0.003 | [-0.040, +0.050] | n.s. |
| citation_accuracy | 30 | -0.357 | [-0.493, -0.228] | **significant** |
| structure_coherence | 30 | -0.013 | [-0.103, +0.073] | n.s. |
| weighted_average | 30 | -0.151 | [-0.212, -0.092] | **significant** |

## multisource vs baseline

| dimension | n | mean delta | CI95 | verdict |
|---|---|---|---|---|
| faithfulness | 30 | -0.123 | [-0.217, -0.023] | **significant** |
| coverage | 30 | -0.023 | [-0.103, +0.043] | n.s. |
| citation_accuracy | 30 | -0.060 | [-0.167, +0.013] | n.s. |
| structure_coherence | 30 | -0.020 | [-0.107, +0.057] | n.s. |
| weighted_average | 30 | -0.062 | [-0.138, -0.000] | **significant** |

