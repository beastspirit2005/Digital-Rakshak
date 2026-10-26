import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from alembic.config import Config
from alembic import command
from core.config import settings

alembic_cfg = Config(os.path.join(backend_dir, "alembic.ini"))
alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

print("Upgrading database to head...")
command.upgrade(alembic_cfg, "head")
print("Upgrade complete!")
