# 🏢 RBMI Inventory Management System

A Flask-based Inventory Management System for managing stock operations of Mess and Canteen departments at RBMI College.  
Includes secure login, role-based dashboards, stock tracking, usage history, pending orders, and password management.

---

## ⚙️ Features

✅ Role-based login (Manager / Mess / Canteen)  
✅ Add, view, and update stock items  
✅ Auto generation of pending orders  
✅ Stock usage logs with filters  
✅ Change password system  
✅ SQLite database (auto created)  
✅ Beautiful Bootstrap 5 interface  
✅ Flash messages for user feedback  

---

## 🧰 Tech Stack

| Component | Technology |
|------------|-------------|
| **Language** | Python 3.9+ |
| **Framework** | Flask |
| **Database** | MYSql |
| **Frontend** | HTML5, CSS3, Bootstrap 5 |
| **Icons** | Bootstrap Icons |
| **Template Engine** | Jinja2 |

---

## 🖥️ Local Setup (From Zero)

### 🔹 Step 1: Extract the Project

Unzip the folder `Stock-main.zip` anywhere on your system, e.g.:

C:\Users<YourName>\Documents\Stock-main

---

### 🔹 Step 2: Install Python

Make sure Python 3.9 or above is installed.  
Check:
```bash
python --version
🔹 Step 3: Open Terminal / CMD inside the Project
cd path\to\Stock-main

Example:
cd C:\Users\user_name\Documents\Stock-main


🔹 Step 4: Create Virtual Environment
python -m venv venv

Activate it:


Windows:
venv\Scripts\activate

🔹 Step 5: Install Dependencies
pip install -r requirements.txt



🔹 Step 6: Run the Application
python app.py

When running successfully, you’ll see:
 * Running on http://127.0.0.1:5000/

Now open that link in your browser.

🧑‍💻 Default Login Credentials
1.username manager
password 1234

2.username mess
pssword 1234

3. camteen
password 1234

📂 Project Structure
Stock-main/
│
├── app.py                    # Main Flask app
├── requirements.txt           # Python dependencies
│
├── static/                    # Static files (CSS, JS, images)
│   ├── css/
│   ├── js/
│   └── images/
│
├── templates/                 # HTML templates (Jinja2)
│   ├── login.html
│   ├── manager_dashboard.html
│   ├── mess_dashboard.html
│   ├── canteen_dashboard.html
│   ├── pending_orders.html
│   └── change_password.html
│
├── canteen_inventory1              # MySql database import it in workbench manually
│
└── README.md


🧩 Troubleshooting
❌ Flask not found
pip install flask

❌ MYSql error: no such table
❌ Port already in use
flask run --port=5050

❌ CSS/Bootstrap not loading
➡ Make sure static/ folder structure is intact.

🚀 Deployment (Optional)
You can deploy on Render, PythonAnywhere, or Heroku easily.
Basic WSGI entry point example (for deployment):
from app import app

if __name__ == "__main__":
    app.run()


🤝 Contributors


Rohtash Kumar , Somil Sahu , Priyanshi Singh , Ritik kumar , Devansh Arya — Developer


RBMI Bareilly — Project Supervisor



📜 License
This project is for educational and internal college use only.
© 2025 RBMI Inventory Management System

---