"""内置策略集合。

每个策略通过 :func:`~easy_tdx.backtest.strategies.registry.register_strategy`
登记到全局注册表，并声明参数 schema 供 Web API 表单动态渲染。

导入本模块即触发所有策略的注册。Web API / CLI 通过 ``get_registry()```
发现策略，无需手动枚举。
"""

from __future__ import annotations

from easy_tdx.backtest.strategies.registry import (
    Param,
    ParametrizedStrategy,
    register_strategy,
)
from easy_tdx.MyTT import BOLL, CROSS, KDJ, MA, MACD, RSI

__all__: list[str] = []  # 注册副作用即可，无需导出符号


# ── 双均线交叉 ─────────────────────────────────────────────────────────────────


@register_strategy(
    name="ma_cross",
    label="双均线交叉",
    description="快线上穿慢线买入，快线下穿慢线卖出。最经典的趋势跟随策略。",
)
class MaCrossStrategy(ParametrizedStrategy):
    """快慢均线金叉买入、死叉卖出。"""

    params = [
        Param("fast", int, default=5, min_value=1, max_value=60, label="快线周期"),
        Param("slow", int, default=20, min_value=5, max_value=250, label="慢线周期"),
    ]

    def init(self) -> None:
        self.ma_fast = self.I(MA, self.data.close, self.p["fast"])
        self.ma_slow = self.I(MA, self.data.close, self.p["slow"])
        self.gold = self.I(CROSS, self.ma_fast, self.ma_slow)
        self.dead = self.I(CROSS, self.ma_slow, self.ma_fast)

    def next(self) -> None:
        i = self._bar_index
        if self.gold[i]:
            self.buy()
        elif self.dead[i] and self.position["size"] > 0:
            self.sell()


# ── MACD 金叉 ──────────────────────────────────────────────────────────────────


@register_strategy(
    name="macd",
    label="MACD 金叉",
    description="DIF 上穿 DEA 买入（金叉），DIF 下穿 DEA 卖出（死叉）。",
)
class MacdStrategy(ParametrizedStrategy):
    """MACD 金叉/死叉。"""

    params = [
        Param("short", int, default=12, min_value=2, max_value=50, label="短期EMA"),
        Param("long", int, default=26, min_value=5, max_value=100, label="长期EMA"),
        Param("signal", int, default=9, min_value=2, max_value=50, label="信号周期"),
    ]

    def init(self) -> None:
        self.dif, self.dea, self._hist = self.I(
            MACD,
            self.data.close,
            self.p["short"],
            self.p["long"],
            self.p["signal"],
        )
        self.gold = self.I(CROSS, self.dif, self.dea)
        self.dead = self.I(CROSS, self.dea, self.dif)

    def next(self) -> None:
        i = self._bar_index
        if self.gold[i]:
            self.buy()
        elif self.dead[i] and self.position["size"] > 0:
            self.sell()


# ── 布林带突破 ─────────────────────────────────────────────────────────────────


@register_strategy(
    name="boll_breakout",
    label="布林带突破",
    description="收盘价突破下轨买入，突破上轨卖出（均值回归思路）。",
)
class BollBreakoutStrategy(ParametrizedStrategy):
    """价格触及下轨买入、触及上轨卖出。"""

    params = [
        Param("n", int, default=20, min_value=5, max_value=100, label="周期"),
        Param("p", float, default=2.0, min_value=0.5, max_value=4.0, label="标准差倍数"),
    ]

    def init(self) -> None:
        self.upper, self.mid, self.lower = self.I(BOLL, self.data.close, self.p["n"], self.p["p"])

    def next(self) -> None:
        i = self._bar_index
        close = self.data.close[0]
        # 触及下轨买入（均值回归）；触及上轨获利了结
        if close <= self.lower[i] and self.position["size"] == 0:
            self.buy()
        elif close >= self.upper[i] and self.position["size"] > 0:
            self.sell()


# ── RSI 超买超卖 ───────────────────────────────────────────────────────────────


@register_strategy(
    name="rsi_reversal",
    label="RSI 超卖反弹",
    description="RSI 低于超卖线买入，RSI 高于超买线卖出。",
)
class RsiReversalStrategy(ParametrizedStrategy):
    """RSI 超卖买入、超买卖出。"""

    params = [
        Param("n", int, default=14, min_value=2, max_value=50, label="RSI周期"),
        Param("oversold", int, default=30, min_value=5, max_value=45, label="超卖线"),
        Param("overbought", int, default=70, min_value=55, max_value=95, label="超买线"),
    ]

    def init(self) -> None:
        self.rsi = self.I(RSI, self.data.close, self.p["n"])

    def next(self) -> None:
        i = self._bar_index
        rsi = self.rsi[i]
        if rsi <= self.p["oversold"] and self.position["size"] == 0:
            self.buy()
        elif rsi >= self.p["overbought"] and self.position["size"] > 0:
            self.sell()


# ── KDJ 金叉 ───────────────────────────────────────────────────────────────────


@register_strategy(
    name="kdj_cross",
    label="KDJ 金叉",
    description="K 线上穿 D 线买入（金叉），K 线下穿 D 线卖出（死叉）。",
)
class KdjCrossStrategy(ParametrizedStrategy):
    """KDJ K/D 金叉死叉。"""

    params = [
        Param("n", int, default=9, min_value=2, max_value=30, label="RSV周期"),
    ]

    def init(self) -> None:
        self.k, self.d, self._j = self.I(
            KDJ,
            self.data.close,
            self.data.high,
            self.data.low,
            self.p["n"],
        )
        self.gold = self.I(CROSS, self.k, self.d)
        self.dead = self.I(CROSS, self.d, self.k)

    def next(self) -> None:
        i = self._bar_index
        if self.gold[i]:
            self.buy()
        elif self.dead[i] and self.position["size"] > 0:
            self.sell()
