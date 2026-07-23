# Paired significance vs baseline

Source: `benchmarks/results/ablation_20260430_201202.json` — 90 ok records, configs: {'baseline': 30, 'debate_1round': 30, 'debate_2round': 30}

Positive delta = better than baseline. CI excluding 0 = significant.

## debate_1round vs baseline

| dimension | n | mean delta | CI95 | verdict |
|---|---|---|---|---|
| faithfulness | 30 | -0.120 | [-0.230, -0.020] | **significant** |
| coverage | 30 | +0.047 | [-0.017, +0.117] | n.s. |
| citation_accuracy | 30 | -0.194 | [-0.277, -0.118] | **significant** |
| structure_coherence | 30 | -0.057 | [-0.137, +0.030] | n.s. |
| weighted_average | 30 | -0.084 | [-0.136, -0.033] | **significant** |

## debate_2round vs baseline

| dimension | n | mean delta | CI95 | verdict |
|---|---|---|---|---|
| faithfulness | 30 | -0.303 | [-0.423, -0.187] | **significant** |
| coverage | 30 | -0.027 | [-0.097, +0.047] | n.s. |
| citation_accuracy | 30 | -0.303 | [-0.399, -0.210] | **significant** |
| structure_coherence | 30 | -0.050 | [-0.130, +0.033] | n.s. |
| weighted_average | 30 | -0.184 | [-0.252, -0.116] | **significant** |

