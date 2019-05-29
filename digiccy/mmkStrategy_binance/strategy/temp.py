# 价格趋势系数
    def price_trend_factor(self, trades, buy1_price, sell1_price, buy2_price, sell2_price, buy3_price, sell3_price, vol_list, index_type=None, symmetric=True):
        prices = trades["price"].values.tolist()
        latest_trades = prices[-6:]
        mid_price = (buy1_price+sell1_price)/2*0.7 + (buy2_price+sell2_price)/2*0.2 + (buy3_price+sell3_price)/2*0.1
        latest_trades.append(mid_price)
        is_bull_trend = False
        is_bear_trend = False
        last_price_too_far_from_latest = False
        has_large_vol_trade = False

        if latest_trades[-1] > max(latest_trades[:-1]) + latest_trades[-1]*0.00005 or (latest_trades[-1] > max(latest_trades[:-2]) + latest_trades[-1]*0.00005 and latest_trades[-1] > latest_trades[-2]):
            is_bull_trend = True
        elif latest_trades[-1] < min(latest_trades[:-1]) - latest_trades[-1]*0.00005 or (latest_trades[-1] < min(latest_trades[:-2]) - latest_trades[-1]*0.00005 and latest_trades[-1] < latest_trades[-2]):
            is_bear_trend = True

        if abs(latest_trades[-1] - latest_trades[-2]*0.7 - latest_trades[-3]*0.2 - latest_trades[-4]*0.1) > latest_trades[-1]*0.002:
            last_price_too_far_from_latest = True

        if max(vol_list) > 20:
            has_large_vol_trade = True

        if is_bull_trend or is_bear_trend or last_price_too_far_from_latest or has_large_vol_trade:
            return 0

        if index_type == "rsi":
            prices = trades["price"]
            index = indicators.rsi_value(prices, len(prices)-1)
        else:
            index = self.buy_trades_ratio(trades)
        # 价格趋势严重，暂停交易
        if index <= 20 or index >= 80:
            return 0

        # 对称下单时，factor用来调整下单总数
        if symmetric:
            factor = 1 - abs(index-50)/50
        # 非对称下单时，factor用来调整买入订单的数量
        else:
            factor = index / 50
        return factor

# 做市模块
def trade_thread(self):
        while True:
            try:
                if self.timeInterval > 0:
                    self.timeLog("Trade - 等待 %d 秒进入下一个循环..." % self.timeInterval)
                    time.sleep(self.timeInterval)

                # 检查order_info_list里面还有没有pending的order，然后cancel他们
                order_id_list = []
                for odr in self.order_info_list:
                    order_id_list.append(odr["order_id"])
                self.huobi_cancel_pending_orders(order_id_list=order_id_list)
                self.order_info_list = []

                account = self.get_huobi_account_info()

                buy1_price = self.get_huobi_buy_n_price()
                sell1_price = self.get_huobi_sell_n_price()
                buy2_price = self.get_huobi_buy_n_price(n=2)
                sell2_price = self.get_huobi_sell_n_price(n=2)
                buy3_price = self.get_huobi_buy_n_price(n=3)
                sell3_price = self.get_huobi_sell_n_price(n=3)

                buy1_vol = self.get_huobi_buy_n_vol()
                sell1_vol = self.get_huobi_sell_n_vol()
                buy2_vol = self.get_huobi_buy_n_vol(n=2)
                sell2_vol = self.get_huobi_sell_n_vol(n=2)
                buy3_vol = self.get_huobi_buy_n_vol(n=3)
                sell3_vol = self.get_huobi_sell_n_vol(n=3)
                buy4_vol = self.get_huobi_buy_n_vol(n=4)
                sell4_vol = self.get_huobi_sell_n_vol(n=4)
                buy5_vol = self.get_huobi_buy_n_vol(n=5)
                sell5_vol = self.get_huobi_sell_n_vol(n=5)

                vol_list = [buy1_vol,buy2_vol,buy3_vol,buy4_vol,buy5_vol,sell1_vol,sell2_vol,sell3_vol,sell4_vol,sell5_vol]

                latest_trades_info = self.get_latest_market_trades()

                # 账户或者行情信息没有取到
                if not all([account, buy1_price, sell1_price]):
                    continue

                self.heart_beat_time.value = time.time()

                global init_account_info
                if init_account_info is None:
                    init_account_info = account

                global account_info_for_r_process
                account_info_for_r_process = copy.deepcopy(self.account_info)

                min_price_spread = self.arbitrage_min_spread(self.get_huobi_buy_n_price(), self.min_spread_rate)
                # 计算下单数量
                total_qty = min(self.total_qty_per_transaction, account.btc, account.cash / buy1_price)
                trend_factor = self.price_trend_factor(latest_trades_info, buy1_price, sell1_price, buy2_price, sell2_price, buy3_price, sell3_price, vol_list, symmetric=self.is_symmetric)
                if self.is_symmetric:
                    total_qty *= trend_factor
                    buy_ratio = 1
                    sell_ratio = 1
                else:
                    buy_ratio = trend_factor
                    sell_ratio = 2-trend_factor
                order_data_list = self.orders_price_and_qty_from_min_spread(buy1_price, sell1_price, total_qty,
                                                                            self.price_step, self.qty_step,
                                                                            self.min_qty_per_order,
                                                                            self.max_qty_per_order,
                                                                            min_price_spread, buy_ratio=buy_ratio,
                                                                            sell_ratio=sell_ratio)
                self.spot_batch_limit_orders(self.market_type, order_data_list, time_interval_between_threads=self.time_interval_between_threads)
                current_spread = self.bid_ask_spread(self.exchange)
                self.save_transactions(signal_spread=current_spread, signal_side="market_maker")
                self.latest_trade_time = time.time()
            except Exception:
                self.timeLog(traceback.format_exc())
                continue


# 从最小价差向外挂单
def orders_price_and_qty_from_min_spread(self, buy1_price, sell1_price, total_qty, price_step, qty_step,
                                         min_qty_per_order, max_qty_per_order, min_price_spread, buy_ratio=1, sell_ratio=1):
    orders_list = []
    remaining_qty = total_qty
    avg_price = (buy1_price + sell1_price) / 2

    if buy_ratio > 1: # price is going down
        avg_price += 0.2
    elif sell_ratio > 1: # price is going up
        avg_price -= 0.2

    buy_order_price = avg_price - min_price_spread / 2
    sell_order_price = avg_price + min_price_spread / 2
    order_qty = min(min_qty_per_order, remaining_qty)
    while remaining_qty >= min_qty_per_order and buy_order_price > buy1_price and sell_order_price < sell1_price:
        #buy_order_qty = max(order_qty * buy_ratio, self.min_order_qty)
        #sell_order_qty = max(order_qty * sell_ratio, self.min_order_qty)
        buy_order_qty = max(order_qty, self.min_order_qty)
        sell_order_qty = max(order_qty, self.min_order_qty)
        orders_list.append({"price": buy_order_price, "amount": buy_order_qty, "type": "buy"})
        orders_list.append({"price": sell_order_price, "amount": sell_order_qty, "type": "sell"})
        remaining_qty -= buy_order_qty
        buy_order_price -= price_step
        sell_order_price += price_step
        order_qty = min(buy_order_qty + qty_step, max_qty_per_order)
        order_qty = min(remaining_qty, order_qty)
    return orders_list

# 再平衡模块
def go(self):
        while True:
            try:
                if self.timeInterval > 0:
                    self.timeLog("R-balance - 等待 %d 秒进入下一个循环..." % self.timeInterval)
                    time.sleep(self.timeInterval)

                # 检查order_info_list里面还有没有pending的order，然后cancel他们
                order_id_list = []
                for odr in self.order_info_list:
                    order_id_list.append(odr["order_id"])
                self.huobi_cancel_pending_orders(order_id_list=order_id_list)
                self.order_info_list = []

                global init_account_info
                account_info = self.get_huobi_account_info_1(max_delay=self.account_info_max_delay)
                buy_1_price = self.get_huobi_buy_n_price()
                sell_1_price = self.get_huobi_sell_n_price()

                if not all([account_info, init_account_info, buy_1_price, sell_1_price]):
                    continue

                self.heart_beat_time.value = time.time()

                qty_delta = account_info.btc_total - init_account_info.btc_total
                cash_delta = account_info.cash_total - init_account_info.cash_total

                # 需要卖出
                if qty_delta >= self.min_order_qty:
                    trade_type = helper.SPOT_TRADE_TYPE_SELL
                    order_qty = qty_delta
                    if cash_delta <= 0:
                        holding_avg_price = abs(cash_delta/qty_delta)
                    else:
                        holding_avg_price = None
                    init_price = sell_1_price
                    if holding_avg_price is None:
                        worst_price = buy_1_price
                    else:
                        worst_price = max(buy_1_price, holding_avg_price * (1+self.mim_spread_rate))
                        #worst_price = buy_1_price
                # 需要买入
                elif qty_delta <= -self.min_order_qty:
                    trade_type = helper.SPOT_TRADE_TYPE_BUY
                    order_qty = -qty_delta
                    if cash_delta > 0:
                        holding_avg_price = abs(cash_delta/qty_delta)
                    # 钱与币都减少，卖出的均价为负
                    else:
                        holding_avg_price = None
                    init_price = buy_1_price
                    if holding_avg_price is None:
                        worst_price = sell_1_price
                    else:
                        worst_price = min(sell_1_price, holding_avg_price * (1-self.mim_spread_rate))
                        #worst_price = sell_1_price
                # 无需操作
                else:
                    continue

                # 下单限价单
                res = self.spot_order_to_target_qty(self.market_type, self.coin_type, trade_type, order_qty, init_price,
                                                    price_step=self.price_step, worst_price=worst_price,
                                                    max_qty_per_order=self.qty_per_order, max_time=self.max_time)
                if res is None:
                    total_executed_qty = 0
                else:
                    total_executed_qty, deal_avg_price = res

                remaining_qty = order_qty - total_executed_qty

                # 若设置了参数MARKET_ORDER_WHEN_QTY_DIFF_TOO_LARGE 为True，则可能需要市价单补单
                if remaining_qty >= self.min_order_qty and self.use_market_order:
                    current_diff_ratio = remaining_qty / init_account_info.btc_total
                    if self.max_qty_per_market_order is not None:
                        order_qty = min(remaining_qty, self.max_qty_per_market_order)
                    else:
                        order_qty = remaining_qty
                    order_id = None
                    # 市价卖出
                    if trade_type == helper.SPOT_TRADE_TYPE_SELL and current_diff_ratio > self.max_positive_diff_ratio:
                        order_id = self.spot_order(self.market_type, self.coin_type, trade_type,
                                                   helper.ORDER_TYPE_MARKET_ORDER, quantity=order_qty)
                    # 市价买入
                    elif trade_type == helper.SPOT_TRADE_TYPE_BUY and current_diff_ratio > self.max_negative_diff_ratio:
                        cash_amount = sell_1_price * order_qty
                        order_id = self.spot_order(self.market_type, self.coin_type, trade_type,
                                                   helper.ORDER_TYPE_MARKET_ORDER, cash_amount=cash_amount)
                    if order_id is not None:
                        self.spot_order_wait_and_cancel(self.market_type, self.coin_type, order_id)

                self.save_transactions(signal_side="rebalance")
                self.latest_trade_time = time.time()
            except Exception:
                self.timeLog(traceback.format_exc())
                continue


###########################################################################################
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from signalGenerator.futureSpotArb import *
from signalGenerator.strategyConfig import changeFutureContractConfig as rollCfg
import time, threading

class FutureMarketMaker(FutureSpotArb):
     def __init__(self, startRunningTime, orderRatio, timeInterval, orderWaitingTime,
                 coinMarketType, open_diff, close_diff, heart_beat_time, depth_data, account_info, transaction_info, maximum_qty_multiplier=None,
                 dailyExitTime=None):
        super(FutureMarketMaker, self).__init__(startRunningTime, orderRatio, timeInterval, orderWaitingTime,
                 coinMarketType, open_diff, close_diff, heart_beat_time, depth_data, account_info, transaction_info, maximum_qty_multiplier=maximum_qty_multiplier,
                 dailyExitTime=dailyExitTime)
                # 显示在邮件中的策略名字
        self.strat_name = "期货做市-%s" % startRunningTime.strftime("%Y%m%d_%H%M%S")
        self.trade_threshold = 0.0003 * 1.01
        self.sell_cut = 0.6
        self.buy_cut = 0.6
        self.leverage = 5
        self.remaining_delta_cash = 0
         # 策略下单参数
        self.coin_type = helper.HUOBI_COIN_TYPE_BTC
        self.contract_type = helper.CONTRACT_TYPE_WEEK
        self.initial_acct_info = None

     # cancel all pending orders
     def cancel_pending_orders(self):
        orders = self.BitVCService.order_list(self.coin_type,self.contract_type)
        while orders is not None and len(componentExtract(orders, "week", [])) > 0:
            orders = componentExtract(orders, "week", [])
            for order in orders:
                if componentExtract(order, u"id", "") != "":
                    order_id = order[u"id"]
                    self.BitVCService.order_cancel(self.coin_type,self.contract_type, order_id)
            orders = self.BitVCService.order_list(self.coin_type,self.contract_type)

     def go(self):
        self.timeLog("日志启动于 %s" % self.getStartRunningTime().strftime(self.TimeFormatForLog))
        self.timeLog("开始cancel pending orders")
        self.cancel_pending_orders()
        self.timeLog("完成cancel pending orders")

        while True:
            # 期货移仓期间，程序一直sleep
            if self.in_time_period(datetime.datetime.now(), rollCfg.CHANGE_CONTRACT_START_WEEK_DAY_FOR_NORMAL,
                                      rollCfg.CHANGE_CONTRACT_END_WEEK_DAY_FOR_NORMAL, rollCfg.CHANGE_CONTRACT_START_TIME_FOR_NORMAL,
                                      rollCfg.CHANGE_CONTRACT_END_TIME_FOR_NORMAL):
                self.timeLog("当前处于移仓时间，程序进入睡眠状态……")
                time.sleep(60)
                continue

            if self.timeInterval > 0:
                self.timeLog("等待 %d 秒进入下一个循环..." % self.timeInterval)
                time.sleep(self.timeInterval)

            self.order_info_list = []

            # 获取账户持仓信息
            try:
                account = copy.deepcopy(self.account_info)
                acct_info = account["account_info"]
                account_update_time = account["time"]
            except Exception:
                self.timeLog("尚未取得账户信息")
                continue

            # 检查账户获取时间
            if account_update_time < self.latest_trade_time:
                self.timeLog("当前账户信息时间晚于最近交易时间，需要重新获取")
                continue

            # setup initial account info
            if self.initial_acct_info is None:
                self.initial_acct_info = acct_info

            short_pos_money_delta = acct_info["bitvc_btc_hold_money_week_short"] - self.initial_acct_info["bitvc_btc_hold_money_week_short"]
            long_pos_money_delta = acct_info["bitvc_btc_hold_money_week_long"] - self.initial_acct_info["bitvc_btc_hold_money_week_long"]
            self.remaining_delta_cash = long_pos_money_delta - short_pos_money_delta  # 代表着增加了多少开多的money，需要减去（sell）
            if self.remaining_delta_cash != 0:
                self.timeLog("剩余 %.4f 数量还没有平" % self.remaining_delta_cash)

            # 查询bitvc深度数据
            try:
                bitvcDepth = copy.deepcopy(self.depth_data)["bitvc"]
            except Exception:
                self.timeLog("尚未取得bitvc深度数据")
                continue

            # 查看行情信息时间戳是否合理
            timestamp_list = [bitvcDepth["time"]]
            if not self.check_time(timestamp_list):
                self.timeLog("获取的行情信息时间延迟过大，被舍弃，进入下一循环")
                continue

            self.timeLog("记录心跳信息...")
            self.heart_beat_time.value = time.time()

            asks = bitvcDepth["asks"]
            bids = bitvcDepth["bids"]
            bitvc_sell_1_price = float(asks[len(asks) - 1][0])
            bitvc_buy_1_price = float(bids[0][0])
            margin = bitvc_sell_1_price - bitvc_buy_1_price

            future_order_sell_price = bitvc_sell_1_price - 0.5*margin*self.sell_cut
            future_order_buy_price = bitvc_buy_1_price + 0.5*margin*self.buy_cut

            future_order_sell_money = 100
            future_order_buy_money = 100

            if self.remaining_delta_cash > 0: #bought too much
                future_order_sell_money += self.remaining_delta_cash
                future_order_sell_price -= 0.2*margin*self.sell_cut
                future_order_buy_price -= 0.1*margin*self.buy_cut

            else:
                future_order_buy_money += abs(self.remaining_delta_cash)
                future_order_buy_price += 0.2*margin*self.buy_cut
                future_order_sell_price += 0.1*margin*self.sell_cut

            diff_percentage = (future_order_sell_price - future_order_buy_price)/future_order_sell_price

            if diff_percentage < self.trade_threshold:
                self.timeLog("future_order_sell_price: %.2f, future_order_buy_price: %.2f, diff percentage: %.6f%% smaller than trade threshold: %.6f%%, so ignore and continue" % ( future_order_sell_price, future_order_buy_price, diff_percentage*100, self.trade_threshold*100))
                continue

            bitvc_btc_hold_money_week_long = acct_info["bitvc_btc_hold_money_week_long"]
            bitvc_btc_hold_money_week_short = acct_info["bitvc_btc_hold_money_week_short"]

            global sold_money
            sold_money = 0
            global bought_money
            bought_money = 0

            # 策略下单参数
            coin_type = self.coin_type
            contract_type = self.contract_type

            def loop1():
                # place sell order
                order_id_list_sell = []
                if bitvc_btc_hold_money_week_long > future_order_sell_money:
                    order_id_list_sell.append(self.bitvc_order(coin_type, contract_type, helper.CONTRACT_ORDER_TYPE_CLOSE, helper.CONTRACT_TRADE_TYPE_SELL, future_order_sell_price, future_order_sell_money, leverage=self.leverage))
                else:
                    if bitvc_btc_hold_money_week_long > 0:
                        order_id_list_sell.append(self.bitvc_order(coin_type, contract_type, helper.CONTRACT_ORDER_TYPE_CLOSE, helper.CONTRACT_TRADE_TYPE_SELL, future_order_sell_price, bitvc_btc_hold_money_week_long, leverage=self.leverage))
                    if future_order_sell_money-bitvc_btc_hold_money_week_long > 0:
                        order_id_list_sell.append(self.bitvc_order(coin_type, contract_type, helper.CONTRACT_ORDER_TYPE_OPEN, helper.CONTRACT_TRADE_TYPE_SELL, future_order_sell_price, future_order_sell_money-bitvc_btc_hold_money_week_long, leverage=self.leverage))
                if self.remaining_delta_cash > 0:
                    bitvc_order_query_retry_maximum_times = 100
                    bitvc_order_cancel_query_retry_maximum_times = 10
                else:
                    bitvc_order_query_retry_maximum_times = 100
                    bitvc_order_cancel_query_retry_maximum_times = 10
                global sold_money
                for order_id in order_id_list_sell:
                    if order_id is not None:
                        tmp = self.bitvc_order_wait_and_cancel(coin_type, contract_type, order_id, returnProcessedMoney=True, bitvc_order_query_retry_maximum_times=bitvc_order_query_retry_maximum_times, bitvc_order_cancel_query_retry_maximum_times=bitvc_order_cancel_query_retry_maximum_times)
                        if tmp is not None:
                            sold_money += tmp
                order_id_list_sell = []
                if sold_money < future_order_sell_money and bought_money > 0: # buy side is partially filled or filled
                    adjusted_future_order_sell_price = future_order_buy_price * (1 + 0.0003)
                    adjusted_future_order_sell_money = future_order_sell_money - sold_money
                    if bitvc_btc_hold_money_week_long - sold_money > adjusted_future_order_sell_money:
                        order_id_list_sell.append(self.bitvc_order(coin_type, contract_type, helper.CONTRACT_ORDER_TYPE_CLOSE, helper.CONTRACT_TRADE_TYPE_SELL, adjusted_future_order_sell_price, adjusted_future_order_sell_money, leverage=self.leverage))
                    else:
                        if bitvc_btc_hold_money_week_long - sold_money > 0:
                            order_id_list_sell.append(self.bitvc_order(coin_type, contract_type, helper.CONTRACT_ORDER_TYPE_CLOSE, helper.CONTRACT_TRADE_TYPE_SELL, adjusted_future_order_sell_price, bitvc_btc_hold_money_week_long - sold_money, leverage=self.leverage))
                        if bitvc_btc_hold_money_week_long - sold_money < 0:
                            #already opened short
                            remaining_short = adjusted_future_order_sell_money
                        else:
                            remaining_short = adjusted_future_order_sell_money - (bitvc_btc_hold_money_week_long - sold_money)
                        if remaining_short > 0:
                            order_id_list_sell.append(self.bitvc_order(coin_type, contract_type, helper.CONTRACT_ORDER_TYPE_OPEN, helper.CONTRACT_TRADE_TYPE_SELL, adjusted_future_order_sell_price, remaining_short, leverage=self.leverage))
                for order_id in order_id_list_sell:
                    if order_id is not None:
                        tmp = self.bitvc_order_wait_and_cancel(coin_type, contract_type, order_id, returnProcessedMoney=True, bitvc_order_query_retry_maximum_times=bitvc_order_query_retry_maximum_times, bitvc_order_cancel_query_retry_maximum_times=bitvc_order_cancel_query_retry_maximum_times)
                        if tmp is not None:
                            sold_money += tmp

            def loop2():
                # place buy order
                order_id_list_buy = []
                if bitvc_btc_hold_money_week_short > future_order_buy_money:
                    order_id_list_buy.append(self.bitvc_order(coin_type, contract_type, helper.CONTRACT_ORDER_TYPE_CLOSE, helper.CONTRACT_TRADE_TYPE_BUY, future_order_buy_price, future_order_buy_money, leverage=self.leverage))
                else:
                    if bitvc_btc_hold_money_week_short > 0:
                        order_id_list_buy.append(self.bitvc_order(coin_type, contract_type, helper.CONTRACT_ORDER_TYPE_CLOSE, helper.CONTRACT_TRADE_TYPE_BUY, future_order_buy_price, bitvc_btc_hold_money_week_short, leverage=self.leverage))
                    if future_order_buy_money-bitvc_btc_hold_money_week_short > 0:
                        order_id_list_buy.append(self.bitvc_order(coin_type, contract_type, helper.CONTRACT_ORDER_TYPE_OPEN, helper.CONTRACT_TRADE_TYPE_BUY, future_order_buy_price, future_order_buy_money-bitvc_btc_hold_money_week_short, leverage=self.leverage))
                if self.remaining_delta_cash < 0:
                    bitvc_order_query_retry_maximum_times = 100
                    bitvc_order_cancel_query_retry_maximum_times = 10
                else:
                    bitvc_order_query_retry_maximum_times = 100
                    bitvc_order_cancel_query_retry_maximum_times = 10
                global bought_money
                for order_id in order_id_list_buy:
                    if order_id is not None:
                        tmp = self.bitvc_order_wait_and_cancel(coin_type, contract_type, order_id, returnProcessedMoney=True, bitvc_order_query_retry_maximum_times=bitvc_order_query_retry_maximum_times, bitvc_order_cancel_query_retry_maximum_times=bitvc_order_cancel_query_retry_maximum_times)
                        if tmp is not None:
                            bought_money += tmp
                order_id_list_buy = []
                if bought_money < future_order_buy_money and sold_money > 0: # sell side is partially filled or filled
                    adjusted_future_order_buy_price = future_order_sell_price * (1 - 0.0003)
                    adjusted_future_order_buy_money = future_order_buy_money - bought_money
                    if bitvc_btc_hold_money_week_short - bought_money > adjusted_future_order_buy_money:
                        order_id_list_buy.append(self.bitvc_order(coin_type, contract_type, helper.CONTRACT_ORDER_TYPE_CLOSE, helper.CONTRACT_TRADE_TYPE_BUY, adjusted_future_order_buy_price, adjusted_future_order_buy_money, leverage=self.leverage))
                    else:
                        if bitvc_btc_hold_money_week_short - bought_money > 0:
                            order_id_list_buy.append(self.bitvc_order(coin_type, contract_type, helper.CONTRACT_ORDER_TYPE_CLOSE, helper.CONTRACT_TRADE_TYPE_BUY, adjusted_future_order_buy_price, bitvc_btc_hold_money_week_short - bought_money, leverage=self.leverage))
                        if bitvc_btc_hold_money_week_short - bought_money < 0:
                            # already opened long
                            remaining_long = adjusted_future_order_buy_money
                        else:
                            remaining_long = adjusted_future_order_buy_money - (bitvc_btc_hold_money_week_short - bought_money)
                        if remaining_long > 0:
                            order_id_list_buy.append(self.bitvc_order(coin_type, contract_type, helper.CONTRACT_ORDER_TYPE_OPEN, helper.CONTRACT_TRADE_TYPE_BUY, adjusted_future_order_buy_price, remaining_long, leverage=self.leverage))
                for order_id in order_id_list_buy:
                    if order_id is not None:
                        tmp = self.bitvc_order_wait_and_cancel(coin_type, contract_type, order_id, returnProcessedMoney=True, bitvc_order_query_retry_maximum_times=bitvc_order_query_retry_maximum_times, bitvc_order_cancel_query_retry_maximum_times=bitvc_order_cancel_query_retry_maximum_times)
                        if tmp is not None:
                            bought_money += tmp

            t1 = threading.Thread(target=loop1, name='LoopThread1')
            t2 = threading.Thread(target=loop2, name='LoopThread2')
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            if len(self.order_info_list) > 0:
                transaction_id = helper.getUUID()
                for order_info in self.order_info_list:
                    coinType = self.coinMarketType
                    marketType = order_info["marketType"]
                    order_id = order_info["order_id"]
                    self.put_order_info_in_queue(coinType, marketType, order_id, transaction_id)

            self.cancel_pending_orders()
            self.latest_trade_time = time.time()


##################################################################################
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from signalGenerator.futureSpotArb import *
from signalGenerator.strategyConfig import changeFutureContractConfig as rollCfg
import time

class ChangeFutureContract(FutureSpotArb):
    def __init__(self, startRunningTime, orderRatio, timeInterval, orderWaitingTime,
                 coinMarketType, open_diff, close_diff, heart_beat_time, depth_data, account_info, transaction_info, maximum_qty_multiplier=None,
                 dailyExitTime=None):
        super(ChangeFutureContract, self).__init__(startRunningTime, orderRatio, timeInterval, orderWaitingTime,
                 coinMarketType, open_diff, close_diff, heart_beat_time, depth_data, account_info, transaction_info, maximum_qty_multiplier=maximum_qty_multiplier,
                 dailyExitTime=dailyExitTime)

        self.strat_name = "合约滚动-%s" % startRunningTime.strftime("%Y%m%d_%H%M%S")

        self.change_contract_diff = rollCfg.CHANGE_CONTRACT_DIFF_1
        self.initial_acct_info = None
        self.coin_type = rollCfg.COIN_TYPE

        self.is_short_contract = None

    # 计算当前的换合约需要满足的价差比例
    def current_change_contract_diff(self, current_time):
        if self.in_time_period(current_time, rollCfg.CHANGE_CONTRACT_START_WEEK_DAY_STAGE_1,
                               rollCfg.CHANGE_CONTRACT_END_WEEK_DAY_STAGE_1, rollCfg.CHANGE_CONTRACT_START_TIME_STAGE_1,
                               rollCfg.CHANGE_CONTRACT_END_TIME_STAGE_1):
            return rollCfg.CHANGE_CONTRACT_DIFF_1
        elif self.in_time_period(current_time, rollCfg.CHANGE_CONTRACT_START_WEEK_DAY_STAGE_2,
                               rollCfg.CHANGE_CONTRACT_END_WEEK_DAY_STAGE_2, rollCfg.CHANGE_CONTRACT_START_TIME_STAGE_2,
                               rollCfg.CHANGE_CONTRACT_END_TIME_STAGE_2):
            return rollCfg.CHANGE_CONTRACT_DIFF_2
        elif self.in_time_period(current_time, rollCfg.CHANGE_CONTRACT_START_WEEK_DAY_STAGE_3,
                               rollCfg.CHANGE_CONTRACT_END_WEEK_DAY_STAGE_3, rollCfg.CHANGE_CONTRACT_START_TIME_STAGE_3,
                               rollCfg.CHANGE_CONTRACT_END_TIME_STAGE_3):
            return rollCfg.CHANGE_CONTRACT_DIFF_3
        elif self.in_time_period(current_time, rollCfg.CHANGE_CONTRACT_START_WEEK_DAY_STAGE_4,
                               rollCfg.CHANGE_CONTRACT_END_WEEK_DAY_STAGE_4, rollCfg.CHANGE_CONTRACT_START_TIME_STAGE_4,
                               rollCfg.CHANGE_CONTRACT_END_TIME_STAGE_4):
            return rollCfg.CHANGE_CONTRACT_DIFF_4
        else:
            return None

    # 计算盘口满足价差的深度数量
    def qty_and_price(self, buy_side_data, sell_side_data, price_diff):
        max_qty = 0
        buy_current_depth = 0
        sell_current_depth = 0
        buy_limit_price = None
        sell_limit_price = None

        buy_price = float(buy_side_data[buy_current_depth][0])
        sell_price = float(sell_side_data[sell_current_depth][0])
        buy_qty = float(buy_side_data[buy_current_depth][1])
        sell_qty = float(sell_side_data[sell_current_depth][1])

        while sell_price - buy_price >= price_diff:
            buy_limit_price = buy_price
            sell_limit_price = sell_price
            # 数量少的一方，深度+1
            if buy_qty > sell_qty:
                max_qty = sell_qty
                sell_current_depth += 1
                sell_qty += float(sell_side_data[sell_current_depth][1])
            else:
                max_qty = buy_qty
                buy_current_depth += 1
                buy_qty += float(buy_side_data[buy_current_depth][1])
            if buy_current_depth >= len(buy_side_data) or sell_current_depth >= len(sell_side_data):
                break
            buy_price = float(buy_side_data[buy_current_depth][0])
            sell_price = float(sell_side_data[sell_current_depth][0])
        self.timeLog("盘口数量为:%s, buy：%s， sell：%s" % (max_qty, buy_limit_price, sell_limit_price))
        return max_qty, buy_limit_price, sell_limit_price

    # cancel all pending orders
    def cancel_pending_orders(self, contract_type):
        orders = self.BitVCService.order_list(self.coin_type, contract_type)
        while orders is not None and len(componentExtract(orders, contract_type, [])) > 0:
            orders = componentExtract(orders, contract_type, [])
            for order in orders:
                if componentExtract(order, u"id", "") != "":
                    order_id = order[u"id"]
                    self.BitVCService.order_cancel(self.coin_type, contract_type, order_id)
            orders = self.BitVCService.order_list(self.coin_type, contract_type)

    def cancel_all_pending_orders(self):
        self.cancel_pending_orders(helper.CONTRACT_TYPE_WEEK)
        self.cancel_pending_orders(helper.CONTRACT_TYPE_NEXT_WEEK)
        self.latest_trade_time = time.time()

    def go(self):
        self.timeLog("日志启动于 %s" % self.getStartRunningTime().strftime(self.TimeFormatForLog))
        self.timeLog("开始cancel pending orders")
        self.cancel_all_pending_orders()
        self.timeLog("完成cancel pending orders")

        while True:
            # 非换期货时间，程序一直sleep
            if not self.in_time_period(datetime.datetime.now(), rollCfg.CHANGE_CONTRACT_START_WEEK_DAY,
                                      rollCfg.CHANGE_CONTRACT_END_WEEK_DAY, rollCfg.CHANGE_CONTRACT_START_TIME,
                                      rollCfg.CHANGE_CONTRACT_END_TIME):
                self.timeLog("当前处于非移仓时间，程序进入睡眠状态……")
                time.sleep(60)
                continue

            if self.timeInterval > 0:
                self.timeLog("等待 %d 秒进入下一个循环..." % self.timeInterval)
                time.sleep(self.timeInterval)

            # 重置部分self级别变量
            self.order_info_list = []
            self.change_contract_diff = self.current_change_contract_diff(datetime.datetime.now())

            # 查询bitvc深度数据
            try:
                bitvc_week_depth = copy.deepcopy(self.depth_data)["bitvc"]
                bitvc_next_week_depth = copy.deepcopy(self.depth_data)["bitvc_next_week"]
            except Exception:
                self.timeLog("尚未取得bitvc深度数据")
                continue
            # 查看行情信息时间戳是否合理
            timestamp_list = [bitvc_week_depth["time"], bitvc_next_week_depth["time"]]
            if not self.check_time(timestamp_list):
                self.timeLog("获取的行情信息时间延迟过大，被舍弃，进入下一循环")
                continue

            bitvc_week_depth["asks"].reverse()
            bitvc_week_sell = bitvc_week_depth["asks"]
            bitvc_next_week_buy = bitvc_next_week_depth["bids"]
            bitvc_week_buy = bitvc_week_depth["bids"]
            bitvc_next_week_depth["asks"].reverse()
            bitvc_next_week_sell = bitvc_next_week_depth["asks"]

            # 本周合约：买入平仓(看卖1)， 下周合约：卖出开仓（看买1）
            bitvc_week_sell_1 = float(bitvc_week_sell[0][0])
            bitvc_next_week_buy_1 = float(bitvc_next_week_buy[0][0])
            bitvc_week_buy_1 = float(bitvc_week_buy[0][0])
            bitvc_next_week_sell_1 = float(bitvc_next_week_sell[0][0])
            market_price = np.mean([bitvc_week_sell_1, bitvc_next_week_buy_1, bitvc_week_buy_1, bitvc_next_week_sell_1])
            price_diff = self.change_contract_diff * market_price

            try:
                account = copy.deepcopy(self.account_info)
                accountInfo = account["account_info"]
                account_update_time = account["time"]
            except Exception:
                self.timeLog("尚未取得账户信息")
                continue
            # 检查账户获取时间
            if account_update_time < self.latest_trade_time:
                self.timeLog("当前账户信息时间晚于最近交易时间，需要重新获取")
                continue

            accountInfo = self.update_bitvc_account_info(accountInfo, market_price)

            self.timeLog("记录心跳信息...")
            self.heart_beat_time.value = time.time()

            self.timeLog("换空头合约价差：%.2f, 换多头合约价差：%.2f。 当前信号价差：%.2f" % (bitvc_next_week_buy_1-bitvc_week_sell_1, bitvc_week_buy_1-bitvc_next_week_sell_1, price_diff))

            # setup initial account info
            if self.initial_acct_info is None:
                self.initial_acct_info = accountInfo
            print(self.initial_acct_info["bitvc_btc_hold_quantity_week_short"])
            # 判断合约的方向
            if self.is_short_contract is None:
                if self.initial_acct_info["bitvc_btc_hold_quantity_week_short"] > 0:
                    self.is_short_contract = True
                elif self.initial_acct_info["bitvc_btc_hold_quantity_week_long"] > 0:
                    self.is_short_contract = False

            # 空头合约，本周买入平仓，下周开空仓
            if self.is_short_contract:
                print("short")
                buy_side = bitvc_week_sell
                sell_side = bitvc_next_week_buy
                week_decreased = self.initial_acct_info["bitvc_btc_hold_quantity_week_short"] - \
                                 accountInfo["bitvc_btc_hold_quantity_week_short"]
                next_week_increased = accountInfo["bitvc_btc_hold_quantity_next_week_short"] - \
                                      self.initial_acct_info["bitvc_btc_hold_quantity_next_week_short"]
                # 本周合约剩余的money，按市场价折算成可成交数量
                week_remaining_qty = accountInfo["bitvc_btc_hold_money_week_short"] / market_price
                week_trade_type = helper.CONTRACT_TRADE_TYPE_BUY
                next_week_trade_type = helper.CONTRACT_TRADE_TYPE_SELL
                week_contract_avg_price = accountInfo["bitvc_btc_hold_price_week_short"]
            else:
                buy_side = bitvc_next_week_sell
                sell_side = bitvc_week_buy
                week_decreased = self.initial_acct_info["bitvc_btc_hold_quantity_week_long"] - \
                                 accountInfo["bitvc_btc_hold_quantity_week_long"]
                next_week_increased = accountInfo["bitvc_btc_hold_quantity_next_week_long"] - \
                                      self.initial_acct_info["bitvc_btc_hold_quantity_next_week_long"]
                # 本周合约剩余的money，按市场价折算成可成交数量
                week_remaining_qty = accountInfo["bitvc_btc_hold_money_week_long"] / market_price
                week_trade_type = helper.CONTRACT_TRADE_TYPE_SELL
                next_week_trade_type = helper.CONTRACT_TRADE_TYPE_BUY
                week_contract_avg_price = accountInfo["bitvc_btc_hold_price_week_long"]

            week_order_type = helper.CONTRACT_ORDER_TYPE_CLOSE
            next_week_order_type = helper.CONTRACT_ORDER_TYPE_OPEN

            max_qty, buy_limit_price, sell_limit_price = self.qty_and_price(buy_side, sell_side, price_diff)
            if max_qty is None:
                continue
            if self.is_short_contract:
                week_order_price = buy_limit_price
                next_week_order_price = sell_limit_price
            else:
                week_order_price = sell_limit_price
                next_week_order_price = buy_limit_price

            # qty_delta > 0, 说明本周合约买入的比下周合约成交的多，下一次挂单，下周合约多成交一些
            qty_delta = week_decreased - next_week_increased
            if week_remaining_qty == 0 and abs(qty_delta) * next_week_order_price < self.bitvc_min_cash_amount:
                continue

            # 最多平掉本周合约的全部
            qty = min(max_qty, week_remaining_qty)

            qty_week = qty
            cash_amount_week = qty_week * week_order_price
            order_id_week = self.bitvc_order(self.coin_type, helper.CONTRACT_TYPE_WEEK,
                                                 week_order_type, week_trade_type, week_order_price,
                                                 cash_amount_week, leverage=self.lever)
            executed_qty_week = self.bitvc_order_wait_and_cancel(self.coin_type, CONTRACT_TYPE_WEEK,
                                                                     order_id_week)
            if executed_qty_week is None:
                executed_qty_week = 0
            if week_contract_avg_price != 0:
                executed_qty_week = executed_qty_week * week_order_price / week_contract_avg_price
            else:
                executed_qty_week = 0
            qty_next_week = min(executed_qty_week + qty_delta,
                                     accountInfo["bitvc_btc_available_margin"] * self.lever)
            cash_amount_next_week = qty_next_week * next_week_order_price
            order_id_next_week = self.bitvc_order(self.coin_type, helper.CONTRACT_TYPE_NEXT_WEEK,
                                                       next_week_order_type, next_week_trade_type,
                                                  next_week_order_price, cash_amount_next_week,
                                                       leverage=self.lever)
            self.bitvc_order_wait_and_cancel(self.coin_type, helper.CONTRACT_TYPE_NEXT_WEEK,
                                             order_id_next_week)
            self.cancel_all_pending_orders()