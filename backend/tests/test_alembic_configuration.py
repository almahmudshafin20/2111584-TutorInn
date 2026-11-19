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


def test_alembic_has_one_linear_head_for_auth_tasks_and_groups() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)

    assert scripts.get_heads() == ["20261119_0004"]
    assert scripts.get_revision("20261119_0002").down_revision == "20261116_0001"
    assert scripts.get_revision("20261119_0003").down_revision == "20261119_0002"
    assert scripts.get_revision("20261119_0004").down_revision == "20261119_0003"
    baseline = scripts.get_revision("20261116_0001")
    assert baseline is not None
    assert baseline.down_revision is None

    personal_tasks = (BACKEND_DIR / "alembic/versions/20261119_0003_personal_learning_tasks.py").read_text()
    group_learning = (BACKEND_DIR / "alembic/versions/20261119_0004_group_learning.py").read_text()
    assert '"personal_learning_tasks"' in personal_tasks
    assert '"learning_groups"' in group_learning
    assert '"group_task_assignments"' in group_learning
    assert '"video_url"' in group_learning
