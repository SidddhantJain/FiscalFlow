import sqlite3
import sys

con = sqlite3.connect('backend/fiscalflow.db')
cur = con.cursor()
rows = cur.execute("SELECT id, date, description, amount, type, category_id, tags FROM transactions WHERE description LIKE '%VIVEK%'").fetchall()
print('Rows matching VIVEK:', rows)
for r in rows:
    cat_id = r[5]
    if cat_id:
        cat = cur.execute('SELECT id, name, type FROM categories WHERE id = ?', (cat_id,)).fetchone()
        print(f"Transaction ID {r[0]} Category: {cat}")

print("\n--- Check how many credit/income vs debit/expense exist in DB vs statement ---")
print("Total INCOME in DB:", cur.execute("SELECT count(*) FROM transactions WHERE type='INCOME'").fetchone()[0])
print("Total EXPENSE in DB:", cur.execute("SELECT count(*) FROM transactions WHERE type='EXPENSE'").fetchone()[0])

con.close()
