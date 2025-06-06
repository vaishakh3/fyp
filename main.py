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
            try:
                chat_summary = client.chat.completions.create(messages=[
                    {
                        "role": "system",
                        "content": """You must analyze the conversation carefully and respond with a valid JSON object containing exactly these fields:
                            {
                              "summary": "A brief summary of the conversation",
                              "criticality": "Criticality of the emergency call using these guidelines: HIGH (immediate life-threatening situations, major fires, violent crimes in progress), MEDIUM (non-life threatening injuries, property damage, ongoing but non-violent crimes), LOW (minor incidents, information requests, non-emergency situations)",
                              "isSpam": "True if the call appears to be a prank, contains no actual emergency, is deliberately misleading, or the caller is not serious. False for genuine emergency calls",
                              "department": "Department name (Fire, Police, Medical, or combination if multiple services needed)",
                              "user": "User name (Unknown if not provided)",
                              "location": "User location (Unknown if not provided)"
                            }
                            Carefully examine the conversation context to accurately determine criticality and spam status. Do not default to HIGH criticality unless truly warranted by the situation described. Do not include any other text or formatting.
                        """.strip()
                    },
                    {
                        "role": "user",
                        "content": conversations
                    }
                ], model='llama3-8b-8192', stream=False)
                
                print("Received response from model:", chat_summary.choices[0].message.content)
                response_content = chat_summary.choices[0].message.content.strip()
                
                # Special handling for malformed JSON responses
                if not (response_content.startswith('{') and response_content.endswith('}')):
                    print("Warning: Response is not valid JSON, attempting to fix...")
                    # Try to extract JSON from the response if it's embedded in other text
                    import re
                    json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                    if json_match:
                        response_content = json_match.group(0)
                        print("Extracted JSON:", response_content)
                    else:
                        # Create default JSON if extraction fails
                        print("Could not extract JSON, creating default response...")
                        response_content = """
                        {
                          "summary": "Unable to determine details from conversation",
                          "criticality": "LOW",
                          "isSpam": "True",
                          "department": "Unknown",
                          "user": "Unknown",
                          "location": "Unknown"
                        }
                        """
                        print("Created default JSON:", response_content)
                
                try:
                    json_data = json.loads(response_content)
                    print("Successfully parsed JSON data")
                except json.JSONDecodeError as je:
                    print(f"JSON parsing error: {je}")
                    # Create default json_data as fallback
                    json_data = {
                        "summary": "Unable to parse conversation details",
                        "criticality": "LOW",
                        "isSpam": "True",
                        "department": "Unknown",
                        "user": "Unknown",
                        "location": "Unknown"
                    }
                    print("Using default JSON data due to parsing error")
                
            except Exception as model_error:
                print(f"Error generating summary with model: {model_error}")
                # Create default json_data
                json_data = {
                    "summary": "Error processing conversation",
                    "criticality": "LOW",
                    "isSpam": "True",
                    "department": "Unknown",
                    "user": "Unknown",
                    "location": "Unknown"
                }
                print("Using default JSON data due to model error")
            
            # Convert string "True"/"False" to boolean for isSpam
            try:
                is_spam = True if json_data["isSpam"].lower() == "true" else False
            except (KeyError, AttributeError) as e:
                print(f"Error processing isSpam value: {e}")
                is_spam = True  # Default to True for safety
            
            try:
                # Ensure criticality is one of the expected values
                valid_criticalities = ["HIGH", "MEDIUM", "LOW"]
                if json_data.get("criticality", "").upper() not in valid_criticalities:
                    print(f"Invalid criticality value: {json_data.get('criticality')}")
                    json_data["criticality"] = "LOW"  # Default to low if invalid
                else:
                    # Normalize to uppercase
                    json_data["criticality"] = json_data["criticality"].upper()
            except Exception as e:
                print(f"Error processing criticality: {e}")
                json_data["criticality"] = "LOW"  # Default to low
            
            # Get current timestamp
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print("Inserting into database...")
            conn = sqlite3.connect('conversation.db')
            c = conn.cursor()
            uid = str(uuid.uuid4())
            
            # Fill in missing fields with defaults if necessary
            for field in ["summary", "department", "user", "location"]:
                if field not in json_data or not json_data[field]:
                    json_data[field] = "Unknown"
                    print(f"Using default value for missing field: {field}")
            
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
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        
        # Attempt to create a record even when an error occurs
        try:
            print("Attempting to create error record in database...")
            conn = sqlite3.connect('conversation.db')
            c = conn.cursor()
            uid = str(uuid.uuid4())
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get conversation text if possible
            try:
                with open("conversations.txt", "r") as f:
                    conversations = f.read()
            except:
                conversations = "Error retrieving conversation text"
            
            # Create error record
            error_values = (
                uid, 
                conversations,
                current_time,
                f"Error processing conversation: {str(e)}",
                "LOW",  # Default criticality
                True,   # Mark as spam for error cases
                "Unknown",
                "Unknown"
            )
            
            c.execute("INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?, ?, ?)", error_values)
            conn.commit()
            
            # Create summary completion signal
            with open("summary_complete.txt", "w") as f:
                f.write(uid)
            
            conn.close()
            print("Created error record in database with uid:", uid)
        except Exception as recovery_error:
            print(f"Failed to create error record: {recovery_error}")
        
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