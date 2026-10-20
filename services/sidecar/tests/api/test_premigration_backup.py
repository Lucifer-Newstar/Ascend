from alembic import command
from app.core.config import Settings
from app.core.migrate import alembic_config
from app.main import create_app
from app.modules.io import backup


def backups(settings: Settings) -> list[backup.BackupInfo]:
    return backup.list_backups(backup.backups_dir(settings.data_dir))


def test_an_older_database_is_backed_up_before_it_is_migrated(settings, clock):
    command.upgrade(alembic_config(settings.resolved_db_url), "0008")
    create_app(settings, clock=clock, outbox_interval=0)
    [info] = backups(settings)
    assert info.reason == "pre-migration"
    assert info.schema == "0008"  # the copy is of the database before the upgrade


def test_fresh_installs_and_current_databases_are_not_backed_up(settings, clock):
    create_app(settings, clock=clock, outbox_interval=0)  # fresh: nothing to protect
    create_app(settings, clock=clock, outbox_interval=0)  # already at head
    assert backups(settings) == []


def test_only_the_newest_automatic_backups_are_kept(settings, clock, tmp_path):
    from datetime import timedelta

    db_file = tmp_path / "test.db"
    command.upgrade(alembic_config(settings.resolved_db_url), "0008")
    folder = backup.backups_dir(settings.data_dir)
    manual = backup.create_backup(db_file, folder, clock.now)
    for i in range(7):
        backup.create_backup(db_file, folder, clock.now + timedelta(minutes=i + 1), "pre-migration")
    removed = backup.prune_automatic(folder, keep=5)
    assert removed == 2
    left = backups(settings)
    assert sum(1 for b in left if b.reason == "pre-migration") == 5
    assert manual.path in [b.path for b in left]  # manual backups are never pruned
