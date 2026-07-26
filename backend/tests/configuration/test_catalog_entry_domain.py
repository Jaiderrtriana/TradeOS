from app.modules.configuration.domain.catalog_entry import (
    ENTRY_TRIGGER,
    MISTAKE_TAG,
    SESSION,
    SETUP,
    STRATEGY,
    VALID_KINDS,
    CatalogEntry,
)


def test_defaults_to_active():
    entry = CatalogEntry(kind=SETUP, name="Pullback Continuation")
    assert entry.is_active is True


def test_each_entry_gets_its_own_id():
    first = CatalogEntry(kind=SESSION, name="NY")
    second = CatalogEntry(kind=SESSION, name="EU")
    assert first.id != second.id


def test_valid_kinds_matches_database_design_check_constraint():
    """TRADEOS_DATABASE_DESIGN.md §6.8: kind IN
    ('setup','session','strategy','entry_trigger','mistake_tag')."""
    assert VALID_KINDS == {SETUP, SESSION, STRATEGY, ENTRY_TRIGGER, MISTAKE_TAG}
