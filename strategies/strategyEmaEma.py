import talib
from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)


class EmaEmaStrategy(CtaTemplate):
    """"""

    author = "DEAN"

    ema_period = 20
    k_minute = 30
    fixed_size = 1

    parameters = ["k_minute", "ema_period", "fixed_size"]
    variables = []

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super(EmaEmaStrategy, self).__init__(
            cta_engine, strategy_name, vt_symbol, setting
        )

        self.bg = BarGenerator(self.on_bar, self.k_minute, self.on_mymin_bar)
        self.am = ArrayManager()

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        self.load_bar(30)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("策略启动")

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.bg.update_bar(bar)

    def on_mymin_bar(self, bar: BarData):
        """"""
        self.cancel_all()

        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        self.ema = talib.EMA(am.close, self.ema_period)
        self.emaema = talib.EMA(self.ema, self.ema_period)

        if self.pos == 0:
            self.longPrice = 0
            self.shortPrice = 0
            self.highPrice = 0
            self.lowPrice = 0
            if self.ema[-1] > self.emaema[-1]:
                self.buy(self.bg.last_bar.high_price+3, self.fixed_size)
                self.sell(self.bg.last_bar.close_price-5, self.fixed_size, True)
                self.longPrice = self.bg.last_bar.close_price
                self.highPrice = self.bg.last_bar.high_price

            elif self.ema[-1] < self.emaema[-1]:
                self.short(self.bg.last_bar.low_price-3, self.fixed_size)
                self.cover(self.bg.last_bar.close_price+5, self.fixed_size, True)
                self.shortPrice = self.bg.last_bar.close_price
                self.lowPrice = self.bg.last_bar.low_price

        elif self.pos > 0:
            if self.ema[-1] < self.emaema[-1]:
                self.sell(self.bg.last_bar.close_price-3, self.fixed_size)
            elif self.bg.last_bar.close_price < self.highPrice-5:
                self.sell(self.bg.last_bar.close_price-3, self.fixed_size)
            else:
                self.sell(self.longPrice-5, self.fixed_size, True)

            self.highPrice = self.bg.last_bar.high_price
        elif self.pos < 0:
            if self.ema[-1] > self.emaema[-1]:
                self.cover(self.bg.last_bar.close_price+3, self.fixed_size)
            elif self.bg.last_bar.close_price > self.lowPrice+5:
                self.cover(self.bg.last_bar.close_price+3, self.fixed_size)
            else:
                self.cover(self.shortPrice+5, self.fixed_size, True)

            self.lowPrice = self.bg.last_bar.low_price
        self.put_event()

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        pass
