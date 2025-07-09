import pytest
from avalontgbot.role import Role


def test_role_file():
    # Test that the role file exists for each role
    for role_instance in Role:
        assert role_instance.role_file.exists(), f"Role file for {role_instance.name} does not exist."

def test_description():
    # Test that the description method returns a string for each role
    for role_instance in Role:
        description = role_instance.description()
        assert isinstance(description, str), f"Description for {role_instance.name} is not a string."
        assert description, f"Description for {role_instance.name} is empty."
