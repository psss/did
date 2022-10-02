import os

import pytest

env_vars_parametrization = (
    ("env_name", "value"),
    (
        ("STR", "O"),
        ("INT", "0"),
        ("DOTENV_STR", "dotenv_str"),
        ("DOTENV_INT", "1"),
        ("YAML_STR", "yaml_str_overwritten"),
        ("YAML_INT", "1"),
        ("SPECIAL", "/=(;-)"),
        ),
    )


@pytest.mark.parametrize(*env_vars_parametrization)
def test_environment_file_with_variables(env_name, value):
    assert os.environ[env_name] == value
