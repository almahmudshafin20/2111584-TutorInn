from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_alembic_configuration_resolves_paths_from_config_location() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))

    assert Path(config.get_main_option("script_location")).resolve() == (
        BACKEND_DIR / "alembic"
    ).resolve()
    assert Path(config.get_main_option("prepend_sys_path")).resolve() == BACKEND_DIR.resolve()


def test_alembic_has_one_existing_schema_baseline_head() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)

    assert scripts.get_heads() == ["20261116_0004"]
    baseline = scripts.get_revision("20261116_0001")
    personal_tasks = scripts.get_revision("20261116_0002")
    group_learning = scripts.get_revision("20261116_0003")
    tutor_verification = scripts.get_revision("20261116_0004")
    assert personal_tasks is not None
    assert personal_tasks.down_revision == "20261116_0001"
    assert baseline is not None
    assert baseline.down_revision is None
    assert group_learning is not None
    assert group_learning.down_revision == "20261116_0002"
    assert tutor_verification is not None
    assert tutor_verification.down_revision == "20261116_0003"
