import os
import sys
from dotenv import load_dotenv
from telbot_llm import config

def main():
    # Load environment variables from .env file
    load_dotenv()

    # Set up the configuration
    config.load_config()

    # Start the development server
    print("Starting the development server...")
    os.system("python -m telbot_llm")

if __name__ == "__main__":
    main()