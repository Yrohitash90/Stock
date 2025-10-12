check
# Canteen Inventory Management

## Overview
Flask-based inventory system with three roles:
- Manager: Add stock, add item, view usage history
- Mess: Use stock, view own usage history, date filter
- Canteen: Use stock, view own usage history, date filter

## Setup Instructions

1. Clone the repo:
```bash
git clone < stock >



#-------database-------
create database canteen_inventory1;
use canteen_inventory1;
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    password VARCHAR(255),
    role ENUM('manager', 'canteen', 'mess')
);

CREATE TABLE stock (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    item_name VARCHAR(100) UNIQUE,
    quantity INT,
    min_quantity INT,
    max_quantity INT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE use_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_role ENUM('canteen','mess'),
    item_name VARCHAR(100),
    quantity_used INT,
    date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Passwords hashed using SHA256
-- manager123, canteen123, mess123

INSERT INTO users (username, password, role) VALUES 
('manager', SHA2('manager123',256), 'manager'),
('canteen', SHA2('canteen123',256), 'canteen'),
('mess', SHA2('mess123',256), 'mess');




#3----------run this in terminal 

python -m venv venv
pip install -r requirements.txt


#4  run_app.bat file from my pc

click on link