# 事件合约检验：Kronos 能否预测 BTC/ETH 下一根 10min / 30min / 1h K 线涨跌

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Musenxi/Kronos/blob/event-contract/event_contract/kronos_event_colab.ipynb)

```bash
pip install -r requirements.txt scipy tabulate pyarrow
python event_contract/run_event.py download            # Binance 公开归档 1m 永续 K 线，2025-07 ~ 2026-10
python event_contract/run_event.py predict --tf 1h      # 滚动预测（GPU 自动启用），按月断点续跑
python event_contract/run_event.py evaluate             # → event_contract/output/report.md / report.csv
```

## 口径
| 项 | 设定 |
|---|---|
| 下单 | bar t 收盘后立刻下单，入场价 = close_t |
| 结算 | close_{t+1}（永续 1m 合成；交易所按指数价结算，有小偏差） |
| 赔率 | 10min 80%，30min / 1h 85% → 盈亏平衡胜率 55.6% / 54.1%；平局按输 |
| Kronos | Kronos-small，回看 512 根，窗口自身 z-score；采样 32 次，P(上涨) = 预测 close > close_t 的比例 |
| 样本外 | 只评估 2025-09 之后（模型 2025-08 发布）；发现期 2025-09~2026-02 选阈值 theta，留出期 2026-03~2026-10 只看一次 |
| 规则 | P(上涨) ≥ theta 买涨，≤ 1-theta 买跌，其余不下单；theta 在发现期按每笔期望选，要求 ≥ 200 注 |

原版 `KronosPredictor.predict()` 只返回采样均值（`model/kronos.py` 中 `np.mean(preds, axis=1)`），拿不到涨跌概率，
所以这里用同一套 `encode → decode_s1 → decode_s2 → decode` 调用自己做单步采样，上下文只算一次。

## 基准（每根都下注，2025-09 ~ 2026-10）
| 策略 | 胜率范围（2 币 × 3 周期 × 发现/留出） | 每笔期望 |
|---|---|---|
| 总是买涨 | 49.6% ~ 50.7% | -6% ~ -11% |
| 动量（上一根涨就买涨） | 47.0% ~ 49.2% | -9% ~ -14% |
| 反转（上一根跌就买涨） | 51.3% ~ 52.9% | -2% ~ -8% |

反转稳定 > 50%（短期均值回归），但仍低于盈亏平衡线。Kronos 需要在其下单的时点上明显超过反转才有意义。

## Kronos 结果（2026-11，Colab T4，Kronos-small，全量不抽样）
留出期 2026-03 ~ 2026-10，theta 仅用发现期选定：

| | Kronos 胜率 | 下注数 | 盈亏平衡 | 每笔期望 | 反转基准 |
|---|---|---|---|---|---|
| BTC 10min | 52.7% | 11,011 | 55.6% | -5.1% | 51.3% |
| ETH 10min | 52.3% | 10,619 | 55.6% | -5.9% | 51.7% |
| BTC 30min | 51.0% | 3,804 | 54.1% | -5.6% | 51.8% |
| ETH 30min | 52.8% | 3,706 | 54.1% | -2.3% | 51.7% |
| BTC 1h | 52.1% | 1,876 | 54.1% | -3.6% | 52.4% |
| ETH 1h | 49.8% | 2,179 | 54.1% | -7.9% | 52.9% |

- 全部 6 组负期望。留出期 Rank IC 0.005 ~ 0.036，有弱信息，但 P(上涨) 与本 bar 收益相关 -0.26 ~ -0.32，主要就是短期反转。
- 严重过度自信：P(上涨) 最高五分位均值约 0.84，实际上涨率约 51% ~ 52.5%。
- 两次独立运行（seed=0）的 1h 预测逐项相同。
- **结论：预训练 Kronos-small 不适合做事件合约。**

## 注意
- `finetune_csv` 训练时用包含未来段的整窗统计量归一化（训练/推理不一致），模板 `test_ratio: 0` 无测试集；做微调前先修。
- 本目录不修改 Kronos 原有代码。
