# CashWave - Wallet Management System

CashWave is a secure and user-friendly wallet management application built using Flask and MongoDB. Users can sign up, log in, send money, add funds, and request money from other users. The platform also keeps track of all transactions and money requests.

## 📽️ Video Demo
[Watch the Video Demo](https://www.loom.com/share/2017772e60d54bd88d3b94276d5937f7)

## 🌐 Hosted Links
- **SDNS Link:** [CashWave on AWS](http://ec2-43-204-215-114.ap-south-1.compute.amazonaws.com:8000)
- **DDNS Link:** [CashWave on Render](https://cashwave.onrender.com)

---

## 🚀 Features
- User Registration and Login (Password Hashing with Bcrypt)
- Secure Session Management
- Add Money to Wallet
- Send Money to Other Users
- Request Money from Users
- Track Transaction History
- Manage Money Requests (Approve/Reject)

---

## 🛠️ Tech Stack
- **Backend:** Flask (Python)
- **Database:** MongoDB (Hosted on MongoDB Atlas)
- **Frontend:** HTML, CSS (via Jinja Templates)
- **Authentication:** bcrypt

---

## 🛎️ Installation

1. **Clone the Repository:**
```bash
git clone https://github.com/Soujash-123/CashWave.git
```

2. **Navigate to the Directory:**
```bash
cd cashwave
```

3. **Create a Virtual Environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

4. **Install Dependencies:**
```bash
pip install Flask pymongo bcrypt
```

5. **Run the Application:**
```bash
python app.py
```

6. **Access in Browser:**
```bash
http://localhost:5000
```

---

## 🗃️ Environment Variables
Ensure you have the following environment variables configured for MongoDB and secret key management:
```bash
export MONGO_URI="your_mongo_connection_string"
export SECRET_KEY="your_secret_key"
```

---

## 🧑‍💻 API Endpoints

| Method | Endpoint              | Description                    |
|---------|-----------------------|--------------------------------|
| GET     | `/`                   | Home Page                     |
| GET/POST| `/signup`             | User Registration              |
| GET/POST| `/login`              | User Login                     |
| GET     | `/dashboard`          | User Dashboard                 |
| POST    | `/add_money`          | Add Money to Wallet            |
| POST    | `/send_money`         | Send Money to Other Users      |
| POST    | `/request_money`      | Request Money from Users       |
| POST    | `/money-request/<request_id>/<action>` | Approve or Reject Money Request |
| GET     | `/search_users`       | Search for Other Users         |
| GET     | `/logout`             | User Logout                    |

---

## ⚡ Contact
For any issues or support, reach out to:
- **Email:** support@cashwave.com
- **GitHub:** [Your GitHub Link](https://github.com/yourusername/cashwave)

Enjoy using CashWave! 💸

