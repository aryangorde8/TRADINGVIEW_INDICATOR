"""Generate data/labeled_examples.jsonl with verbatim-span validation."""
import json
import sys

EXAMPLES = [
    # ---- survivorship_bias ----
    {
        "id": "survivorship-1",
        "text": "Every trader I follow on X who used this breakout system got rich. Thousands of people trade it successfully, so the edge is clearly real.",
        "labels": [{"fallacy": "survivorship_bias", "span": "Every trader I follow on X who used this breakout system got rich"}],
    },
    {
        "id": "survivorship-2",
        "text": "I studied the 20 best-performing hedge funds of the last decade and every one of them averages down on losing positions, which proves averaging down works.",
        "labels": [{"fallacy": "survivorship_bias", "span": "I studied the 20 best-performing hedge funds of the last decade and every one of them averages down on losing positions, which proves averaging down works"}],
    },
    {
        "id": "survivorship-3",
        "text": "I backtested buy-the-dip on the current Nifty 50 constituents over the past 15 years. Every dip recovered, so buying dips in index stocks is a guaranteed strategy.",
        "labels": [{"fallacy": "survivorship_bias", "span": "I backtested buy-the-dip on the current Nifty 50 constituents over the past 15 years"}],
    },
    # ---- lookahead_bias ----
    {
        "id": "lookahead-1",
        "text": "My scanner ranks stocks by today's closing relative strength and enters at today's open. The backtest shows 74% winners, so the ranking clearly predicts intraday moves.",
        "labels": [{"fallacy": "lookahead_bias", "span": "ranks stocks by today's closing relative strength and enters at today's open"}],
    },
    {
        "id": "lookahead-2",
        "text": "In the backtest I exit at the high of the day whenever the session closes red. That single exit rule doubled the Sharpe ratio, so the system is far more robust than it looks.",
        "labels": [{"fallacy": "lookahead_bias", "span": "I exit at the high of the day whenever the session closes red"}],
    },
    {
        "id": "lookahead-3",
        "text": "I chose 2020 through 2023 as my evaluation window because I already knew markets trended strongly in those years, and sure enough my trend-following system crushed it there.",
        "labels": [{"fallacy": "lookahead_bias", "span": "I chose 2020 through 2023 as my evaluation window because I already knew markets trended strongly in those years"}],
    },
    # ---- overfitting ----
    {
        "id": "overfitting-1",
        "text": "After tuning 12 parameters across 400 combinations, my backtest Sharpe hit 3.4. With in-sample numbers that good, taking it live is a formality.",
        "labels": [{"fallacy": "overfitting", "span": "After tuning 12 parameters across 400 combinations, my backtest Sharpe hit 3.4"}],
    },
    {
        "id": "overfitting-2",
        "text": "I kept adding filters until the equity curve was smooth: time of day, VIX regime, day of week, even lunar phase. Now it never loses in the backtest, so it is ready for real money.",
        "labels": [{"fallacy": "overfitting", "span": "I kept adding filters until the equity curve was smooth"}],
    },
    {
        "id": "overfitting-3",
        "text": "The system fits the last decade of data perfectly, and a perfect historical fit is the strongest possible evidence of a genuine edge.",
        "labels": [{"fallacy": "overfitting", "span": "a perfect historical fit is the strongest possible evidence of a genuine edge"}],
    },
    # ---- base_rate_neglect ----
    {
        "id": "baserate-1",
        "text": "This candlestick pattern appeared before 8 of the last 10 major rallies. So whenever you see the pattern, a rally is near-certain.",
        "labels": [{"fallacy": "base_rate_neglect", "span": "This candlestick pattern appeared before 8 of the last 10 major rallies. So whenever you see the pattern, a rally is near-certain"}],
    },
    {
        "id": "baserate-2",
        "text": "Ninety percent of big crashes were preceded by an inverted yield curve. The curve just inverted, so a crash is coming.",
        "labels": [{"fallacy": "base_rate_neglect", "span": "Ninety percent of big crashes were preceded by an inverted yield curve. The curve just inverted, so a crash is coming"}],
    },
    {
        "id": "baserate-3",
        "text": "I have won my last six trades in a row, which is only a 1.6% probability by pure chance, so my discretionary method clearly has a real edge.",
        "labels": [{"fallacy": "base_rate_neglect", "span": "I have won my last six trades in a row, which is only a 1.6% probability by pure chance"}],
    },
    # ---- unfalsifiable ----
    {
        "id": "unfalsifiable-1",
        "text": "When price rallies, it confirms smart money accumulation. When price drops, it just proves smart money is shaking out weak hands before the real rally.",
        "labels": [{"fallacy": "unfalsifiable", "span": "When price rallies, it confirms smart money accumulation. When price drops, it just proves smart money is shaking out weak hands before the real rally"}],
    },
    {
        "id": "unfalsifiable-2",
        "text": "The strategy itself is sound. Every losing streak it has is caused by market-maker manipulation, not by the system.",
        "labels": [{"fallacy": "unfalsifiable", "span": "Every losing streak it has is caused by market-maker manipulation, not by the system"}],
    },
    {
        "id": "unfalsifiable-3",
        "text": "The wave count predicted this move. If the count ever looks wrong, that only means we are in a different wave degree, and the wave principle still holds.",
        "labels": [{"fallacy": "unfalsifiable", "span": "If the count ever looks wrong, that only means we are in a different wave degree, and the wave principle still holds"}],
    },
    # ---- multi-fallacy ----
    {
        "id": "multi-1",
        "text": "I tuned 15 indicator thresholds until the 2019-2024 backtest was flawless. And whenever the live version loses, it is because algos are hunting my stops.",
        "labels": [
            {"fallacy": "overfitting", "span": "I tuned 15 indicator thresholds until the 2019-2024 backtest was flawless"},
            {"fallacy": "unfalsifiable", "span": "whenever the live version loses, it is because algos are hunting my stops"},
        ],
    },
    # ---- clean (no fallacies) ----
    {
        "id": "clean-1",
        "text": "I froze the pullback system's parameters on 2015-2021 data, then tested on held-out 2022-2024 data. Out of sample it won 48% of trades with an average R of 1.7 and stayed profitable after costs. I will paper trade it for three months and stop if drawdown exceeds 12%.",
        "labels": [],
    },
    {
        "id": "clean-2",
        "text": "The signal fires about 30 times a year. Historically 55% of those trades closed profitably, versus a 52% base rate for random entries taken at the same times. The difference is small and may not survive slippage, so I am collecting more live data before sizing up.",
        "labels": [],
    },
    # ---- v0.4 expansion: harder single-fallacy examples ----
    {
        "id": "survivorship-4",
        "text": "Of the fifty systems I have built since 2019, the three I still trade all share this volume filter. That common thread is clearly what separates winning systems from losing ones.",
        "labels": [{"fallacy": "survivorship_bias", "span": "the three I still trade all share this volume filter. That common thread is clearly what separates winning systems from losing ones"}],
    },
    {
        "id": "survivorship-5",
        "text": "The podcast interviewed twelve full-time traders who all quit their day jobs within two years of starting. If they can live off trading that quickly, any disciplined person can.",
        "labels": [{"fallacy": "survivorship_bias", "span": "The podcast interviewed twelve full-time traders who all quit their day jobs within two years of starting. If they can live off trading that quickly, any disciplined person can"}],
    },
    {
        "id": "survivorship-6",
        "text": "Look at the wallets that held bitcoin through every crash since 2013: diamond hands always won. Never selling is therefore the optimal long-term strategy for any coin.",
        "labels": [{"fallacy": "survivorship_bias", "span": "Look at the wallets that held bitcoin through every crash since 2013: diamond hands always won"}],
    },
    {
        "id": "lookahead-4",
        "text": "My screener selects the twenty most volatile stocks of the month, and I backtest a mean-reversion entry inside that same month. Returns are stellar and remarkably stable.",
        "labels": [{"fallacy": "lookahead_bias", "span": "selects the twenty most volatile stocks of the month, and I backtest a mean-reversion entry inside that same month"}],
    },
    {
        "id": "lookahead-5",
        "text": "For the 9:30 entry signal I normalise each day's features by that day's full high-low range, which makes the model much more stable across regimes.",
        "labels": [{"fallacy": "lookahead_bias", "span": "I normalise each day's features by that day's full high-low range"}],
    },
    {
        "id": "lookahead-6",
        "text": "I dropped 2020 from the backtest because COVID was a once-in-a-century anomaly that no reasonable system could have been expected to handle. Without it, the strategy is consistently profitable.",
        "labels": [{"fallacy": "lookahead_bias", "span": "I dropped 2020 from the backtest because COVID was a once-in-a-century anomaly"}],
    },
    {
        "id": "overfitting-4",
        "text": "The first walk-forward test failed, so I adjusted the stop distance and re-ran it until the walk-forward passed too. Now both in-sample and out-of-sample look great, so the system is validated.",
        "labels": [{"fallacy": "overfitting", "span": "I adjusted the stop distance and re-ran it until the walk-forward passed too"}],
    },
    {
        "id": "overfitting-5",
        "text": "Our genetic optimiser searched forty thousand rule combinations and the best one returned 61% annually in the backtest. That combination is the strategy we now sell to subscribers.",
        "labels": [{"fallacy": "overfitting", "span": "searched forty thousand rule combinations and the best one returned 61% annually in the backtest"}],
    },
    {
        "id": "overfitting-6",
        "text": "Each market regime gets its own parameter set: I fitted nine separate regimes so the equity curve stays smooth across the whole decade. Smoothness across ten years proves robustness.",
        "labels": [{"fallacy": "overfitting", "span": "I fitted nine separate regimes so the equity curve stays smooth across the whole decade"}],
    },
    {
        "id": "baserate-4",
        "text": "Our signal service called the March top to the day. That call is proof our model sees market turns coming before they happen.",
        "labels": [{"fallacy": "base_rate_neglect", "span": "Our signal service called the March top to the day. That call is proof our model sees market turns coming"}],
    },
    {
        "id": "baserate-5",
        "text": "83% of our winning trades happened when RSI was below 30, so RSI below 30 is clearly where the edge lives and where we should concentrate size.",
        "labels": [{"fallacy": "base_rate_neglect", "span": "83% of our winning trades happened when RSI was below 30, so RSI below 30 is clearly where the edge lives"}],
    },
    {
        "id": "baserate-6",
        "text": "This fund beat the index five years straight. The odds of that happening by luck are one in thirty-two, so skill is statistically proven.",
        "labels": [{"fallacy": "base_rate_neglect", "span": "The odds of that happening by luck are one in thirty-two, so skill is statistically proven"}],
    },
    {
        "id": "unfalsifiable-4",
        "text": "A true trend-follower profits in all market conditions. If a trend system loses money, that just shows it was never a true trend system to begin with.",
        "labels": [{"fallacy": "unfalsifiable", "span": "If a trend system loses money, that just shows it was never a true trend system to begin with"}],
    },
    {
        "id": "unfalsifiable-5",
        "text": "The harmonic pattern completed perfectly on the daily chart, and where it appeared to fail, the market was simply respecting a higher-degree pattern instead.",
        "labels": [{"fallacy": "unfalsifiable", "span": "where it appeared to fail, the market was simply respecting a higher-degree pattern instead"}],
    },
    {
        "id": "unfalsifiable-6",
        "text": "My mentor's method never fails. When students lose money with it, it is because they lacked the discipline to apply the method correctly.",
        "labels": [{"fallacy": "unfalsifiable", "span": "When students lose money with it, it is because they lacked the discipline to apply the method correctly"}],
    },
    # ---- v0.4 expansion: multi-fallacy ----
    {
        "id": "multi-2",
        "text": "I tested three hundred indicator pairs and the MACD-ADX combo hit 78% winners. A rate of 78% cannot be chance, so it is now my core system.",
        "labels": [
            {"fallacy": "overfitting", "span": "I tested three hundred indicator pairs and the MACD-ADX combo hit 78% winners"},
            {"fallacy": "base_rate_neglect", "span": "A rate of 78% cannot be chance"},
        ],
    },
    {
        "id": "multi-3",
        "text": "Every famous trader says to cut losses early, so it must be the single key to success. And if someone cut losses early and still failed, they obviously did it wrong.",
        "labels": [
            {"fallacy": "survivorship_bias", "span": "Every famous trader says to cut losses early, so it must be the single key to success"},
            {"fallacy": "unfalsifiable", "span": "if someone cut losses early and still failed, they obviously did it wrong"},
        ],
    },
    {
        "id": "multi-4",
        "text": "I picked the five best-performing currency pairs of 2024 and then tuned my entries until each of them was profitable across 2024. All five now pass, so the framework generalises.",
        "labels": [
            {"fallacy": "lookahead_bias", "span": "I picked the five best-performing currency pairs of 2024"},
            {"fallacy": "overfitting", "span": "tuned my entries until each of them was profitable across 2024"},
        ],
    },
    # ---- v0.4 expansion: trap-clean (superficially fallacious, sound) ----
    {
        "id": "clean-3",
        "text": "I studied the ten best funds of the decade and also the two hundred that closed. The winners' common trait disappeared once the failed funds were included, so I discarded that trait as noise.",
        "labels": [],
    },
    {
        "id": "clean-4",
        "text": "The signal uses yesterday's close and enters at today's open. Higher-timeframe data is requested with lookahead disabled and offset by one completed bar, so nothing in the pipeline sees the future.",
        "labels": [],
    },
    {
        "id": "clean-5",
        "text": "I tuned the lookback length on 2015-2019 data, froze every parameter, and then accepted the weaker but still positive 2020-2024 out-of-sample result without making further changes.",
        "labels": [],
    },
    {
        "id": "clean-6",
        "text": "The pattern fires about forty times a year and precedes a rally 22% of the time, versus an 18% unconditional base rate over the same period. That is a small edge that may vanish after costs.",
        "labels": [],
    },
    {
        "id": "clean-7",
        "text": "If NIFTY closes below 22,000 the breakout thesis is wrong and I exit the position entirely. That level is my explicit falsification point, decided before entry.",
        "labels": [],
    },
    {
        "id": "clean-8",
        "text": "A fund returning 90% in a single year is within the range that pure luck produces across the thousands of funds operating, so I treat one great year as noise until a longer record exists.",
        "labels": [],
    },
    {
        "id": "clean-9",
        "text": "The backtest universe includes delisted tickers up to their delisting dates and uses point-in-time index membership, so companies that later failed are fully represented.",
        "labels": [],
    },
    {
        "id": "clean-10",
        "text": "My last six trades all won, which I attribute mostly to a strongly trending regime rather than skill. Six trades is far too small a sample to infer anything about edge.",
        "labels": [],
    },
]

# Internal consistency gate: every gold span must be a verbatim substring.
errors = []
for ex in EXAMPLES:
    for label in ex["labels"]:
        if label["span"] not in ex["text"]:
            errors.append(f"{ex['id']}: span not verbatim: {label['span']!r}")
ids = [ex["id"] for ex in EXAMPLES]
if len(ids) != len(set(ids)):
    errors.append("duplicate ids")
if errors:
    print("\n".join(errors))
    sys.exit(1)

out = sys.argv[1]
with open(out, "w") as f:
    for ex in EXAMPLES:
        f.write(json.dumps(ex, ensure_ascii=False) + "\n")

n_labels = sum(len(ex["labels"]) for ex in EXAMPLES)
print(f"wrote {len(EXAMPLES)} examples, {n_labels} gold labels -> {out}")
