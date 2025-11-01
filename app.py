from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import hashlib
from functools import wraps

app = Flask(__name__)
app.secret_key = "supersecretkey"
# ---------------- MySQL Connection ----------------
try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="canteen_inventory1",
        connection_timeout=5
    )
    cursor = conn.cursor(dictionary=True)
    print("Database connected successfully!")
except Exception as e:
    print("Warning: Database connection failed!", e)
    conn = None
    cursor = None

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

def safe_query(query, params=()):
    """Execute query safely; return empty list if DB not available or fail"""
    if cursor:
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except Exception as e:
            flash(f"Database query failed: {e}", "warning")
            return []
    else:
        flash("Database unavailable", "warning")
        return []

def safe_commit():
    """Commit safely"""
    if conn:
        try:
            conn.commit()
        except Exception as e:
            flash(f"Database commit failed: {e}", "danger")
    else:
        flash("Database unavailable. Changes not saved.", "warning")

        # ---------------- Role-based access decorator ----------------
def role_required(allowed_role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("role") != allowed_role:
                flash("Unauthorized access!", "danger")
                return redirect(url_for(f"{session.get('role')}_dashboard"))
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ---------------- Routes ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username = request.form['username'].strip()
        password = request.form['password']
        role = request.form['role']

        user = None
        if cursor:
            try:
                cursor.execute("SELECT password, role FROM users WHERE username=%s", (username,))
                user = cursor.fetchone()
            except Exception as e:
                flash(f"Database error: {e}", "danger")

        if not user:
            flash("User not found or DB unavailable", "danger")
            return redirect(url_for('login'))
        if hash_password(password) != user['password']:
            flash("Incorrect password","danger")
            return redirect(url_for('login'))
        if role != user['role']:
            flash("Selected role does not match","danger")
            return redirect(url_for('login'))

        session['username'] = username
        session['role'] = role

        return redirect(url_for(f'{role}_dashboard'))

    return render_template("login.html")

# ---------------- Manager Dashboard ----------------
@app.route("/manager_dashboard", methods=["GET","POST"])
@login_required
@role_required("manager")
def manager_dashboard():
    stock_items = safe_query("SELECT * FROM stock")

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

    usage = safe_query(query, tuple(params))
    filters = {'user_role': user_role, 'from_date': from_date, 'to_date': to_date}

    return render_template("manager_dashboard.html", stock=stock_items, usage=usage, filters=filters)

# ---------------- Use Stock ----------------
@app.route("/use_stock", methods=["POST"])
@login_required
def use_stock():
    role = session['role']
    item_name = request.form['item_name']
    quantity = int(request.form['quantity'])

    manager_stock = safe_query("SELECT quantity FROM stock WHERE item_name=%s", (item_name,))
    if manager_stock:
        manager_stock = manager_stock[0]['quantity']
        if quantity > manager_stock:
            flash("Not enough stock in manager inventory", "danger")
        else:
            if cursor:
                try:
                    cursor.execute("UPDATE stock SET quantity=quantity-%s WHERE item_name=%s", (quantity, item_name))
                    cursor.execute("INSERT INTO use_history (user_role, item_name, quantity_used) VALUES (%s,%s,%s)",
                                   (role, item_name, quantity))
                    safe_commit()
                    flash(f"{quantity} units of {item_name} used successfully", "success")
                except Exception as e:
                    flash(f"Use stock failed: {e}", "danger")
            else:
                flash("Database unavailable. Cannot use stock.", "warning")
    else:
        flash("Item not found or DB unavailable", "warning")

    return redirect(url_for(f'{role}_dashboard'))

# ---------------- Add Stock ----------------
@app.route("/add_stock", methods=["POST"])
@login_required
def add_stock():
    item_name = request.form['item_name']
    quantity = int(request.form['quantity'])
    if cursor:
        try:
            cursor.execute("UPDATE stock SET quantity=quantity+%s WHERE item_name=%s", (quantity, item_name))
            safe_commit()
            flash("Stock added successfully","success")
        except Exception as e:
            flash(f"Add stock failed: {e}", "danger")
    else:
        flash("Database unavailable. Cannot add stock.", "warning")
    return redirect(url_for('manager_dashboard'))

# ---------------- Add Item ----------------
@app.route("/add_item", methods=["POST"])
@login_required
def add_item():
    item_name = request.form['item_name']
    min_qty = int(request.form.get('min_quantity',0))
    max_qty = int(request.form.get('max_quantity',100))
    if cursor:
        try:
            cursor.execute("INSERT INTO stock (item_name, min_quantity, max_quantity, quantity) VALUES (%s,%s,%s,0)",
                           (item_name, min_qty, max_qty))
            safe_commit()
            flash(f"Item {item_name} added","success")
        except Exception as e:
            flash(f"Add item failed: {e}", "danger")
    else:
        flash("Database unavailable. Cannot add item.", "warning")
    return redirect(url_for('manager_dashboard'))

# ---------------- Mess Dashboard ----------------
@app.route('/mess_dashboard')
@login_required
@role_required("mess")
def mess_dashboard():
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')

    stock_items = safe_query("SELECT * FROM stock")
    query = "SELECT * FROM use_history WHERE user_role='mess'"
    params = []
    if from_date:
        query += " AND DATE(date_time) >= %s"
        params.append(from_date)
    if to_date:
        query += " AND DATE(date_time) <= %s"
        params.append(to_date)
    query += " ORDER BY date_time DESC"
    usage = safe_query(query, tuple(params))
    filters = {'from_date': from_date, 'to_date': to_date}

    return render_template('mess_dashboard.html', stock=stock_items, usage=usage, filters=filters)

# ---------------- Canteen Dashboard ----------------
@app.route('/canteen_dashboard')
@login_required
@role_required("canteen")
def canteen_dashboard():
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')

    stock_items = safe_query("SELECT * FROM stock")
    query = "SELECT * FROM use_history WHERE user_role='canteen'"
    params = []
    if from_date:
        query += " AND DATE(date_time) >= %s"
        params.append(from_date)
    if to_date:
        query += " AND DATE(date_time) <= %s"
        params.append(to_date)
    query += " ORDER BY date_time DESC"
    usage = safe_query(query, tuple(params))
    filters = {'from_date': from_date, 'to_date': to_date}

    return render_template('canteen_dashboard.html', stock=stock_items, usage=usage, filters=filters)

# ---------------- Hello / Test Route ----------------
@app.route("/hello")
def hello():
    return "Hello! Flask app is running even if DB is down."

# ---------------- Logout ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------- Change Password ----------------
@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old_pwd = request.form["old_password"]
        new_pwd = request.form["new_password"]
        confirm_pwd = request.form["confirm_password"]

        if new_pwd != confirm_pwd:
            flash("New password and confirm password do not match!", "danger")
            return redirect(url_for("change_password"))

        username = session["username"]

        # Old password check
        cursor.execute("SELECT password FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if not user or hash_password(old_pwd) != user["password"]:
            flash("Old password is incorrect!", "danger")
            return redirect(url_for("change_password"))

        # Update new password
        hashed_new = hash_password(new_pwd)
        cursor.execute("UPDATE users SET password=%s WHERE username=%s", (hashed_new, username))
        safe_commit()
        flash("Password changed successfully!", "success")
        return redirect(url_for(f"{session['role']}_dashboard"))

    return render_template("change_password.html")


if __name__=="__main__":
    app.run(debug=True, port=5000)