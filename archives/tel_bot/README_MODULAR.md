# Fundlink Telegram Bot - Modular Architecture

## 🏗️ Architecture Overview

This bot has been refactored into a clean, modular MVP structure with clear separation of concerns:

```
tel_bot/
├── main.py              # Main bot application
├── bot.py               # Entry point (backward compatibility)
├── config.py            # Configuration settings
├── webhook.py           # Webhook server (legacy)
├── webhook_new.py       # Modular webhook server
├── utils.py             # Legacy utilities
├── utils_legacy.py      # Backward compatibility layer
├── requirements.txt     # Dependencies
├── handlers/            # Bot command and callback handlers
│   ├── __init__.py
│   ├── base.py         # Base handler class
│   ├── commands.py     # Command handlers (/start, /campaigns, etc.)
│   └── callbacks.py    # Callback query handlers (button clicks)
├── services/           # Business logic and external integrations
│   ├── __init__.py
│   ├── api_client.py   # Backend API communication
│   ├── deep_link.py    # MetaMask deep link generation
│   └── message_formatter.py  # Telegram message formatting
└── core/               # Core utilities and validation
    ├── __init__.py
    ├── validators.py   # Input validation functions
    └── exceptions.py   # Custom exception classes
```

## 🚀 Key Features of Modular Design

### 1. **Separation of Concerns**
- **Handlers**: Pure Telegram bot interaction logic
- **Services**: Business logic and external API calls
- **Core**: Validation and utility functions

### 2. **Error Handling**
- Centralized error handling in `BaseHandler`
- Custom exceptions for different error types
- Graceful fallbacks for API failures

### 3. **Logging & Monitoring**
- Structured logging throughout all modules
- User action tracking for analytics
- Error logging with context

### 4. **Validation**
- Input validation for amounts, tokens, addresses
- Type safety with proper validation functions
- Security checks for user inputs

## 📦 Module Descriptions

### Handlers (`handlers/`)
- **`base.py`**: Base class with common handler functionality
- **`commands.py`**: Handles `/start`, `/campaigns`, `/history`, `/help`
- **`callbacks.py`**: Handles button clicks and inline interactions

### Services (`services/`)
- **`api_client.py`**: Communicates with Django backend API
- **`deep_link.py`**: Generates MetaMask deep links for donations  
- **`message_formatter.py`**: Formats messages for Telegram display

### Core (`core/`)
- **`validators.py`**: Validates amounts, tokens, addresses, etc.
- **`exceptions.py`**: Custom exception classes for error handling

## 🔧 Usage

### Running the Bot

**Polling Mode (Development):**
```bash
python bot.py
# or
python main.py
```

**Webhook Mode (Production):**
```bash
python webhook_new.py
```

### Configuration

All configuration is handled in `config.py` via environment variables:

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token
BACKEND_URL=https://your-backend.com
INTERNAL_API_KEY=your_internal_service_key

# Optional
BOT_DEBUG=false
BOT_LOG_LEVEL=INFO
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8443
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook
```

## 🧪 Testing

The modular structure makes testing much easier:

```python
# Test individual handlers
from handlers.commands import CommandHandlers
from services.api_client import APIClient

# Mock the API client for testing
api_client = MockAPIClient()
command_handler = CommandHandlers(api_client, message_formatter)

# Test command handling
await command_handler.start(mock_update, mock_context)
```

## 🔄 Migration from Legacy Code

The old monolithic `bot.py` has been replaced, but backward compatibility is maintained:

1. **Entry Point**: `bot.py` still works as the main entry point
2. **Legacy Imports**: `utils_legacy.py` provides backward compatibility
3. **Same Functionality**: All existing features work exactly the same

## 🎯 MVP Benefits

1. **Maintainability**: Clean separation makes code easier to understand and modify
2. **Testability**: Each component can be tested independently
3. **Scalability**: Easy to add new features without affecting existing code
4. **Reliability**: Better error handling and logging
5. **Developer Experience**: Clear structure for new team members

## 🔄 Future Enhancements

The modular structure makes it easy to add:

- Custom amount input flows
- Multi-language support
- Advanced analytics
- Integration with other payment methods
- Admin commands for NGO management
- Notification systems

## 📝 Development Guidelines

1. **Add new commands**: Create methods in `CommandHandlers`
2. **Add new callbacks**: Create methods in `CallbackHandlers`  
3. **Add new services**: Create new files in `services/`
4. **Add validation**: Add functions to `core/validators.py`
5. **Handle errors**: Use custom exceptions from `core/exceptions.py`

This modular architecture provides a solid foundation for the Fundlink bot MVP while maintaining clean, maintainable, and testable code.