import sql5
db = sql5.connect(path="box5.db")
c = db.execute("SELECT id, filename FROM files WHERE id IN (SELECT MAX(id) FROM files WHERE user_id=1 AND folder='public' GROUP BY filename)")
print(c.fetchall())
