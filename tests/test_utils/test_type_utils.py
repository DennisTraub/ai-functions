"""Unit tests for type_utils module.

Tests for is_pydantic_model, is_json_serializable_type, and generate_type_compliance_text functions.
"""

import enum
from typing import Callable, Dict, List, Optional

from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel, Field

from ai_functions.utils._type import generate_type_compliance_text, is_json_serializable_type, is_pydantic_model


class TestIsPydanticModel:
    """Tests for is_pydantic_model function."""

    def test_returns_true_for_pydantic_model(self, sample_pydantic_model):
        """Test is_pydantic_model returns True for Pydantic BaseModel subclass."""
        assert is_pydantic_model(sample_pydantic_model) is True

    def test_returns_true_for_nested_pydantic_model(self):
        """Test is_pydantic_model returns True for nested Pydantic model."""

        class InnerModel(BaseModel):
            value: int

        class OuterModel(BaseModel):
            inner: InnerModel

        assert is_pydantic_model(OuterModel) is True
        assert is_pydantic_model(InnerModel) is True

    def test_returns_false_for_non_pydantic_type_str(self):
        """Test is_pydantic_model returns False for str type."""
        assert is_pydantic_model(str) is False

    def test_returns_false_for_non_pydantic_type_dict(self):
        """Test is_pydantic_model returns False for dict type."""
        assert is_pydantic_model(dict) is False

    def test_returns_false_for_non_pydantic_type_int(self):
        """Test is_pydantic_model returns False for int type."""
        assert is_pydantic_model(int) is False

    def test_returns_false_for_non_pydantic_type_list(self):
        """Test is_pydantic_model returns False for list type."""
        assert is_pydantic_model(list) is False

    def test_returns_false_for_non_type_string_value(self):
        """Test is_pydantic_model returns False for string value without raising."""
        assert is_pydantic_model("not a type") is False

    def test_returns_false_for_non_type_integer_value(self):
        """Test is_pydantic_model returns False for integer value without raising."""
        assert is_pydantic_model(123) is False

    def test_returns_false_for_non_type_none_value(self):
        """Test is_pydantic_model returns False for None value without raising."""
        assert is_pydantic_model(None) is False

    def test_returns_false_for_pydantic_instance(self, sample_pydantic_instance):
        """Test is_pydantic_model returns False for Pydantic model instance."""
        assert is_pydantic_model(sample_pydantic_instance) is False


class TestIsJsonSerializableType:
    """Tests for is_json_serializable_type function."""

    def test_returns_true_for_pydantic_model(self, sample_pydantic_model):
        """Test is_json_serializable_type returns True for Pydantic models."""
        assert is_json_serializable_type(sample_pydantic_model) is True

    def test_returns_true_for_str(self):
        """Test is_json_serializable_type returns True for str type."""
        assert is_json_serializable_type(str) is True

    def test_returns_true_for_int(self):
        """Test is_json_serializable_type returns True for int type."""
        assert is_json_serializable_type(int) is True

    def test_returns_true_for_float(self):
        """Test is_json_serializable_type returns True for float type."""
        assert is_json_serializable_type(float) is True

    def test_returns_true_for_bool(self):
        """Test is_json_serializable_type returns True for bool type."""
        assert is_json_serializable_type(bool) is True

    def test_returns_true_for_list(self):
        """Test is_json_serializable_type returns True for list type."""
        assert is_json_serializable_type(list) is True

    def test_returns_true_for_dict(self):
        """Test is_json_serializable_type returns True for dict type."""
        assert is_json_serializable_type(dict) is True

    def test_returns_true_for_typed_list(self):
        """Test is_json_serializable_type returns True for List[str]."""
        assert is_json_serializable_type(List[str]) is True

    def test_returns_true_for_typed_dict(self):
        """Test is_json_serializable_type returns True for Dict[str, int]."""
        assert is_json_serializable_type(Dict[str, int]) is True

    def test_returns_true_for_optional_type(self):
        """Test is_json_serializable_type returns True for Optional[str]."""
        assert is_json_serializable_type(Optional[str]) is True

    def test_returns_false_for_non_serializable_callable(self):
        """Test is_json_serializable_type returns False for callable."""
        from typing import Callable

        assert is_json_serializable_type(Callable) is False

    def test_returns_false_for_custom_class(self):
        """Test is_json_serializable_type returns False for non-Pydantic class."""

        class CustomClass:
            def __init__(self, value):
                self.value = value

        assert is_json_serializable_type(CustomClass) is False


# Property-based tests


class TestIsPydanticModelProperty:
    """Property-based tests for is_pydantic_model."""

    @given(st.sampled_from([str, int, float, bool, list, dict, tuple, set, bytes]))
    @settings(max_examples=100)
    def test_non_pydantic_types_return_false(self, type_):
        """For any non-Pydantic type, is_pydantic_model should return False."""
        assert is_pydantic_model(type_) is False


class TestIsJsonSerializableTypeProperty:
    """Property-based tests for is_json_serializable_type."""

    @given(st.sampled_from([str, int, float, bool, list, dict]))
    @settings(max_examples=100)
    def test_primitive_types_are_serializable(self, type_):
        """For any primitive type, is_json_serializable_type should return True."""
        assert is_json_serializable_type(type_) is True


class TestGenerateTypeComplianceText:
    """Tests for generate_type_compliance_text function."""

    def test_str_returns_none(self):
        """str needs no extra guidance."""
        assert generate_type_compliance_text(str) is None

    def test_bool_returns_boolean_guidance(self):
        """bool must return boolean guidance, NOT integer guidance."""
        result = generate_type_compliance_text(bool)
        assert result is not None
        assert "## Expected Output Type" in result
        assert "boolean" in result
        assert "integer" not in result.lower().split("boolean")[0]  # no int leakage

    def test_int_returns_integer_guidance(self):
        result = generate_type_compliance_text(int)
        assert result is not None
        assert "## Expected Output Type" in result
        assert "integer" in result

    def test_float_returns_float_guidance(self):
        result = generate_type_compliance_text(float)
        assert result is not None
        assert "## Expected Output Type" in result
        assert "number" in result

    def test_enum_lists_member_values(self):
        class Color(enum.Enum):
            RED = "red"
            GREEN = "green"
            BLUE = "blue"

        result = generate_type_compliance_text(Color)
        assert result is not None
        assert "## Expected Output Type" in result
        assert "`red`" in result
        assert "`green`" in result
        assert "`blue`" in result
        assert "exactly one of" in result

    def test_str_enum_works(self):
        class Priority(enum.StrEnum):
            LOW = "low"
            HIGH = "high"

        result = generate_type_compliance_text(Priority)
        assert result is not None
        assert "`low`" in result
        assert "`high`" in result

    def test_base_model_lists_fields(self):
        class User(BaseModel):
            name: str
            age: int
            bio: str = Field(default="", description="Short biography")

        result = generate_type_compliance_text(User)
        assert result is not None
        assert "## Expected Output Type" in result
        assert "User" in result
        assert "**name**" in result
        assert "**age**" in result
        assert "**bio**" in result
        assert "required" in result
        assert "optional" in result
        assert "Short biography" in result

    def test_list_str_describes_array(self):
        result = generate_type_compliance_text(List[str])
        assert result is not None
        assert "## Expected Output Type" in result
        assert "array" in result

    def test_dict_str_int_describes_object(self):
        result = generate_type_compliance_text(Dict[str, int])
        assert result is not None
        assert "## Expected Output Type" in result
        assert "object" in result

    def test_bare_list_gives_generic_guidance(self):
        result = generate_type_compliance_text(list)
        assert result is not None
        assert "## Expected Output Type" in result
        assert "array" in result.lower() or "list" in result.lower()

    def test_bare_dict_gives_generic_guidance(self):
        result = generate_type_compliance_text(dict)
        assert result is not None
        assert "## Expected Output Type" in result
        assert "object" in result.lower() or "dict" in result.lower()

    def test_callable_returns_none(self):
        """Non-serializable types return None."""
        assert generate_type_compliance_text(Callable) is None

    def test_nested_list_base_model(self):
        class Item(BaseModel):
            id: int

        result = generate_type_compliance_text(List[Item])
        assert result is not None
        assert "array" in result
        assert "Item" in result
