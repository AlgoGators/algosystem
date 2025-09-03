import pytest

def test_available_components_structure():
    try:
        from algosystem.backtesting.dashboard.web_app.available_components import (
            AVAILABLE_CHARTS,
            AVAILABLE_METRICS,
        )
        assert isinstance(AVAILABLE_CHARTS, list)
        assert isinstance(AVAILABLE_METRICS, list)
    except ImportError:
        pytest.skip("Web app components not available")