"""Type utility functions for AI Functions.

This module provides helper functions for type introspection and validation.
"""

import enum
import inspect
from typing import get_args, get_origin

from pydantic import BaseModel, TypeAdapter


def is_pydantic_model(type_: type) -> bool:
    """Check if a type is a Pydantic model.

    Args:
        type_: The type to check

    Returns:
        True if the type is a Pydantic BaseModel subclass
    """
    return isinstance(type_, type) and issubclass(type_, BaseModel)


def is_json_serializable_type(type_: type) -> bool:
    """Check if a type can be serialized to/from JSON using Pydantic's TypeAdapter.

    Args:
        type_: The type to check

    Returns:
        True if the type is JSON-serializable, False otherwise
    """
    # Pydantic models are always JSON-serializable
    if is_pydantic_model(type_):
        return True

    # Use Pydantic's TypeAdapter as the authoritative check
    try:
        adapter: TypeAdapter[type] = TypeAdapter(type_)
        adapter.json_schema(mode="serialization")
        return True
    except Exception:
        return False


def generate_signature_from_model(model: type[BaseModel], func_name: str = "final_answer") -> str:
    """Generate function signature corresponding to the constructor of a pydantic model."""
    # Create parameter list
    params = []
    for field_name, field_info in model.model_fields.items():
        annotation = field_info.annotation
        if field_info.is_required():
            params.append(inspect.Parameter(field_name, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=annotation))
        else:
            params.append(
                inspect.Parameter(
                    field_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=field_info.default,
                    annotation=annotation,
                )
            )

    # Create signature
    sig = inspect.Signature(params)
    return f"{func_name}{sig}"


def _describe_type(t: type) -> str:
    """Return a short human-readable label for a type."""
    origin = get_origin(t)
    if origin is list:
        args = get_args(t)
        inner = _describe_type(args[0]) if args else "any value"
        return f"a JSON array where each element is {inner}"
    if origin is dict:
        args = get_args(t)
        if args and len(args) == 2:
            return f"a JSON object with {_describe_type(args[0])} keys and {_describe_type(args[1])} values"
        return "a JSON object"
    if t is str:
        return "a string"
    if t is bool:
        return "a boolean (true or false)"
    if t is int:
        return "an integer"
    if t is float:
        return "a number (float)"
    if isinstance(t, type) and issubclass(t, BaseModel):
        return f"a {t.__name__} object"
    if isinstance(t, type) and issubclass(t, enum.Enum):
        return f"one of the {t.__name__} values"
    return t.__name__ if hasattr(t, "__name__") else str(t)


def _pydantic_model_compliance_text(model_type: type[BaseModel]) -> str:
    """Build a field-list description for a Pydantic model."""
    lines = [f"Respond with a JSON object conforming to the **{model_type.__name__}** schema:", ""]
    for name, field in model_type.model_fields.items():
        annotation = field.annotation
        type_label = _describe_type(annotation) if annotation is not None else "any"
        required = "required" if field.is_required() else "optional"
        desc = f" - {field.description}" if field.description else ""
        lines.append(f"- **{name}** ({type_label}, {required}){desc}")
    return "\n".join(lines)


def generate_type_compliance_text(return_type: type) -> str | None:
    """Generate a markdown section describing the expected output type.

    Returns None for str (no extra guidance needed) and for types that
    cannot be meaningfully described (e.g. Callable).
    """
    if return_type is str:
        return None

    # bool must be checked before int (bool is a subclass of int)
    if return_type is bool:
        return (
            "## Expected Output Type\n\n"
            "Your answer must be a **boolean** value: `true` or `false`.\n"
            "Do not wrap it in quotes or add explanation - return only the boolean."
        )

    if return_type is int:
        return (
            "## Expected Output Type\n\n"
            "Your answer must be an **integer** (whole number).\n"
            "Do not include decimal points, quotes, or units - return only the number."
        )

    if return_type is float:
        return (
            "## Expected Output Type\n\n"
            "Your answer must be a **number** (float).\n"
            "Return a numeric value. Do not include quotes or units."
        )

    if isinstance(return_type, type) and issubclass(return_type, enum.Enum):
        members = [f"`{m.value}`" for m in return_type]
        return (
            "## Expected Output Type\n\n"
            f"Your answer must be exactly one of the following {return_type.__name__} values:\n"
            + "\n".join(f"- {m}" for m in members)
            + "\n\nReturn only the value, with no extra text."
        )

    if isinstance(return_type, type) and issubclass(return_type, BaseModel):
        return "## Expected Output Type\n\n" + _pydantic_model_compliance_text(return_type)

    # Generic types: list[T], dict[K, V], bare list, bare dict
    origin = get_origin(return_type)
    if origin is list or return_type is list:
        desc = _describe_type(return_type)
        return f"## Expected Output Type\n\nYour answer must be {desc}.\nReturn valid JSON array syntax."

    if origin is dict or return_type is dict:
        desc = _describe_type(return_type)
        return f"## Expected Output Type\n\nYour answer must be {desc}.\nReturn valid JSON object syntax."

    # Fallback: try JSON schema description
    if is_json_serializable_type(return_type):
        desc = _describe_type(return_type)
        return f"## Expected Output Type\n\nYour answer must be {desc}."

    # Non-serializable (e.g. Callable) - no guidance possible
    return None
