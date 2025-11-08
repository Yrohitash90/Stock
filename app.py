from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import csv
from io import StringIO
from flask import Response
import hashlib
from functools import wraps
from datetime import datetime
import threading
import webview
from flask import Flask, render_template
import time


app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- MySQL Connection ----------------
try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Somil@1234",
        database="canteen_inventory1",
        connection_timeout=20
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



@app.route('/canteen_dashboard_new')
@login_required
def canteen_dashboard_new():
    cursor = conn.cursor(dictionary=True)
    # Manager stock (canteen items)
    manager_stock = safe_query("SELECT * FROM stock WHERE use_type IN ('canteen','both')")

    # Canteen personal stock
    personal_stock = safe_query("SELECT * FROM canteen_stock")

    selected_date = request.args.get('selected_date')
    if not selected_date:
        selected_date = datetime.now().strftime("%Y-%m-%d")

    # Canteen usage history
    cursor.execute("""
        SELECT item_name, quantity_used, date_time 
        FROM canteen_use_history 
        WHERE DATE(date_time)=%s
        ORDER BY date_time DESC
    """, (selected_date,))
    usage = cursor.fetchall()

    conn.commit()
    cursor.close()
    # Render template
    return render_template(
        'canteen_dashboard_new.html',
        manager_stock=manager_stock,
        personal_stock=personal_stock,
        usage=usage,
        filters={'selected_date': selected_date}  # optional: date filter placeholder
    )


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

    # Pending Orders
    pending_orders = []
    for item in stock_items:
        if item['quantity'] <= item['min_quantity']:
            pending_orders.append({
                'item_name': item['item_name'],
                'current_qty': item['quantity'],
                'min_qty': item['min_quantity'],
                'max_qty': item['max_quantity'],
                'order_qty': item['max_quantity'] - item['quantity']
            })

    return render_template("manager_dashboard.html",
                           stock=stock_items,
                           usage=usage,
                           filters=filters,
                           pending_orders=pending_orders)


# ---------------- Pending Orders Page (UPDATED + HISTORY) ----------------
@app.route("/pending_orders", methods=["GET", "POST"])
@login_required
@role_required("manager")
def pending_orders_page():
    if request.method == "POST":
        item_name = request.form["item_name"]
        order_qty = int(request.form["order_qty"])
        try:
            # Update stock
            cursor.execute("UPDATE stock SET quantity = quantity + %s WHERE item_name = %s", (order_qty, item_name))
            # Log in order history
            cursor.execute(
                "INSERT INTO order_history (item_name, quantity_added, added_by) VALUES (%s, %s, %s)",
                (item_name, order_qty, session["username"])
            )
            safe_commit()
            flash(f"{item_name} stock updated by {order_qty} units!", "success")
        except Exception as e:
            flash(f"Failed to update stock: {e}", "danger")
        return redirect(url_for("pending_orders_page"))

    # Pending order logic
    stock_items = safe_query("SELECT * FROM stock")
    pending_orders = []
    for item in stock_items:
        if item["quantity"] <= item["min_quantity"]:
            pending_orders.append({
                "item_name": item["item_name"],
                "current_qty": item["quantity"],
                "min_qty": item["min_quantity"],
                "max_qty": item["max_quantity"],
                "order_qty": item["max_quantity"] - item["quantity"]
            })

    # Fetch order history
    order_history = safe_query("SELECT * FROM order_history ORDER BY date_time DESC LIMIT 100")

    return render_template("pending_orders.html",
                           pending_orders=pending_orders,
                           order_history=order_history)


# ---------------- Use Stock ----------------
@app.route("/use_stock", methods=["POST"])
@login_required
def use_stock():
    item_name = request.form['item_name']
    quantity = int(request.form['quantity'])
    source = request.form.get('source', '')  # 'mess', 'canteen', 'manager'
    personal_use = request.form.get('personal', '0')  # hidden field for manager HTML

    if quantity <= 0:
        flash("Quantity must be at least 1!", "warning")
        return redirect(request.referrer)

    try:
        # ------------------- CANTEEN PERSONAL STOCK -------------------
        if source == 'canteen':
            cursor.execute("SELECT quantity FROM canteen_stock WHERE item_name=%s", (item_name,))
            existing = cursor.fetchone()

            if not existing:
                flash(f"{item_name} not in personal stock! Cannot use.", "danger")
                return redirect(url_for('canteen_dashboard_new'))
            if existing['quantity'] < quantity:
                flash(f"Not enough personal stock for {item_name}!", "danger")
                return redirect(url_for('canteen_dashboard_new'))

            cursor.execute(
                "UPDATE canteen_stock SET quantity = quantity - %s, last_updated=NOW() WHERE item_name=%s",
                (quantity, item_name)
            )
            # Log in canteen usage history
            cursor.execute(
                "INSERT INTO canteen_use_history (item_name, quantity_used) VALUES (%s, %s)",
                (item_name, quantity)
            )
            safe_commit()
            flash(f"{quantity} units of {item_name} used from personal stock.", "success")
            return redirect(url_for('canteen_dashboard_new'))

        # ------------------- MANAGER STOCK -------------------
        elif source == 'manager':
            cursor.execute("SELECT quantity FROM stock WHERE item_name=%s", (item_name,))
            stock = cursor.fetchone()
            if not stock or stock['quantity'] < quantity:
                flash(f"Not enough manager stock for {item_name}!", "danger")
                return redirect(request.referrer)

            # Deduct from manager stock
            cursor.execute("UPDATE stock SET quantity = quantity - %s WHERE item_name=%s", (quantity, item_name))

            if personal_use == '1':
                # Add to canteen personal stock
                cursor.execute("SELECT quantity FROM canteen_stock WHERE item_name=%s", (item_name,))
                personal = cursor.fetchone()
                if personal:
                    cursor.execute(
                        "UPDATE canteen_stock SET quantity = quantity + %s, last_updated=NOW() WHERE item_name=%s",
                        (quantity, item_name)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO canteen_stock (item_name, quantity, last_updated) VALUES (%s, %s, NOW())",
                        (item_name, quantity)
                    )
                # Log in canteen_use_history
                cursor.execute(
                    "INSERT INTO use_history (user_role, item_name, quantity_used) VALUES (%s, %s, %s)",
                    ('canteen', item_name, quantity)
                )
                flash(f"{quantity} units of {item_name} moved to personal stock and logged in canteen usage.", "success")
            else:
                # Normal manager usage → log in use_history
                cursor.execute(
                    "INSERT INTO use_history (user_role, item_name, quantity_used) VALUES (%s, %s, %s)",
                    ('canteen', item_name, quantity)
                )
                flash(f"{quantity} units of {item_name} used from manager stock.", "success")

            safe_commit()
            return redirect(url_for('canteen_dashboard'))

        # ------------------- MESS STOCK -------------------
        elif source == 'mess':
            cursor.execute("SELECT quantity FROM stock WHERE item_name=%s", (item_name,))
            mess_stock = cursor.fetchone()

            if not mess_stock or mess_stock['quantity'] < quantity:
                flash(f"Not enough stock for {item_name}!", "danger")
                return redirect(url_for('mess_dashboard'))

            cursor.execute("UPDATE stock SET quantity = quantity - %s WHERE item_name=%s", (quantity, item_name))
            cursor.execute(
                "INSERT INTO use_history (user_role, item_name, quantity_used) VALUES (%s, %s, %s)",
                ('mess', item_name, quantity)
            )
            safe_commit()
            flash(f"{quantity} units of {item_name} used for mess.", "success")
            return redirect(url_for('mess_dashboard'))

        else:
            flash("Invalid source specified!", "danger")
            return redirect(request.referrer)

    except Exception as e:
        flash(f"Error using stock: {e}", "danger")
        return redirect(request.referrer)

# ---------------- Add Stock ----------------
@app.route("/add_stock", methods=["POST"])
@login_required
def add_stock():
    item_name = request.form['item_name']
    quantity = int(request.form['quantity'])
    if cursor:
        try:
            cursor.execute("UPDATE stock SET quantity=quantity+%s WHERE item_name=%s", (quantity, item_name))
            # Insert into history also
            cursor.execute(
                "INSERT INTO order_history (item_name, quantity_added, added_by) VALUES (%s, %s, %s)",
                (item_name, quantity, session["username"])
            )
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
    min_qty = int(request.form.get('min_quantity', 0))
    max_qty = int(request.form.get('max_quantity', 100))
    use_type = request.form.get('use_type', 'both')

    if cursor:
        try:
            cursor.execute(
                "INSERT INTO stock (item_name, min_quantity, max_quantity, quantity, use_type) VALUES (%s,%s,%s,0,%s)",
                (item_name, min_qty, max_qty, use_type)
            )
            safe_commit()
            flash(f"Item '{item_name}' added for {use_type} use", "success")
        except Exception as e:
            flash(f"Add item failed: {e}", "danger")
    else:
        flash("Database unavailable. Cannot add item.", "warning")

    # Always redirect to Manage Items page
    return redirect(url_for('add_item_page'))


# ---------------- Delete Item ----------------
@app.route("/delete_item", methods=["POST"])
@login_required
def delete_item():
    item_name = request.form["item_name"]
    try:
        cursor.execute("DELETE FROM stock WHERE item_name=%s", (item_name,))
        safe_commit()
        flash(f"Item '{item_name}' deleted successfully!", "success")
    except Exception as e:
        flash(f"Failed to delete item: {e}", "danger")

    # Always redirect to Manage Items page
    return redirect(url_for('add_item_page'))

# ---------------- Mess Dashboard ----------------
@app.route('/mess_dashboard', methods=['GET', 'POST'])
@login_required
@role_required("manager")
def mess_dashboard():
    cursor = conn.cursor(dictionary=True)

    # ✅ Mess & Both type items for stock display
    cursor.execute("SELECT * FROM stock WHERE use_type IN ('mess', 'both') AND quantity > 0")
    stock = cursor.fetchall()

    # ✅ Default selected date = today
    selected_date = request.args.get('selected_date')
    if not selected_date:
        selected_date = datetime.now().strftime("%Y-%m-%d")

    # ✅ Fetch today's (or selected day's) usage
    cursor.execute("""
        SELECT item_name, quantity_used, date_time 
        FROM use_history 
        WHERE user_role='mess' AND DATE(date_time)=%s
        ORDER BY date_time DESC
    """, (selected_date,))
    usage = cursor.fetchall()

    conn.commit()
    cursor.close()

    return render_template(
        'mess_dashboard.html',
        stock=stock,
        usage=usage,
        filters={'selected_date': selected_date}
    )



# ---------------- Canteen Dashboard ----------------
@app.route('/canteen_dashboard')
@login_required
@role_required("canteen")
def canteen_dashboard():
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')

    stock_items = safe_query("SELECT * FROM stock WHERE use_type IN ('canteen', 'both')")

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


# ---------------- Logout ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------- Add Item Page ----------------
@app.route("/add_item_page")
@login_required
def add_item_page():
    stock_items = safe_query("SELECT * FROM stock ORDER BY item_name")
    return render_template("add_item.html", stock=stock_items)


# ---------------- Usage History Page ----------------
@app.route("/usage_history_page", methods=["GET"])
@login_required
@role_required("manager")
def usage_history_page():
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

    usage_data = safe_query(query, tuple(params))
    filters = {'user_role': user_role, 'from_date': from_date, 'to_date': to_date}

    return render_template("usage_history.html", usage=usage_data, filters=filters)

@app.route("/export_usage_csv", methods=["GET"])
@login_required
@role_required("manager")
def export_usage_csv():
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

    usage_data = safe_query(query, tuple(params))

    # CSV likhne ke liye memory buffer
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Sr. No", "User Role", "Item Name", "Quantity Used", "Date & Time"])

    for i, row in enumerate(usage_data, start=1):
        writer.writerow([i, row['user_role'], row['item_name'], row['quantity_used'], row['date_time']])

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=usage_history.csv"}
    )


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

        cursor.execute("SELECT password FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if not user or hash_password(old_pwd) != user["password"]:
            flash("Old password is incorrect!", "danger")
            return redirect(url_for("change_password"))

        hashed_new = hash_password(new_pwd)
        cursor.execute("UPDATE users SET password=%s WHERE username=%s", (hashed_new, username))
        safe_commit()
        flash("Password changed successfully!", "success")
        return redirect(url_for(f"{session['role']}_dashboard"))

    return render_template("change_password.html")


if __name__=="__main__":
    app.run(debug=False,host='0.0.0.0')
