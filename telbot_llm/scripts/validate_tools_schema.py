def validate_tools_schema(tools):
    """
    Validates the schema of the tools defined in tools.py.

    Args:
        tools (list): A list of tool definitions to validate.

    Returns:
        bool: True if all tools are valid, False otherwise.
    """
    required_keys = {"name", "description", "parameters"}

    for tool in tools:
        if not isinstance(tool, dict):
            print(f"Invalid tool format: {tool}. Tool must be a dictionary.")
            return False
        
        if not required_keys.issubset(tool.keys()):
            print(f"Missing required keys in tool: {tool}. Required keys are: {required_keys}.")
            return False
        
        # Validate parameters if they exist
        if "parameters" in tool:
            if not isinstance(tool["parameters"], dict):
                print(f"Parameters for tool {tool['name']} must be a dictionary.")
                return False

    print("All tools are valid.")
    return True


if __name__ == "__main__":
    from telbot_llm.tools import tools  # Assuming tools.py is in the same package

    is_valid = validate_tools_schema(tools)
    exit(0 if is_valid else 1)