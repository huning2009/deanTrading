"""
Gateway for Binance Crypto Exchange.
"""

import urllib
import hashlib
import hmac
import time
from copy import copy
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock

from vnpy.api.rest import RestClient, Request
from vnpy.api.websocket import WebsocketClient
from vnpy.trader.constant import (
    Direction,
    Product,
    Status,
    OrderType,
    Interval
)
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.object import (
    TickData,
    OrderData,
    TradeData,
    AccountData,
    PositionData,
    ContractData,
    BarData,
    OrderRequest,
    CancelRequest,
    SubscribeRequest,
    HistoryRequest
)
from vnpy.trader.event import EVENT_TIMER
from vnpy.event import Event

from myConstant import Exchange


REST_HOST = "https://fapi.binance.com"
WEBSOCKET_TRADE_HOST = "wss://fstream.binance.com/ws/"
WEBSOCKET_DATA_HOST = "wss://fstream.binance.com/stream?streams="

STATUS_BINANCE2VT = {
    "NEW": Status.NOTTRADED,
    "PARTIALLY_FILLED": Status.PARTTRADED,
    "FILLED": Status.ALLTRADED,
    "CANCELED": Status.CANCELLED,
    "REJECTED": Status.REJECTED
}

ORDERTYPE_VT2BINANCE = {
    OrderType.LIMIT: "LIMIT",
    OrderType.MARKET: "MARKET"
}
ORDERTYPE_BINANCE2VT = {v: k for k, v in ORDERTYPE_VT2BINANCE.items()}

DIRECTION_VT2BINANCE = {
    Direction.LONG: "BUY",
    Direction.SHORT: "SELL"
}
DIRECTION_BINANCE2VT = {v: k for k, v in DIRECTION_VT2BINANCE.items()}

INTERVAL_VT2BINANCE = {
    Interval.MINUTE: "1m",
    Interval.HOUR: "1h",
    Interval.DAILY: "1d",
}

TIMEDELTA_MAP = {
    Interval.MINUTE: timedelta(minutes=1),
    Interval.HOUR: timedelta(hours=1),
    Interval.DAILY: timedelta(days=1),
}


class Security(Enum):
    NONE = 0
    SIGNED = 1
    API_KEY = 2


symbol_name_map = {}


class BinanceFuturesGateway(BaseGateway):
    """
    VN Trader Gateway for Binance Futures connection.
    """

    default_setting = {
        "key": "",
        "secret": "",
        "session_number": 3,
        "proxy_host": "",
        "proxy_port": 0,
    }

    exchanges = [Exchange.BINANCEFUTURES]

    def __init__(self, event_engine):
        """Constructor"""
        super().__init__(event_engine, "BINANCEFUTURES")

        self.trade_ws_api = BinanceTradeWebsocketApi(self)
        self.market_ws_api = BinanceDataWebsocketApi(self)
        self.rest_api = BinanceRestApi(self)

    def connect(self, setting: dict):
        """"""
        key = setting["key"]
        secret = setting["secret"]
        session_number = setting["session_number"]
        proxy_host = setting["proxy_host"]
        proxy_port = setting["proxy_port"]

        self.rest_api.connect(key, secret, session_number,
                              proxy_host, proxy_port)
        self.market_ws_api.connect(proxy_host, proxy_port)

        self.init_query()

    def subscribe(self, req: SubscribeRequest):
        """"""
        self.market_ws_api.subscribe(req)

    def send_order(self, req: OrderRequest):
        """"""
        return self.rest_api.send_order(req)

    def cancel_order(self, req: CancelRequest):
        """"""
        self.rest_api.cancel_order(req)

    def query_account(self):
        """"""
        self.rest_api.query_account()

    def query_position(self):
        """"""
        self.rest_api.query_position()

    def query_history(self, req: HistoryRequest):
        """"""
        return self.rest_api.query_history(req)

    def close(self):
        """"""
        self.rest_api.stop()
        self.trade_ws_api.stop()
        self.market_ws_api.stop()

    def process_timer_event(self, event: Event):
        """"""
        self.count += 1
        self.rest_api.keep_user_stream()

        if self.count < 3:
            return
        else:
            self.count = 0
            # self.query_account()
            # self.query_position()

    def init_query(self):
        """"""
        self.count = 0
        self.event_engine.register(EVENT_TIMER, self.process_timer_event)

class BinanceRestApi(RestClient):
    """
    BINANCE REST API
    """

    def __init__(self, gateway: BinanceFuturesGateway):
        """"""
        super().__init__()

        self.gateway = gateway
        self.gateway_name = gateway.gateway_name

        self.trade_ws_api = self.gateway.trade_ws_api

        self.key = ""
        self.secret = ""

        self.user_stream_key = ""
        self.keep_alive_count = 0
        self.recv_window = 5000
        self.time_offset = 0

        self.order_count = 1_000_000
        self.order_count_lock = Lock()
        self.connect_time = 0

    def sign(self, request):
        """
        Generate BINANCE signature.
        """
        security = request.data["security"]
        if security == Security.NONE:
            request.data = None
            return request

        if request.params:
            path = request.path + "?" + urllib.parse.urlencode(request.params)
        else:
            request.params = dict()
            path = request.path

        if security == Security.SIGNED:
            timestamp = int(time.time() * 1000)

            if self.time_offset > 0:
                timestamp -= abs(self.time_offset)
            elif self.time_offset < 0:
                timestamp += abs(self.time_offset)

            request.params["timestamp"] = timestamp

            query = urllib.parse.urlencode(sorted(request.params.items()))
            signature = hmac.new(self.secret, query.encode(
                "utf-8"), hashlib.sha256).hexdigest()

            query += "&signature={}".format(signature)
            path = request.path + "?" + query

        request.path = path
        request.params = {}
        request.data = {}

        # Add headers
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "X-MBX-APIKEY": self.key
        }

        if security in [Security.SIGNED, Security.API_KEY]:
            request.headers = headers

        return request

    def connect(
        self,
        key: str,
        secret: str,
        session_number: int,
        proxy_host: str,
        proxy_port: int
    ):
        """
        Initialize connection to REST server.
        """
        self.key = key
        self.secret = secret.encode()
        self.proxy_port = proxy_port
        self.proxy_host = proxy_host

        self.connect_time = (
            int(datetime.now().strftime("%y%m%d%H%M%S")) * self.order_count
        )

        self.init(REST_HOST, proxy_host, proxy_port)
        self.start(session_number)

        self.gateway.write_log("FUTURES REST API启动成功")

        self.query_time()
        self.query_account()
        # self.query_position()
        self.query_order()
        self.query_contract()
        self.start_user_stream()

    def query_time(self):
        """"""
        data = {
            "security": Security.NONE
        }
        path = "/fapi/v1/time"

        return self.add_request(
            "GET",
            path,
            callback=self.on_query_time,
            data=data
        )

    def query_account(self):
        """"""
        data = {"security": Security.SIGNED}

        self.add_request(
            method="GET",
            path="/fapi/v1/account",
            callback=self.on_query_account,
            data=data
        )

    def query_position(self):
        """"""
        data = {"security": Security.SIGNED}

        self.add_request(
            method="GET",
            path="/fapi/v1/positionRisk",
            callback=self.on_query_position,
            data=data
        )

    def query_order(self):
        """"""
        data = {"security": Security.SIGNED}

        self.add_request(
            method="GET",
            path="/fapi/v1/openOrders",
            callback=self.on_query_order,
            data=data
        )

    def query_contract(self):
        """"""
        data = {
            "security": Security.NONE
        }
        self.add_request(
            method="GET",
            path="/fapi/v1/exchangeInfo",
            callback=self.on_query_contract,
            data=data
        )

    def _new_order_id(self):
        """"""
        with self.order_count_lock:
            self.order_count += 1
            return self.order_count

    def send_order(self, req: OrderRequest):
        """"""
        orderid = str(self.connect_time + self._new_order_id())
        order = req.create_order_data(
            orderid,
            self.gateway_name
        )
        self.gateway.on_order(order)

        data = {
            "security": Security.SIGNED
        }

        params = {
            "symbol": req.symbol,
            "timeInForce": "GTC",
            "side": DIRECTION_VT2BINANCE[req.direction],
            "type": ORDERTYPE_VT2BINANCE[req.type],
            "price": str(req.price),
            "quantity": str(req.volume),
            "newClientOrderId": orderid,
        }

        self.add_request(
            method="POST",
            path="/fapi/v1/order",
            callback=self.on_send_order,
            data=data,
            params=params,
            extra=order,
            on_error=self.on_send_order_error,
            on_failed=self.on_send_order_failed
        )

        return order.vt_orderid

    def cancel_order(self, req: CancelRequest):
        """"""
        data = {
            "security": Security.SIGNED
        }

        params = {
            "symbol": req.symbol,
            "origClientOrderId": req.orderid
        }

        self.add_request(
            method="DELETE",
            path="/fapi/v1/order",
            callback=self.on_cancel_order,
            params=params,
            data=data,
            extra=req
        )

    def start_user_stream(self):
        """"""
        data = {
            "security": Security.API_KEY
        }

        self.add_request(
            method="POST",
            path="/fapi/v1/listenKey",
            callback=self.on_start_user_stream,
            data=data
        )

    def keep_user_stream(self):
        """"""
        self.keep_alive_count += 1
        if self.keep_alive_count < 1800:
            return

        data = {
            "security": Security.API_KEY
        }

        params = {
            "listenKey": self.user_stream_key
        }

        self.add_request(
            method="PUT",
            path="/fapi/v1/listenKey",
            callback=self.on_keep_user_stream,
            params=params,
            data=data
        )

    def on_query_time(self, data, request):
        """"""
        local_time = int(time.time() * 1000)
        server_time = int(data["serverTime"])
        self.time_offset = local_time - server_time

    def on_query_account(self, data, request):
        """"""
        for account_data in data["assets"]:
            account = AccountData(
                accountid=account_data["asset"],
                balance=float(account_data["walletBalance"]) ,
                frozen=float(account_data["initialMargin"]) + float(account_data["maintMargin"]),
                gateway_name=self.gateway_name
            )

            if account.balance:
                self.gateway.on_account(account)

        self.gateway.write_log("FUTURES账户资金查询成功")

    def on_query_position(self, data, request):
        """"""
        for position_data in data:
            if float(position_data["positionAmt"]) > 1.0e-8:
                direction = Direction.LONG
                volume = float(position_data["positionAmt"])
            elif float(position_data["positionAmt"]) < -1.0e-8:
                direction = Direction.SHORT
                volume = abs(float(position_data["positionAmt"]))
            else:
                break

            position = PositionData(
                symbol=position_data["symbol"],
                exchange=Exchange.BINANCEFUTURES,
                direction=direction,
                volume=volume,
                # frozen=float(position_data["positionAmt"]),
                price=float(position_data["entryPrice"]),
                pnl=float(position_data["unRealizedProfit"]),

                gateway_name=self.gateway_name
            )

            if position.volume:
                self.gateway.on_position(position)

        self.gateway.write_log("FUTURES账户资金查询成功")

    def on_query_order(self, data, request):
        """"""
        for d in data:
            dt = datetime.fromtimestamp(d["time"] / 1000)
            time = dt.strftime("%Y-%m-%d %H:%M:%S")

            order = OrderData(
                orderid=d["clientOrderId"],
                symbol=d["symbol"],
                exchange=Exchange.BINANCEFUTURES,
                price=float(d["price"]),
                volume=float(d["origQty"]),
                type=ORDERTYPE_BINANCE2VT[d["type"]],
                direction=DIRECTION_BINANCE2VT[d["side"]],
                traded=float(d["executedQty"]),
                status=STATUS_BINANCE2VT.get(d["status"], None),
                time=time,
                gateway_name=self.gateway_name,
            )
            self.gateway.on_order(order)

        self.gateway.write_log("FUTURES委托信息查询成功")

    def on_query_contract(self, data, request):
        """"""
        for d in data["symbols"]:
            pricetick = 1
            min_volume = 1

            for f in d["filters"]:
                if f["filterType"] == "PRICE_FILTER":
                    pricetick = float(f["tickSize"])
                elif f["filterType"] == "LOT_SIZE":
                    min_volume = float(f["stepSize"])

            contract = ContractData(
                symbol=d["symbol"],
                exchange=Exchange.BINANCEFUTURES,
                name=d["symbol"],
                pricetick=pricetick,
                size=1,
                min_volume=min_volume,
                product=Product.FUTURES,
                history_data=True,
                net_position=True,
                gateway_name=self.gateway_name,
            )
            self.gateway.on_contract(contract)

            symbol_name_map[contract.symbol] = contract.name

        self.gateway.write_log("FUTURES合约信息查询成功")

    def on_send_order(self, data, request):
        """"""
        pass

    def on_send_order_failed(self, status_code: str, request: Request):
        """
        Callback when sending order failed on server.
        """
        order = request.extra
        order.status = Status.REJECTED
        self.gateway.on_order(order)

        msg = f"委托失败，状态码：{status_code}，信息：{request.response.text}"
        self.gateway.write_log(msg)

    def on_send_order_error(
        self, exception_type: type, exception_value: Exception, tb, request: Request
    ):
        """
        Callback when sending order caused exception.
        """
        order = request.extra
        order.status = Status.REJECTED
        self.gateway.on_order(order)

        # Record exception if not ConnectionError
        if not issubclass(exception_type, ConnectionError):
            self.on_error(exception_type, exception_value, tb, request)

    def on_cancel_order(self, data, request):
        """"""
        pass

    def on_start_user_stream(self, data, request):
        """"""
        self.user_stream_key = data["listenKey"]
        self.keep_alive_count = 0
        url = WEBSOCKET_TRADE_HOST + self.user_stream_key

        self.trade_ws_api.connect(url, self.proxy_host, self.proxy_port)

    def on_keep_user_stream(self, data, request):
        """"""
        pass

    def query_history(self, req: HistoryRequest):
        """"""
        history = []
        limit = 1000
        start_time = int(datetime.timestamp(req.start))

        while True:
            # Create query params
            params = {
                "symbol": req.symbol,
                "interval": INTERVAL_VT2BINANCE[req.interval],
                "limit": limit,
                "startTime": start_time * 1000,         # convert to millisecond
            }

            # Add end time if specified
            if req.end:
                end_time = int(datetime.timestamp(req.end))
                params["endTime"] = end_time * 1000     # convert to millisecond

            # Get response from server
            resp = self.request(
                "GET",
                "/fapi/v1/klines",
                data={"security": Security.NONE},
                params=params
            )

            # Break if request failed with other status code
            if resp.status_code // 100 != 2:
                msg = f"获取历史数据失败，状态码：{resp.status_code}，信息：{resp.text}"
                self.gateway.write_log(msg)
                break
            else:
                data = resp.json()
                if not data:
                    msg = f"获取历史数据为空，开始时间：{start_time}"
                    self.gateway.write_log(msg)
                    break

                buf = []

                for l in data:
                    dt = datetime.fromtimestamp(l[0] / 1000)    # convert to second

                    bar = BarData(
                        symbol=req.symbol,
                        exchange=req.exchange,
                        datetime=dt,
                        interval=req.interval,
                        volume=float(l[5]),
                        open_price=float(l[1]),
                        high_price=float(l[2]),
                        low_price=float(l[3]),
                        close_price=float(l[4]),
                        gateway_name=self.gateway_name
                    )
                    buf.append(bar)

                history.extend(buf)

                begin = buf[0].datetime
                end = buf[-1].datetime
                msg = f"获取历史数据成功，{req.symbol} - {req.interval.value}，{begin} - {end}"
                self.gateway.write_log(msg)

                # Break if total data count less than limit (latest date collected)
                if len(data) < limit:
                    break

                # Update start time
                start_dt = bar.datetime + TIMEDELTA_MAP[req.interval]
                start_time = int(datetime.timestamp(start_dt))

        return history


class BinanceTradeWebsocketApi(WebsocketClient):
    """"""

    def __init__(self, gateway):
        """"""
        super().__init__()

        self.gateway = gateway
        self.gateway_name = gateway.gateway_name

    def connect(self, url, proxy_host, proxy_port):
        """"""
        self.init(url, proxy_host, proxy_port)
        self.start()

    def on_connected(self):
        """"""
        self.gateway.write_log("FUTURES交易Websocket API连接成功")

    def on_packet(self, packet: dict):  # type: (dict)->None
        """"""
        if packet["e"] == "ACCOUNT_UPDATE":
            self.on_account(packet['a'])
        elif packet["e"] == "ORDER_TRADE_UPDATE":
            self.on_order(packet['o'])

    def on_account(self, packet):
        """"""
        # print('gateway on_account')
        # print(packet)
        for d in packet["B"]:
            account = AccountData(
                accountid=d["a"],
                balance=float(d["wb"]),
                frozen=float(d["wb"]) - float(d["cw"]),
                gateway_name=self.gateway_name
            )

            if account.balance:
                self.gateway.on_account(account)

        for d in packet['P']:
            # if float(d["pa"]) > 1.0e-8:
            #     direction = Direction.LONG
            #     volume = float(d["pa"])
            # elif float(d["pa"]) < -1.0e-8:
            #     direction = Direction.SHORT
            #     volume = abs(float(d["pa"]))
            # else:
            #     break

            position = PositionData(
                symbol=d["s"],
                exchange=Exchange.BINANCEFUTURES,
                direction=Direction.NET,
                volume=float(d["pa"]),
                # frozen=float(position_data["positionAmt"]),
                price=float(d["ep"]),
                pnl=float(d["up"]),

                gateway_name=self.gateway_name
            )

            if position.volume:
                self.gateway.on_position(position)

    def on_order(self, packet: dict):
        """"""
        # print('gateway on_order')
        # print(packet)
        dt = datetime.fromtimestamp(packet["T"] / 1000)
        time = dt.strftime("%Y-%m-%d %H:%M:%S")

        orderid = packet["c"]
        order = OrderData(
            symbol=packet["s"],
            exchange=Exchange.BINANCEFUTURES,
            orderid=orderid,
            type=ORDERTYPE_BINANCE2VT[packet["o"]],
            direction=DIRECTION_BINANCE2VT[packet["S"]],
            price=float(packet["p"]),
            volume=float(packet["q"]),
            traded=float(packet["z"]),
            status=STATUS_BINANCE2VT[packet["X"]],
            time=time,
            gateway_name=self.gateway_name
        )

        self.gateway.on_order(order)

        # Push trade event
        trade_volume = float(packet["l"])
        if not trade_volume:
            return

        trade_dt = datetime.fromtimestamp(packet["T"] / 1000)
        trade_time = trade_dt.strftime("%Y-%m-%d %H:%M:%S")

        trade = TradeData(
            symbol=order.symbol,
            exchange=order.exchange,
            orderid=order.orderid,
            tradeid=order.orderid,
            direction=order.direction,
            price=float(packet["L"]),
            volume=trade_volume,
            time=trade_time,
            gateway_name=self.gateway_name,
        )
        self.gateway.on_trade(trade)


class BinanceDataWebsocketApi(WebsocketClient):
    """"""

    def __init__(self, gateway):
        """"""
        super().__init__()

        self.gateway = gateway
        self.gateway_name = gateway.gateway_name

        self.ticks = {}

    def connect(self, proxy_host: str, proxy_port: int):
        """"""
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

    def on_connected(self):
        """"""
        self.gateway.write_log("FUTURES行情Websocket API连接刷新")

    def subscribe(self, req: SubscribeRequest):
        """"""
        if req.symbol not in symbol_name_map:
            self.gateway.write_log(f"FUTURES找不到该合约代码{req.symbol}")
            return

        # Create tick buf data
        tick = TickData(
            symbol=req.symbol,
            name=symbol_name_map.get(req.symbol, ""),
            exchange=Exchange.BINANCEFUTURES,
            datetime=datetime.now(),
            gateway_name=self.gateway_name,
        )
        self.ticks[req.symbol.lower()] = tick

        # Close previous connection
        if self._active:
            self.stop()
            self.join()

        # Create new connection
        channels = []
        for ws_symbol in self.ticks.keys():
            channels.append(ws_symbol + "@ticker")
            channels.append(ws_symbol + "@depth5")

        url = WEBSOCKET_DATA_HOST + "/".join(channels)
        self.init(url, self.proxy_host, self.proxy_port)
        self.start()

    def on_packet(self, packet):
        """"""
        stream = packet["stream"]
        data = packet["data"]

        symbol, channel = stream.split("@")
        tick = self.ticks[symbol]

        if channel == "ticker":
            tick.volume = float(data['v'])
            tick.open_price = float(data['o'])
            tick.high_price = float(data['h'])
            tick.low_price = float(data['l'])
            tick.last_price = float(data['c'])
            tick.datetime = datetime.fromtimestamp(float(data['E']) / 1000)
        else:
            bids = data["b"]
            for n in range(5):
                price, volume = bids[n]
                tick.__setattr__("bid_price_" + str(n + 1), float(price))
                tick.__setattr__("bid_volume_" + str(n + 1), float(volume))

            asks = data["a"]
            for n in range(5):
                price, volume = asks[n]
                tick.__setattr__("ask_price_" + str(n + 1), float(price))
                tick.__setattr__("ask_volume_" + str(n + 1), float(volume))

        if tick.last_price:
            self.gateway.on_tick(copy(tick))
