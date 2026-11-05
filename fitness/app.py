from flask import Flask, render_template, request, redirect, url_for
from db import get_db
from datetime import date, timedelta

app = Flask(__name__)

@app.route('/')
def index():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) AS cnt FROM memberships WHERE CURDATE() BETWEEN start_date AND end_date")
    active = cur.fetchone()['cnt']
    cur.execute("""SELECT COALESCE(SUM(mt.price),0) AS income 
                   FROM memberships m JOIN membership_types mt ON m.type_id = mt.id""")
    income = cur.fetchone()['income']
    db.close()
    return render_template('index.html', active=active, income=income)

@app.route('/clients', methods=['GET', 'POST'])
def clients():
    db = get_db()
    cur = db.cursor(dictionary=True)
    if request.method == 'POST':
        cur.execute("INSERT INTO clients (full_name, phone, email) VALUES (%s, %s, %s)",
                    (request.form['full_name'], request.form['phone'], request.form['email']))
        db.commit()
        return redirect(url_for('clients'))
    search = request.args.get('search', '')
    if search:
        cur.execute("SELECT * FROM clients WHERE full_name LIKE %s OR phone LIKE %s",
                    (f"%{search}%", f"%{search}%"))
    else:
        cur.execute("SELECT * FROM clients ORDER BY id DESC")
    rows = cur.fetchall()
    db.close()
    return render_template('clients.html', clients=rows, search=search)

@app.route('/memberships', methods=['GET', 'POST'])
def memberships():
    db = get_db()
    cur = db.cursor(dictionary=True)
    if request.method == 'POST':
        cur.execute("SELECT duration_days FROM membership_types WHERE id=%s", (request.form['type_id'],))
        days = cur.fetchone()['duration_days']
        start = date.fromisoformat(request.form['start_date'])
        end = start + timedelta(days=days)
        cur.execute("""INSERT INTO memberships (client_id, type_id, start_date, end_date)
                       VALUES (%s, %s, %s, %s)""",
                    (request.form['client_id'], request.form['type_id'], start, end))
        db.commit()
        return redirect(url_for('memberships'))
    cur.execute("SELECT id, full_name FROM clients")
    clients_list = cur.fetchall()
    cur.execute("SELECT * FROM membership_types")
    types = cur.fetchall()
    cur.execute("""SELECT m.*, c.full_name, mt.name,
                   IF(CURDATE() BETWEEN m.start_date AND m.end_date, 'Активен', 'Неактивен') AS status
                   FROM memberships m
                   JOIN clients c ON m.client_id = c.id
                   JOIN membership_types mt ON m.type_id = mt.id
                   ORDER BY m.id DESC""")
    rows = cur.fetchall()
    db.close()
    return render_template('memberships.html', clients=clients_list, types=types, memberships=rows)

@app.route('/visits', methods=['GET', 'POST'])
def visits():
    db = get_db()
    cur = db.cursor(dictionary=True)
    msg = None
    if request.method == 'POST':
        client_id = request.form['client_id']
        cur.execute("SELECT id FROM memberships WHERE client_id=%s AND CURDATE() BETWEEN start_date AND end_date", (client_id,))
        if cur.fetchone():
            cur.execute("INSERT INTO visits (client_id) VALUES (%s)", (client_id,))
            db.commit()
            msg = "Посещение добавлено"
        else:
            msg = "Нет активного абонемента!"
    cur.execute("SELECT id, full_name FROM clients")
    clients_list = cur.fetchall()
    cur.execute("""SELECT v.id, c.full_name, v.visit_date FROM visits v
                   JOIN clients c ON v.client_id = c.id ORDER BY v.id DESC LIMIT 50""")
    rows = cur.fetchall()
    db.close()
    return render_template('visits.html', clients=clients_list, visits=rows, msg=msg)

if __name__ == '__main__':
    app.run(debug=True)