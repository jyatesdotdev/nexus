import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Any

from orchestrator.tools import (
    get_sensor_reading,
    query_prometheus_metric,
    fetch_ynab_budget,
    extract_entities_with_grounding,
    execute_safe_bash_command,
    SensorReading,
    MetricValue,
    BudgetBalance,
    ExtractedEntities,
    BashOutput,
)


def test_get_sensor_reading() -> None:
    result = get_sensor_reading("sensor_1")
    assert isinstance(result, SensorReading)
    assert result.status == "success"
    assert result.sensor_id == "sensor_1"
    assert result.temperature == 22.5


@pytest.mark.asyncio
async def test_query_prometheus_metric() -> None:
    # EDUCATIONAL NOTE: Mocking External Dependencies
    # When testing the tool, we mock the asynchronous HTTP call to avoid 
    # hitting a real Prometheus server during unit tests.
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "success",
        "data": {"result": [{"value": [12345, "42.5"]}]}
    }
    
    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    
    # httpx.AsyncClient is used as an async context manager
    mock_client_cls = MagicMock()
    mock_client_cls.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_cls.__aexit__ = AsyncMock(return_value=None)
    
    with patch("httpx.AsyncClient", return_value=mock_client_cls):
        result = await query_prometheus_metric("avg(cpu_usage)")
        
    assert isinstance(result, MetricValue)
    assert result.status == "success"
    assert result.value == 42.5


def test_fetch_ynab_budget() -> None:
    result = fetch_ynab_budget("Groceries")
    assert isinstance(result, BudgetBalance)
    assert result.status == "success"
    assert result.balance == 150.0


def test_extract_entities_with_grounding() -> None:
    result = extract_entities_with_grounding("Hello world", "PERSON")
    assert isinstance(result, ExtractedEntities)
    assert result.status == "success"
    assert len(result.extractions) > 0


@patch("subprocess.run")
def test_execute_safe_bash_command_allowed(mock_run: Any) -> None:
    mock_run.return_value = MagicMock(stdout="up 2 days", returncode=0)
    result = execute_safe_bash_command("uptime")
    assert isinstance(result, BashOutput)
    # EDUCATIONAL NOTE: result might be error if uptime is not on the system, but it should be permitted
    assert result.status in ["success", "error"]
    if result.status == "error":
        assert result.error is not None
        assert "not permitted" not in result.error


@patch("subprocess.run")
def test_execute_safe_bash_command_forbidden(mock_run: Any) -> None:
    result = execute_safe_bash_command("rm -rf /")
    assert isinstance(result, BashOutput)
    assert result.status == "error"
    assert result.error is not None
    assert "not permitted" in result.error
