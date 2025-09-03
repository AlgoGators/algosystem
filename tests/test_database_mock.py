from unittest.mock import Mock, patch
import pytest

@patch('algosystem.data.connectors.db_models.get_engine')
def test_db_manager_initialization(mock_engine):
    from algosystem.data.connectors.db_manager import DBManager
    mock_engine.return_value = Mock()
    
    with patch.dict('os.environ', {
        'DB_HOST': 'localhost',
        'DB_USER': 'test',
        'DB_PASSWORD': 'test',
        'DB_PORT': '5432',
        'DB_NAME': 'test'
    }):
        db = DBManager()
        assert db is not None