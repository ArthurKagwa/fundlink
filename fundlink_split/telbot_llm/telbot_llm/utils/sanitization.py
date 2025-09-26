def sanitize_input(user_input: str) -> str:
    """
    Sanitize user input to prevent security issues such as XSS or injection attacks.
    This function removes any potentially harmful characters or scripts from the input.
    """
    # Remove leading and trailing whitespace
    sanitized_input = user_input.strip()
    
    # Replace HTML tags with empty strings
    sanitized_input = re.sub(r'<.*?>', '', sanitized_input)
    
    # Escape special characters
    sanitized_input = sanitized_input.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    return sanitized_input

def sanitize_response(llm_response: str) -> str:
    """
    Sanitize LLM responses to ensure they do not contain harmful content.
    This function checks for any inappropriate or unsafe content and removes it.
    """
    # Basic sanitization: remove any HTML tags
    sanitized_response = re.sub(r'<.*?>', '', llm_response)
    
    # Further checks can be added here for specific content filtering
    
    return sanitized_response