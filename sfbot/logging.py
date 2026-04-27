"""Context-aware logging helpers for concurrent account runners.

Logs are written to the ``logs/`` directory using Python's :mod:`logging`
module.

Bot logs go to ``logs/bot/<account>.log``.
Crawl logs go to ``logs/crawl/<server>.log``.

Format: ``TIMESTAMP:LOG_LEVEL message``
"""

import logging
from contextvars import ContextVar, Token
from pathlib import Path

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
BOT_LOG_DIR = LOG_DIR / "bot"
CRAWL_LOG_DIR = LOG_DIR / "crawl"
BOT_LOG_DIR.mkdir(parents=True, exist_ok=True)
CRAWL_LOG_DIR.mkdir(parents=True, exist_ok=True)

_FMT = "%(asctime)s:%(levelname)s %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"
_loggers: dict[str, logging.Logger] = {}

# ---------------------------------------------------------------------------
# Context vars
# ---------------------------------------------------------------------------


class BotLogContext:
    """Holds the per-task bot log prefix (one per account task)."""

    _var: ContextVar[str] = ContextVar("sfbot_log_prefix", default="")

    @classmethod
    def set(cls, prefix: str) -> Token[str]:
        return cls._var.set(prefix)

    @classmethod
    def reset(cls, token: Token[str]) -> None:
        cls._var.reset(token)

    @classmethod
    def get(cls) -> str:
        return cls._var.get()


class CrawlLogContext:
    """Holds the per-task crawl log prefix (one per server task)."""

    _var: ContextVar[str] = ContextVar("sfbot_crawl_log_prefix", default="")

    @classmethod
    def set(cls, prefix: str) -> Token[str]:
        return cls._var.set(prefix)

    @classmethod
    def reset(cls, token: Token[str]) -> None:
        cls._var.reset(token)

    @classmethod
    def get(cls) -> str:
        return cls._var.get()


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _make_logger(key: str, path: Path) -> logging.Logger:
    logger = logging.getLogger(f"sfbot.{key}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(_FMT, datefmt=_DATE_FMT))
    logger.addHandler(handler)
    _loggers[key] = logger
    return logger


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_bot_main_logger() -> logging.Logger:
    """Return the shared bot main logger (logs/bot/bot.log)."""
    key = "__bot_main__"
    if key in _loggers:
        return _loggers[key]
    return _make_logger(key, BOT_LOG_DIR / ".log")


def get_crawl_main_logger() -> logging.Logger:
    """Return the shared crawl main logger (logs/crawl/crawl.log)."""
    key = "__crawl_main__"
    if key in _loggers:
        return _loggers[key]
    return _make_logger(key, CRAWL_LOG_DIR / ".log")


def get_main_logger() -> logging.Logger:
    """Return the bot logger for the current task context."""
    name = BotLogContext.get()
    if name in _loggers:
        return _loggers[name]
    safe = name.replace("/", "_")
    return _make_logger(name, BOT_LOG_DIR / f"{safe}.log")


def get_crawl_logger() -> logging.Logger:
    """Return the crawl logger for the current task context."""
    name = CrawlLogContext.get()
    if name in _loggers:
        return _loggers[name]
    safe = name.replace("/", "_")
    return _make_logger(name, CRAWL_LOG_DIR / f"{safe}.log")
