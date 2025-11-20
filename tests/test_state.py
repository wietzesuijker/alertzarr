from pathlib import Path

from autopilot.state import AlertStateStore


def test_state_store_persists_ids(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = AlertStateStore(path)
    assert store.is_new("a")
    store.mark_processed("a")
    assert not store.is_new("a")

    reloaded = AlertStateStore(path)
    assert not reloaded.is_new("a")


def test_state_store_extend(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    store = AlertStateStore(path)
    store.extend(["a", "b"])
    assert not store.is_new("a")
    assert not store.is_new("b")
