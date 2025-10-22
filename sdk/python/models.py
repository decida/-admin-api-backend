"""
Data models for Admin API SDK
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class BusinessObjectParam:
    """Business Object parameter definition"""
    name: str
    type: str
    required: bool = False
    default_value: Any = None


@dataclass
class VariableSource:
    """Variable source for parameter mapping"""
    step_index: int | None = None
    field_name: str = ""


@dataclass
class ParameterMapping:
    """Parameter mapping configuration"""
    parameter_name: str
    source_type: str  # "static" or "variable"
    static_value: Any = ""
    variable_source: VariableSource = field(default_factory=VariableSource)


@dataclass
class ExecutionChainStep:
    """Execution chain step definition"""
    business_object_id: str
    business_object_name: str
    business_object_type: str
    business_object_params: list[BusinessObjectParam]
    order: int
    parameter_mappings: list[ParameterMapping] = field(default_factory=list)


@dataclass
class APIResource:
    """API Resource definition"""
    id: str
    path: str
    method: str
    description: str | None
    is_active: bool
    business_object_id: str
    business_object_name: str
    business_object_params: list[BusinessObjectParam]
    execution_chain: list[ExecutionChainStep] | None
    created_at: datetime
    updated_at: datetime


@dataclass
class ExecutionResult:
    """Result of API resource execution (legacy single business object)"""
    success: bool
    rows: list[dict] | None = None
    row_count: int | None = None
    error: str | None = None


@dataclass
class ChainExecutionError:
    """Error details for chain execution"""
    message: str
    step: int | None = None
    business_object_name: str | None = None
    details: str | None = None


@dataclass
class ChainExecutionResult:
    """Result of chain execution"""
    success: bool
    steps: int | None = None
    result: dict | list | None = None
    all_results: list[dict | list] | None = None
    error: ChainExecutionError | None = None
