from vnpy.app.spread_trading import (
    SpreadAlgoTemplate,
    SpreadData,
    OrderData,
    TradeData
)

from Digiccy1.futures_spot_arbitrage.template import SpreadStrategyTemplate

class MyBasicSpreadStrategy(SpreadStrategyTemplate):
    """"""

    author = "Dean"

    buy_price = 0.0
    sell_price = 0.0
    cover_price = 0.0
    short_price = 0.0
    max_pos = 0.0
    lot_size = 0.0
    payup = 10
    interval = 5
    cancel_active_short_interval = 600

    spread_pos = 0.0

    parameters = [
        "buy_price",
        "sell_price",
        "cover_price",
        "short_price",
        "max_pos",
        "lot_size",
        "payup",
        "interval",
        "cancel_active_short_interval"
    ]
    variables = [
        "spread_pos",
        "buy_algoids",
        "sell_algoids",
        "short_algoids",
        "cover_algoids",
    ]

    def __init__(
        self,
        strategy_engine,
        strategy_name: str,
        spread: SpreadData,
        setting: dict
    ):
        """"""
        super().__init__(
            strategy_engine, strategy_name, spread, setting
        )

        self.buy_algoids = []
        self.sell_algoids = []
        self.short_algoids = []
        self.cover_algoids = []
        self.sell_algo_aggpos = 0.0
        self.cover_algo_aggpos = 0.0
        # print('%s interval: %s' % (self.spread_name, self.interval))
        # print('%s cancel_active_short_interval: %s' % (self.spread_name, self.cancel_active_short_interval))
    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")

    def on_start(self):
        """
        Callback when strategy is started.
        """
        print(self.get_parameters())
        self.write_log("策略启动")

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")

        self.buy_algoids = []
        self.sell_algoids = []
        self.short_algoids = []
        self.cover_algoids = []
        self.put_event()

    def on_spread_data(self):
        """
        Callback when spread price is updated.
        """
        self.spread_pos = self.get_spread_pos()
        # print(f'{self.strategy_name}on_spread_data,spread_pos:{self.spread_pos}')
        # No position
        if not self.spread_pos:
            self.stop_close_algos()

            # Start open algos
            if len(self.buy_algoids)==0:
                buy_algoid = self.start_long_algo(
                    self.buy_price, self.max_pos, self.lot_size, self.payup, self.interval, self.cancel_active_short_interval
                )
                self.buy_algoids.append(buy_algoid)

            if len(self.short_algoids)==0:
                short_algoid = self.start_short_algo(
                    self.short_price, self.max_pos, self.lot_size, self.payup, self.interval, self.cancel_active_short_interval
                )
                self.short_algoids.append(short_algoid)

        # Long position
        elif self.spread_pos > 0:
            if self.spread_pos >= self.max_pos:
                self.stop_open_algos()

                # Start sell close algo
                if len(self.sell_algoids)==0:
                    sell_algoid = self.start_short_algo(
                        self.sell_price, self.spread_pos, self.lot_size, self.payup, self.interval, self.cancel_active_short_interval
                    )
                    self.sell_algoids.append(sell_algoid)
                    self.sell_algo_aggpos += self.spread_pos
            else:
                start_short_vol = self.spread_pos - self.sell_algo_aggpos
                if start_short_vol > 0 and start_short_vol*self.spread.active_leg.last_price > 12:
                    sell_algoid = self.start_short_algo(
                            self.sell_price, start_short_vol, self.lot_size, self.payup, self.interval, self.cancel_active_short_interval
                        )
                    self.sell_algo_aggpos += start_short_vol
                    self.sell_algoids.append(sell_algoid)

        # Short position
        elif self.spread_pos < 0:
            if self.spread_pos <= -self.max_pos:
                self.stop_open_algos()

                # Start cover close algo
                if len(self.cover_algoids) == 0:
                    cover_algoid = self.start_long_algo(self.cover_price, abs(self.spread_pos), self.lot_size, self.payup, self.interval, self.cancel_active_short_interval)
                    self.cover_algoids.append(cover_algoid)
                    self.cover_algo_aggpos -= abs(self.spread_pos)
            else:
                start_cover_vol = -(self.spread_pos - self.cover_algo_aggpos)
                if start_cover_vol > 0 and start_short_vol*self.spread.active_leg.last_price > 12:
                    cover_algoid = self.start_long_algo(self.cover_price, start_cover_vol, self.lot_size, self.payup, self.interval, self.cancel_active_short_interval)
                    self.cover_algo_aggpos -= start_cover_vol
                    self.cover_algoids.append(cover_algoid)

        self.put_event()

    def on_spread_pos(self):
        """
        Callback when spread position is updated.
        """
        self.spread_pos = self.get_spread_pos()
        self.put_event()

    def on_spread_algo(self, algo: SpreadAlgoTemplate):
        """
        Callback when algo status is updated.
        """
        if not algo.is_active():
            if algo.algoid in self.buy_algoids:
                self.buy_algoids.remove(algo.algoid)
            elif algo.algoid in self.sell_algoids:
                self.sell_algoids.remove(algo.algoid)
                self.sell_algo_aggpos -= algo.volume
            elif algo.algoid in self.short_algoids:
                self.short_algoids.remove(algo.algoid)
            elif algo.algoid in self.cover_algoids:
                self.cover_algoids.remove(algo.algoid)
                self.cover_algo_aggpos += algo.volume
            else:
                print('on_spread_algo has no algo:%s' % algo.algoid)

        self.put_event()

    def on_order(self, order: OrderData):
        """
        Callback when order status is updated.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback when new trade data is received.
        """
        pass

    def stop_open_algos(self):
        """"""
        for buy_algoid in self.buy_algoids:
            self.stop_algo(buy_algoid)

        for short_algoid in self.short_algoids:
            self.stop_algo(short_algoid)

    def stop_close_algos(self):
        """"""
        for sell_algoid in self.sell_algoids:
            self.stop_algo(sell_algoid)

        for cover_algoid in self.cover_algoids:
            self.stop_algo(cover_algoid)
