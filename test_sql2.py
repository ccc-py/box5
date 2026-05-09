import sql5
db = sql5.connect(path="box5.db")
c = db.execute("SELECT id, filename, folder FROM files")
for row in c.fetchall():
    print(row)
