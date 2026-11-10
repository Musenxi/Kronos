# Kronos × 事件合约（BTC/ETH）

赔率 {'10min': 0.8, '30min': 0.85, '1h': 0.85}，平局按输。发现期 2025-09-01~2026-03-01（Kronos 在此选 theta），留出期 2026-03-01~2026-11-01。
ev_per_bet：每笔期望（单位本金）；p_vs_breakeven：胜率高于盈亏平衡胜率的单侧二项检验 p 值。

| symbol   | tf    | signal    |   theta | period    |   bets |   win_rate |   breakeven |   ev_per_bet |   total_units |   p_vs_breakeven |
|:---------|:------|:----------|--------:|:----------|-------:|-----------:|------------:|-------------:|--------------:|-----------------:|
| BTCUSDT  | 10min | always_up |  0.5000 | discovery |  26064 |     0.5007 |      0.5556 |      -0.0987 |    -2572.2000 |           1.0000 |
| BTCUSDT  | 10min | always_up |  0.5000 | holdout   |  35134 |     0.4962 |      0.5556 |      -0.1068 |    -3752.8000 |           1.0000 |
| BTCUSDT  | 10min | momentum  |  0.5000 | discovery |  26064 |     0.4814 |      0.5556 |      -0.1334 |    -3477.6000 |           1.0000 |
| BTCUSDT  | 10min | momentum  |  0.5000 | holdout   |  35134 |     0.4866 |      0.5556 |      -0.1242 |    -4363.0000 |           1.0000 |
| BTCUSDT  | 10min | reversal  |  0.5000 | discovery |  26064 |     0.5181 |      0.5556 |      -0.0673 |    -1755.0000 |           1.0000 |
| BTCUSDT  | 10min | reversal  |  0.5000 | holdout   |  35134 |     0.5126 |      0.5556 |      -0.0774 |    -2717.8000 |           1.0000 |
| BTCUSDT  | 30min | always_up |  0.5000 | discovery |   8688 |     0.5073 |      0.5405 |      -0.0616 |     -535.0500 |           1.0000 |
| BTCUSDT  | 30min | always_up |  0.5000 | holdout   |  11710 |     0.5027 |      0.5405 |      -0.0699 |     -819.0500 |           1.0000 |
| BTCUSDT  | 30min | momentum  |  0.5000 | discovery |   8688 |     0.4822 |      0.5405 |      -0.1080 |     -938.3500 |           1.0000 |
| BTCUSDT  | 30min | momentum  |  0.5000 | holdout   |  11710 |     0.4823 |      0.5405 |      -0.1077 |    -1261.2000 |           1.0000 |
| BTCUSDT  | 30min | reversal  |  0.5000 | discovery |   8688 |     0.5176 |      0.5405 |      -0.0424 |     -368.5500 |           1.0000 |
| BTCUSDT  | 30min | reversal  |  0.5000 | holdout   |  11710 |     0.5177 |      0.5405 |      -0.0423 |     -495.3000 |           1.0000 |
| BTCUSDT  | 1h    | always_up |  0.5000 | discovery |   4344 |     0.4982 |      0.5405 |      -0.0784 |     -340.6000 |           1.0000 |
| BTCUSDT  | 1h    | always_up |  0.5000 | holdout   |   5854 |     0.5000 |      0.5405 |      -0.0750 |     -439.0500 |           1.0000 |
| BTCUSDT  | 1h    | momentum  |  0.5000 | discovery |   4344 |     0.4896 |      0.5405 |      -0.0942 |     -409.0500 |           1.0000 |
| BTCUSDT  | 1h    | momentum  |  0.5000 | holdout   |   5854 |     0.4756 |      0.5405 |      -0.1202 |     -703.6000 |           1.0000 |
| BTCUSDT  | 1h    | reversal  |  0.5000 | discovery |   4344 |     0.5101 |      0.5405 |      -0.0563 |     -244.4000 |           1.0000 |
| BTCUSDT  | 1h    | reversal  |  0.5000 | holdout   |   5854 |     0.5243 |      0.5405 |      -0.0301 |     -176.3500 |           0.9940 |
| ETHUSDT  | 10min | always_up |  0.5000 | discovery |  26064 |     0.4997 |      0.5556 |      -0.1005 |    -2619.0000 |           1.0000 |
| ETHUSDT  | 10min | always_up |  0.5000 | holdout   |  35134 |     0.4968 |      0.5556 |      -0.1058 |    -3716.8000 |           1.0000 |
| ETHUSDT  | 10min | momentum  |  0.5000 | discovery |  26064 |     0.4769 |      0.5556 |      -0.1416 |    -3690.0000 |           1.0000 |
| ETHUSDT  | 10min | momentum  |  0.5000 | holdout   |  35134 |     0.4811 |      0.5556 |      -0.1340 |    -4708.6000 |           1.0000 |
| ETHUSDT  | 10min | reversal  |  0.5000 | discovery |  26064 |     0.5221 |      0.5556 |      -0.0603 |    -1571.4000 |           1.0000 |
| ETHUSDT  | 10min | reversal  |  0.5000 | holdout   |  35134 |     0.5170 |      0.5556 |      -0.0694 |    -2438.8000 |           1.0000 |
| ETHUSDT  | 30min | always_up |  0.5000 | discovery |   8688 |     0.5022 |      0.5405 |      -0.0710 |     -616.4500 |           1.0000 |
| ETHUSDT  | 30min | always_up |  0.5000 | holdout   |  11710 |     0.4994 |      0.5405 |      -0.0761 |     -891.2000 |           1.0000 |
| ETHUSDT  | 30min | momentum  |  0.5000 | discovery |   8688 |     0.4785 |      0.5405 |      -0.1148 |     -997.5500 |           1.0000 |
| ETHUSDT  | 30min | momentum  |  0.5000 | holdout   |  11710 |     0.4820 |      0.5405 |      -0.1083 |    -1268.6000 |           1.0000 |
| ETHUSDT  | 30min | reversal  |  0.5000 | discovery |   8688 |     0.5209 |      0.5405 |      -0.0362 |     -314.9000 |           0.9999 |
| ETHUSDT  | 30min | reversal  |  0.5000 | holdout   |  11710 |     0.5174 |      0.5405 |      -0.0428 |     -500.8500 |           1.0000 |
| ETHUSDT  | 1h    | always_up |  0.5000 | discovery |   4344 |     0.4984 |      0.5405 |      -0.0780 |     -338.7500 |           1.0000 |
| ETHUSDT  | 1h    | always_up |  0.5000 | holdout   |   5854 |     0.4991 |      0.5405 |      -0.0766 |     -448.3000 |           1.0000 |
| ETHUSDT  | 1h    | momentum  |  0.5000 | discovery |   4344 |     0.4915 |      0.5405 |      -0.0908 |     -394.2500 |           1.0000 |
| ETHUSDT  | 1h    | momentum  |  0.5000 | holdout   |   5854 |     0.4701 |      0.5405 |      -0.1303 |     -762.8000 |           1.0000 |
| ETHUSDT  | 1h    | reversal  |  0.5000 | discovery |   4344 |     0.5085 |      0.5405 |      -0.0592 |     -257.3500 |           1.0000 |
| ETHUSDT  | 1h    | reversal  |  0.5000 | holdout   |   5854 |     0.5292 |      0.5405 |      -0.0210 |     -122.7000 |           0.9601 |
