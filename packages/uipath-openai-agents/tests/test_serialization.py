"""Tests for serialization module."""

import dataclasses
from enum import Enum
from typing import Any

from pydantic import BaseModel

from uipath_openai_agents.runtime._serialize import serialize_output


class SampleEnum(Enum):
    """Sample enum for testing."""

    OPTION_A = "option_a"
    OPTION_B = "option_b"


class PydanticModel(BaseModel):
    """Sample Pydantic model."""

    name: str
    value: int
    active: bool = True


@dataclasses.dataclass
class DataclassModel:
    """Sample dataclass model."""

    id: str
    count: int
    metadata: dict[str, Any] | None = None


class TestSerializeOutput:
    """Tests for serialize_output function."""

    def test_serialize_none(self):
        """Test serializing None returns empty dict."""
        result = serialize_output(None)
        assert result == {}

    def test_serialize_primitive_string(self):
        """Test serializing string returns string."""
        result = serialize_output("test string")
        assert result == "test string"

    def test_serialize_primitive_int(self):
        """Test serializing int returns int."""
        result = serialize_output(42)
        assert result == 42

    def test_serialize_primitive_float(self):
        """Test serializing float returns float."""
        result = serialize_output(3.14)
        assert result == 3.14

    def test_serialize_primitive_bool(self):
        """Test serializing bool returns bool."""
        result = serialize_output(True)
        assert result is True

    def test_serialize_simple_dict(self):
        """Test serializing simple dictionary."""
        data = {"name": "Alice", "age": 30, "active": True}
        result = serialize_output(data)
        assert result == data

    def test_serialize_nested_dict(self):
        """Test serializing nested dictionary."""
        data = {
            "user": {"name": "Bob", "email": "bob@example.com"},
            "settings": {"theme": "dark", "notifications": True},
        }
        result = serialize_output(data)
        assert result == data

    def test_serialize_simple_list(self):
        """Test serializing simple list."""
        data = [1, 2, 3, 4, 5]
        result = serialize_output(data)
        assert result == data

    def test_serialize_list_of_dicts(self):
        """Test serializing list of dictionaries."""
        data = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"},
        ]
        result = serialize_output(data)
        assert result == data

    def test_serialize_pydantic_model(self):
        """Test serializing Pydantic model."""
        model = PydanticModel(name="TestModel", value=100)
        result = serialize_output(model)

        assert isinstance(result, dict)
        assert result["name"] == "TestModel"
        assert result["value"] == 100
        assert result["active"] is True  # default value

    def test_serialize_pydantic_model_with_nested(self):
        """Test serializing Pydantic model with nested data."""

        class NestedModel(BaseModel):
            items: list[str]
            count: int

        class ParentModel(BaseModel):
            name: str
            nested: NestedModel

        model = ParentModel(
            name="Parent", nested=NestedModel(items=["a", "b"], count=2)
        )
        result = serialize_output(model)

        assert isinstance(result, dict)
        assert result["name"] == "Parent"
        assert isinstance(result["nested"], dict)
        assert result["nested"]["items"] == ["a", "b"]
        assert result["nested"]["count"] == 2

    def test_serialize_dataclass(self):
        """Test serializing dataclass."""
        obj = DataclassModel(id="test-123", count=5, metadata={"key": "value"})
        result = serialize_output(obj)

        assert isinstance(result, dict)
        assert result["id"] == "test-123"
        assert result["count"] == 5
        assert result["metadata"] == {"key": "value"}

    def test_serialize_dataclass_without_optional(self):
        """Test serializing dataclass without optional field."""
        obj = DataclassModel(id="test-456", count=10)
        result = serialize_output(obj)

        assert isinstance(result, dict)
        assert result["id"] == "test-456"
        assert result["count"] == 10
        # None values are recursively converted to {}
        assert result["metadata"] == {}

    def test_serialize_enum(self):
        """Test serializing enum."""
        result = serialize_output(SampleEnum.OPTION_A)
        assert result == "option_a"

    def test_serialize_dict_with_enum_values(self):
        """Test serializing dict with enum values."""
        data = {"status": SampleEnum.OPTION_B, "count": 5}
        result = serialize_output(data)

        assert result["status"] == "option_b"
        assert result["count"] == 5

    def test_serialize_complex_nested_structure(self):
        """Test serializing complex nested structure."""
        model = PydanticModel(name="Complex", value=999)
        dataclass_obj = DataclassModel(id="dc-1", count=3)

        data = {
            "models": [model, PydanticModel(name="Another", value=42)],
            "dataclass": dataclass_obj,
            "enum_value": SampleEnum.OPTION_A,
            "nested": {
                "list": [1, 2, 3],
                "dict": {"key": "value"},
            },
            "primitives": {"str": "text", "int": 123, "bool": False},
        }

        result = serialize_output(data)

        # Verify structure
        assert isinstance(result, dict)
        assert len(result["models"]) == 2
        assert result["models"][0]["name"] == "Complex"
        assert result["models"][0]["value"] == 999
        assert result["dataclass"]["id"] == "dc-1"
        assert result["enum_value"] == "option_a"
        assert result["nested"]["list"] == [1, 2, 3]
        assert result["primitives"]["str"] == "text"

    def test_serialize_empty_structures(self):
        """Test serializing empty structures."""
        empty_dict: dict[str, str] = {}
        empty_list: list[int] = []

        assert serialize_output(empty_dict) == {}
        assert serialize_output(empty_list) == []

    def test_serialize_dict_with_none_values(self):
        """Test serializing dict with None values."""
        data = {"key1": "value1", "key2": None, "key3": 0}
        result = serialize_output(data)

        # None values are recursively converted to {}
        assert result["key1"] == "value1"
        assert result["key2"] == {}
        assert result["key3"] == 0

    def test_serialize_list_with_mixed_types(self):
        """Test serializing list with mixed types."""
        data = [
            "string",
            123,
            True,
            {"nested": "dict"},
            PydanticModel(name="Model", value=50),
            None,
        ]

        result = serialize_output(data)

        assert isinstance(result, list)
        assert result[0] == "string"
        assert result[1] == 123
        assert result[2] is True
        assert result[3] == {"nested": "dict"}
        assert isinstance(result[4], dict)
        assert result[4]["name"] == "Model"
        # None values are recursively converted to {}
        assert result[5] == {}

    def test_serialize_dict_with_numeric_keys_as_strings(self):
        """Test that numeric keys are preserved."""
        data = {"1": "one", "2": "two", "3": "three"}
        result = serialize_output(data)
        assert result == data

    def test_serialize_unicode_strings(self):
        """Test serializing unicode strings."""
        data = {"chinese": "你好", "emoji": "😀🎉", "arabic": "مرحبا"}
        result = serialize_output(data)
        assert result == data

    def test_serialize_bytes_as_is(self):
        """Test that bytes are returned as is (not iterated)."""
        data = b"binary data"
        result = serialize_output(data)
        assert result == data

    def test_serialize_pydantic_with_field_alias(self):
        """Test serializing Pydantic model with field aliases."""

        class AliasModel(BaseModel):
            internal_name: str

            class Config:
                fields = {"internal_name": {"alias": "externalName"}}

        model = AliasModel(internal_name="test")
        result = serialize_output(model)

        # Should use alias in serialization
        assert isinstance(result, dict)
        # Note: behavior depends on model_dump(by_alias=True)

    def test_serialize_pydantic_model_class(self):
        """Test that Pydantic model classes (not instances) are handled safely."""
        # This should not raise TypeError about missing 'self'
        result = serialize_output(PydanticModel)
        # Model classes should be returned as-is (not serialized)
        assert result == PydanticModel

    def test_serialize_dict_containing_model_class(self):
        """Test serializing dict that contains a Pydantic model class."""
        data = {
            "model_class": PydanticModel,
            "instance": PydanticModel(name="test", value=42),
            "other": "data",
        }
        result = serialize_output(data)

        # Model class should be returned as-is
        assert result["model_class"] == PydanticModel
        # Instance should be serialized
        assert result["instance"] == {"name": "test", "value": 42, "active": True}
        # Other data should pass through
        assert result["other"] == "data"
