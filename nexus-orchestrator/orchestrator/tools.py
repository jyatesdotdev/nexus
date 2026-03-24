import subprocess
from typing import Dict, Any, List, Optional, Protocol, runtime_checkable
from pydantic import BaseModel, Field

# ==========================================
# 1. Pydantic Models for Structured Output
# ==========================================

class SensorReading(BaseModel):
    """Data model for a physical sensor reading."""
    status: str = Field(..., description="Operation status (success/error)")
    sensor_id: str = Field(..., description="ID of the sensor queried")
    temperature: float = Field(..., description="Measured temperature in Celsius")
    humidity: float = Field(..., description="Measured relative humidity percentage")

class MetricValue(BaseModel):
    """Data model for a Prometheus metric value."""
    status: str = Field(..., description="Operation status")
    query: str = Field(..., description="The PromQL query executed")
    value: float = Field(..., description="The metric result value")
    unit: str = Field(..., description="Unit of measurement (e.g., CPU %, Bytes)")

class BudgetBalance(BaseModel):
    """Data model for a YNAB budget category balance."""
    status: str = Field(..., description="Operation status")
    category: str = Field(..., description="The budget category name")
    balance: float = Field(..., description="Remaining funds available")
    currency: str = Field("USD", description="Currency code")

class ExtractedEntities(BaseModel):
    """Data model for extracted entities from text."""
    status: str = Field(..., description="Operation status")
    extractions: List[Dict[str, str]] = Field(..., description="List of extracted entities and their types")

class BashOutput(BaseModel):
    """Data model for bash command output."""
    status: str = Field(..., description="Operation status")
    output: Optional[str] = Field(None, description="Standard output from the command")
    error: Optional[str] = Field(None, description="Error message if command failed")

# ==========================================
# 2. Tool Implementation with Protocol
# ==========================================

@runtime_checkable
class OrchestratorTool(Protocol):
    """
    Protocol defining the structure of a tool.
    This demonstrates structural subtyping (Duck Typing).
    """
    def __call__(self, *args, **kwargs) -> BaseModel:
        ...

def get_sensor_reading(sensor_id: str) -> SensorReading:
    """
    Retrieves current data from a specified IoT sensor.
    Args:
        sensor_id: The unique identifier for the hardware sensor.
    Returns:
        A SensorReading object containing temp and humidity.
    """
    return SensorReading(status="success", sensor_id=sensor_id, temperature=22.5, humidity=45.0)

def query_prometheus_metric(query: str) -> MetricValue:
    """
    Executes a PromQL query against the corporate Prometheus instance.
    Args:
        query: A valid PromQL string (e.g., 'avg(cpu_usage)').
    Returns:
        A MetricValue object with the result and unit.
    """
    return MetricValue(status="success", query=query, value=95.4, unit="CPU %")

def fetch_ynab_budget(category: str) -> BudgetBalance:
    """
    Fetches the remaining balance for a specific budget category from YNAB.
    Args:
        category: The name of the category (e.g., 'Groceries', 'Rent').
    Returns:
        A BudgetBalance object with the currency and amount.
    """
    return BudgetBalance(status="success", category=category, balance=150.00, currency="USD")

def extract_entities_with_grounding(text: str, entity_type: str) -> ExtractedEntities:
    """
    Uses NLP to extract specific entities from a block of unstructured text.
    Args:
        text: The source text to parse.
        entity_type: The type of entity to look for (e.g., 'PERSON', 'ORG').
    Returns:
        An ExtractedEntities object with the list of findings.
    """
    return ExtractedEntities(status="success", extractions=[{"text": "Mock", "type": entity_type}])

def execute_safe_bash_command(command: str) -> BashOutput:
    """
    Executes a limited set of safe system-level bash commands.
    Args:
        command: The bash command to execute (limited to allow-listed commands).
    Returns:
        A BashOutput object containing the result or an error message.
    """
    allowed_commands = ["uptime", "df -h", "free -m"]
    
    if not any(command.startswith(cmd) for cmd in allowed_commands):
        return BashOutput(status="error", error=f"Command '{command}' not permitted.")
    
    try:
        result = subprocess.run(command.split(), capture_output=True, text=True, check=True)
        return BashOutput(status="success", output=result.stdout)
    except Exception as e:
        return BashOutput(status="error", error=str(e))
