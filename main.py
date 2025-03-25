import asyncio
from hume import HumeVoiceClient, MicrophoneInterface
from dotenv import load_dotenv
import os
from groq import Groq
import sqlite3
import json
import uuid
from datetime import datetime

# Using sqlite3 to store the conversation
conn = sqlite3.connect('conversation.db')
c = conn.cursor()

# create a table conversations only if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS conversations
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

    try:
        async with client.connect(config_id=os.getenv("CONFIG_ID")) as socket:
            mic_interface = None
            try:
                mic_interface = await MicrophoneInterface.start(socket, allow_user_interrupt=True)
                
                # Check for end call signal
                while not os.path.exists("end_call.txt"):
                    await asyncio.sleep(0.1)
                print("End call signal detected")
                
                # Force stop the microphone interface immediately
                if mic_interface:
                    print("Force stopping microphone interface...")
                    try:
                        await mic_interface.stop()
                        await socket.close()  # Force close the socket
                        print("Microphone interface and socket stopped")
                    except:
                        # If normal stop fails, force close everything
                        try:
                            socket._ws.close()
                            print("Socket forcefully closed")
                        except:
                            pass
                    
                # Clean up end call signal
                if os.path.exists("end_call.txt"):
                    os.remove("end_call.txt")
                    
            except asyncio.CancelledError:
                print("Conversation cancelled by user")
                # Force stop everything
                if mic_interface:
                    try:
                        await mic_interface.stop()
                        await socket.close()
                    except:
                        try:
                            socket._ws.close()
                        except:
                            pass
                    print("Microphone and socket forcefully stopped after cancellation")
            except Exception as e:
                print(f"Error during conversation: {e}")
                raise
            finally:
                # Ensure everything is stopped in any case
                if mic_interface:
                    try:
                        await mic_interface.stop()
                        await socket.close()
                    except:
                        try:
                            socket._ws.close()
                        except:
                            pass
                    print("Microphone and socket forcefully stopped in cleanup")
    except Exception as e:
        print(f"Connection error: {e}")
        raise

def get_conversation():
    try:
        print("\nStarting conversation processing...")
        # Keep reading the conversation file that is asyncronously written to by the chat client and wait for 'end the call' to be said by the user. then return the conversation
        with open("conversations.txt", "r") as f:
            conversations = f.read()
            print("Retrieved conversation text:", conversations[:100], "...")  # Print first 100 chars
            
            if not conversations.strip():
                print("Warning: Empty conversation text!")
                return
            
            print("Generating summary with Groq...")
            chat_summary = client.chat.completions.create(messages=[
                {
                    "role": "system",
                    "content": """You must respond with a valid JSON object containing exactly these fields. Provide criticality of the call, isSpam bool, user name, user location in the format only:
                        {
                          "summary": "The summary of the conversation",
                          "criticality": "The criticality of the call(eg. high, medium, low)",
                          "isSpam": "True or False",
                          "department": "Department name(Fire, Police, Medical)",
                          "user": "User name (Unknown if not provided)",
                          "location": "User location (Unknown if not provided)"
                        }
                        Do not include any other text or formatting.
                    """.strip()
                },
                {
                    "role": "user",
                    "content": conversations
                }
            ], model='llama3-8b-8192', stream=False)
            
            print("Received response from model:", chat_summary.choices[0].message.content)
            json_data = json.loads(chat_summary.choices[0].message.content)
            
            # Convert string "True"/"False" to boolean for isSpam
            is_spam = True if json_data["isSpam"].lower() == "true" else False
            
            # Get current timestamp
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print("Inserting into database...")
            conn = sqlite3.connect('conversation.db')
            c = conn.cursor()
            uid = str(uuid.uuid4())
            
            # Print values being inserted
            values = (uid, conversations, current_time, json_data["summary"],
                     json_data["criticality"], is_spam,
                     json_data["user"], json_data["location"])
            print("Inserting values into database:", values)
            
            try:
                c.execute("INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?, ?, ?)", values)
                conn.commit()
                print("Database commit successful")
                
                # Verify insertion
                c.execute("SELECT * FROM conversations WHERE uid = ?", (uid,))
                result = c.fetchone()
                print("Verified database insertion:", result is not None)
                if result:
                    print("Retrieved row:", result)
                
                conn.close()
                print("Database connection closed")
                
                # Create a file to signal that summary is complete
                with open("summary_complete.txt", "w") as f:
                    f.write(uid)
                print("Created summary_complete.txt with uid:", uid)
                
            except sqlite3.Error as e:
                print(f"Database error: {e}")
                raise
            except Exception as e:
                print(f"Error during database operations: {e}")
                raise
            
    except Exception as e:
        print("Error during conversation processing:", str(e))
        raise

if __name__ == "__main__":
    try:
        print("Starting main process...")
        asyncio.run(main())
        print("------------Conversation has ended------------")
    except Exception as e:
        print(f"Fatal error in main process: {e}")
    finally:
        print("Main process completed")