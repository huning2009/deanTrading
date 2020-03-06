import traceback
import importlib
import os
from typing import List, Dict, Set, Callable, Any, Type
from collections import defaultdict
from copy import copy
from pathlib import Path
from datetime import datetime, timedelta

from myEvent import EventEngine, Event, EVENT_TICK, EVENT_POSITION, EVENT_CONTRACT, EVENT_ACCOUNT, EVENT_LOG, EVENT_ORDER, EVENT_TRADE, EVENT_TIMER

from myUtility import load_json, save_json
from myObject import (
    TickData, ContractData, LogData, CancelRequest,
    SubscribeRequest, OrderRequest, MarginAccountData, FuturesAccountData
)
from myConstant import (
    Direction, Offset, OrderType, Interval, EVENT_ACCOUNT_MARGIN, EVENT_ACCOUNT_FUTURES
)
from myGateway import BaseGateway

from .base import (
    LegData, SpreadData
)
from .template import SpreadAlgoTemplate, SpreadStrategyTemplate
from .algo import SpreadTakerAlgo

class SpreadEngine(object):
    """"""

    def __init__(self, event_engine: EventEngine):
        """Constructor"""
        self.active = False

        self.event_engine = event_engine
        
        self.gateways = {}
        self.exchanges = []

        self.data_engine: SpreadDataEngine = SpreadDataEngine(self)
        self.algo_engine: SpreadAlgoEngine = SpreadAlgoEngine(self)
        self.strategy_engine: SpreadStrategyEngine = SpreadStrategyEngine(self)

        self.add_spread = self.data_engine.add_spread
        self.remove_spread = self.data_engine.remove_spread
        self.get_spread = self.data_engine.get_spread
        self.get_all_spreads = self.data_engine.get_all_spreads
        self.get_contract = self.data_engine.get_contract
        self.get_order = self.data_engine.get_order

        self.start_algo = self.algo_engine.start_algo
        self.stop_algo = self.algo_engine.stop_algo

        self.event_engine.start()

    def start(self):
        """"""
        if self.active:
            return
        self.active = True

        self.data_engine.start()
        self.algo_engine.start()
        self.strategy_engine.start()

    def stop(self):
        """"""
        self.data_engine.stop()
        self.algo_engine.stop()
        self.strategy_engine.close()

    def write_log(self, msg: str):
        """"""
        log = LogData(
            msg=msg,
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


class SpreadDataEngine:
    """"""
    setting_filename = "spread_trading_setting.json"

    def __init__(self, spread_engine: SpreadEngine):
        """"""
        self.spread_engine: SpreadEngine = spread_engine
        self.event_engine: EventEngine = spread_engine.event_engine

        self.ticks = {}
        self.orders = {}
        self.trades = {}
        self.positions = {}
        self.accounts = {}
        self.contracts = {}

        self.legs: Dict[str, LegData] = {}          # vt_symbol: leg
        self.spreads: Dict[str, SpreadData] = {}    # name: spread
        self.symbol_spread_map: Dict[str, List[SpreadData]] = defaultdict(list)
        self.timer_count = 0

        self.write_log = spread_engine.write_log

    def start(self):
        """"""
        self.load_setting()
        self.register_event()

        self.write_log("价差数据引擎启动成功")

    def stop(self):
        """"""
        pass

    def load_setting(self) -> None:
        """"""
        setting = load_json(self.setting_filename)

        for spread_setting in setting:
            self.add_spread(
                spread_setting["name"],
                spread_setting["leg_settings"],
                spread_setting["active_symbol"],
                spread_setting.get("min_volume", 1),
                save=False
            )

    def save_setting(self) -> None:
        """"""
        setting = []

        for spread in self.spreads.values():
            leg_settings = []
            for leg in spread.legs.values():
                price_multiplier = spread.price_multipliers[leg.vt_symbol]
                trading_multiplier = spread.trading_multipliers[leg.vt_symbol]
                inverse_contract = spread.inverse_contracts[leg.vt_symbol]

                leg_setting = {
                    "vt_symbol": leg.vt_symbol,
                    "price_multiplier": price_multiplier,
                    "trading_multiplier": trading_multiplier,
                    "inverse_contract": inverse_contract
                }
                leg_settings.append(leg_setting)

            spread_setting = {
                "name": spread.name,
                "leg_settings": leg_settings,
                "active_symbol": spread.active_leg.vt_symbol,
                "min_volume": spread.min_volume
            }
            setting.append(spread_setting)

        save_json(self.setting_filename, setting)

    def register_event(self) -> None:
        """"""
        self.event_engine.register(EVENT_TICK, self.process_tick_event)
        self.event_engine.register(EVENT_TRADE, self.process_trade_event)
        self.event_engine.register(EVENT_POSITION, self.process_position_event)
        self.event_engine.register(EVENT_CONTRACT, self.process_contract_event)
        self.event_engine.register(EVENT_TIMER, self.process_timer_event)

    def process_timer_event(self, event: Event):
        self.timer_count += 1
        if self.timer_count > 1800:
            self.timer_count = 0
            for spread in self.spreads.values():
                d = dict()
                for leg in spread.legs.values():
                    d[leg.vt_symbol] = leg.last_price

                timer_msg = "TIMER CHECK %s %s: %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), spread.name, d)
                self.write_log(timer_msg)
    def process_tick_event(self, event: Event) -> None:
        """"""
        tick = event.data
        leg = self.legs.get(tick.vt_symbol, None)
        if not leg:
            return
        leg.update_tick(tick)

        for spread in self.symbol_spread_map[tick.vt_symbol]:
            spread.calculate_price()
            
        self.spread_engine.algo_engine.process_tick(tick)

    def process_position_event(self, event: Event) -> None:
        """"""
        position = event.data
        self.positions[position.vt_positionid] = position

        leg = self.legs.get(position.vt_symbol, None)
        if not leg:
            return
        leg.update_position(position)

        for spread in self.symbol_spread_map[position.vt_symbol]:
            spread.calculate_pos()
            self.spread_engine.strategy_engine.process_spread_pos(spread)

    def process_trade_event(self, event: Event) -> None:
        """"""
        trade = event.data

        leg = self.legs.get(trade.vt_symbol, None)
        if not leg:
            return
        leg.update_trade(trade)
        
        self.spread_engine.algo_engine.process_trade(trade)

        for spread in self.symbol_spread_map[trade.vt_symbol]:
            spread.calculate_pos()
            self.spread_engine.strategy_engine.process_spread_pos(spread)

        # self.spread_engine.strategy_engine.process_trade(trade)

    def process_contract_event(self, event: Event) -> None:
        """"""
        contract = event.data
        self.contracts[contract.vt_symbol] = contract

        leg = self.legs.get(contract.vt_symbol, None)

        if leg:
            # Update contract data
            leg.update_contract(contract)

            req = SubscribeRequest(
                contract.symbol, contract.exchange
            )
            self.spread_engine.subscribe(req, contract.gateway_name)
            self.write_log('subscribe>>>>>>>>>>>>>>>>>>>:%s' % leg.vt_symbol)

    def get_leg(self, vt_symbol: str) -> LegData:
        """"""
        leg = self.legs.get(vt_symbol, None)

        if not leg:
            leg = LegData(vt_symbol)
            self.legs[vt_symbol] = leg

            # Subscribe market data
            contract = self.spread_engine.get_contract(vt_symbol)
            if contract:
                leg.update_contract(contract)

                req = SubscribeRequest(
                    contract.symbol,
                    contract.exchange
                )
                self.spread_engine.subscribe(req, contract.gateway_name)

            # Initialize leg position
            for direction in Direction:
                vt_positionid = f"{vt_symbol}.{direction.value}"
                position = self.get_position(vt_positionid)

                if position:
                    leg.update_position(position)

        return leg

    def add_spread(
        self,
        name: str,
        leg_settings: List[Dict],
        active_symbol: str,
        min_volume: float,
        save: bool = True
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

            legs.append(leg)
            price_multipliers[vt_symbol] = leg_setting["price_multiplier"]
            trading_multipliers[vt_symbol] = leg_setting["trading_multiplier"]
            inverse_contracts[vt_symbol] = leg_setting.get(
                "inverse_contract", False)

        spread = SpreadData(
            name,
            legs,
            price_multipliers,
            trading_multipliers,
            active_symbol,
            inverse_contracts,
            min_volume
        )
        self.spreads[name] = spread
        self.spread_engine.algo_engine.process_spread(spread)

        for leg in spread.legs.values():
            self.symbol_spread_map[leg.vt_symbol].append(spread)

        if save:
            self.save_setting()

        self.write_log("价差创建成功：{}".format(name))

    def remove_spread(self, name: str) -> None:
        """"""
        if name not in self.spreads:
            return

        spread = self.spreads.pop(name)

        for leg in spread.legs.values():
            self.symbol_spread_map[leg.vt_symbol].remove(spread)

        self.save_setting()
        self.write_log("价差移除成功：{}，重启后生效".format(name))

    def get_spread(self, name: str) -> SpreadData:
        """"""
        spread = self.spreads.get(name, None)
        return spread

    def get_all_spreads(self) -> List[SpreadData]:
        """"""
        return list(self.spreads.values())

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

    def get_position(self, vt_positionid):
        """
        Get latest position data by vt_positionid.
        """
        return self.positions.get(vt_positionid, None)

class SpreadAlgoEngine:
    """"""
    algo_class = SpreadTakerAlgo

    def __init__(self, spread_engine: SpreadEngine):
        """"""
        self.spread_engine: SpreadEngine = spread_engine
        self.event_engine: EventEngine = spread_engine.event_engine

        self.write_log = spread_engine.write_log

        self.spreads: Dict[str: SpreadData] = {}
        self.algos: Dict[str: SpreadAlgoTemplate] = {}

        self.order_algo_map: Dict[str: SpreadAlgoTemplate] = {}
        self.symbol_algo_map: Dict[str: SpreadAlgoTemplate] = defaultdict(list)

        self.algo_count: int = 0
        self.vt_tradeids: Set = set()
        self.margin_accounts: Dict = {}

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
        self.event_engine.register(EVENT_ACCOUNT_MARGIN, self.process_account_margin_event)
        self.event_engine.register(EVENT_TIMER, self.process_timer_event)
        # self.event_engine.register(
        #     EVENT_SPREAD_DATA, self.process_spread_event
        # )

    def process_account_margin_event(self, event: Event):
        account_margin = event.data
        self.margin_accounts[account_margin.vt_accountid] = account_margin

    def process_spread(self, spread):
        """"""
        self.spreads[spread.name] = spread

    def process_tick(self, tick: TickData):
        """"""
        algos = self.symbol_algo_map[tick.vt_symbol]
        # print(algos)
        if not algos:
            return

        buf = copy(algos)
        for algo in buf:
            if not algo.is_active():
                algos.remove(algo)
            else:
                algo.update_tick(tick)

    def process_order_event(self, event: Event):
        """"""
        order = event.data
        algo = self.order_algo_map.get(order.vt_orderid, None)
        if algo and algo.is_active():
            algo.update_order(order)
        # else:
        #     return
        self.spread_engine.strategy_engine.process_order(order)

    def process_trade(self, trade):
        """"""
        # print('process_trade_event(algo engine) vt_tradeids: %s<<<<<<<<<<<<<<' % self.vt_tradeids)
        # Filter duplicate trade push
        if trade.vt_tradeid in self.vt_tradeids:
            return
        self.vt_tradeids.add(trade.vt_tradeid)

        algo = self.order_algo_map.get(trade.vt_orderid, None)
        # print("process_trade_event(algo engine)>>>>vt_orderid: %s" % trade.vt_orderid)
        # if algo:
        #     print('process_trade_event(algo engine) %s status: %s' % (algo.algoid, algo.status))
        if algo and algo.is_active():
            # print("process_trade_event(algo engine)>>>> algo.is_active:%s" % algo.is_active())
            algo.update_trade(trade)

        # self.spread_engine.strategy_engine.process_spread_algo(algo)
    def process_position(self, position):
        """"""
        pass

    def process_timer_event(self, event: Event):
        """"""
        buf = list(self.algos.values())

        for algo in buf:
            if not algo.is_active():
                self.algos.pop(algo.algoid)
            else:
                algo.update_timer()

    def start_algo(
        self,
        spread_name: str,
        direction: Direction,
        offset: Offset,
        price: float,
        volume: float,
        lot_size: float,
        payup: int,
        interval: int,
        cancel_active_short_interval: int,
        lock: bool
    ) -> str:
        # Find spread object
        spread = self.spreads.get(spread_name, None)
        if not spread:
            self.write_log("创建价差算法失败，找不到价差：{}".format(spread_name))
            return ""

        # Generate algoid str
        self.algo_count += 1
        algo_count_str = str(self.algo_count).rjust(6, "0")
        algoid = f"{self.algo_class.algo_name}_{algo_count_str}"

        # Create algo object
        algo = self.algo_class(
            self,
            algoid,
            spread,
            direction,
            offset,
            price,
            volume,
            lot_size,
            payup,
            interval,
            cancel_active_short_interval,
            lock
        )
        self.algos[algoid] = algo

        # Generate map between vt_symbol and algo
        for leg in spread.legs.values():
            self.symbol_algo_map[leg.vt_symbol].append(algo)
        # print(self.symbol_algo_map)
        # Put event to update GUI
        # self.spread_engine.strategy_engine.process_spread_algo(algo)

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

    def put_algo_to_strategy_engine(self, algo: SpreadAlgoTemplate) -> None:
        """"""
        self.spread_engine.strategy_engine.process_spread_algo(algo)

    def write_algo_log(self, algo: SpreadAlgoTemplate, msg: str) -> None:
        """"""
        msg = f"{algo.algoid}：{msg}"
        self.write_log(msg)

    def send_order(
        self,
        algo: SpreadAlgoTemplate,
        vt_symbol: str,
        price: float,
        volume: float,
        direction: Direction,
        lock: bool
    ):
        """"""
        contract = self.spread_engine.get_contract(vt_symbol)

        original_req = OrderRequest(
            symbol=contract.symbol,
            exchange=contract.exchange,
            direction=direction,
            type=OrderType.LIMIT,
            price=price,
            volume=volume
        )

        vt_orderid = self.spread_engine.send_order(
            original_req, contract.gateway_name)

        # Check if sending order successful
        if not vt_orderid:
            return ''
        # Save relationship between orderid and algo.
        self.order_algo_map[vt_orderid] = algo
        # print('%s algo engine send_order vt_orderid:%s,price: %s' % (algo.algoid, vt_orderid, req.price))

        return vt_orderid

    def cancel_order(self, algo: SpreadAlgoTemplate, vt_orderid: str) -> None:
        """"""
        order = self.spread_engine.get_order(vt_orderid)
        if not order:
            self.write_algo_log(algo, "撤单失败，找不到委托{}".format(vt_orderid))
            return

        req = order.create_cancel_request()
        self.spread_engine.cancel_order(req, order.gateway_name)

    def get_contract(self, vt_symbol: str) -> ContractData:
        """"""
        return self.spread_engine.get_contract(vt_symbol)

class SpreadStrategyEngine:
    """"""

    setting_filename = "spread_trading_strategy.json"

    def __init__(self, spread_engine: SpreadEngine):
        """"""
        self.spread_engine: SpreadEngine = spread_engine
        self.event_engine: EventEngine = spread_engine.event_engine

        self.write_log = spread_engine.write_log

        self.strategy_setting: Dict[str: Dict] = {}

        self.classes: Dict[str: Type[SpreadStrategyTemplate]] = {}
        self.strategies: Dict[str: SpreadStrategyTemplate] = {}

        self.order_strategy_map: Dict[str: SpreadStrategyTemplate] = {}
        self.algo_strategy_map: Dict[str: SpreadStrategyTemplate] = {}
        self.spread_strategy_map: Dict[str: SpreadStrategyTemplate] = defaultdict(
            list)
        self.vt_tradeids: Set = set()

        self.load_strategy_class()

    def start(self):
        """"""
        self.load_strategy_setting()

        self.write_log("价差策略引擎启动成功")

    def close(self):
        """"""
        self.stop_all_strategies()

    def load_strategy_class(self):
        """
        Load strategy class from source code.
        """
        path1 = Path(__file__).parent.joinpath("strategies")
        self.load_strategy_class_from_folder(
            path1, "Digiccy1.futures_spot_arbitrage.strategies")

        # path2 = Path.cwd().joinpath("strategies")
        # self.load_strategy_class_from_folder(path2, "strategies")

    def load_strategy_class_from_folder(self, path: Path, module_name: str = ""):
        """
        Load strategy class from certain folder.
        """
        for dirpath, dirnames, filenames in os.walk(str(path)):
            for filename in filenames:
                if filename.endswith(".py"):
                    strategy_module_name = ".".join(
                        [module_name, filename.replace(".py", "")])
                elif filename.endswith(".pyd"):
                    strategy_module_name = ".".join(
                        [module_name, filename.split(".")[0]])
                self.load_strategy_class_from_module(strategy_module_name)

    def load_strategy_class_from_module(self, module_name: str):
        """
        Load strategy class from module file.
        """
        try:
            module = importlib.import_module(module_name)
            for name in dir(module):
                value = getattr(module, name)
                if (isinstance(value, type) and issubclass(value, SpreadStrategyTemplate) and value is not SpreadStrategyTemplate):
                    self.classes[value.__name__] = value

        except:  # noqa
            msg = f"策略文件{module_name}加载失败，触发异常：\n{traceback.format_exc()}"
            self.write_log(msg)

    def get_all_strategy_class_names(self):
        """"""
        return list(self.classes.keys())

    def load_strategy_setting(self):
        """
        Load setting file.
        """
        self.strategy_setting = load_json(self.setting_filename)

        for strategy_name, strategy_config in self.strategy_setting.items():
            self.add_strategy(
                strategy_config["class_name"],
                strategy_name,
                strategy_config["spread_name"],
                strategy_config["setting"]
            )

    def update_strategy_setting(self, strategy_name: str, setting: dict):
        """
        Update setting file.
        """
        strategy = self.strategies[strategy_name]

        self.strategy_setting[strategy_name] = {
            "class_name": strategy.__class__.__name__,
            "spread_name": strategy.spread_name,
            "setting": setting,
        }
        save_json(self.setting_filename, self.strategy_setting)

    def remove_strategy_setting(self, strategy_name: str):
        """
        Update setting file.
        """
        if strategy_name not in self.strategy_setting:
            return

        self.strategy_setting.pop(strategy_name)
        save_json(self.setting_filename, self.strategy_setting)

    def process_spread_pos(self, spread):
        """"""
        strategies = self.spread_strategy_map[spread.name]

        for strategy in strategies:
            if strategy.inited:
                self.call_strategy_func(strategy, strategy.on_spread_pos)

    def process_spread_algo(self, algo):
        """"""
        strategy = self.algo_strategy_map.get(algo.algoid, None)

        if strategy:
            self.call_strategy_func(
                strategy, strategy.update_spread_algo, algo)

    def process_order(self, order):
        """"""
        strategy = self.order_strategy_map.get(order.vt_orderid, None)

        if strategy:
            self.call_strategy_func(strategy, strategy.update_order, order)

    def process_trade(self, trade):
        """"""
        strategy = self.order_strategy_map.get(trade.vt_orderid, None)

        if strategy:
            self.call_strategy_func(strategy, strategy.on_trade, trade)

    def call_strategy_func(
        self, strategy: SpreadStrategyTemplate, func: Callable, params: Any = None
    ):
        """
        Call function of a strategy and catch any exception raised.
        """
        try:
            if params:
                func(params)
            else:
                func()
        except Exception:
            strategy.trading = False
            strategy.inited = False

            msg = f"触发异常已停止\n{traceback.format_exc()}"
            self.write_strategy_log(strategy, msg)

    def add_strategy(
        self, class_name: str, strategy_name: str, spread_name: str, setting: dict
    ):
        """
        Add a new strategy.
        """
        if strategy_name in self.strategies:
            self.write_log(f"创建策略失败，存在重名{strategy_name}")
            return

        strategy_class = self.classes.get(class_name, None)
        if not strategy_class:
            self.write_log(f"创建策略失败，找不到策略类{class_name}")
            return

        spread = self.spread_engine.get_spread(spread_name)
        if not spread:
            self.write_log(f"创建策略失败，找不到价差{spread_name}")
            return

        strategy = strategy_class(self, strategy_name, spread, setting)
        self.strategies[strategy_name] = strategy

        # Add vt_symbol to strategy map.
        strategies = self.spread_strategy_map[spread_name]
        strategies.append(strategy)

        # Update to setting file.
        self.update_strategy_setting(strategy_name, setting)      

    def edit_strategy(self, strategy_name: str, setting: dict):
        """
        Edit parameters of a strategy.
        """
        strategy = self.strategies[strategy_name]
        strategy.update_setting(setting)

        self.update_strategy_setting(strategy_name, setting)

    def remove_strategy(self, strategy_name: str):
        """
        Remove a strategy.
        """
        strategy = self.strategies[strategy_name]
        if strategy.trading:
            self.write_log(f"策略{strategy.strategy_name}移除失败，请先停止")
            return

        # Remove setting
        self.remove_strategy_setting(strategy_name)

        # Remove from symbol strategy map
        strategies = self.spread_strategy_map[strategy.spread_name]
        strategies.remove(strategy)

        # Remove from strategies
        self.strategies.pop(strategy_name)

        return True

    def init_strategy(self, strategy_name: str):
        """"""
        strategy = self.strategies[strategy_name]

        if strategy.inited:
            self.write_log(f"{strategy_name}已经完成初始化，禁止重复操作")
            return

        self.call_strategy_func(strategy, strategy.on_init)
        strategy.inited = True

        self.write_log(f"{strategy_name}初始化完成")

    def start_strategy(self, strategy_name: str):
        """"""
        strategy = self.strategies[strategy_name]
        if not strategy.inited:
            self.write_log(f"策略{strategy.strategy_name}启动失败，请先初始化")
            return

        if strategy.trading:
            self.write_log(f"{strategy_name}已经启动，请勿重复操作")
            return

        self.call_strategy_func(strategy, strategy.on_start)

    def stop_strategy(self, strategy_name: str):
        """"""
        strategy = self.strategies[strategy_name]
        if not strategy.trading:
            return

        self.call_strategy_func(strategy, strategy.on_stop)

        strategy.stop_all_algos()
        strategy.cancel_all_orders()

        strategy.trading = False

    def init_all_strategies(self):
        """"""
        for strategy in self.strategies.keys():
            self.init_strategy(strategy)

    def start_all_strategies(self):
        """"""
        for strategy in self.strategies.keys():
            self.start_strategy(strategy)

    def stop_all_strategies(self):
        """"""
        for strategy in self.strategies.keys():
            self.stop_strategy(strategy)

    def get_strategy_class_parameters(self, class_name: str):
        """
        Get default parameters of a strategy class.
        """
        strategy_class = self.classes[class_name]

        parameters = {}
        for name in strategy_class.parameters:
            parameters[name] = getattr(strategy_class, name)

        return parameters

    def get_strategy_parameters(self, strategy_name):
        """
        Get parameters of a strategy.
        """
        strategy = self.strategies[strategy_name]
        return strategy.get_parameters()

    def start_algo(
        self,
        strategy: SpreadStrategyTemplate,
        spread_name: str,
        direction: Direction,
        offset: Offset,
        price: float,
        volume: float,
        lot_size: float,
        payup: int,
        interval: int,
        cancel_active_short_interval: int,
        lock: bool
    ) -> str:
        """"""
        algoid = self.spread_engine.start_algo(
            spread_name,
            direction,
            offset,
            price,
            volume,
            lot_size,
            payup,
            interval,
            cancel_active_short_interval,
            lock
        )

        self.algo_strategy_map[algoid] = strategy

        return algoid

    def stop_algo(self, strategy: SpreadStrategyTemplate, algoid: str):
        """"""
        self.spread_engine.stop_algo(algoid)

    def stop_all_algos(self, strategy: SpreadStrategyTemplate):
        """"""
        pass

    def send_order(
        self,
        strategy: SpreadStrategyTemplate,
        vt_symbol: str,
        price: float,
        volume: float,
        direction: Direction,
        offset: Offset,
        lock: bool
    ):
        contract = self.spread_engine.get_contract(vt_symbol)

        original_req = OrderRequest(
            symbol=contract.symbol,
            exchange=contract.exchange,
            direction=direction,
            offset=offset,
            type=OrderType.LIMIT,
            price=price,
            volume=volume
        )

        vt_orderid = self.spread_engine.send_order(
            original_req, contract.gateway_name)
        if not vt_orderid:
            return ''
        # Save relationship between orderid and strategy.
        self.order_strategy_map[vt_orderid] = strategy

        return vt_orderid

    def cancel_order(self, strategy: SpreadStrategyTemplate, vt_orderid: str):
        """"""
        order = self.spread_engine.get_order(vt_orderid)
        if not order:
            self.write_strategy_log(
                strategy, "撤单失败，找不到委托{}".format(vt_orderid))
            return

        req = order.create_cancel_request()
        self.spread_engine.cancel_order(req, order.gateway_name)

    def cancel_all_orders(self, strategy: SpreadStrategyTemplate):
        """"""
        pass

    def write_strategy_log(self, strategy: SpreadStrategyTemplate, msg: str):
        """"""
        msg = f"{strategy.strategy_name}：{msg}"
        self.write_log(msg)

    def send_strategy_email(self, strategy: SpreadStrategyTemplate, msg: str):
        """"""
        if strategy:
            subject = f"{strategy.strategy_name}"
        else:
            subject = "价差策略引擎"

        self.spread_engine.send_email(subject, msg)
