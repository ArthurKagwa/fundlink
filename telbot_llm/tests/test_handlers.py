from unittest import AsyncTestCase
from unittest.mock import patch, AsyncMock
from telegram import Update
from telegram.ext import ContextTypes
from telbot_llm.handlers import handle_message

class TestHandlers(AsyncTestCase):

    @patch('telbot_llm.handlers.call_django_api', new_callable=AsyncMock)
    @patch('telbot_llm.handlers.chat_with_tools', new_callable=AsyncMock)
    async def test_handle_message_tool_call(self, mock_chat_with_tools, mock_call_django_api):
        # Arrange
        update = Update(update_id=1, message=type('Message', (object,), {'text': 'I want to donate', 'from_user': type('User', (object,), {'id': 12345})}))
        context = ContextTypes.DEFAULT_TYPE()

        mock_chat_with_tools.return_value = {
            "tool_call": {
                "name": "list_campaigns",
                "arguments": {}
            }
        }
        mock_call_django_api.return_value = {"campaigns": ["Campaign 1", "Campaign 2"]}

        # Act
        await handle_message(update, context)

        # Assert
        mock_chat_with_tools.assert_called_once_with('I want to donate', '12345')
        mock_call_django_api.assert_called_once_with("list_campaigns", {})

    @patch('telbot_llm.handlers.call_django_api', new_callable=AsyncMock)
    @patch('telbot_llm.handlers.chat_with_tools', new_callable=AsyncMock)
    async def test_handle_message_text_response(self, mock_chat_with_tools, mock_call_django_api):
        # Arrange
        update = Update(update_id=1, message=type('Message', (object,), {'text': 'Tell me about donations', 'from_user': type('User', (object,), {'id': 12345})}))
        context = ContextTypes.DEFAULT_TYPE()

        mock_chat_with_tools.return_value = {
            "text": "Here is some information about donations."
        }

        # Act
        await handle_message(update, context)

        # Assert
        mock_chat_with_tools.assert_called_once_with('Tell me about donations', '12345')
        mock_call_django_api.assert_not_called()  # No tool call should be made

    @patch('telbot_llm.handlers.call_django_api', new_callable=AsyncMock)
    @patch('telbot_llm.handlers.chat_with_tools', new_callable=AsyncMock)
    async def test_handle_message_register_user(self, mock_chat_with_tools, mock_call_django_api):
        # Arrange
        update = Update(update_id=1, message=type('Message', (object,), {'text': 'I want to register', 'from_user': type('User', (object,), {'id': 12345, 'username': 'test_user'})}))
        context = ContextTypes.DEFAULT_TYPE()

        mock_chat_with_tools.return_value = {
            "tool_call": {
                "name": "register_user",
                "arguments": {
                    "telegram_id": "12345",
                    "username": "test_user"
                }
            }
        }
        mock_call_django_api.return_value = {"success": True}

        # Act
        await handle_message(update, context)

        # Assert
        mock_call_django_api.assert_called_once_with("register_user", {"telegram_id": "12345", "username": "test_user"})