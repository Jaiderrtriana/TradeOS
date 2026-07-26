from uuid import uuid4

from app.modules.preferences.domain.user_preferences import UserPreferences


def test_defaults_match_database_design_spec():
    """TRADEOS_DATABASE_DESIGN.md §6.2: theme DEFAULT 'dark', language DEFAULT 'es'."""
    preferences = UserPreferences(user_id=uuid4())
    assert preferences.theme == "dark"
    assert preferences.language == "es"
    assert preferences.notification_settings == {}


def test_each_instance_gets_its_own_notification_settings_dict():
    """Mutable default must not be shared across instances (dataclass field(default_factory=...))."""
    first = UserPreferences(user_id=uuid4())
    second = UserPreferences(user_id=uuid4())
    first.notification_settings["email_alerts"] = True
    assert second.notification_settings == {}
