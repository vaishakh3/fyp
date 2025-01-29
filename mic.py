import asyncio
from hume import HumeVoiceClient, MicrophoneInterface
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

async def main():
    HUME_API_KEY = os.getenv("HUME_API_KEY")
    if not HUME_API_KEY:
        raise ValueError("HUME_API_KEY environment variable is not set")

    client = HumeVoiceClient(HUME_API_KEY)

    async with client.connect(config_id=os.getenv("CONFIG_ID")) as socket:
        try:
            await MicrophoneInterface.start(socket, allow_user_interrupt=True)
        except Exception as e:
            print(f"Error occurred: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")