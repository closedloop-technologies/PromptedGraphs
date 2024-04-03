import unittest
from typing import List, Dict, Any

from promptedgraphs.generation.schema_from_data import schema_from_data

class TestSchemaFromData(unittest.TestCase):
    def test_empty_data_samples(self):
        data_samples: List[Dict[str, Any]] = []
        expected_schema = {}
        self.assertEqual(schema_from_data(data_samples), expected_schema)

    def test_single_data_sample(self):
        data_samples = [
            {"name": "John", "age": 30, "city": "New York"}
        ]
        expected_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "city": {"type": "string"}
            },
            "required": ["name", "age", "city"]
        }
        self.assertEqual(schema_from_data(data_samples), expected_schema)

    def test_multiple_data_samples(self):
        data_samples = [
            {"name": "John", "age": 30, "city": "New York"},
            {"name": "Alice", "age": 25, "city": "London"},
            {"name": "Bob", "age": 35, "country": "USA"}
        ]
        expected_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "city": {"type": "string"},
                "country": {"type": "string"}
            },
            "required": ["name", "age"]
        }
        self.assertEqual(schema_from_data(data_samples), expected_schema)

    def test_nested_objects(self):
        data_samples = [
            {"person": {"name": "John", "age": 30}, "city": "New York"},
            {"person": {"name": "Alice", "age": 25}, "city": "London"}
        ]
        expected_schema = {
            "type": "object",
            "properties": {
                "person": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"}
                    }
                },
                "city": {"type": "string"}
            },
            "required": ["person", "city"]
        }
        self.assertEqual(schema_from_data(data_samples), expected_schema)

    def test_arrays(self):
        data_samples = [
            {"name": "John", "hobbies": ["reading", "swimming"]},
            {"name": "Alice", "hobbies": ["painting", "dancing"]}
        ]
        expected_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "hobbies": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": sorted(["name", "hobbies"])
        }
        self.assertEqual(schema_from_data(data_samples), expected_schema)

    def test_type_merging(self):
        data_samples = [
            {"value": 10},
            {"value": "20"},
            {"value": 30.5}
        ]
        expected_schema = {
            "type": "object",
            "properties": {
                "value": {
                    "anyOf": [
                        {"type": "integer"},
                        {"type": "number"},
                        {"type": "string"}
                    ]
                }
            },
            "required": ["value"]
        }
        self.assertEqual(schema_from_data(data_samples), expected_schema)

if __name__ == '__main__':
    unittest.main()