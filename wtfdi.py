import inspect
from collections.abc import Collection
from contextlib import contextmanager
from functools import reduce
from types import FrameType
from typing import Annotated, Any, Callable, Final, Generator

DEP_VAR: Final = "__wtfdi_deps__"
type Depends[T] = Annotated[T, "Depends"]


class DependencyNotFoundError(KeyError):
    """Raised when context dependency not found."""

    def __init__(
            self,
            name: str,
            func: Callable[..., Any],
            available: Collection[str]
    ) -> None:
        """
        Create exception.
        :param name: name of missing dependency
        :param func: function in which exception occurred
        :param available: available names in context
        """
        super().__init__(name)
        self.name = name
        self.func = func
        self.available = available

    def __str__(self) -> str:
        """To string."""
        return (
            f"Dependency {self.name} of {self.func} "
            f"was not found in context. "
            f"Context contained: {self.available}"
        )


def _build_dependencies(frame: FrameType) -> dict[str, Any]:
    dependencies = []
    while frame.f_back:
        if DEP_VAR in frame.f_locals:
            dependencies.append(frame.f_locals[DEP_VAR])
    return reduce(lambda a, b: a | b, dependencies, {})


@contextmanager
def context(**deps: Any) -> Generator[None]:
    """Provide context."""
    # Two frames back because we are wrapped with contextmanager
    frame = inspect.currentframe().f_back.f_back
    outer_dependencies = _build_dependencies(frame)
    frame.f_locals[DEP_VAR] = outer_dependencies | deps
    try:
        yield
    finally:
        frame.f_locals.pop(DEP_VAR)


def with_context[T, **P](func: Callable[P, T]) -> Callable[..., T]:
    """Wrap function to provide context."""
    def _wrapper(*args, **kwargs) -> T:
        frame = inspect.currentframe().f_back
        source = frame.f_locals.get(DEP_VAR, {})
        for dep in _resolve_dependencies(func):
            if dep not in source:
                raise DependencyNotFoundError(dep, func, source.keys())
            kwargs[dep] = source[dep]
        return func(*args, **kwargs)

    return _wrapper


def _resolve_dependencies(func: Callable[..., Any]) -> list[str]:
    return [
        name
        for name, anno in (getattr(func, "__annotations__", {}) or {}).items()
        if getattr(anno, "__name__", None) == "Depends"
    ]


@with_context
def say_hello(to_who: str, logger: Depends) -> None:
    logger("Hello,", to_who)


with context(logger=print):
    say_hello("Kotlin")