import sqlite3
from tabulate import tabulate

# Connect to the SQLite database
connection = sqlite3.connect('conversation.db')

# Create a cursor object
cursor = connection.cursor()

# Fetch column names
cursor.execute("PRAGMA table_info(conversations);")
columns = [column[1] for column in cursor.fetchall()]

# Fetch all rows
cursor.execute("SELECT * FROM conversations;")
rows = cursor.fetchall()

# Print column names and table contents using tabulate
print("\nFormatted Contents of 'conversations' Table:")
print(tabulate(rows, headers=columns, tablefmt="grid"))

# Close the connection
connection.close()
