# bstock-trade Demo extension

Dedicated branch: `codex/bstock-demo`. Upstream base: `9af100d6822da7d2d0291a906c730ef172284ee2` (v2.17.0).

The branch registers Binance Spot Demo REST/market WS/private WS routing and includes the corresponding connector tests. `ControlledDemoGateway` provides caller-supplied client IDs, query/cancel/trade import and a no-resubmission contract for the bstock-trade application.

The caller must durably persist intent and ID before `submit`, reconcile ambiguous outcomes using the original ID, deduplicate fills and manage inventory/risk. The gateway uses BinanceExchange auth, time synchronization and throttling; the application does not start the default PositionExecutor retry loop or a second strategy writer. It currently uses REST polling rather than an independently running WS account loop.

Source/fixture checks are not signed-account or order-lifecycle acceptance. The application defaults to disabled new orders and observation-only instruments. Demo candle collection belongs to the application; upstream production candle constants are not implicitly converted.

`aiohttp` is constrained below 3.14 because aioresponses 0.7.9 cannot construct the new ClientResponse interface; the targeted upstream connector tests are verified against 3.13.5. See the application lock file for the complete tested environment.
