"""Brand asset resolution tests."""

from pathlib import Path

from smartinstall.ui.resources.brand_assets import brand_kit_logo_path, clear_brand_asset_cache


def test_brand_logo_resolves_from_project_images(project_root: Path) -> None:
    clear_brand_asset_cache()
    logo = project_root / "images" / "logo.png"
    assert logo.is_file()
    resolved = brand_kit_logo_path()
    assert resolved is not None
    assert resolved.name.lower() == "logo.png"
