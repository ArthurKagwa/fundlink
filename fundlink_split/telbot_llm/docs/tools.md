# Tools Documentation for telbot_llm Module

## Overview
The `telbot_llm` module provides a set of tools that the LLM can call to interact with the Django backend. These tools enable the bot to perform various actions such as fetching campaigns, registering users, and notifying donors.

## Available Tools

### 1. List Campaigns
- **Name:** `list_campaigns`
- **Description:** Retrieves a list of active campaigns available for donations.
- **Parameters:** None

### 2. Get Campaign
- **Name:** `get_campaign`
- **Description:** Fetches detailed information about a specific campaign.
- **Parameters:**
  - `campaign_id` (integer): The unique identifier of the campaign.

### 3. Register User
- **Name:** `register_user`
- **Description:** Registers a Telegram user in the backend database.
- **Parameters:**
  - `telegram_id` (string): The unique identifier for the Telegram user.
  - `username` (string): The username of the Telegram user.

### 4. Get Donations
- **Name:** `get_donations`
- **Description:** Retrieves the donation history for a specific Telegram user.
- **Parameters:**
  - `telegram_id` (string): The unique identifier for the Telegram user.

### 5. Notify Donor
- **Name:** `notify_donor`
- **Description:** Sends a notification message to a donor via the backend.
- **Parameters:**
  - `telegram_id` (string): The unique identifier for the Telegram user.
  - `message` (string): The notification message to be sent.

### 6. Apply NGO
- **Name:** `apply_ngo`
- **Description:** Submits an application for NGO registration.
- **Parameters:**
  - `name` (string): The name of the NGO.
  - `email` (string): The contact email for the NGO.
  - `wallet_address` (string): The wallet address associated with the NGO.
  - `website` (string): The website of the NGO.

## Usage
These tools are designed to be called by the LLM during conversations with users. The LLM will determine when to invoke a tool based on user input and will handle the responses accordingly.

## Security Considerations
- Ensure that all tool calls are validated and that sensitive information is handled securely.
- Use appropriate authentication mechanisms when interacting with the Django backend.

## Future Enhancements
- Additional tools may be added to support new features and functionalities as the project evolves.