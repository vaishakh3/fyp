import asyncio
from hume import HumeVoiceClient, MicrophoneInterface
from dotenv import load_dotenv
import os
from groq import Groq
import sqlite3
import json
import uuid

# Using sqlite3 to store the conversation
if os.path.exists('conversation.db'):
  os.remove('conversation.db')
conn = sqlite3.connect('conversation.db')
c = conn.cursor()

# create a table conversations with conversation long text, a uid for each conversation and a timestamp, also include a column for the summary of the conversation, criticality of the call, isSpam bool, user name, user location
c.execute('''CREATE TABLE conversations
              (uid text, conversation text, timestamp text, summary text, criticality text, isSpam bool, user text, location text)''')
conn.commit()
conn.close()

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


conversations = None
async def main() -> None:
  # Paste your Hume API key here
  HUME_API_KEY = os.getenv("HUME_API_KEY")
  # Connect and authenticate with Hume
  client = HumeVoiceClient(HUME_API_KEY)
  # Start streaming EVI over your device's microphone and speakers
  with open ("conversations.txt", "w") as f:
    f.write("")
  
  
  async with client.connect(config_id=os.getenv("CONFIG_ID")) as socket:
      conv = None
      try:
        conv = await MicrophoneInterface.start(socket, allow_user_interrupt=True)
      except Exception as e:
        print(e)
      finally:
        print(conv)
        
      
  with open("conversations.txt", "r") as f:
    conversations = f.read()


def get_conversation():
  # Keep reading the conversation file that is asyncronously written to by the chat client and wait for 'end the call' to be said by the user. then return the conversation
  with open("conversations.txt", "r") as f:
    conversations = f.read()
    chat_summary = client.chat.completions.create(messages=[
      {
        "role": "system",
        "content": """Provide criticality of the call, isSpam bool, user name, user location in the format only:
            {
              "summary": "The summary of the conversation",
              "criticality": "The criticality of the call(eg. high, medium, low)",
              "isSpam": "True or False",
              "department": "Department name(Fire, Police, Medical)",
              "user": "User name (Unknown if not provided)",
              "location": "User location (Unknown if not provided)"
            }
        """.strip()
      }, 
      {
        "role": "user",
        "content": conversations
      }
      
      ], model='llama3-8b-8192',stream=False)
    print(chat_summary.choices[0].message.content)
    json_data = json.loads(chat_summary.choices[0].message.content)
    conn = sqlite3.connect('conversation.db')
    c = conn.cursor()
    c.execute("INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (str(uuid.uuid4()), conversations, str(uuid.uuid4()), json_data["summary"], json_data["criticality"], json_data["isSpam"], json_data["user"], json_data["location"]))
    conn.commit()
    conn.close()
  
if __name__ == "__main__":
  try:
    asyncio.run(main())
    print("------------Conversation has ended------------")
  except Exception as e:
    print(e)
  finally:
    get_conversation()