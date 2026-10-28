"""Explanation seat — FAO/INRA reference folder and offline templates."""

from pathlib import Path

from app.services import explain as explain_module
from app.services.explain import knowledge_dir, list_reference_pages, template_texts


def test_knowledge_folder_resolves_under_backend():
    """The knowledge folder lives next to the backend package."""
    root = knowledge_dir()
    assert root.is_dir()
    # The FAO and INRA subfolders exist and contain reference pages.
    assert (root / "fao").is_dir()
    assert (root / "inra").is_dir()


def test_reference_pages_are_loaded():
    pages = list_reference_pages()
    assert pages, "expected at least one markdown reference page"
    assert all(p.suffix == ".md" for p in pages)
    assert all(p.is_file() for p in pages)


def test_offline_templates_three_languages():
    payload = {
        "status": "show_dose",
        "display_dose": 4.7,
        "etc_mm": 3.15,
        "effective_rain_mm": 1.5,
        "gross_irrigation_mm": 4.7,
        "irrigation_method": "drip",
        "crop": "citrus",
        "fungal_risk": "medium",
        "spray_blocked": False,
    }
    out = template_texts(payload)
    assert set(out) == {"fr", "ar", "darija"}
    assert "3.15" in out["fr"] or "3,15" in out["fr"]
    assert "4.7" in out["fr"] or "4,7" in out["fr"]
    # No invented number.
    assert "5.0" not in out["fr"]


def test_offline_templates_needs_check_hides_dose():
    out = template_texts({"status": "needs_check"})
    assert set(out) == {"fr", "ar", "darija"}
    assert "3.15" not in out["fr"]


def test_module_reexports_template_engine():
    """The public entry point still exposes the template engine."""
    assert hasattr(explain_module, "template_texts")
    assert hasattr(explain_module, "explain")
    assert hasattr(explain_module, "ask_qatra")