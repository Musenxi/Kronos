"""Kronos 预训练模型在 BTC/ETH 事件合约（10min / 30min / 1h 涨跌）上的样本外检验（独立版）。

与 Musenxi/Quant 的 scripts/run_kronos_event.py（RESEARCH_LOG #43）口径一致，只依赖本仓库 + pandas/scipy。

用法（在 Kronos 仓库根目录）：
    python event_contract/run_event.py download                 # 下载 1m 永续 K 线（data.binance.vision）
    python event_contract/run_event.py predict --tf 1h           # 滚动预测，按月断点续跑
    python event_contract/run_event.py evaluate                  # 报告 → event_contract/output/report.md

事件合约口径：
- bar t 收盘后立刻下单，入场价 = close_t；结算价 = close_{t+1}（永续 1m 合成；交易所用指数价，有小偏差）。
- 猜对赚 payout 倍本金，猜错亏 1 倍；平局按输。赔率：10min 80%，30min / 1h 85%。
- 只用完整 bar（分钟数齐全）；预测窗口或下一根跨缺口则不预测、不计分。
Kronos：用 bar t 及之前 L 根已收盘 bar（窗口自身 z-score，clip ±5，与 KronosPredictor.predict 一致）采样 N 次下一根；
P(上涨) = 预测 close > 实际 close_t 的样本比例。pred_len=1 时 y_stamp 不参与计算。
样本外：只评估 2025-09-01 之后（模型 2025-08 发布）；发现期 2025-09~2026-02 选阈值，留出期 2026-03~2026-10 只看一次。
"""
from __future__ import annotations

import argparse
import io
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = HERE / "data"
OUT = HERE / "output"
PRED_DIR = OUT / "preds"
BASE_URL = "https://data.binance.vision/data/futures/um/monthly/klines"
PAYOUT = {"10min": 0.80, "30min": 0.85, "1h": 0.85}
TFS = tuple(PAYOUT)
DATA_START, DATA_END = "2025-07", "2026-10"          # 含 512 根 1h 预热
EVAL_START, SPLIT, EVAL_END = "2025-09-01", "2026-03-01", "2026-11-01"
FEATURES = ["open", "high", "low", "close", "volume", "amount"]
SYMBOLS = ("BTCUSDT", "ETHUSDT")


# ---------------------------------------------------------------- 数据

def _month_frame(symbol: str, month: str) -> pd.DataFrame:
    """下载并解析一个月度 1m 档案（兼容有无表头）；本地缓存 zip。"""
    cache = DATA / "raw" / f"{symbol}-1m-{month}.zip"
    if not cache.exists():
        with urlopen(f"{BASE_URL}/{symbol}/1m/{symbol}-1m-{month}.zip", timeout=120) as r:
            payload = r.read()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(payload)
    with zipfile.ZipFile(cache) as z:
        raw = z.read(z.namelist()[0])
    header = not raw.split(b",", 1)[0].strip().isdigit()
    df = pd.read_csv(io.BytesIO(raw), header=0 if header else None).iloc[:, :8]
    df.columns = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume"]
    t = pd.to_numeric(df["open_time"])
    df.index = pd.to_datetime(np.where(t > 1e14, t // 1000, t), unit="ms", utc=True)
    return df[["open", "high", "low", "close", "volume", "quote_volume"]].astype(float)


def download(args: argparse.Namespace) -> None:
    """下载 DATA_START~DATA_END 的 1m 永续 K 线，存 data/{SYM}_1m.parquet。"""
    months = [f"{m:%Y-%m}" for m in pd.date_range(DATA_START, DATA_END, freq="MS")]
    for symbol in args.symbols:
        with ThreadPoolExecutor(8) as pool:
            frames = list(pool.map(lambda m: _month_frame(symbol, m), months))
        m1 = pd.concat(frames).sort_index()
        m1 = m1.loc[~m1.index.duplicated(keep="last")]
        gaps = m1.index.to_series().diff().gt(pd.Timedelta("1min")).sum()
        m1.to_parquet(DATA / f"{symbol}_1m.parquet")
        print(f"{symbol}: {len(m1):,} bars {m1.index[0]} ~ {m1.index[-1]}, gaps={gaps}")


def load_bars(symbol: str, tf: str) -> pd.DataFrame:
    """1m → tf 完整 bar（索引 = 开盘时间 UTC），附连续标记和下一根涨跌标签（唯一向前看的列）。"""
    m1 = pd.read_parquet(DATA / f"{symbol}_1m.parquet")
    rs = dict(rule=tf, label="left", closed="left")
    bars = m1.resample(**rs).agg({"open": "first", "high": "max", "low": "min", "close": "last",
                                  "volume": "sum", "quote_volume": "sum"}).rename(columns={"quote_volume": "amount"})
    need = int(pd.Timedelta(tf) / pd.Timedelta("1min"))
    bars = bars.loc[m1["close"].resample(**rs).count() == need].copy()
    bars["contiguous"] = bars.index.to_series().diff().eq(pd.Timedelta(tf)).to_numpy()
    nxt, ok = bars["close"].shift(-1), bars["contiguous"].shift(-1, fill_value=False).astype(bool)
    bars["next_ret"] = (nxt / bars["close"] - 1).where(ok)
    bars["next_up"] = np.where(ok, (nxt > bars["close"]).astype(float), np.nan)
    bars["next_down"] = np.where(ok, (nxt < bars["close"]).astype(float), np.nan)
    return bars


# ---------------------------------------------------------------- 预测

def predict(args: argparse.Namespace) -> None:
    """滚动预测，按 品种_周期_月份 写 parquet（已存在则跳过，断线可续跑）。"""
    import torch
    sys.path.insert(0, str(REPO))
    from model import Kronos, KronosTokenizer
    from model.kronos import sample_from_logits

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(args.seed)
    print(f"device={device} model={args.model} L={args.lookback} N={args.samples}", flush=True)
    tok = KronosTokenizer.from_pretrained(args.tokenizer).eval().to(device)
    model = Kronos.from_pretrained(args.model).eval().to(device)
    L, N, max_ctx, c = args.lookback, args.samples, 512, FEATURES.index("close")

    for symbol in args.symbols:
        for tf in args.tf:
            bars = load_bars(symbol, tf)
            x_all = bars[FEATURES].to_numpy(np.float32)
            ix = bars.index
            stamp_all = np.stack([ix.minute, ix.hour, ix.weekday, ix.day, ix.month], 1).astype(np.float32)
            seg = (~bars["contiguous"]).cumsum().to_numpy()
            pos = np.arange(len(bars))
            for month in pd.date_range(EVAL_START, pd.Timestamp(EVAL_END) - pd.Timedelta(days=1), freq="MS"):
                out = PRED_DIR / f"{symbol}_{tf}_{args.tag}_{month:%Y-%m}.parquet"
                if out.exists():
                    continue
                lo, hi = month.tz_localize("UTC"), (month + pd.offsets.MonthBegin(1)).tz_localize("UTC")
                cand = pos[(ix >= lo) & (ix < hi) & (pos >= L - 1) & bars["next_up"].notna().to_numpy()]
                cand = cand[seg[cand] == seg[np.maximum(cand - L + 1, 0)]][:: args.stride]
                t0, rows = time.time(), []
                for i in range(0, len(cand), args.batch):
                    idx = cand[i:i + args.batch]
                    B = len(idx)
                    win = np.stack([x_all[j - L + 1:j + 1] for j in idx])
                    mean, std = win.mean(1, keepdims=True), win.std(1, keepdims=True)
                    xn = np.clip((win - mean) / (std + 1e-5), -5, 5)
                    st = np.stack([stamp_all[j - L + 1:j + 1] for j in idx])
                    with torch.no_grad():
                        s1, s2 = tok.encode(torch.from_numpy(xn).to(device), half=True)
                        logits, ctx = model.decode_s1(s1, s2, torch.from_numpy(st).to(device))
                        pre = sample_from_logits(logits[:, -1, :].repeat_interleave(N, 0), temperature=args.T,
                                                 top_k=0, top_p=args.top_p, sample_logits=True)
                        s2_logits = model.decode_s2(ctx.repeat_interleave(N, 0), pre)[:, -1, :]
                        post = sample_from_logits(s2_logits, temperature=args.T, top_k=0, top_p=args.top_p,
                                                  sample_logits=True)
                        f1 = torch.cat([s1.repeat_interleave(N, 0), pre], 1)[:, -max_ctx:]
                        f2 = torch.cat([s2.repeat_interleave(N, 0), post], 1)[:, -max_ctx:]
                        z = tok.decode([f1, f2], half=True).float().cpu().numpy().reshape(B, N, -1, 6)
                    pc, recon = z[:, :, -1, c], z[:, :, -2, c]
                    pred_close = pc * (std[:, 0, c][:, None] + 1e-5) + mean[:, 0, c][:, None]
                    last_close = win[:, -1, c][:, None]
                    rows += [{"open_time": ix[j],
                              "p_up": float((pc[k] > xn[k, -1, c]).mean()),
                              "p_up_recon": float((pc[k] > recon[k]).mean()),
                              "pred_ret_mean": float((pred_close[k] / last_close[k] - 1).mean()),
                              "pred_ret_std": float((pred_close[k] / last_close[k] - 1).std())}
                             for k, j in enumerate(idx)]
                PRED_DIR.mkdir(parents=True, exist_ok=True)
                pd.DataFrame(rows).set_index("open_time").to_parquet(out)
                print(f"{symbol} {tf} {month:%Y-%m}: {len(rows)} preds, {time.time() - t0:.0f}s", flush=True)


# ---------------------------------------------------------------- 评估

def bet_stats(direction: pd.Series, lab: pd.DataFrame, payout: float) -> dict:
    """direction +1 买涨 / -1 买跌 / 0 不下；返回次数、胜率、每笔期望、总损益、对盈亏平衡胜率的单侧二项检验。"""
    d = direction.reindex(lab.index).fillna(0)
    win = np.where(d > 0, lab["next_up"], np.where(d < 0, lab["next_down"], np.nan))
    pnl = pd.Series(np.where(win == 1, payout, -1.0), index=lab.index).where((d != 0) & lab["next_up"].notna())
    p = pnl.dropna()
    n, wins = len(p), int((p > 0).sum())
    be = 1 / (1 + payout)
    if n == 0:
        return {"bets": 0, "win_rate": np.nan, "breakeven": be, "ev_per_bet": np.nan, "total_units": 0.0,
                "p_vs_breakeven": np.nan}
    return {"bets": n, "win_rate": wins / n, "breakeven": be, "ev_per_bet": p.mean(), "total_units": p.sum(),
            "p_vs_breakeven": stats.binomtest(wins, n, be, alternative="greater").pvalue}


def direction(prob: pd.Series, theta: float) -> pd.Series:
    """P(上涨) ≥ theta 买涨，≤ 1-theta 买跌。"""
    d = pd.Series(0.0, index=prob.index)
    d[prob >= theta], d[prob <= 1 - theta] = 1.0, -1.0
    return d


def evaluate(args: argparse.Namespace) -> None:
    """基准（每根都下注）与 Kronos（发现期选 theta，要求 ≥200 注）在留出期的事件合约结果。"""
    rows, calib = [], []
    split = pd.Timestamp(SPLIT, tz="UTC")
    for symbol in args.symbols:
        for tf in TFS:
            bars = load_bars(symbol, tf)
            bars = bars[(bars.index >= pd.Timestamp(EVAL_START, tz="UTC")) & (bars.index < pd.Timestamp(EVAL_END, tz="UTC"))]
            payout = PAYOUT[tf]
            up = np.sign(bars["close"] - bars["open"])
            mom = pd.Series(np.select([up > 0, up < 0], [1.0, 0.0], 0.5), index=bars.index)
            signals = {"always_up": pd.Series(1.0, index=bars.index), "momentum": mom, "reversal": 1 - mom}
            files = sorted(PRED_DIR.glob(f"{symbol}_{tf}_{args.tag}_*.parquet"))
            if files:
                pr = pd.concat(pd.read_parquet(f) for f in files).sort_index()
                signals["kronos_p_up"], signals["kronos_p_up_recon"] = pr["p_up"], pr["p_up_recon"]
            for name, prob in signals.items():
                prob = prob.reindex(bars.index)
                lab = bars.loc[prob.notna()]
                disc, hold = lab[lab.index < split], lab[lab.index >= split]
                theta = 0.5
                if name.startswith("kronos"):
                    grid = [(th, bet_stats(direction(prob.reindex(disc.index), th), disc, payout))
                            for th in np.round(np.arange(0.5, 0.801, 0.025), 3)]
                    ok = [(th, s["ev_per_bet"]) for th, s in grid if s["bets"] >= 200]
                    theta = max(ok, key=lambda t: t[1])[0] if ok else 0.5
                for period, part in (("discovery", disc), ("holdout", hold)):
                    rows.append({"symbol": symbol, "tf": tf, "signal": name, "theta": theta, "period": period,
                                 **bet_stats(direction(prob.reindex(part.index), theta), part, payout)})
                if name == "kronos_p_up" and len(hold):
                    df = pd.DataFrame({"p": prob.reindex(hold.index), "up": hold["next_up"], "ret": hold["next_ret"]})
                    ic = df["p"].corr(df["ret"], method="spearman")
                    df["bin"] = pd.qcut(df["p"].rank(method="first"), 5, labels=False)
                    cal = df.groupby("bin").agg(p_mean=("p", "mean"), up_rate=("up", "mean"), n=("up", "size"))
                    calib.append(f"### {symbol} {tf}（留出期 Rank IC={ic:.4f}）\n\n{cal.to_markdown(floatfmt='.4f')}\n")
    table = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    table.to_csv(OUT / "report.csv", index=False)
    md = ["# Kronos × 事件合约（BTC/ETH）", "",
          f"赔率 {PAYOUT}，平局按输。发现期 {EVAL_START}~{SPLIT}（Kronos 在此选 theta），留出期 {SPLIT}~{EVAL_END}。",
          "ev_per_bet：每笔期望（单位本金）；p_vs_breakeven：胜率高于盈亏平衡胜率的单侧二项检验 p 值。", "",
          table.to_markdown(index=False, floatfmt=".4f")]
    if calib:
        md += ["", "## Kronos 校准（留出期，P(上涨) 五分位）", ""] + calib
    (OUT / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(table.to_string(index=False))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("download")
    p = sub.add_parser("predict")
    p.add_argument("--model", default="NeoQuasar/Kronos-small")
    p.add_argument("--tokenizer", default="NeoQuasar/Kronos-Tokenizer-base")
    p.add_argument("--lookback", type=int, default=512)
    p.add_argument("--samples", type=int, default=32)
    p.add_argument("--T", type=float, default=1.0)
    p.add_argument("--top-p", type=float, default=0.9)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--stride", type=int, default=1, help="每隔几根 bar 预测一次（10min 太慢可设 2/3）")
    p.add_argument("--device", default=None, help="cuda / cpu；默认有 GPU 就用")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--tag", default="small")
    p.add_argument("--tf", nargs="+", default=list(TFS), choices=TFS)
    e = sub.add_parser("evaluate")
    e.add_argument("--tag", default="small")
    for q in (d, p, e):
        q.add_argument("--symbols", nargs="+", default=list(SYMBOLS))
    args = ap.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    {"download": download, "predict": predict, "evaluate": evaluate}[args.cmd](args)


if __name__ == "__main__":
    main()
