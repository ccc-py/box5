import sql5
import time
db = sql5.connect("box5.db", transport="websocket", host="127.0.0.1", port=8080)
db.execute("CREATE TABLE IF NOT EXISTS test_files (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, folder TEXT)")
db.execute("INSERT INTO test_files (filename, folder) VALUES ('ccc.md', 'public')")
db.execute("INSERT INTO test_files (filename, folder) VALUES ('ccc.md', 'public')")
db.execute("INSERT INTO test_files (filename, folder) VALUES ('hello.py', 'public')")
c = db.execute("SELECT id, filename FROM test_files WHERE id IN (SELECT MAX(id) FROM test_files WHERE folder = 'public' GROUP BY filename)")
print(c.fetchall())
