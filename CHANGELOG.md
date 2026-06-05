# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Token requests no longer retry on 4xx errors.** An invalid AppKey/Secret
  returns HTTP 4xx (e.g. `403 IGW00103`), which is deterministic — the client
  used to retry 3× with backoff (~15s) before raising `TokenError`. It now
  fails fast and raises immediately. Transient errors (network, 5xx) still
  retry as before.

## [1.0.0] - 2026-03-23

### Added

- **ChartData model** — fully typed OHLCV candle data via `ChartCandle` and `ChartData` Pydantic models
- **Enhanced OrderBook model** — structured bid/ask levels via `OrderBookLevel`, 10-level price/volume parsing
- **5 new exception types** — `RateLimitError`, `InvalidOrderError`, `InsufficientBalanceError`, `WebSocketError`, `ValidationError`
- **Smart error classification** — HTTP client raises specific exceptions based on status code and `rsp_cd`
- **WebSocket heartbeat** — periodic ping/pong to detect stale connections (`heartbeat_interval` parameter)
- **WebSocket queue overflow protection** — bounded `asyncio.Queue` with configurable `queue_maxsize`
- **Reconnection jitter** — exponential backoff with randomized jitter for WebSocket reconnects
- **8 new example files** — real-time monitoring, stop-loss, portfolio summary, WebSocket orderbook, chart analysis, order management, futures/options, error handling

### Changed

- `chart()` methods now return `ChartData` instead of `dict[str, Any]` (use `.raw` for original dict)
- `OrderBook.from_api()` now parses structured ask/bid levels (backward-compatible: `.raw` still accessible)
- Input validation now raises `ValidationError` (subclass of both `PyDBSecError` and `ValueError`)
- Development Status classifier upgraded to "5 - Production/Stable"

[1.0.0]: https://github.com/Jaeminyx-Stoa/pydbsec/compare/v0.5.2...v1.0.0

## [0.5.2] - 2026-03-23

### Added

- Input validation for all API methods — `stock_code`, `quantity`, `price`, `date` parameters are validated before sending requests
- Async client tests (`AsyncPyDBSec` — balance, price, buy, portfolio_summary, context manager)
- Sell, cancel, chart, order_book API tests for domestic and overseas
- Validation test suite (stock_code, quantity, price, date edge cases)

### Fixed

- `__version__` mismatch between `__init__.py` and `pyproject.toml`

[0.5.2]: https://github.com/Jaeminyx-Stoa/pydbsec/compare/v0.5.1...v0.5.2

## [0.5.1] - 2026-03-21

### Changed

- Repository migrated from STOA-company to Jaeminyx-Stoa
- Updated all URLs, docs, and package metadata

[0.5.1]: https://github.com/Jaeminyx-Stoa/pydbsec/compare/v0.5.0...v0.5.1

## [0.5.0] - 2026-03-18

### Added

- **MCP Helper Functions** — Anthropic API 연동, MCP 클라이언트, 응답 파싱
  - `get_anthropic_tools()` — Claude API tool 정의 생성
  - `execute_tool()` — agentic loop에서 tool 로컬 실행
  - `DBSecMCPClient` — typed async MCP 클라이언트
  - `parse_stock_price()`, `parse_balance()`, `parse_order_result()`, `parse_order_book()` — 응답 파싱
- **npm wrapper** — `npx pydbsec-mcp`로 zero-config MCP 서버 실행
- **Documentation** — 제품 소개 랜딩 페이지, MCP 가이드, CLI/WebSocket/Rate Limiting 문서
- **STOA Company 브랜딩** — docs footer, 히어로 섹션

### Fixed

- Badge 렌더링 (마크다운 → HTML img 태그)

[0.5.0]: https://github.com/Jaeminyx-Stoa/pydbsec/compare/v0.4.0...v0.5.0

## [0.4.0] - 2026-03-17

### Added

- **MCP Server** — AI 어시스턴트 (Claude Desktop, Cursor 등)에서 DB증권 API 직접 호출
  - `pip install pydbsec[mcp]` → `pydbsec-mcp` 실행
  - Tools: get_stock_price, get_balance, get_portfolio_summary, place_order, get_order_book, get_chart
  - stdio transport (Claude Desktop config에 추가하여 사용)

[0.4.0]: https://github.com/Jaeminyx-Stoa/pydbsec/compare/v0.3.0...v0.4.0

## [0.3.0] - 2026-03-17

### Added

- **CLI tool** — `pydbsec` command for terminal-based API access
  - `pydbsec price 005930` — stock price lookup
  - `pydbsec balance` / `pydbsec balance --overseas` — balance inquiry
  - `pydbsec portfolio` — unified KR+US portfolio summary
  - `pydbsec buy/sell` — order placement
  - `--json` flag for raw JSON output
  - Credentials via `DBSEC_APP_KEY`/`DBSEC_APP_SECRET` env vars or `--key`/`--secret` flags
- **Rate limiting** (enabled by default) — token bucket per endpoint, respects DB Securities rate limits
- **`portfolio_summary()`** — unified domestic+overseas balance in a single call
- **Configurable logging** — `PyDBSec(log_level=logging.DEBUG)`

### Fixed

- All 60 mypy strict type errors resolved (0 errors on 19 source files)
- `base_url` propagation to `TokenManager`
- Async token refresh event loop blocking

[0.3.0]: https://github.com/Jaeminyx-Stoa/pydbsec/compare/v0.2.0...v0.3.0

## [0.2.0] - 2026-03-17

### Added

- **WebSocket real-time data**: `DBSecWebSocket` async client for live market data
  - Production `wss://openapi.dbsec.co.kr:7070`, sandbox `:17070`
  - TR codes: S00 (체결가), S01 (호가), IS0/IS1 (주문접수/체결), W00/W01 (ELW), U00 (업종지수)
  - Async iterator protocol (`async for msg in ws`)
  - Auto-reconnect with configurable retry
  - Optional dependency: `pip install pydbsec[ws]`
- `PyDBSec.ws` / `AsyncPyDBSec.ws` lazy property for WebSocket access

### Fixed

- `base_url` not propagated to `TokenManager` — token requests now use custom base_url
- Async token refresh blocked event loop — now uses `asyncio.to_thread()`

### Changed

- HTTP clients use persistent connection pools (`httpx.Client` / `AsyncClient`)
- Pagination results merged into single `dict` (Out1/Out2 lists concatenated)
- Return type simplified to `dict[str, Any]` (no more `dict | list[dict]` union)
- Error codes extracted to constants (`ERROR_TOKEN_EXPIRED`, etc.)

[0.2.0]: https://github.com/Jaeminyx-Stoa/pydbsec/compare/v0.1.0...v0.2.0

## [0.1.0] - 2026-03-17

### Added

- `PyDBSec` synchronous client
- `AsyncPyDBSec` asynchronous client
- OAuth2 token management with auto-refresh and thread-safe locking
- httpx-based HTTP client with automatic pagination (`cont_yn`/`cont_key`)
- **Domestic (국내) API**: balance, price, order_book, buy/sell/cancel, chart, deposit, orderable_quantity, transaction_history, trading_history, daily_trade_report, tickers
- **Overseas (해외) API**: balance, price, order_book, buy/sell/cancel, chart, deposit, orderable_quantity, transaction_history, tickers
- **Futures (선물) API**: balance
- Pydantic v2 typed response models: `DomesticBalance`, `OverseasBalance`, `FuturesBalance`, `StockPrice`, `OrderBook`, `OrderResult`
- Custom exceptions: `PyDBSecError`, `TokenError`, `TokenExpiredError`, `APIError`
- Context manager support (`with` / `async with`)
- `py.typed` marker (PEP 561)
- GitHub Actions CI (Python 3.10–3.13)
- PyPI trusted publishing workflow

[0.1.0]: https://github.com/Jaeminyx-Stoa/pydbsec/releases/tag/v0.1.0
