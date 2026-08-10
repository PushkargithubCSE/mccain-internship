from pathlib import Path

from loguru import logger

from shared.config.settings import settings

# Create logs directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Remove default logger
logger.remove()

# Console Logger
logger.add(
    sink=lambda msg: print(msg, end=""),
    level=settings.log_level,
    colorize=True,
)

# File Logger
logger.add(
    LOG_DIR / "app.log",
    level=settings.log_level,
    rotation="10 MB",
    retention="7 days",
    compression="zip",
)
