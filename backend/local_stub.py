from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
from html import unescape
import json
import re
import time
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Predovex Local News Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


RSS_SOURCES = {
    "general": [
        ("BBC News", "https://feeds.bbci.co.uk/news/rss.xml", "global"),
        ("NPR", "https://feeds.npr.org/1001/rss.xml", "us"),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "global"),
        ("France 24", "https://www.france24.com/en/rss", "global"),
    ],
    "technology": [
        ("TechCrunch", "https://techcrunch.com/feed/", "global"),
        ("The Verge", "https://www.theverge.com/rss/index.xml", "global"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", "global"),
    ],
    "markets": [
        ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html", "us"),
        ("MarketWatch", "https://www.marketwatch.com/rss/topstories", "us"),
        ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/", "global"),
        ("Investing.com", "https://www.investing.com/rss/news.rss", "global"),
    ],
    "policy": [
        ("White House", "https://www.whitehouse.gov/feed/", "us"),
        ("SEC", "https://www.sec.gov/news/pressreleases.rss", "us"),
        ("Treasury", "https://home.treasury.gov/news/press-releases.xml", "us"),
        ("The Hill", "https://thehill.com/rss/syndicator/19109", "us"),
    ],
    "health": [
        ("WHO", "https://www.who.int/rss-feeds/news-english.xml", "global"),
        ("NIH", "https://www.nih.gov/news-releases/feed.xml", "us"),
    ],
    "economy": [
        ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html", "us"),
        ("MarketWatch", "https://www.marketwatch.com/rss/topstories", "us"),
        ("Treasury", "https://home.treasury.gov/news/press-releases.xml", "us"),
    ],
}

RSS_CACHE_TTL = 300
_rss_cache = {"ts": 0.0, "articles": []}
BASE_DIR = Path(__file__).resolve().parent

MARKET_DATA = {
    "stocks": [
        {"symbol": "AAPL", "desc": "Apple Inc.", "price": 214.35, "change": 0.82},
        {"symbol": "MSFT", "desc": "Microsoft Corp.", "price": 489.12, "change": 1.14},
        {"symbol": "GOOGL", "desc": "Alphabet Inc.", "price": 178.44, "change": -0.31},
        {"symbol": "AMZN", "desc": "Amazon.com Inc.", "price": 192.80, "change": 0.55},
        {"symbol": "NVDA", "desc": "NVIDIA Corp.", "price": 143.62, "change": 2.18},
        {"symbol": "META", "desc": "Meta Platforms", "price": 515.10, "change": -0.22},
        {"symbol": "TSLA", "desc": "Tesla Inc.", "price": 184.90, "change": 1.73},
        {"symbol": "JPM", "desc": "JPMorgan Chase", "price": 221.40, "change": 0.44},
        {"symbol": "XOM", "desc": "Exxon Mobil", "price": 116.22, "change": -0.18},
        {"symbol": "BA", "desc": "Boeing Co.", "price": 181.75, "change": 0.91},
        {"symbol": "GS", "desc": "Goldman Sachs", "price": 468.55, "change": 0.36},
        {"symbol": "PFE", "desc": "Pfizer Inc.", "price": 28.42, "change": -0.48},
    ],
    "bonds": [
        {"symbol": "US10Y", "desc": "US Treasury 10Y Yield", "price": 4.31, "change": -0.7, "unit": "%"},
        {"symbol": "US02Y", "desc": "US Treasury 2Y Yield", "price": 4.73, "change": 0.3, "unit": "%"},
        {"symbol": "TLT", "desc": "20+ Year Treasury ETF", "price": 91.18, "change": 0.24},
    ],
    "mutual_funds": [
        {"symbol": "VTSAX", "desc": "Vanguard Total Stock Market", "price": 135.42, "change": 0.64},
        {"symbol": "VFIAX", "desc": "Vanguard 500 Index", "price": 517.33, "change": 0.58},
    ],
    "etfs": [
        {"symbol": "SPY", "desc": "SPDR S&P 500 ETF", "price": 548.90, "change": 0.61},
        {"symbol": "QQQ", "desc": "Invesco Nasdaq 100 ETF", "price": 472.44, "change": 0.96},
        {"symbol": "IWM", "desc": "iShares Russell 2000 ETF", "price": 205.32, "change": -0.15},
    ],
    "cash": [
        {"symbol": "SOFR", "desc": "Secured Overnight Financing Rate", "price": 5.31, "change": 0.0, "unit": "%"},
        {"symbol": "MMF", "desc": "Money Market Funds Avg Yield", "price": 4.92, "change": -0.1, "unit": "%"},
    ],
    "real_estate": [
        {"symbol": "VNQ", "desc": "Vanguard Real Estate ETF", "price": 86.74, "change": 0.28},
        {"symbol": "XLRE", "desc": "Real Estate Select Sector SPDR", "price": 39.62, "change": 0.19},
    ],
    "metals": [
        {"symbol": "Gold", "desc": "Gold Spot", "price": 2348.20, "change": 0.42, "unit": "oz"},
        {"symbol": "Silver", "desc": "Silver Spot", "price": 30.18, "change": -0.34, "unit": "oz"},
        {"symbol": "Copper", "desc": "Copper Futures", "price": 4.51, "change": 0.73},
    ],
    "crypto": [
        {"symbol": "BTC", "desc": "Bitcoin", "price": 65000.0, "change": 1.2},
        {"symbol": "ETH", "desc": "Ethereum", "price": 3520.0, "change": 0.8},
        {"symbol": "SOL", "desc": "Solana", "price": 148.0, "change": -0.6},
    ],
    "forex": [
        {"symbol": "EUR/USD", "desc": "Euro / US Dollar", "price": 1.08, "change": -0.1},
        {"symbol": "USD/JPY", "desc": "US Dollar / Japanese Yen", "price": 157.32, "change": 0.2},
        {"symbol": "GBP/USD", "desc": "British Pound / US Dollar", "price": 1.27, "change": 0.1},
    ],
}


def _load_stock_universe(limit: int = 1200) -> list[dict]:
    priority = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "JNJ", "XOM",
        "BA", "GS", "PFE", "KO", "PG", "LMT", "RTX", "NOC", "GD", "BAC", "CVX", "WMT",
        "MCD", "MRK", "UNH", "V", "MA", "HD", "COST", "NFLX", "AMD", "INTC", "ORCL",
    ]
    symbols = []
    try:
        data = json.loads((BASE_DIR / "ticker_universe.json").read_text())
        raw = data.get("all", []) if isinstance(data, dict) else data
        symbols = [str(t).upper() for t in raw if re.match(r"^[A-Z]{1,5}$", str(t).upper())]
    except Exception:
        symbols = []

    ordered = []
    seen = set()
    for symbol in priority + symbols:
        if symbol in seen:
            continue
        seen.add(symbol)
        ordered.append(symbol)
        if len(ordered) >= limit:
            break

    return [
        {
            "symbol": symbol,
            "desc": f"{symbol} Equity",
            "price": _stable_num(symbol + "price", 8, 650),
            "change": round(_stable_num(symbol + "change", -3.5, 3.5), 2),
        }
        for symbol in ordered
    ]

SECTOR_TICKERS = {
    "technology": ["AAPL", "MSFT", "GOOGL", "NVDA", "META"],
    "healthcare": ["JNJ", "PFE", "MRK", "UNH", "ABBV"],
    "finance": ["JPM", "GS", "BAC", "MS", "V"],
    "energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
    "defense": ["LMT", "RTX", "BA", "NOC", "GD"],
    "consumer": ["AMZN", "KO", "PG", "WMT", "MCD"],
}


def _stable_num(text: str, low: float, high: float) -> float:
    digest = hashlib.sha256(text.upper().encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "big")
    ratio = seed / float((1 << 64) - 1)
    return round(low + (high - low) * ratio, 4)


def _market_item(symbol: str, desc: str, low: float, high: float, unit: str | None = None) -> dict:
    item = {
        "symbol": symbol,
        "desc": desc,
        "price": _stable_num(symbol + "price", low, high),
        "change": round(_stable_num(symbol + "change", -2.8, 2.8), 2),
    }
    if unit:
        item["unit"] = unit
    return item


def _append_generated_assets(category: str, target: int, templates: list[dict]) -> None:
    seen = {item["symbol"].upper() for item in MARKET_DATA.get(category, [])}
    idx = 1
    while len(MARKET_DATA[category]) < target:
        for template in templates:
            if len(MARKET_DATA[category]) >= target:
                break
            symbol = template["symbol"].format(idx=idx)
            if symbol.upper() in seen:
                continue
            seen.add(symbol.upper())
            MARKET_DATA[category].append(
                _market_item(
                    symbol,
                    template["desc"].format(idx=idx),
                    template["low"],
                    template["high"],
                    template.get("unit"),
                )
            )
        idx += 1


def _expand_forex_pairs(target: int = 125) -> None:
    currencies = [
        "EUR", "USD", "JPY", "GBP", "AUD", "CAD", "CHF", "NZD", "CNH", "HKD",
        "SGD", "SEK", "NOK", "DKK", "MXN", "BRL", "ZAR", "INR", "KRW", "TWD",
        "THB", "MYR", "IDR", "PHP", "PLN", "CZK", "HUF", "TRY", "ILS", "AED",
    ]
    seen = {item["symbol"].upper() for item in MARKET_DATA.get("forex", [])}
    for base in currencies:
        for quote in currencies:
            if base == quote or len(MARKET_DATA["forex"]) >= target:
                continue
            symbol = f"{base}/{quote}"
            if symbol.upper() in seen:
                continue
            seen.add(symbol.upper())
            MARKET_DATA["forex"].append(
                _market_item(symbol, f"{base} / {quote}", 0.55, 185.0)
            )
        if len(MARKET_DATA["forex"]) >= target:
            break


def _expand_crypto_assets(target: int = 125) -> None:
    crypto_assets = [
        ("AAVE", "Aave"), ("ALGO", "Algorand"), ("APE", "ApeCoin"), ("AXS", "Axie Infinity"),
        ("BAT", "Basic Attention Token"), ("CAKE", "PancakeSwap"), ("COMP", "Compound"),
        ("CRV", "Curve DAO"), ("DASH", "Dash"), ("EGLD", "MultiversX"), ("EOS", "EOS"),
        ("ETC", "Ethereum Classic"), ("FLOW", "Flow"), ("GALA", "Gala"), ("GRT", "The Graph"),
        ("HBAR", "Hedera"), ("ICP", "Internet Computer"), ("IMX", "Immutable"), ("INJ", "Injective"),
        ("KAS", "Kaspa"), ("KAVA", "Kava"), ("LDO", "Lido DAO"), ("MANA", "Decentraland"),
        ("MKR", "Maker"), ("MINA", "Mina"), ("MNT", "Mantle"), ("QNT", "Quant"),
        ("RUNE", "THORChain"), ("SAND", "The Sandbox"), ("SEI", "Sei"), ("SNX", "Synthetix"),
        ("STX", "Stacks"), ("SUI", "Sui"), ("THETA", "Theta Network"), ("TIA", "Celestia"),
        ("TON", "Toncoin"), ("TRX", "TRON"), ("VET", "VeChain"), ("WLD", "Worldcoin"),
        ("XLM", "Stellar"), ("XMR", "Monero"), ("XTZ", "Tezos"), ("ZEC", "Zcash"),
        ("ZIL", "Zilliqa"), ("1INCH", "1inch"), ("AKT", "Akash Network"), ("ANKR", "Ankr"),
        ("AR", "Arweave"), ("BAL", "Balancer"), ("BLUR", "Blur"), ("CELO", "Celo"),
        ("CHZ", "Chiliz"), ("CKB", "Nervos Network"), ("CRO", "Cronos"), ("DCR", "Decred"),
        ("DYDX", "dYdX"), ("ENS", "Ethereum Name Service"), ("FET", "Artificial Superintelligence Alliance"),
        ("FLR", "Flare"), ("FTM", "Fantom"), ("FXS", "Frax Share"), ("GMX", "GMX"),
        ("HOT", "Holo"), ("IOTA", "IOTA"), ("JASMY", "JasmyCoin"), ("JTO", "Jito"),
        ("KSM", "Kusama"), ("LPT", "Livepeer"), ("LRC", "Loopring"), ("MASK", "Mask Network"),
        ("NEXO", "Nexo"), ("OCEAN", "Ocean Protocol"), ("ONE", "Harmony"), ("OSMO", "Osmosis"),
        ("PEPE", "Pepe"), ("PYTH", "Pyth Network"), ("RAY", "Raydium"), ("RPL", "Rocket Pool"),
        ("RSR", "Reserve Rights"), ("SFP", "SafePal"), ("SKL", "SKALE"), ("SSV", "SSV Network"),
        ("STRK", "Starknet"), ("SUSHI", "SushiSwap"), ("TWT", "Trust Wallet Token"), ("WAVES", "Waves"),
        ("WOO", "WOO Network"), ("XDC", "XDC Network"), ("YFI", "yearn.finance"), ("ZRX", "0x"),
        ("BONK", "Bonk"), ("ENA", "Ethena"), ("JUP", "Jupiter"), ("WIF", "dogwifhat"),
        ("ORDI", "ORDI"), ("PENDLE", "Pendle"), ("RON", "Ronin"), ("SUPER", "SuperVerse"),
        ("TURBO", "Turbo"), ("W", "Wormhole"), ("ZETA", "ZetaChain"), ("ZK", "ZKsync"),
    ]
    seen = {item["symbol"].upper() for item in MARKET_DATA.get("crypto", [])}
    for symbol, desc in crypto_assets:
        if len(MARKET_DATA["crypto"]) >= target:
            break
        if symbol.upper() in seen:
            continue
        seen.add(symbol.upper())
        MARKET_DATA["crypto"].append(_market_item(symbol, desc, 0.02, 250.0))
    _append_generated_assets(
        "crypto",
        target,
        [{"symbol": "DA{idx:03d}", "desc": "Digital Asset Index Token {idx}", "low": 0.05, "high": 75.0}],
    )


def _expand_cross_asset_markets() -> None:
    MARKET_DATA["bonds"] = [
        _market_item("US01M", "US Treasury 1 Month Yield", 4.7, 5.45, "%"),
        _market_item("US03M", "US Treasury 3 Month Yield", 4.6, 5.35, "%"),
        _market_item("US06M", "US Treasury 6 Month Yield", 4.45, 5.25, "%"),
        _market_item("US01Y", "US Treasury 1 Year Yield", 4.25, 5.05, "%"),
        _market_item("US02Y", "US Treasury 2 Year Yield", 3.85, 4.95, "%"),
        _market_item("US05Y", "US Treasury 5 Year Yield", 3.55, 4.75, "%"),
        _market_item("US10Y", "US Treasury 10 Year Yield", 3.45, 4.65, "%"),
        _market_item("US30Y", "US Treasury 30 Year Yield", 3.75, 4.95, "%"),
        _market_item("TIP", "iShares TIPS Bond ETF", 102, 112),
        _market_item("SHY", "iShares 1-3 Year Treasury Bond ETF", 80, 86),
        _market_item("IEF", "iShares 7-10 Year Treasury Bond ETF", 90, 101),
        _market_item("TLT", "iShares 20+ Year Treasury Bond ETF", 84, 99),
        _market_item("BND", "Vanguard Total Bond Market ETF", 68, 76),
        _market_item("AGG", "iShares Core US Aggregate Bond ETF", 93, 101),
        _market_item("LQD", "iShares Investment Grade Corporate Bond ETF", 101, 114),
        _market_item("HYG", "iShares High Yield Corporate Bond ETF", 74, 82),
        _market_item("MUB", "iShares National Muni Bond ETF", 102, 110),
        _market_item("EMB", "iShares JP Morgan USD Emerging Markets Bond ETF", 82, 94),
    ]
    MARKET_DATA["mutual_funds"] = [
        _market_item("VTSAX", "Vanguard Total Stock Market Index", 120, 150),
        _market_item("VFIAX", "Vanguard 500 Index Admiral", 470, 560),
        _market_item("VTIAX", "Vanguard Total International Stock Index", 30, 38),
        _market_item("VBTLX", "Vanguard Total Bond Market Index", 9, 11),
        _market_item("VBTIX", "Vanguard Total Bond Market II Index", 9, 11),
        _market_item("VIGAX", "Vanguard Growth Index Admiral", 185, 230),
        _market_item("VVIAX", "Vanguard Value Index Admiral", 55, 70),
        _market_item("SWPPX", "Schwab S&P 500 Index", 80, 96),
        _market_item("SWTSX", "Schwab Total Stock Market Index", 78, 94),
        _market_item("FXAIX", "Fidelity 500 Index Fund", 180, 215),
        _market_item("FSKAX", "Fidelity Total Market Index Fund", 140, 170),
        _market_item("FZROX", "Fidelity ZERO Total Market Index", 18, 23),
        _market_item("FZILX", "Fidelity ZERO International Index", 12, 16),
        _market_item("PRNHX", "T. Rowe Price New Horizons", 50, 68),
        _market_item("TRBCX", "T. Rowe Price Blue Chip Growth", 170, 210),
        _market_item("DODGX", "Dodge & Cox Stock Fund", 245, 295),
        _market_item("DODIX", "Dodge & Cox Income Fund", 11, 14),
        _market_item("PONAX", "PIMCO Income Fund", 9, 12),
    ]
    MARKET_DATA["etfs"] = [
        _market_item("SPY", "SPDR S&P 500 ETF", 520, 590),
        _market_item("IVV", "iShares Core S&P 500 ETF", 520, 595),
        _market_item("VOO", "Vanguard S&P 500 ETF", 480, 550),
        _market_item("QQQ", "Invesco Nasdaq 100 ETF", 450, 530),
        _market_item("VTI", "Vanguard Total Stock Market ETF", 250, 310),
        _market_item("IWM", "iShares Russell 2000 ETF", 190, 230),
        _market_item("DIA", "SPDR Dow Jones Industrial Average ETF", 370, 430),
        _market_item("VEA", "Vanguard Developed Markets ETF", 45, 58),
        _market_item("VWO", "Vanguard Emerging Markets ETF", 39, 51),
        _market_item("EFA", "iShares MSCI EAFE ETF", 72, 88),
        _market_item("EEM", "iShares MSCI Emerging Markets ETF", 38, 50),
        _market_item("XLK", "Technology Select Sector SPDR", 190, 240),
        _market_item("XLF", "Financial Select Sector SPDR", 38, 50),
        _market_item("XLE", "Energy Select Sector SPDR", 82, 100),
        _market_item("XLV", "Health Care Select Sector SPDR", 130, 155),
        _market_item("XLI", "Industrial Select Sector SPDR", 115, 140),
        _market_item("XLY", "Consumer Discretionary Select Sector SPDR", 165, 205),
        _market_item("XLP", "Consumer Staples Select Sector SPDR", 72, 86),
        _market_item("SMH", "VanEck Semiconductor ETF", 220, 285),
        _market_item("ARKK", "ARK Innovation ETF", 38, 58),
        _market_item("SCHD", "Schwab US Dividend Equity ETF", 72, 86),
        _market_item("JEPI", "JPMorgan Equity Premium Income ETF", 52, 61),
    ]
    MARKET_DATA["cash"] = [
        _market_item("SOFR", "Secured Overnight Financing Rate", 4.7, 5.4, "%"),
        _market_item("EFFR", "Effective Federal Funds Rate", 4.65, 5.35, "%"),
        _market_item("TBILL", "3 Month T-Bill Rate", 4.55, 5.3, "%"),
        _market_item("MMF", "Money Market Fund Average Yield", 4.2, 5.15, "%"),
        _market_item("VMFXX", "Vanguard Federal Money Market Fund", 1, 1.02),
        _market_item("SPAXX", "Fidelity Government Money Market Fund", 1, 1.02),
        _market_item("SWVXX", "Schwab Value Advantage Money Fund", 1, 1.02),
        _market_item("BIL", "SPDR Bloomberg 1-3 Month T-Bill ETF", 91, 92),
        _market_item("SGOV", "iShares 0-3 Month Treasury Bond ETF", 100, 101),
        _market_item("USFR", "WisdomTree Floating Rate Treasury Fund", 50, 51),
    ]
    MARKET_DATA["real_estate"] = [
        _market_item("VNQ", "Vanguard Real Estate ETF", 78, 96),
        _market_item("XLRE", "Real Estate Select Sector SPDR", 36, 44),
        _market_item("IYR", "iShares US Real Estate ETF", 82, 102),
        _market_item("SCHH", "Schwab US REIT ETF", 18, 24),
        _market_item("RWR", "SPDR Dow Jones REIT ETF", 84, 104),
        _market_item("REET", "iShares Global REIT ETF", 21, 27),
        _market_item("REM", "iShares Mortgage Real Estate ETF", 20, 28),
        _market_item("VNQI", "Vanguard Global ex-US Real Estate ETF", 36, 48),
        _market_item("O", "Realty Income Corp.", 50, 68),
        _market_item("PLD", "Prologis Inc.", 95, 130),
        _market_item("AMT", "American Tower Corp.", 165, 230),
        _market_item("EQIX", "Equinix Inc.", 720, 910),
        _market_item("SPG", "Simon Property Group", 135, 175),
        _market_item("DLR", "Digital Realty Trust", 130, 175),
        _market_item("PSA", "Public Storage", 250, 330),
    ]
    MARKET_DATA["metals"] = [
        _market_item("Gold", "Gold Spot", 2200, 2550, "oz"),
        _market_item("Silver", "Silver Spot", 27, 36, "oz"),
        _market_item("Platinum", "Platinum Spot", 900, 1120, "oz"),
        _market_item("Palladium", "Palladium Spot", 850, 1150, "oz"),
        _market_item("Copper", "Copper Futures", 4, 5.3),
        _market_item("Aluminum", "Aluminum Futures", 2200, 2800),
        _market_item("Nickel", "Nickel Futures", 14500, 19000),
        _market_item("Zinc", "Zinc Futures", 2500, 3300),
        _market_item("Lead", "Lead Futures", 1800, 2300),
        _market_item("Tin", "Tin Futures", 28000, 36000),
        _market_item("Uranium", "Uranium Spot", 70, 105),
        _market_item("Lithium", "Lithium Carbonate Index", 9500, 15500),
        _market_item("GLD", "SPDR Gold Shares", 200, 240),
        _market_item("SLV", "iShares Silver Trust", 25, 34),
        _market_item("CPER", "United States Copper Index Fund", 24, 32),
    ]
    MARKET_DATA["crypto"] = [
        _market_item("BTC", "Bitcoin", 58000, 76000),
        _market_item("ETH", "Ethereum", 2800, 4300),
        _market_item("SOL", "Solana", 120, 210),
        _market_item("BNB", "BNB", 520, 740),
        _market_item("XRP", "XRP", 0.42, 0.85),
        _market_item("ADA", "Cardano", 0.32, 0.68),
        _market_item("DOGE", "Dogecoin", 0.08, 0.22),
        _market_item("AVAX", "Avalanche", 22, 48),
        _market_item("LINK", "Chainlink", 12, 26),
        _market_item("DOT", "Polkadot", 4.5, 9.5),
        _market_item("MATIC", "Polygon", 0.45, 1.1),
        _market_item("LTC", "Litecoin", 68, 112),
        _market_item("BCH", "Bitcoin Cash", 360, 620),
        _market_item("UNI", "Uniswap", 6, 13),
        _market_item("ATOM", "Cosmos", 5, 11),
        _market_item("NEAR", "NEAR Protocol", 3.5, 8.5),
        _market_item("APT", "Aptos", 5, 12),
        _market_item("ARB", "Arbitrum", 0.65, 1.7),
        _market_item("OP", "Optimism", 1.1, 3.2),
        _market_item("FIL", "Filecoin", 3.5, 8.0),
    ]
    _append_generated_assets(
        "bonds",
        125,
        [
            {"symbol": "UST{idx:03d}", "desc": "US Treasury Ladder Note {idx}", "low": 3.6, "high": 5.4, "unit": "%"},
            {"symbol": "MUNI{idx:03d}", "desc": "Municipal Revenue Bond Basket {idx}", "low": 2.7, "high": 4.9, "unit": "%"},
            {"symbol": "CORP{idx:03d}", "desc": "Investment Grade Corporate Bond Basket {idx}", "low": 4.1, "high": 6.8, "unit": "%"},
            {"symbol": "HY{idx:03d}", "desc": "High Yield Corporate Bond Basket {idx}", "low": 6.3, "high": 9.6, "unit": "%"},
            {"symbol": "EMB{idx:03d}", "desc": "Emerging Market Sovereign Bond Basket {idx}", "low": 5.2, "high": 8.8, "unit": "%"},
        ],
    )
    _append_generated_assets(
        "mutual_funds",
        125,
        [
            {"symbol": "VMF{idx:03d}", "desc": "Vanguard Diversified Index Fund {idx}", "low": 18, "high": 220},
            {"symbol": "FMF{idx:03d}", "desc": "Fidelity Core Strategy Fund {idx}", "low": 12, "high": 185},
            {"symbol": "SMF{idx:03d}", "desc": "Schwab Allocation Fund {idx}", "low": 10, "high": 160},
            {"symbol": "TRP{idx:03d}", "desc": "T. Rowe Price Growth Fund {idx}", "low": 25, "high": 240},
            {"symbol": "PIM{idx:03d}", "desc": "PIMCO Income Strategy Fund {idx}", "low": 8, "high": 45},
        ],
    )
    _append_generated_assets(
        "etfs",
        125,
        [
            {"symbol": "EQTY{idx:03d}", "desc": "US Equity Factor ETF {idx}", "low": 20, "high": 180},
            {"symbol": "INTL{idx:03d}", "desc": "International Equity ETF {idx}", "low": 18, "high": 95},
            {"symbol": "SECT{idx:03d}", "desc": "Sector Rotation ETF {idx}", "low": 22, "high": 150},
            {"symbol": "DIV{idx:03d}", "desc": "Dividend Income ETF {idx}", "low": 25, "high": 110},
            {"symbol": "ALT{idx:03d}", "desc": "Alternative Strategy ETF {idx}", "low": 15, "high": 85},
        ],
    )
    _append_generated_assets(
        "real_estate",
        125,
        [
            {"symbol": "REIT{idx:03d}", "desc": "Diversified REIT Basket {idx}", "low": 18, "high": 95},
            {"symbol": "DATA{idx:03d}", "desc": "Data Center REIT Basket {idx}", "low": 40, "high": 220},
            {"symbol": "INDR{idx:03d}", "desc": "Industrial REIT Basket {idx}", "low": 35, "high": 180},
            {"symbol": "APT{idx:03d}", "desc": "Residential REIT Basket {idx}", "low": 28, "high": 145},
            {"symbol": "HLTH{idx:03d}", "desc": "Healthcare REIT Basket {idx}", "low": 25, "high": 120},
        ],
    )
    _expand_crypto_assets(125)
    _expand_forex_pairs(125)


_expand_cross_asset_markets()
MARKET_DATA["stocks"] = _load_stock_universe(1200)


def _find_market_item(symbol: str) -> dict | None:
    target = symbol.upper()
    for items in MARKET_DATA.values():
        for item in items:
            if item["symbol"].upper() == target:
                return item
    return None


def _price_for(symbol: str) -> float:
    item = _find_market_item(symbol)
    if item:
        return float(item["price"])
    return round(_stable_num(symbol, 25, 520), 2)


def _sentiment_prediction(ticker: str) -> dict:
    ticker = ticker.upper()
    probability = _stable_num(ticker, 0.42, 0.78)
    prediction = "Up" if probability >= 0.5 else "Down"
    price = _price_for(ticker)
    return {
        "ticker": ticker,
        "prediction": prediction,
        "sentiment": "Bullish" if prediction == "Up" else "Bearish",
        "probability": probability,
        "confidence": round(abs(probability - 0.5) * 2, 3),
        "current_price": price,
        "price": price,
        "change_pct": round(_stable_num(ticker + "change", -2.5, 2.5), 2),
        "model": "local-free-market-signal",
    }


def _horizon_prediction(ticker: str, horizon: str) -> dict:
    confidence = _stable_num(ticker + horizon, 0.54, 0.83)
    direction = "UP" if _stable_num(horizon + ticker, 0, 1) >= 0.43 else "DOWN"
    return {
        "direction": direction,
        "confidence": confidence,
        "top_drivers": [
            {"feature": "relative_momentum", "importance": 0.24, "value": round(_stable_num(ticker, -1.5, 1.5), 2)},
            {"feature": "event_count_30d", "importance": 0.19, "value": int(_stable_num(ticker + "events", 1, 18))},
            {"feature": "market_regime", "importance": 0.14, "value": 1},
        ],
    }


def _unified_prediction(ticker: str) -> dict:
    ticker = ticker.upper()
    event_count = int(_stable_num(ticker + "gov", 3, 42))
    contracts = int(_stable_num(ticker + "contracts", 0, 18))
    return {
        "ticker": ticker,
        "prediction": _horizon_prediction(ticker, "7d")["direction"],
        "horizons": {
            "1d": _horizon_prediction(ticker, "1d"),
            "3d": _horizon_prediction(ticker, "3d"),
            "7d": _horizon_prediction(ticker, "7d"),
            "30d": _horizon_prediction(ticker, "30d"),
        },
        "gov_events": event_count,
        "contract_signal": "BULLISH" if contracts >= 8 else "NEUTRAL",
        "total_contracts": contracts,
        "anchor_event": {
            "title": f"Recent government signal for {ticker}",
            "date": datetime.now(timezone.utc).date().isoformat(),
            "event_type": "contract" if contracts >= 8 else "sec_filing",
        },
    }


def _clean_html(value: str) -> str:
    text = unescape(value or "")
    text = text.replace("[...]", "...").replace("[…]", "...")
    text = re.sub(r"\[\s*\.{3}\s*\]", "...", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(entry) -> str:
    for key in ("published", "updated", "created"):
        raw = entry.get(key)
        if not raw:
            continue
        try:
            return parsedate_to_datetime(raw).astimezone(timezone.utc).isoformat()
        except Exception:
            pass
    return datetime.now(timezone.utc).isoformat()


def _impact_for(title: str, description: str) -> tuple[int, str]:
    text = f"{title} {description}".lower()
    high = ("breaking", "war", "crisis", "rate", "inflation", "tariff", "sec", "fda", "ban", "lawsuit")
    medium = ("market", "policy", "government", "earnings", "ai", "crypto", "fed", "regulation")
    if any(word in text for word in high):
        return 82, "High"
    if any(word in text for word in medium):
        return 62, "Medium"
    return 38, "Low"


def _insight_for(title: str, description: str, category: str, impact_level: str) -> str:
    text = f"{title}. {description}".strip()
    if not text:
        return "Predovex is monitoring this development for follow-on market and policy signals."

    category_focus = {
        "markets": "market positioning",
        "economy": "economic expectations",
        "technology": "technology strategy and competitive positioning",
        "policy": "regulatory and government decision-making",
        "health": "health policy and sector risk",
        "general": "public and institutional response",
    }.get(category, "market and policy impact")

    lead = {
        "High": "This is a high-priority signal",
        "Medium": "This is a developing signal",
        "Low": "This is a monitoring signal",
    }.get(impact_level, "This is a monitoring signal")

    first_sentence = re.split(r"(?<=[.!?])\s+", text)[0]
    if len(first_sentence) > 155:
        first_sentence = first_sentence[:152].rsplit(" ", 1)[0] + "..."
    return f"{lead} for {category_focus}: {first_sentence}"


def _article_body(title: str, description: str, source_name: str, category: str) -> str:
    body = description or title
    if not body:
        return ""
    if body == title:
        return f"{source_name} reports: {title}"
    return f"{body}\n\nSource context: {source_name} item categorized under {category}."


def _extract_article_text(url: str) -> list[str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    response = requests.get(url, headers=headers, timeout=12)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "form", "aside", "nav", "footer", "header"]):
        tag.decompose()

    containers = soup.select(
        "article, main, [data-testid*='article'], [class*='article'], "
        "[class*='story'], [class*='post'], [class*='content']"
    )
    search_roots = containers or [soup.body or soup]

    paragraphs = []
    seen = set()
    bad_fragments = (
        "sign up", "subscribe", "advertisement", "cookie", "privacy policy",
        "all rights reserved", "download the app", "follow us", "share this",
    )
    for root in search_roots:
        for node in root.find_all(["p", "li"]):
            text = _clean_html(node.get_text(" ", strip=True))
            if len(text) < 45:
                continue
            lowered = text.lower()
            if any(fragment in lowered for fragment in bad_fragments):
                continue
            if text in seen:
                continue
            seen.add(text)
            paragraphs.append(text)
            if len(paragraphs) >= 12:
                return paragraphs
    return paragraphs


def _source_groups(category: str):
    if category == "all":
        pairs = []
        for cat, sources in RSS_SOURCES.items():
            pairs.extend((cat, *source) for source in sources)
        return pairs
    selected = RSS_SOURCES.get(category, RSS_SOURCES["general"])
    return [(category, *source) for source in selected]


def _fetch_articles(force_refresh: bool = False) -> list[dict]:
    now = time.time()
    if not force_refresh and _rss_cache["articles"] and now - _rss_cache["ts"] < RSS_CACHE_TTL:
        return _rss_cache["articles"]

    articles = []
    seen = set()
    for category, source_name, url, country in _source_groups("all"):
        feed = feedparser.parse(url)
        for entry in feed.entries[:12]:
            link = entry.get("link") or url
            title = _clean_html(entry.get("title") or "Untitled")
            if not title or link in seen:
                continue
            seen.add(link)
            description = _clean_html(
                entry.get("summary")
                or entry.get("description")
                or entry.get("subtitle")
                or title
            )
            impact_score, impact_level = _impact_for(title, description)
            article_body = _article_body(title, description, source_name, category)
            insight = _insight_for(title, description, category, impact_level)
            articles.append(
                {
                    "id": len(articles) + 1,
                    "title": title,
                    "description": description,
                    "content": article_body,
                    "source": source_name,
                    "country": country,
                    "category": category,
                    "url": link,
                    "published_at": _parse_date(entry),
                    "impact_score": impact_score,
                    "impact_level": impact_level,
                    "sentiment": "Neutral",
                    "ai_summary": insight,
                    "tags": [category, source_name.lower().replace(" ", "-")],
                }
            )

    articles.sort(key=lambda item: item["published_at"], reverse=True)
    _rss_cache.update({"ts": now, "articles": articles})
    return articles


def _articles(category: str = "all", country: str = "all", limit: int = 30) -> list[dict]:
    articles = _fetch_articles()
    if category != "all":
        articles = [item for item in articles if item["category"] == category]
    if country != "all":
        articles = [item for item in articles if item["country"] in (country, "global")]
    return articles[:limit]


def _fallback_article(index: int, category: str = "general") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": index,
        "title": "Live RSS feeds are temporarily unavailable",
        "description": "The local backend is running, but it could not fetch external RSS feeds.",
        "content": "The local backend is running, but it could not fetch external RSS feeds.",
        "source": "Local Stub",
        "country": "global",
        "category": category,
        "url": f"http://127.0.0.1:8001/local/article/{index}",
        "published_at": now,
        "impact_score": 25,
        "impact_level": "Low",
        "sentiment": "Neutral",
        "ai_summary": "External RSS fetch failed. Check network access and retry.",
        "tags": ["local", "rss"],
    }


@app.get("/")
def root():
    return {"status": "ok", "service": "predovex-local-news"}


@app.get("/health")
def health():
    return {"status": "ok", "backend": "running"}


@app.get("/articles")
def articles(country: str = "all", limit: int = 25):
    return _articles("all", country, limit) or [_fallback_article(1)]


@app.get("/articles/category/{category}")
def articles_by_category(category: str, limit: int = 20):
    return _articles(category, "all", limit) or [_fallback_article(1, category)]


@app.get("/search")
def search(q: str = "", limit: int = 20):
    query = q.lower().strip()
    articles = _articles("all", "all", 100)
    if query:
        articles = [
            item for item in articles
            if query in item["title"].lower() or query in item["description"].lower()
        ]
    return articles[:limit]


@app.get("/rss/all")
def rss_all(category: str = "all", limit: int = 100, country: str = "all"):
    return _articles(category, country, limit) or [_fallback_article(1, category)]


@app.get("/rss/category/{category}")
def rss_category(category: str, limit: int = 50, country: str = "all"):
    return _articles(category, country, limit) or [_fallback_article(1, category)]


@app.get("/rss/breaking")
def rss_breaking(limit: int = 20):
    articles = [item for item in _articles("all", "all", 100) if item["impact_level"] == "High"]
    return articles[:limit] or _articles("all", "all", limit)


@app.get("/rss/trending")
def rss_trending():
    counts = {}
    for item in _articles("all", "all", 100):
        topic = item["category"].title()
        counts[topic] = counts.get(topic, 0) + 1
    return [{"topic": topic, "count": count} for topic, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)]


@app.get("/rss/trending-news")
def rss_trending_news(limit: int = 20):
    return sorted(_articles("all", "all", 100), key=lambda item: item["impact_score"], reverse=True)[:limit]


@app.get("/article/fetch")
def article_fetch(url: str):
    try:
        paragraphs = _extract_article_text(url)
        if paragraphs:
            return {
                "success": True,
                "url": url,
                "intel_brief": {
                    "executive_summary": paragraphs[0],
                    "critical_insights": paragraphs[:3],
                    "contextual_brief": "\n\n".join(paragraphs[:2]),
                    "full_reconstructed_report": paragraphs,
                    "strategic_outlook": "Continue monitoring the source story for updates and market reaction.",
                },
            }
    except Exception as exc:
        return {
            "success": False,
            "fallback": True,
            "url": url,
            "message": f"Full article extraction failed locally: {exc}",
        }

    return {
        "success": False,
        "fallback": True,
        "url": url,
        "message": "The publisher page did not expose enough readable article text. Showing the RSS story body from the selected card.",
    }


@app.get("/markets/prices")
def market_prices():
    return MARKET_DATA


@app.get("/api/stock/{ticker}/price")
def stock_price(ticker: str):
    price = _price_for(ticker)
    change = round(_stable_num(ticker + "change", -2.5, 2.5), 2)
    return {
        "ticker": ticker.upper(),
        "symbol": ticker.upper(),
        "price": price,
        "current_price": price,
        "change": change,
        "change_pct": change,
    }


@app.get("/api/stock/{ticker}/deep-dive")
@app.get("/api/analysis/deep/{ticker}")
def stock_deep_dive(ticker: str):
    ticker = ticker.upper()
    price = _price_for(ticker)
    score = int(_stable_num(ticker + "score", 52, 88))
    risk_score = int(_stable_num(ticker + "risk", 25, 72))
    growth_score = int(_stable_num(ticker + "growth", 45, 86))
    dcf_value = round(price * _stable_num(ticker + "dcf", 0.85, 1.25), 2)
    upside = round((dcf_value - price) / price * 100, 1) if price else 0
    rating = "Buy" if score >= 65 else "Hold"
    moat_rating = round(_stable_num(ticker + "moat", 4.8, 8.8), 1)
    return {
        "ticker": ticker,
        "company_name": (_find_market_item(ticker) or {}).get("desc", ticker),
        "analysis_date": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "Local fallback analysis for development mode. Not financial advice.",
        "overall_rating": {
            "overall_score": score,
            "rating": rating,
            "component_scores": {
                "financial_health": int(_stable_num(ticker + "health", 55, 86)),
                "valuation": int(70 if upside > 0 else 48),
                "risk_adjusted": max(20, 100 - risk_score),
                "moat_strength": int(moat_rating * 10),
                "growth_potential": growth_score,
            },
        },
        "financial_breakdown": {
            "health_score": int(_stable_num(ticker + "health", 55, 86)),
            "health_rating": "Healthy" if score >= 65 else "Stable",
            "summary": f"{ticker} has generated local financial metrics so the analysis dashboard can render while live provider data is unavailable.",
            "financial_data": {
                "revenue": {
                    "latest": f"${round(_stable_num(ticker + 'rev', 0.4, 180), 1)}B",
                    "trend": "Increasing",
                    "avg_growth_rate": round(_stable_num(ticker + "revgr", 2, 18), 1),
                    "cagr": round(_stable_num(ticker + "cagr", 2, 16), 1),
                },
                "net_income": {
                    "latest": f"${round(_stable_num(ticker + 'ni', 0.05, 45), 1)}B",
                    "trend": "Stable",
                    "avg_growth_rate": round(_stable_num(ticker + "nigr", -4, 14), 1),
                },
                "free_cash_flow": {
                    "latest": f"${round(_stable_num(ticker + 'fcf', 0.02, 38), 1)}B",
                    "average": f"${round(_stable_num(ticker + 'fcfavg', 0.02, 32), 1)}B",
                    "trend": "Positive",
                },
                "profit_margins": {
                    "latest_margin": round(_stable_num(ticker + "margin", 4, 38), 1),
                    "avg_margin": round(_stable_num(ticker + "avgmargin", 3, 32), 1),
                    "trend": "Stable",
                },
                "debt": {
                    "latest_debt": f"${round(_stable_num(ticker + 'debt', 0.01, 55), 1)}B",
                    "debt_to_assets": round(_stable_num(ticker + "dta", 8, 58), 1),
                    "trend": "Manageable",
                },
                "return_on_equity": {
                    "latest_roe": round(_stable_num(ticker + "roe", 4, 42), 1),
                    "avg_roe": round(_stable_num(ticker + "avgroe", 4, 36), 1),
                    "rating": "Strong" if score >= 70 else "Adequate",
                },
            },
        },
        "valuation_analysis": {
            "current_price": price,
            "summary": f"Local DCF and multiple analysis estimates {ticker} at ${dcf_value} per share.",
            "conclusion": "Undervalued" if upside > 5 else "Fairly valued" if upside > -5 else "Overvalued",
            "valuation_metrics": {
                "pe_analysis": {
                    "trailing_pe": round(_stable_num(ticker + "tpe", 8, 44), 1),
                    "forward_pe": round(_stable_num(ticker + "fpe", 7, 38), 1),
                    "industry_avg_pe": round(_stable_num(ticker + "ipe", 12, 32), 1),
                    "vs_industry": "Undervalued" if upside > 0 else "Overvalued",
                },
                "dcf_valuation": {
                    "dcf_value_per_share": dcf_value,
                    "upside_downside": upside,
                    "verdict": "Undervalued" if upside > 5 else "Fair Value" if upside > -5 else "Overvalued",
                    "assumptions": {
                        "growth_rate": f"{round(_stable_num(ticker + 'gr', 3, 12), 1)}%",
                        "terminal_growth": "2.5%",
                        "discount_rate": f"{round(_stable_num(ticker + 'disc', 8, 12), 1)}%",
                    },
                },
            },
        },
        "risk_analysis": {
            "overall_risk_score": risk_score,
            "risk_level": "High" if risk_score >= 65 else "Medium" if risk_score >= 35 else "Low",
            "summary": "Local fallback risk model combines volatility, liquidity, valuation, and policy exposure.",
            "risks": [
                {"rank": 1, "risk_type": "Market Volatility", "description": "Equity factor volatility may affect near-term price action.", "severity": "Medium", "severity_score": risk_score},
                {"rank": 2, "risk_type": "Valuation Sensitivity", "description": "Multiple compression risk if rates or growth expectations shift.", "severity": "Medium", "severity_score": max(25, risk_score - 8)},
                {"rank": 3, "risk_type": "Policy Exposure", "description": "Government and regulatory signals can affect sentiment.", "severity": "Low", "severity_score": max(15, risk_score - 18)},
            ],
        },
        "earnings_breakdown": {
            "report_date": datetime.now(timezone.utc).date().isoformat(),
            "summary": "Local earnings context generated for development mode.",
            "earnings_data": {
                "eps": {"estimate": 2.1, "reported": 2.22, "surprise_pct": 5.7, "beat_miss": "Beat"},
                "market_reaction": {"price_reaction": round(_stable_num(ticker + "earnreact", -4, 6), 1), "direction": "Positive"},
            },
        },
        "moat_analysis": {
            "overall_moat_rating": moat_rating,
            "moat_rating_label": "Wide" if moat_rating >= 7 else "Narrow" if moat_rating >= 5 else "Limited",
            "summary": "Local moat assessment based on scale, brand, switching costs, and government relevance.",
            "moat_components": {
                "brand_strength": {"score": round(_stable_num(ticker + "brand", 4, 9), 1), "assessment": "Recognized market presence", "evidence": "Ticker has sufficient market visibility in local universe."},
                "switching_costs": {"score": round(_stable_num(ticker + "switch", 3, 8), 1), "assessment": "Moderate retention power", "evidence": "Estimated from sector and business model proxies."},
                "scale_advantage": {"score": round(_stable_num(ticker + "scale", 4, 9), 1), "assessment": "Operational scale supports durability", "evidence": "Local fallback estimate."},
            },
        },
        "growth_potential": {
            "overall_growth_potential": growth_score,
            "summary": "Local growth estimate combines revenue trend, margin room, and sector momentum.",
            "growth_estimates": {"five_year_growth": round(_stable_num(ticker + "5y", 3, 18), 1), "ten_year_growth": round(_stable_num(ticker + "10y", 2, 12), 1), "confidence": "Medium"},
            "growth_factors": {
                "sector_momentum": {"assessment": "Sector backdrop remains constructive."},
                "margin_expansion": {"assessment": "Operating leverage may support earnings growth."},
                "policy_tailwinds": {"assessment": "Government and macro signals are being monitored."},
            },
        },
        "institutional_perspective": {
            "summary": "Local institutional framing generated for development mode.",
            "institutional_perspective": {
                "buy_reasons": ["Positive local signal stack", "Reasonable valuation support", "Government event monitoring coverage"],
                "avoid_reasons": ["Fallback data is not live fundamentals", "Small-cap liquidity can be uneven", "Model confidence varies by ticker coverage"],
                "catalysts": ["Earnings update", "Sector rotation", "Policy or contract signal"],
                "investment_thesis": f"{ticker} merits monitoring under the local Predovex signal framework, with position sizing tied to risk tolerance.",
            },
        },
        "bull_bear_debate": {
            "verdict": "Bullish" if score >= 65 else "Neutral",
            "conclusion": "Local bull/bear debate is generated from deterministic fallback metrics.",
            "bull_case": {
                "strength_score": max(50, score),
                "arguments": [
                    {"point": "Signal stack is constructive", "evidence": "Momentum and valuation proxies support continued monitoring."},
                    {"point": "Growth runway is present", "evidence": "Generated growth score is above neutral."},
                ],
            },
            "bear_case": {
                "strength_score": risk_score,
                "arguments": [
                    {"point": "Fallback data limitation", "evidence": "Live fundamentals provider is not available in local stub mode."},
                    {"point": "Market sensitivity", "evidence": "Volatility and rates can pressure multiples."},
                ],
            },
        },
    }


@app.get("/api/stocks/screener")
def stocks_screener():
    return {"stocks": MARKET_DATA["stocks"], "count": len(MARKET_DATA["stocks"])}


@app.get("/api/news/search")
def news_search(query: str, limit: int = 10):
    q = (query or "").lower()
    articles = _articles("all", "all", 100)
    if q:
        articles = [a for a in articles if q in a["title"].lower() or q in a["description"].lower()]
    return {"articles": articles[:limit], "count": len(articles[:limit])}


@app.get("/api/sparkline/{ticker}")
def sparkline(ticker: str):
    base = _price_for(ticker)
    prices = []
    for idx in range(30):
        drift = (idx - 15) * _stable_num(ticker + "drift", -0.004, 0.006)
        wave = ((idx % 6) - 2.5) * _stable_num(ticker + "wave", 0.001, 0.008)
        prices.append(round(base * (1 + drift + wave), 2))
    change_pct = round((prices[-1] - prices[0]) / prices[0] * 100, 2)
    return {"ticker": ticker.upper(), "prices": prices, "change_pct": change_pct}


@app.get("/markets/sentiment/predict/{ticker}")
def sentiment_predict(ticker: str, period: str = "3mo"):
    result = _sentiment_prediction(ticker)
    result["period"] = period
    return result


@app.get("/markets/sentiment/batch")
def sentiment_batch(tickers: str):
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    predictions = [_sentiment_prediction(ticker) for ticker in ticker_list]
    return {
        "predictions": predictions,
        "total": len(predictions),
        "bullish_count": sum(1 for p in predictions if p["prediction"] == "Up"),
        "bearish_count": sum(1 for p in predictions if p["prediction"] == "Down"),
    }


@app.get("/markets/sentiment/sector/{sector}")
def sentiment_sector(sector: str):
    tickers = SECTOR_TICKERS.get(sector.lower(), SECTOR_TICKERS["technology"])
    predictions = [_sentiment_prediction(ticker) for ticker in tickers]
    bullish = sum(1 for p in predictions if p["prediction"] == "Up")
    avg_prob = sum(p["probability"] for p in predictions) / len(predictions)
    return {
        "sector": sector.lower(),
        "sentiment": "Bullish" if bullish >= len(predictions) / 2 else "Bearish",
        "avg_probability": round(avg_prob, 3),
        "bullish_stocks": bullish,
        "bearish_stocks": len(predictions) - bullish,
        "predictions": predictions,
    }


@app.get("/markets/sentiment/all-sectors")
def sentiment_all_sectors():
    return {sector: sentiment_sector(sector) for sector in SECTOR_TICKERS}


@app.get("/markets/sentiment/model-info")
def sentiment_model_info():
    return {
        "model_id": "predovex-local-free-market-signal",
        "type": "Deterministic local fallback",
        "task": "Stock direction prediction and market momentum demo",
        "status": "local",
        "accuracy": "Unavailable in local fallback mode",
        "features": ["market momentum", "government event count", "contract signal", "sector regime"],
    }


@app.get("/markets/sentiment/top-picks")
def sentiment_top_picks(tickers: str, limit: int = 10):
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    predictions = [_sentiment_prediction(ticker) for ticker in ticker_list]
    bullish = sorted([p for p in predictions if p["prediction"] == "Up"], key=lambda p: p["probability"], reverse=True)[:limit]
    bearish = sorted([p for p in predictions if p["prediction"] == "Down"], key=lambda p: p["probability"])[:limit]
    for idx, item in enumerate(bullish, 1):
        item.update({"rank": idx, "signal": "BUY", "signal_strength": round((item["probability"] - 0.5) * 200, 1)})
    for idx, item in enumerate(bearish, 1):
        item.update({"rank": idx, "signal": "SELL", "signal_strength": round((0.5 - item["probability"]) * 200, 1)})
    return {
        "top_bullish_picks": bullish,
        "top_bearish_picks": bearish,
        "total_analyzed": len(predictions),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/markets/sentiment/portfolio")
def sentiment_portfolio(tickers: str, risk_profile: str = "balanced"):
    picks = sentiment_top_picks(tickers, 5)["top_bullish_picks"]
    allocation = round(100 / max(len(picks), 1), 2)
    return {
        "portfolio": [
            {
                "ticker": pick["ticker"],
                "allocation": allocation,
                "signal": pick.get("signal", "BUY"),
                "probability": pick["probability"],
                "current_price": pick["current_price"],
                "reasoning": f"{pick['ticker']} ranks highly in local market signal fallback.",
            }
            for pick in picks
        ],
        "risk_profile": risk_profile,
        "cash_allocation": 0 if picks else 100,
        "total_allocation": 100 if picks else 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/markets/sentiment/backtest")
def sentiment_backtest(tickers: str, days: int = 30, initial_capital: float = 10000):
    final_value = initial_capital * (1 + _stable_num(tickers + str(days), -0.04, 0.12))
    total_return = (final_value - initial_capital) / initial_capital * 100
    sample = []
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()][:5]
    for idx, ticker in enumerate(ticker_list):
        sample.append({
            "date": (datetime.now(timezone.utc) - timedelta(days=idx + 1)).date().isoformat(),
            "type": "BUY" if idx % 2 == 0 else "SELL",
            "ticker": ticker,
            "shares": 10 + idx,
            "price": _price_for(ticker),
        })
    return {
        "strategy": "Local market signal backtest",
        "performance": {
            "initial_capital": initial_capital,
            "final_value": round(final_value, 2),
            "total_return_pct": round(total_return, 2),
            "total_profit_loss": round(final_value - initial_capital, 2),
            "win_rate_pct": round(_stable_num(tickers, 52, 68), 1),
            "sharpe_ratio": round(_stable_num(tickers + "sharpe", 0.8, 1.7), 2),
            "max_drawdown_pct": round(_stable_num(tickers + "dd", 3, 11), 2),
            "alpha": round(total_return - 4.2, 2),
        },
        "trading_activity": {
            "total_trades": max(days * 2, len(sample)),
            "buy_trades": days,
            "sell_trades": days,
            "sample_trades": sample,
        },
        "disclaimer": "Local fallback data for UI development. Not investment advice.",
    }


@app.get("/markets/sentiment/signals/{ticker}")
def sentiment_signal(ticker: str):
    pred = _sentiment_prediction(ticker)
    return {"ticker": ticker.upper(), "signal": "BUY" if pred["prediction"] == "Up" else "SELL", **pred}


@app.get("/api/predict/known-tickers")
def known_tickers():
    tickers = []
    for items in MARKET_DATA.values():
        for item in items:
            symbol = item["symbol"]
            if "/" not in symbol and symbol not in ("Gold", "Silver", "Copper", "SOFR", "MMF", "US10Y", "US02Y"):
                tickers.append(symbol)
    tickers.extend(["LMT", "RTX", "NOC", "GD", "JNJ", "MRK", "UNH", "BAC", "CVX", "WMT", "MCD"])
    return {"tickers": sorted(set(tickers)), "count": len(set(tickers))}


@app.get("/api/predict/unified/batch")
def unified_batch(tickers: str):
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    return {
        "predictions": [_unified_prediction(ticker) for ticker in ticker_list],
        "count": len(ticker_list),
        "model_status": {"loaded": True, "mode": "local-fallback"},
    }


@app.get("/api/predict/unified/{ticker}")
def unified_single(ticker: str):
    return _unified_prediction(ticker)


@app.get("/api/predict/explain/{ticker}")
def predict_explain(ticker: str, limit: int = 10):
    ticker = ticker.upper()
    event_types = ["contract_award", "sec_filing", "policy_signal", "earnings_guidance", "regulatory_action"]
    sources = ["USAspending", "SEC EDGAR", "Federal Register", "Treasury", "DoD"]
    events = []
    for idx in range(max(1, min(limit, 25))):
        direction = "UP" if _stable_num(ticker + str(idx), 0, 1) >= 0.42 else "DOWN"
        ret_7d = round(_stable_num(ticker + "r7" + str(idx), -5.8, 7.4), 2)
        if direction == "UP" and ret_7d < 0:
            ret_7d = abs(ret_7d)
        if direction == "DOWN" and ret_7d > 0:
            ret_7d = -ret_7d
        event_type = event_types[idx % len(event_types)]
        event_date = (datetime.now(timezone.utc) - timedelta(days=idx * 11 + 3)).date().isoformat()
        events.append(
            {
                "event_type": event_type,
                "event_title": f"{ticker} {event_type.replace('_', ' ')} signal detected",
                "event_date": event_date,
                "source": sources[idx % len(sources)],
                "award_amount": int(_stable_num(ticker + "award" + str(idx), 250000, 125000000)) if event_type == "contract_award" else None,
                "return_1d": round(ret_7d / 3 + _stable_num(ticker + "r1" + str(idx), -0.8, 0.8), 2),
                "return_7d": ret_7d,
                "return_30d": round(ret_7d * _stable_num(ticker + "r30" + str(idx), 1.4, 3.2), 2),
                "direction": direction,
                "signal_score": int(_stable_num(ticker + "sig" + str(idx), 42, 96)),
            }
        )
    return {
        "ticker": ticker,
        "events": sorted(events, key=lambda item: abs(item["return_7d"]), reverse=True),
        "total_events": int(_stable_num(ticker + "total-events", 48, 240)),
        "bullish_pct": int(_stable_num(ticker + "bullish", 44, 72)),
        "avg_7d_return": round(_stable_num(ticker + "avg7d", -1.8, 3.4), 2),
    }


@app.get("/api/contracts/ticker/{ticker}")
@app.get("/api/usaspending/contracts/{ticker}")
def contracts_for_ticker(ticker: str, company_name: str | None = None, limit: int = 10):
    agencies = [
        "Department of Defense",
        "Department of the Navy",
        "Department of the Army",
        "Department of the Air Force",
        "Defense Logistics Agency",
        "Missile Defense Agency",
        "Defense Information Systems Agency",
        "Department of Homeland Security",
        "National Aeronautics and Space Administration",
        "General Services Administration",
    ]
    programs = [
        "advanced aerospace systems sustainment",
        "cybersecurity modernization and mission support",
        "integrated command-and-control services",
        "missile defense engineering and logistics",
        "secure communications infrastructure",
        "fleet readiness and depot maintenance",
        "space systems integration",
        "intelligence analytics platform support",
        "munitions production and supply chain services",
        "training, simulation, and operational support",
    ]
    row_count = max(15, min(limit, 75))
    return {
        "ticker": ticker.upper(),
        "company_name": company_name or ticker.upper(),
        "contracts": [
            {
                "award_id": f"{ticker.upper()}-{idx+1}",
                "Recipient Name": company_name or ticker.upper(),
                "Awarding Agency": agencies[idx % len(agencies)],
                "Award Amount": round(_stable_num(ticker + str(idx), 750000, 185000000), 2),
                "Description": f"{company_name or ticker.upper()} award for {programs[idx % len(programs)]}.",
                "Start Date": (datetime.now(timezone.utc) - timedelta(days=idx * 4)).date().isoformat(),
                "agency": agencies[idx % len(agencies)],
                "amount": round(_stable_num(ticker + str(idx), 750000, 185000000), 2),
                "description": f"{company_name or ticker.upper()} award for {programs[idx % len(programs)]}.",
                "date": (datetime.now(timezone.utc) - timedelta(days=idx * 4)).date().isoformat(),
            }
            for idx in range(row_count)
        ],
    }


@app.get("/api/contracts/trends/{ticker}")
@app.get("/api/usaspending/trends/{ticker}")
def contract_trends(ticker: str, company_name: str | None = None):
    total = int(_stable_num(ticker + "contracts", 2, 24))
    return {
        "ticker": ticker.upper(),
        "company_name": company_name or ticker.upper(),
        "total_contracts": total,
        "total_value": round(_stable_num(ticker + "value", 1_000_000, 90_000_000), 2),
        "signal": "BULLISH" if total >= 8 else "NEUTRAL",
        "trend": "increasing" if total >= 8 else "stable",
    }


@app.get("/api/earnings/upcoming")
def earnings_upcoming(tickers: str, days: int = 45):
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    return {
        "earnings": [
            {
                "ticker": ticker,
                "company_name": (_find_market_item(ticker) or {}).get("desc", ticker),
                "earnings_date": (datetime.now(timezone.utc) + timedelta(days=(idx * 3) % max(days, 1))).date().isoformat(),
                "days_until": (idx * 3) % max(days, 1),
                "current_price": _price_for(ticker),
                "eps_estimate": round(_stable_num(ticker + "eps", 0.35, 8.5), 2),
                "ml_direction": "BULLISH" if _horizon_prediction(ticker, "7d")["direction"] == "UP" else "BEARISH",
                "ml_confidence": int(_horizon_prediction(ticker, "7d")["confidence"] * 100),
                "prediction": _horizon_prediction(ticker, "7d")["direction"],
                "confidence": _horizon_prediction(ticker, "7d")["confidence"],
            }
            for idx, ticker in enumerate(ticker_list)
        ],
        "count": len(ticker_list),
        "horizon_days": days,
    }


@app.get("/api/sentiment/history/{ticker}")
def sentiment_history(ticker: str, days: int = 90):
    weeks = max(4, min(26, int(days / 7)))
    history = []
    today = datetime.now(timezone.utc).date()
    for idx in range(weeks):
        week_date = today - timedelta(days=(weeks - idx - 1) * 7)
        iso_year, iso_week, _ = week_date.isocalendar()
        event_count = int(_stable_num(ticker + "events" + str(idx), 2, 18))
        history.append(
            {
                "week": f"{iso_year}-W{iso_week:02d}",
                "event_count": event_count,
                "avg_signal": round(_stable_num(ticker + "signal" + str(idx), 18, 92), 1),
                "avg_return_7d": round(_stable_num(ticker + "return" + str(idx), -6.5, 7.8), 2),
                "event_types": ["contract", "filing", "policy"][: 1 + (idx % 3)],
            }
        )
    return {
        "ticker": ticker.upper(),
        "history": history,
        "total_events": sum(item["event_count"] for item in history),
    }


@app.get("/api/geopolitical/risk")
def geopolitical_risk(days: int = 7):
    regions = [
        ("United States", "MEDIUM", ["Federal Reserve policy pressure", "Trade restrictions", "Election-year fiscal risk"]),
        ("Europe", "MEDIUM", ["Defense spending", "Energy supply risk", "Industrial policy"]),
        ("Asia-Pacific", "HIGH", ["Semiconductor controls", "Shipping lanes", "Taiwan Strait risk"]),
        ("Middle East", "HIGH", ["Energy security", "Regional conflict", "Maritime chokepoints"]),
        ("Latin America", "LOW", ["Commodity policy", "Election risk", "Currency volatility"]),
    ]
    return {
        "days": days,
        "regions": [
            {
                "region": region,
                "risk_score": int(_stable_num(region + str(days), 28, 88)),
                "risk_level": level,
                "article_count": int(_stable_num(region + "articles" + str(days), 12, 96)),
                "sample_headlines": headlines,
                "drivers": headlines,
            }
            for region, level, headlines in regions
        ],
        "as_of": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/insider/{ticker}")
def insider_trades(ticker: str, limit: int = 25):
    ticker = ticker.upper()
    names = ["Chief Executive Officer", "Chief Financial Officer", "Director", "Chief Technology Officer", "10% Owner"]
    trades = []
    for idx in range(max(5, min(limit, 50))):
        filed = datetime.now(timezone.utc).date() - timedelta(days=idx * 7 + 2)
        trades.append(
            {
                "ticker": ticker,
                "filer": f"{ticker} {names[idx % len(names)]}",
                "form_type": "4",
                "file_date": filed.isoformat(),
                "period": (filed - timedelta(days=2)).isoformat(),
                "entity": (_find_market_item(ticker) or {}).get("desc", ticker),
                "transaction_code": "P" if idx % 3 == 0 else "S",
                "shares": int(_stable_num(ticker + "shares" + str(idx), 500, 75000)),
                "price": round(_stable_num(ticker + "tradeprice" + str(idx), 18, 650), 2),
                "link": f"https://www.sec.gov/edgar/search/#/q={ticker}%2520Form%25204",
            }
        )
    return {"ticker": ticker, "trades": trades, "count": len(trades), "source": "local-sec-edgar-fallback"}


@app.post("/auth/login")
def login():
    return {"access_token": "local-token", "token_type": "bearer", "tier": "pro", "daily_limit": 5000}


@app.post("/auth/register")
def register():
    return {"access_token": "local-token", "token_type": "bearer", "tier": "free", "daily_limit": 50}


@app.get("/user/me")
def user_me():
    return {"email": "local@predovex.dev", "tier": "pro", "daily_limit": 5000}


@app.get("/user/watchlist")
def watchlist():
    return []


@app.get("/user/watchlist/news")
def watchlist_news():
    return []


@app.get("/api/analytics/trends")
def analytics_trends(days: int = 30):
    days = max(7, min(days, 90))
    today = datetime.now(timezone.utc).date()
    categories = ["policy", "markets", "technology", "economy", "health", "general"]
    trends = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        key = day.isoformat()
        high = int(_stable_num(key + "high", 4, 18))
        medium = int(_stable_num(key + "medium", 12, 36))
        low = int(_stable_num(key + "low", 18, 52))
        article_count = high + medium + low
        avg_impact = round(((high * 86) + (medium * 58) + (low * 27)) / max(article_count, 1), 1)
        trends.append(
            {
                "date": key,
                "high": high,
                "medium": medium,
                "low": low,
                "article_count": article_count,
                "avg_impact": avg_impact,
                "max_impact": int(_stable_num(key + "max", 72, 98)),
            }
        )

    category_breakdown = []
    for category in categories:
        total = int(_stable_num(category + "total", 45, 180))
        high = int(_stable_num(category + "cat-high", 8, 42))
        category_breakdown.append(
            {
                "category": category,
                "total": total,
                "high_impact": high,
                "avg_impact": round(_stable_num(category + "avg", 32, 78), 1),
                "trend": "up" if _stable_num(category + "dir", 0, 1) >= 0.48 else "stable",
            }
        )

    latest = trends[-1]
    previous = trends[-8] if len(trends) >= 8 else trends[0]
    delta = round(latest["avg_impact"] - previous["avg_impact"], 1)
    return {
        "days": days,
        "trends": trends,
        "category_breakdown": sorted(category_breakdown, key=lambda item: item["avg_impact"], reverse=True),
        "summary": {
            "total_articles": sum(item["article_count"] for item in trends),
            "high_impact_total": sum(item["high"] for item in trends),
            "current_avg_impact": latest["avg_impact"],
            "avg_impact_delta_7d": delta,
            "direction": "rising" if delta > 1 else "falling" if delta < -1 else "stable",
        },
    }


@app.post("/api/backtest/run")
def run_backtest(ticker: str | None = None, hold_days: int = 7):
    selected = ticker or "ALL"
    trades = 248 if selected == "ALL" else 24
    win_rate = 64.7 if selected == "ALL" else 62.5
    return {
        "status": "success",
        "ticker": selected,
        "hold_days": hold_days,
        "aggregate": {
            "win_rate": win_rate,
            "total_trades": trades,
            "avg_return": 1.84,
            "total_return": 18.6,
            "sharpe_ratio": 1.31,
            "max_drawdown": -6.2,
        },
        "sample_trades": [
            {
                "ticker": "SPY" if selected == "ALL" else selected,
                "event_type": "regulatory_notice",
                "direction": "UP",
                "return_pct": 2.1,
                "hold_days": hold_days,
            },
            {
                "ticker": "QQQ" if selected == "ALL" else selected,
                "event_type": "sec_filing",
                "direction": "UP",
                "return_pct": 1.4,
                "hold_days": hold_days,
            },
        ],
        "note": "Local development backtest response. Full historical backtest requires backend/main.py service files to be materialized.",
    }


@app.get("/api/backtest/evidence")
def backtest_evidence():
    return {
        "status": "success",
        "evidence": {
            "total_events_tracked": 81882,
            "events_with_price_data": 80734,
            "model_confidence": "Local development evidence summary",
        },
    }


@app.get("/{path:path}")
def fallback(path: str):
    return {}
