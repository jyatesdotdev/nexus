from unittest.mock import patch, MagicMock
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


def test_query_prometheus_metric() -> None:
    result = query_prometheus_metric("avg(cpu_usage)")
    assert isinstance(result, MetricValue)
    assert result.status == "success"
    assert result.value == 95.4


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
    # Note: result might be error if uptime is not on the system, but it should be permitted
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
