"""Result monad (api-contracts conventions — no throwing across module boundaries)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from smartinstall.core.results.api_error import ApiError

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Result(Generic[T]):
    """Discriminated success/failure wrapper used by internal services."""

    success: bool
    value: T | None = None
    error: ApiError | None = None

    @classmethod
    def ok(cls, value: T) -> Result[T]:
        return cls(success=True, value=value)

    @classmethod
    def fail(cls, error: ApiError) -> Result[T]:
        return cls(success=False, error=error)

    def unwrap(self) -> T:
        if not self.success or self.value is None:
            raise ValueError("Cannot unwrap a failed Result")
        return self.value
