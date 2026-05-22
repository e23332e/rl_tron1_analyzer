"""Application configuration."""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Database
DB_PATH = BASE_DIR / "config_analyzer.db"

# Upload directory for temporary file storage
UPLOAD_DIR = BASE_DIR / "uploads"

# Default sample config directory
SAMPLE_CONFIG_DIR = Path(r"D:\工作目录\强化学习训练记录\yaml文件记录分析\配置文件样例")

# Flask config
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
