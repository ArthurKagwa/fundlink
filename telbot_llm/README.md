# telbot_llm Module

## Overview
The `telbot_llm` module is part of the FundLink humanitarian donations MVP, designed to facilitate intelligent interactions within a Telegram bot. This module integrates a large language model (LLM) to enhance user experience by enabling natural language understanding and tool-calling capabilities.

## Features
- **Conversational Interface**: Users can interact with the bot using natural language to browse campaigns and make donations.
- **Tool Integration**: The module exposes Django REST API endpoints as callable tools for the LLM, allowing for dynamic data retrieval and actions.
- **Donation Verification**: Integrates with a web3.py-based verifier to ensure on-chain transaction validation and donor notifications.

## Setup Instructions
1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd telbot_llm
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Copy the `.env.example` to `.env` and fill in the required values.

5. **Run the Development Server**:
   ```bash
   python scripts/run_dev.py
   ```

## Usage
- Start the Telegram bot and interact with it to explore available campaigns and make donations.
- The bot will respond to user queries and execute actions based on the LLM's understanding of the intent.

## Contribution Guidelines
1. **Fork the Repository**: Create your own fork of the repository.
2. **Create a Feature Branch**: 
   ```bash
   git checkout -b feature/YourFeature
   ```
3. **Make Your Changes**: Implement your feature or fix.
4. **Run Tests**: Ensure all tests pass before submitting a pull request.
5. **Submit a Pull Request**: Describe your changes and why they are necessary.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.

## Documentation
For detailed architecture and tool documentation, refer to the files in the `docs` directory.