from logging import INFO
import traceback
import importlib
import os
from time import sleep
from typing import List, Dict, Set, Callable, Any, Type
from collections import defaultdict
from copy import copy
from pathlib import Path
from datetime import datetime, timedelta
import math

from myEvent import EventEngine, Event, EVENT_TICK, EVENT_POSITION, EVENT_CONTRACT, EVENT_ACCOUNT, EVENT_LOG, EVENT_ORDER, EVENT_TRADE, EVENT_TIMER
from myConverter import OffsetConverter
from myUtility import load_json, save_json
from myObject import (
    TickData, ContractData, LogData, CancelRequest, PositionData,
    SubscribeRequest, OrderRequest, MarginAccountData, FuturesAccountData
)
from myConstant import (
    Direction, Offset, OrderType, Interval, EVENT_ACCOUNT_MARGIN, EVENT_ACCOUNT_FUTURES, Exchange, EVENT_BORROW_MONEY
)
from myGateway import BaseGateway

from .base import (
    LegData, SpreadData
)
from .template import SpreadAlgoTemplate
from .algo import SpreadTakerAlgo

algo_class_dict = {}
algo_class_dict['FuturesSpotSpread'] = SpreadTakerAlgo

class SpreadEngine(object):
    """"""

    def __init__(self, event_engine: EventEngine, setting_filename:str):
        """Constructor"""
        self.active = False

        self.event_engine = event_engine
        self.setting_filename = setting_filename

        self.gateways = {}
        self.exchanges = []

        self.algo_engine: SpreadAlgoEngine = SpreadAlgoEngine(self)

        self.event_engine.start()

        self.spreads = {}
        self.symbol_spread_map: Dict[str, List[SpreadData]] = defaultdict(list)
        self.legs = {}

    def start(self):
        """"""
        if self.active:
            return
        self.active = True

        self.load_setting()

        self.algo_engine.start()

    def stop(self):
        """"""
        self.algo_engine.stop()

    def load_setting(self) -> None:
        """"""
        setting = load_json(self.setting_filename)

        for spread_setting in setting:
            self.add_spread(
                spread_setting["name"],
                spread_setting["algo_name"],
                spread_setting["leg_settings"],
                spread_setting["active_symbol"],
                spread_setting.get("min_volume", 1),
                spread_setting["buy_price"],
                spread_setting["sell_price"],
                spread_setting["cover_price"],
                spread_setting["short_price"],
                spread_setting["max_pos"],
                spread_setting["lot_size"],
                spread_setting["payup"]
            )

    def add_spread(
        self,
        name: str,
        algo_name: str,
        leg_settings: List[Dict],
        active_symbol: str,
        min_volume: float,
        buy_price: float,
        sell_price: float,
        cover_price: float,
        short_price: float,
        max_pos: float,
        lot_size: float,
        payup: float
    ) -> None:
        """"""
        if name in self.spreads:
            self.write_log("价差创建失败，名称重复：{}".format(name))
            return

        legs: List[LegData] = []
        price_multipliers: Dict[str, int] = {}
        trading_multipliers: Dict[str, int] = {}
        inverse_contracts: Dict[str, bool] = {}

        for leg_setting in leg_settings:
            vt_symbol = leg_setting["vt_symbol"]
            leg = self.get_leg(vt_symbol)
            # update_position
            pos = PositionData(
                gateway_name='',
                symbol='',
                exchange=Exchange.LOCAL,
                direction=Direction.NET,
                volume=leg_setting.get("update_pos", 0),
                price = 0
            )
            leg.update_position(pos)

            legs.append(leg)
            price_multipliers[vt_symbol] = leg_setting["price_multiplier"]
            trading_multipliers[vt_symbol] = leg_setting["trading_multiplier"]
            inverse_contracts[vt_symbol] = leg_setting.get(
                "inverse_contract", False)

        spread = SpreadData(
            name,
            algo_name,
            legs,
            price_multipliers,
            trading_multipliers,
            active_symbol,
            inverse_contracts,
            min_volume,
            buy_price,
            sell_price,
            cover_price,
            short_price,
            max_pos,
            lot_size,
            payup
        )
        spread.calculate_pos()
        self.spreads[name] = spread

        for leg in spread.legs.values():
            self.symbol_spread_map[leg.vt_symbol].append(spread)

        msg = f"价差创建成功：{spread.name}, net_pos: {spread.net_pos}"
        self.write_log(msg)
        
        self.algo_engine.start_algo(spread)

    def get_leg(self, vt_symbol: str) -> LegData:
        """"""
        leg = self.legs.get(vt_symbol, None)
        if not leg:
            leg = LegData(vt_symbol)
            self.legs[vt_symbol] = leg

            # Subscribe market data
            contract = self.algo_engine.get_contract(vt_symbol)
            if contract:
                leg.update_contract(contract)

                req = SubscribeRequest(
                    contract.symbol,
                    contract.exchange
                )
                self.subscribe(req, contract.gateway_name)

            # Initialize leg position
            # for direction in Direction:
            #     vt_positionid = f"{vt_symbol}.{direction.value}"
            #     position = self.algo_engine.get_position(vt_positionid)

            #     if position:
            #         leg.update_position(position)

        return leg

    def write_log(self, msg: str, level=INFO):
        """"""
        log = LogData(
            msg=msg,
            level=level,
            gateway_name = "SpreadTrading"
        )
        event = Event(EVENT_LOG, log)
        self.event_engine.put(event)

    def subscribe(self, req: SubscribeRequest, gateway_name: str):
        """
        Subscribe tick data update of a specific gateway.
        """
        gateway = self.get_gateway(gateway_name)
        if gateway:
            gateway.subscribe(req)

    def send_order(self, req: OrderRequest, gateway_name: str):
        """
        Send new order request to a specific gateway.
        """
        gateway = self.get_gateway(gateway_name)
        if gateway:
            return gateway.send_order(req)
        else:
            return ""

    def cancel_order(self, req: CancelRequest, gateway_name: str):
        """
        Send cancel order request to a specific gateway.
        """
        gateway = self.get_gateway(gateway_name)
        if gateway:
            gateway.cancel_order(req)

    def add_gateway(self, gateway_class: Type[BaseGateway]):
        """
        Add gateway.
        """
        gateway = gateway_class(self.event_engine)
        self.gateways[gateway.gateway_name] = gateway
        print( self.gateways)
        # Add gateway supported exchanges into engine
        for exchange in gateway.exchanges:
            if exchange not in self.exchanges:
                self.exchanges.append(exchange)

        return gateway

    def get_gateway(self, gateway_name: str):
        """
        Return gateway object by name.
        """
        gateway = self.gateways.get(gateway_name, None)
        if not gateway:
            self.write_log(f"找不到底层接口：{gateway_name}")
        return gateway

    def connect(self, setting: dict, gateway_name: str):
        """
        Start connection of a specific gateway.
        """
        gateway = self.get_gateway(gateway_name)
        if gateway:
            gateway.connect(setting)

    def repay(self, asset, amount, gateway_name):
        gateway = self.get_gateway(gateway_name)
        gateway.repay_money(asset, amount)


class SpreadAlgoEngine:
    """"""
    def __init__(self, spread_engine: SpreadEngine):
        """"""
        self.spread_engine: SpreadEngine = spread_engine
        self.event_engine: EventEngine = spread_engine.event_engine

        self.write_log = spread_engine.write_log

        self.algos: Dict[str: SpreadAlgoTemplate] = {}

        self.order_algo_map: Dict[str: SpreadAlgoTemplate] = {}
        self.symbol_algo_map: Dict[str: SpreadAlgoTemplate] = defaultdict(list)

        self.algo_count: int = 0
        self.vt_tradeids: Set = set()

        self.offset_converter: OffsetConverter = OffsetConverter(self)

        self.ticks = {}
        self.orders = {}
        self.trades = {}
        # self.positions = {}
        self.margin_accounts: Dict[str, MarginAccountData] = {}
        self.contracts = {}
        self.borrowmoneys: Dict[str, List] = defaultdict(list)

        self.timer_count = 0

    def start(self):
        """"""
        self.register_event()

        self.write_log("价差算法引擎启动成功")

    def stop(self):
        """"""
        for algo in self.algos.values():
            self.stop_algo(algo)

    def register_event(self):
        """"""
        self.event_engine.register(EVENT_ORDER, self.process_order_event)
        self.event_engine.register(EVENT_TIMER, self.process_timer_event)
        self.event_engine.register(EVENT_TICK, self.process_tick_event)
        self.event_engine.register(EVENT_TRADE, self.process_trade_event)
        # self.event_engine.register(EVENT_POSITION, self.process_position_event)
        self.event_engine.register(EVENT_CONTRACT, self.process_contract_event)
        # self.event_engine.register(EVENT_TIMER, self.process_timer_event)
        # self.event_engine.register(EVENT_BORROW_MONEY, self.process_borrowmoney_event)
        self.event_engine.register(EVENT_ACCOUNT_MARGIN, self.process_account_margin_event)

    def process_timer_event(self, event: Event):
        buf = list(self.algos.values())

        for algo in buf:
            algo.update_timer()

        self.timer_count += 1
        if self.timer_count > 1800:
            self.timer_count = 0
            for spread in self.spread_engine.spreads.values():
                d = dict()
                for leg in spread.legs.values():
                    d[leg.vt_symbol] = leg.last_price

                timer_msg = "TIMER CHECK %s %s: %s, spead_pos: %s, active_leg_net_pos: %s, passive_leg_net_pos: %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), spread.name, d, spread.net_pos, spread.active_leg.net_pos, spread.passive_leg.net_pos)
                self.write_log(timer_msg)

    def process_tick_event(self, event: Event) -> None:
        """"""
        tick = event.data
        leg = self.spread_engine.legs.get(tick.vt_symbol, None)
        if not leg:
            return
        leg.update_tick(tick)
        for spread in self.spread_engine.symbol_spread_map[tick.vt_symbol]:
            spread.calculate_price()
        
        self.process_tick(tick)

    # def process_position_event(self, event: Event) -> None:
    #     """"""
    #     position = event.data

    #     self.offset_converter.update_position(position)

    #     self.positions[position.vt_positionid] = position

    #     leg = self.spread_engine.legs.get(position.vt_symbol, None)
    #     if not leg:
    #         return
    #     leg.update_position(position)

    #     for spread in self.spread_engine.symbol_spread_map[position.vt_symbol]:
    #         spread.calculate_pos()

    def process_trade_event(self, event: Event) -> None:
        """"""
        trade = event.data
        if trade.vt_tradeid in self.vt_tradeids:
            return
        self.vt_tradeids.add(trade.vt_tradeid)

        algo = self.order_algo_map.get(trade.vt_orderid, None)
        # print("process_trade_event(algo engine)>>>>vt_orderid: %s" % trade.vt_orderid)
        # if algo:
        #     print('process_trade_event(algo engine) %s status: %s' % (algo.algoid, algo.status))
        if algo:
            self.offset_converter.update_trade(trade)

            leg = self.spread_engine.legs.get(trade.vt_symbol, None)

            leg.update_trade(trade)
            
            algo.spread.calculate_pos()
            # print("process_trade_event(algo engine)>>>> algo.is_active:%s" % algo.is_active())
            algo.update_trade(trade)

    def process_order_event(self, event: Event):
        """"""
        order = event.data

        algo = self.order_algo_map.get(order.vt_orderid, None)
        if algo:
            self.offset_converter.update_order(order)
            algo.update_order(order)
            self.orders[order.vt_orderid] = order


    def process_contract_event(self, event: Event) -> None:
        """"""
        contract = event.data
        self.contracts[contract.vt_symbol] = contract

        leg = self.spread_engine.legs.get(contract.vt_symbol, None)

        if leg:
            # Update contract data
            leg.update_contract(contract)
            print(contract.symbol, contract.exchange)
            req = SubscribeRequest(
                contract.symbol, contract.exchange
            )
            sleep(3)
            self.spread_engine.subscribe(req, contract.gateway_name)
            self.write_log('subscribe>>>>>>>>>>>>>>>>>>>:%s' % leg.vt_symbol)

    def process_borrowmoney_event(self, event: Event) ->None:
        # borrowmoney_dict = event.data
        # # print(borrowmoney_dict)
        # vt_symbol = borrowmoney_dict['borrow_asset'] + "USDT." + borrowmoney_dict['borrow_exchange'].value
        # leg = self.legs.get(vt_symbol, None)
        # if not leg:
        #     return
        # self.borrowmoneys[vt_symbol].append([borrowmoney_dict['datetime'], borrowmoney_dict['borrow_amount']])
        pass

    def process_account_margin_event(self, event: Event):
        # print(">>>>>>>>process_account_margin_event")
        # 根据self.borrowmoneys 检查是否需要还款
        margin_account_data = event.data
        leg = self.spread_engine.legs.get(margin_account_data.vt_symbol, None)
        if not leg:
            return

        dt_now = datetime.now()
        
        # if margin_account_data.vt_symbol not in self.borrowmoneys and margin_account_data.borrowed:
        #     self.borrowmoneys[margin_account_data.vt_symbol].append([dt_now, margin_account_data.borrowed])
        if dt_now.minute >= 55 and (dt_now.hour > 21 or dt_now.hour < 12):
            if margin_account_data.borrowed > 0 and margin_account_data.free > 0:
                amount = min(margin_account_data.borrowed, margin_account_data.free)
                gateway_name = margin_account_data.exchange.value
                asset = margin_account_data.accountid

                self.spread_engine.repay(asset, amount, gateway_name)
                
                margin_account_data.borrowed -= amount
                margin_account_data.free -= amount
        self.margin_accounts[margin_account_data.vt_symbol] = margin_account_data
        # print(self.borrowmoneys)
        # print(f'{margin_account_data.vt_symbol} max borrow: {margin_account_data.max_borrow}')


    def process_tick(self, tick: TickData):
        """"""
        algos = self.symbol_algo_map[tick.vt_symbol]
        # print(algos)
        if not algos:
            return

        # buf = copy(algos)
        for algo in algos:
            algo.update_tick(tick)

    def start_algo(self, spread) -> str:
        # Generate algoid str
        algo_class = algo_class_dict[spread.algo_name]
        self.algo_count += 1
        algo_count_str = str(self.algo_count).rjust(2, "0")
        algoid = f"{spread.name}_{algo_class.algo_name}_{algo_count_str}"

        # Create algo object
        algo = algo_class(self, algoid, spread)
        self.algos[algoid] = algo

        # Generate map between vt_symbol and algo
        for leg in spread.legs.values():
            self.symbol_algo_map[leg.vt_symbol].append(algo)
        # print(self.symbol_algo_map)

        return algoid

    def stop_algo(
        self,
        algoid: str
    ):
        """"""
        algo = self.algos.get(algoid, None)
        if not algo:
            self.write_log("停止价差算法失败，找不到算法：{}".format(algoid))
            return

        algo.stop()

    def write_algo_log(self, algo: SpreadAlgoTemplate, msg: str, level=INFO) -> None:
        """"""
        msg = f"{algo.algoid}：{msg}"
        self.write_log(msg, level=level)

    def send_order(
        self,
        algo: SpreadAlgoTemplate,
        vt_symbol: str,
        price: float,
        volume: float,
        direction: Direction,
        borrowmoney=False,
        lock: bool = False
    ):
        """"""
        holding = self.offset_converter.get_position_holding(vt_symbol)

        contract = self.get_contract(vt_symbol)

        if direction == Direction.LONG:
            available = holding.short_pos - holding.short_pos_frozen
        else:
            available = holding.long_pos - holding.long_pos_frozen

        # If no position to close, just open new
        if not available:
            offset = Offset.OPEN
        # If enougth position to close, just close old
        elif volume < available:
            offset = Offset.CLOSE
        # Otherwise, just close existing position
        else:
            volume = available
            offset = Offset.CLOSE

        original_req = OrderRequest(
            symbol=contract.symbol,
            exchange=contract.exchange,
            direction=direction,
            offset=offset,
            type=OrderType.LIMIT,
            price=price,
            volume=volume,
            borrowmoney=borrowmoney
        )

        # Convert with offset converter
        req_list = self.offset_converter.convert_order_request(
            original_req, lock)

        # Send Orders
        vt_orderids = []

        for req in req_list:
            vt_orderid = self.spread_engine.send_order(req, contract.gateway_name)

            # Check if sending order successful
            if not vt_orderid:
                    continue

            vt_orderids.append(vt_orderid)

            self.offset_converter.update_order_request(req, vt_orderid)
            # Save relationship between orderid and algo.
            self.order_algo_map[vt_orderid] = algo
            # print('%s algo engine send_order vt_orderid:%s,price: %s' % (algo.algoid, vt_orderid, req.price))

        return vt_orderids

    def cancel_order(self, algo: SpreadAlgoTemplate, vt_orderid: str) -> None:
        """"""
        order = self.get_order(vt_orderid)
        if not order:
            self.write_algo_log(algo, "撤单失败，找不到委托{}".format(vt_orderid))
            return

        req = order.create_cancel_request()
        self.spread_engine.cancel_order(req, order.gateway_name)

    def get_contract(self, vt_symbol):
        """
        Get contract data by vt_symbol.
        """
        return self.contracts.get(vt_symbol, None)

    def get_order(self, vt_orderid):
        """
        Get latest order data by vt_orderid.
        """
        return self.orders.get(vt_orderid, None)

    # def get_position(self, vt_positionid):
    #     """
    #     Get latest position data by vt_positionid.
    #     """
    #     return self.positions.get(vt_positionid, None)






