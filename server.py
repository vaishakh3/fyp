from fastapi import FastAPI
from sqlite3 import connect

app = FastAPI()

@app.get("/conversations")
def get_conversations():
    conn = connect("conversation.db")
    c = conn.cursor()
    c.execute("SELECT * FROM conversations")
    conversations = c.fetchall()
    conn.close()
    return {"conversations": conversations}

@app.post("/conversation")
def add_conversation(data: dict):
    conn = connect("conversation.db")
    c = conn.cursor()
    c.execute("INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
              (data['uid'], data['conversation'], data['timestamp'], 
               data['summary'], data['criticality'], data['isSpam'], 
               data['user'], data['location']))
    conn.commit()
    conn.close()
    return {"status": "success"}

