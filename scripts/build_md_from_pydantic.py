import json
from enum import Enum
from typing import Dict, List, Type

from pydantic import BaseModel

from senv.pyproject import PyProject, _Senv, _SenvEnv, _SenvPackage, _Tool

py_project_schema = json.loads(PyProject.schema_json())
tool_schema = json.loads(_Tool.schema_json())
senv_schema = json.loads(_Senv.schema_json())
senv_env_schema = json.loads(_SenvEnv.schema_json())
senv_package_schema = json.loads(_SenvPackage.schema_json())

py_project_schema.pop("definitions", None)
tool_schema.pop("definitions", None)
senv_schema.pop("definitions", None)
senv_env_schema.pop("definitions", None)
senv_package_schema.pop("definitions", None)


def to_markdown_table(list_of_dicts):
    """Loop through a list of dicts and return a markdown table as a multi-line string.
    listOfDicts -- A list of dictionaries, each dict is a row
    """
    markdown_table = ""
    # Make a string of all the keys in the first dict with pipes before after and between each key
    markdown_header = "| " + " | ".join(map(str, list_of_dicts[0].keys())) + " |"
    # Make a header separator line with dashes instead of key names
    markdown_header_separator = "|-----" * len(list_of_dicts[0].keys()) + "|"
    # Add the header row and separator to the table
    markdown_table += markdown_header + "\n"
    markdown_table += markdown_header_separator + "\n"
    # Loop through the list of dictionaries outputting the rows
    for row in list_of_dicts:
        markdown_row = ""
        for key, col in row.items():
            markdown_row += "| " + str(col) + " "
        markdown_table += markdown_row + "|" + "\n"
    return markdown_table


def get_properties(obj: Type[BaseModel], namespace: str) -> List[Dict]:
    result: List[Dict] = []
    for name, f in obj.__fields__.items():
        is_generic_type = False
        try:
            if issubclass(f.outer_type_, BaseModel):
                continue
        except TypeError:
            is_generic_type = True

        f_class = f.outer_type_ if not is_generic_type else f.outer_type_.__class__
        t = str(f.outer_type_)
        if issubclass(f_class, Enum):
            t = "Enum Choices {{{}}}".format(
                ", ".join([e.value for e in f.outer_type_])
            )
        result.append(
            {
                "namespace": namespace,
                "name": f.alias,
                "type": t,
                "default": f.default or "",
                "description": f.field_info.description or "",
            }
        )

    return result


if __name__ == "__main__":
    properties = (
        get_properties(PyProject, "")
        + get_properties(_Tool, "tool")
        + get_properties(_Senv, "tool.senv")
        + get_properties(_SenvEnv, "tool.senv.env")
        + get_properties(_SenvPackage, "tool.senv.package")
    )

    print(to_markdown_table(properties))
