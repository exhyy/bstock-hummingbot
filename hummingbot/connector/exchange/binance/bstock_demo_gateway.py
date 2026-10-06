"""Explicit-ID, no-retry gateway for bstock-trade's durable order controller.

Uses BinanceExchange authentication, time synchronization and throttling. It does
not start a second strategy or the default PositionExecutor retry loop. The caller
persists order intent before submit and imports REST trades before terminal state.
"""

import time
from datetime import datetime, timezone
from decimal import Decimal


class ControlledDemoGateway:
    def __init__(self, connector):
        if connector.domain != "demo":
            raise ValueError("bstock gateway accepts the Demo domain only")
        from . import binance_web_utils
        from urllib.parse import urlparse

        if urlparse(binance_web_utils.rest_url(connector.domain)).hostname != "demo-api.binance.com":
            raise ValueError("unexpected execution host")
        self.connector = connector
        from hummingbot.core.api_throttler.data_types import LinkedLimitWeightPair, RateLimit
        from . import binance_constants

        # Conservative weights cover the gateway's extra public/private query endpoints.
        self.connector.throttler.add_rate_limits(
            [
                RateLimit(
                    limit_id=path,
                    limit=6000,
                    time_interval=60,
                    linked_limits=[
                        LinkedLimitWeightPair(binance_constants.REQUEST_WEIGHT, weight),
                        LinkedLimitWeightPair(binance_constants.RAW_REQUESTS, 1),
                    ],
                )
                for path, weight in [("/avgPrice", 20), ("/openOrders", 80)]
            ]
        )

    @classmethod
    def from_credentials(cls, key, secret, symbols):
        from .binance_exchange import BinanceExchange

        pairs = [symbol.removesuffix("USDT") + "-USDT" for symbol in symbols]
        return cls(
            BinanceExchange(
                binance_api_key=key,
                binance_api_secret=secret,
                trading_pairs=pairs,
                trading_required=True,
                domain="demo",
            )
        )

    async def initialize(self):
        self.connector.tick(time.time())
        info = await self.connector._api_get(path_url="/exchangeInfo")
        self.connector._initialize_trading_pair_symbols_from_exchange_info(info)
        await self.connector._update_time_synchronizer(pass_on_non_cancelled_error=True)

    def track(self, order):
        from hummingbot.core.data_type.common import OrderType, TradeType

        if order["id"] not in self.connector.in_flight_orders:
            self.connector.tick(time.time())
            self.connector.start_tracking_order(
                order_id=order["id"],
                exchange_order_id=order["exchange_id"],
                trading_pair=order["symbol"].removesuffix("USDT") + "-USDT",
                trade_type=TradeType[order["side"]],
                price=Decimal(order["price"]),
                amount=Decimal(order["quantity"]),
                order_type=OrderType.LIMIT,
            )

    async def submit(self, order):
        from hummingbot.core.data_type.common import OrderType, TradeType

        if len(order["id"]) > 32 or order["side"] not in {"BUY", "SELL"}:
            raise ValueError("invalid preallocated order")
        self.track(order)
        # Exceptions propagate to the durable controller as UNKNOWN, never FAILED/retry.
        exchange_id, _ = await self.connector._place_order(
            order_id=order["id"],
            trading_pair=order["symbol"].removesuffix("USDT") + "-USDT",
            amount=Decimal(order["quantity"]),
            trade_type=TradeType[order["side"]],
            order_type=OrderType.LIMIT,
            price=Decimal(order["price"]),
        )
        if exchange_id == "UNKNOWN":
            return {"status": "UNKNOWN"}
        from hummingbot.core.data_type.in_flight_order import OrderState, OrderUpdate

        self.connector._order_tracker.process_order_update(
            OrderUpdate(
                client_order_id=order["id"],
                exchange_order_id=str(exchange_id),
                trading_pair=order["symbol"].removesuffix("USDT") + "-USDT",
                update_timestamp=time.time(),
                new_state=OrderState.OPEN,
            )
        )
        return {"status": "NEW", "orderId": exchange_id}

    async def query(self, order):
        self.track(order)
        return await self.connector._api_get(
            path_url="/order",
            params={"symbol": order["symbol"], "origClientOrderId": order["id"]},
            is_auth_required=True,
        )

    async def cancel(self, order):
        return await self.connector._api_delete(
            path_url="/order",
            params={"symbol": order["symbol"], "origClientOrderId": order["id"]},
            is_auth_required=True,
        )

    async def trades(self, symbol, exchange_id):
        rows = await self.connector._api_get(
            path_url="/myTrades",
            params={"symbol": symbol, "orderId": exchange_id, "limit": 1000},
            is_auth_required=True,
        )
        if len(rows) >= 1000:
            raise ValueError("trade pagination requires manual reconciliation")
        result = []
        for row in rows:
            if str(row["orderId"]) != str(exchange_id):
                continue
            fill = dict(row)
            fill["time"] = datetime.fromtimestamp(row["time"] / 1000, timezone.utc).isoformat()
            result.append(fill)
        return result

    async def balances(self):
        account = await self.connector._api_get(path_url="/account", is_auth_required=True)
        if not account.get("canTrade", False):
            raise ValueError("Demo account does not permit trading")
        return {
            row["asset"]: {
                "free": row["free"],
                "locked": row["locked"],
                "total": str(Decimal(row["free"]) + Decimal(row["locked"])),
            }
            for row in account["balances"]
        }

    async def average_price(self, symbol):
        return await self.connector._api_get(path_url="/avgPrice", params={"symbol": symbol})

    async def open_orders(self, symbol):
        return await self.connector._api_get(
            path_url="/openOrders", params={"symbol": symbol}, is_auth_required=True
        )

    async def close(self):
        from hummingbot.core.web_assistant.connections.connections_factory import ConnectionsFactory

        await ConnectionsFactory().close()
