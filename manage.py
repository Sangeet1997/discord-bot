import sys
import argparse
from pathlib import Path
from alembic.config import Config
from alembic import command

# Ensure the project root is in sys.path so alembic can import project modules (database, config, etc.)
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Locate alembic.ini (check alembic/alembic.ini first, then project root)
ALEMBIC_INI_PATH = BASE_DIR / "alembic" / "alembic.ini"
if not ALEMBIC_INI_PATH.exists():
    ALEMBIC_INI_PATH = BASE_DIR / "alembic.ini"


def get_alembic_config() -> Config:
    """Load and return the Alembic Config instance."""
    if not ALEMBIC_INI_PATH.exists():
        raise FileNotFoundError(f"Alembic configuration file not found at: {ALEMBIC_INI_PATH}")
    return Config(str(ALEMBIC_INI_PATH))


def make_migration(message: str = "auto migration") -> None:
    """Generate a new migration revision file based on model differences."""
    config = get_alembic_config()
    print(f"Generating migration revision with message: '{message}'...")
    command.revision(config, message=message, autogenerate=True)
    print("Migration revision file created successfully.")


def migrate(revision: str = "head") -> None:
    """Apply migrations up to the specified revision (defaults to head)."""
    config = get_alembic_config()
    print(f"Applying migrations to '{revision}'...")
    command.upgrade(config, revision)
    print("Migrations applied successfully.")


def main():
    parser = argparse.ArgumentParser(description="Database management script")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: make_migration / makemigrations
    make_migration_parser = subparsers.add_parser(
        "make_migration",
        aliases=["makemigrations", "makemigration"],
        help="Generate a new migration revision file"
    )
    make_migration_parser.add_argument(
        "message",
        nargs="?",
        default="auto migration",
        help="Migration description message"
    )
    make_migration_parser.add_argument(
        "-m", "--message-flag",
        dest="flag_message",
        help="Migration description message (flag style)"
    )

    # Command: migrate
    migrate_parser = subparsers.add_parser("migrate", help="Apply pending migrations")
    migrate_parser.add_argument(
        "revision",
        nargs="?",
        default="head",
        help="Target revision (default: head)"
    )

    args = parser.parse_args()

    if args.command in ("make_migration", "makemigrations", "makemigration"):
        msg = args.flag_message or args.message
        make_migration(message=msg)
    elif args.command == "migrate":
        migrate(revision=args.revision)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
