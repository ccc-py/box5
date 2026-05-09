CREATE TABLE files (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, folder TEXT);
INSERT INTO files (filename, folder) VALUES ('ccc.md', 'public');
INSERT INTO files (filename, folder) VALUES ('ccc.md', 'public');
INSERT INTO files (filename, folder) VALUES ('ccc.md', 'public');
INSERT INTO files (filename, folder) VALUES ('hello.py', 'public');
INSERT INTO files (filename, folder) VALUES ('hello.py', 'public');
SELECT MAX(id) FROM files WHERE folder = 'public' GROUP BY filename;
SELECT id, filename FROM files WHERE id IN (SELECT MAX(id) FROM files WHERE folder = 'public' GROUP BY filename);
