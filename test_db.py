import sql5
db = sql5.connect("box5.db")
for row in db.execute("SELECT * FROM files").fetchall():
    print(row)
