#------------sr
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import hashlib
from functools import wraps

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- MySQL Connection ----------------
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="3809", #here your mysql password
    database="canteen_inventory1"
)
cursor = conn.cursor(dictionary=True)

# ---------------- Helper Functions ----------------
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ---------------- Routes ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username = request.form['username'].strip()
        password = request.form['password']
        role = request.form['role']

        cursor.execute("SELECT password, role FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if not user:
            flash("User not found","danger")
            return redirect(url_for('login'))
        if hash_password(password) != user['password']:
            flash("Incorrect password","danger")
            return redirect(url_for('login'))
        if role != user['role']:
            flash(f"Selected role does not match","danger")
            return redirect(url_for('login'))

        session['username'] = username
        session['role'] = role

        return redirect(url_for(f'{role}_dashboard'))

    return render_template("login.html")

# ---------------- Dashboards ----------------
@app.route("/manager_dashboard", methods=["GET","POST"])
@login_required
def manager_dashboard():
    # --- Stock Table (Always Visible) ---
    cursor.execute("SELECT * FROM stock")
    stock_items = cursor.fetchall()

    # --- Usage History Filter ---
    user_role = request.args.get('user_role', '')
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')

    query = "SELECT * FROM use_history WHERE 1=1"
    params = []

    if user_role:
        query += " AND user_role=%s"
        params.append(user_role)
    if from_date:
        query += " AND DATE(date_time) >= %s"
        params.append(from_date)
    if to_date:
        query += " AND DATE(date_time) <= %s"
        params.append(to_date)

    query += " ORDER BY date_time DESC"
    cursor.execute(query, tuple(params))
    usage = cursor.fetchall()

    filters = {'user_role': user_role, 'from_date': from_date, 'to_date': to_date}

    return render_template("manager_dashboard.html", stock=stock_items, usage=usage, filters=filters)

# ---------------- Use Stock ----------------
@app.route("/use_stock", methods=["POST"])
@login_required
def use_stock():
    role = session['role']   # get role from logged-in session
    item_name = request.form['item_name']
    quantity = int(request.form['quantity'])

    # Manager stock check
    cursor.execute("SELECT quantity FROM stock WHERE item_name=%s", (item_name,))
    manager_stock = cursor.fetchone()['quantity']

    if quantity > manager_stock:
        flash("Not enough stock in manager inventory", "danger")
        return redirect(url_for(f'{role}_dashboard'))

    # Reduce manager stock
    cursor.execute("UPDATE stock SET quantity=quantity-%s WHERE item_name=%s", (quantity, item_name))

    # Add usage entry
    cursor.execute("INSERT INTO use_history (user_role, item_name, quantity_used) VALUES (%s,%s,%s)",
                   (role, item_name, quantity))
    conn.commit()
    flash(f"{quantity} units of {item_name} used successfully", "success")
    return redirect(url_for(f'{role}_dashboard'))


# ---------------- Add Stock (Manager) ----------------
@app.route("/add_stock", methods=["POST"])
@login_required
def add_stock():
    item_name = request.form['item_name']
    quantity = int(request.form['quantity'])
    cursor.execute("UPDATE stock SET quantity=quantity+%s WHERE item_name=%s", (quantity, item_name))
    conn.commit()
    flash("Stock added successfully","success")
    return redirect(url_for('manager_dashboard'))

#------------add item-------
@app.route("/add_item", methods=["POST"])
@login_required
def add_item():
    item_name = request.form['item_name']
    min_qty = int(request.form.get('min_quantity',0))
    max_qty = int(request.form.get('max_quantity',100))
    cursor.execute("INSERT INTO stock (item_name, min_quantity, max_quantity, quantity) VALUES (%s,%s,%s,0)",
                   (item_name, min_qty, max_qty))
    conn.commit()
    flash(f"Item {item_name} added","success")
    return redirect(url_for('manager_dashboard'))

#--------------mess dashboard=------------
@app.route('/mess_dashboard')
@login_required
def mess_dashboard():
    # Get optional date filters
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')

    # ---------------- Manager Stock ----------------
    cursor.execute("SELECT * FROM stock")
    stock_items = cursor.fetchall()  # All stock visible

    # ---------------- Mess Usage History ----------------
    query = "SELECT * FROM use_history WHERE user_role='mess'"
    params = []

    if from_date:
        query += " AND DATE(date_time) >= %s"
        params.append(from_date)
    if to_date:
        query += " AND DATE(date_time) <= %s"
        params.append(to_date)

    query += " ORDER BY date_time DESC"
    cursor.execute(query, tuple(params))
    usage = cursor.fetchall()

    filters = {'from_date': from_date, 'to_date': to_date}

    return render_template('mess_dashboard.html', stock=stock_items, usage=usage, filters=filters)


#----------------canteen--------
@app.route('/canteen_dashboard')
@login_required
def canteen_dashboard():
    # Get optional date filters
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')

    # ---------------- Manager Stock ----------------
    cursor.execute("SELECT * FROM stock")
    stock_items = cursor.fetchall()  # All stock visible

    # ---------------- Canteen Usage History ----------------
    query = "SELECT * FROM use_history WHERE user_role='canteen'"
    params = []

    if from_date:
        query += " AND DATE(date_time) >= %s"
        params.append(from_date)
    if to_date:
        query += " AND DATE(date_time) <= %s"
        params.append(to_date)

    query += " ORDER BY date_time DESC"
    cursor.execute(query, tuple(params))
    usage = cursor.fetchall()

    filters = {'from_date': from_date, 'to_date': to_date}

    return render_template('canteen_dashboard.html', stock=stock_items, usage=usage, filters=filters)



# ---------------- Logout ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__=="__main__":
    app.run(debug=True,port=5000)
