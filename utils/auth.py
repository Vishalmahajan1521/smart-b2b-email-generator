import streamlit as st
import json
import os
from datetime import datetime

def initialize_users_file():
    if not os.path.exists("users.json"):
        with open("users.json", "w") as f:
            json.dump({}, f)

def load_users():
    initialize_users_file()
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)

def signup(salesperson_name, salesperson_title, salesperson_company, email, mobile, website, linkedin, password):
    users = load_users()
    if email in users:
        return False, "Email already registered."
    users[email] = {
        "salesperson_name": salesperson_name,
        "salesperson_title": salesperson_title,
        "salesperson_company": salesperson_company,
        "salesperson_email": email,
        "salesperson_mobile": mobile,
        "salesperson_website": website,
        "salesperson_linkedin": linkedin,
        "password": password,  # In production, hash passwords
        "created_at": datetime.now().isoformat()
    }
    save_users(users)
    return True, "Signup successful! Please log in."

def login(email, password):
    users = load_users()
    if email in users and users[email]["password"] == password:
        st.session_state.user = {
            "email": email,
            "salesperson_name": users[email]["salesperson_name"],
            "salesperson_title": users[email]["salesperson_title"],
            "salesperson_company": users[email]["salesperson_company"],
            "salesperson_email": users[email]["salesperson_email"],
            "salesperson_mobile": users[email]["salesperson_mobile"],
            "salesperson_website": users[email]["salesperson_website"],
            "salesperson_linkedin": users[email]["salesperson_linkedin"]
        }
        return True, "Login successful!"
    return False, "Invalid email or password."

def update_user_details(email, salesperson_name, salesperson_title, salesperson_company, salesperson_email, salesperson_mobile, salesperson_website, salesperson_linkedin):
    users = load_users()
    if email in users:
        users[email].update({
            "salesperson_name": salesperson_name,
            "salesperson_title": salesperson_title,
            "salesperson_company": salesperson_company,
            "salesperson_email": salesperson_email,
            "salesperson_mobile": salesperson_mobile,
            "salesperson_website": salesperson_website,
            "salesperson_linkedin": salesperson_linkedin
        })
        save_users(users)
        st.session_state.user.update({
            "salesperson_name": salesperson_name,
            "salesperson_title": salesperson_title,
            "salesperson_company": salesperson_company,
            "salesperson_email": salesperson_email,
            "salesperson_mobile": salesperson_mobile,
            "salesperson_website": salesperson_website,
            "salesperson_linkedin": salesperson_linkedin
        })
        return True, "Details updated successfully!"
    return False, "User not found."

def logout():
    if "user" in st.session_state:
        del st.session_state.user
    st.session_state.pop("articles_dict kind of articles", None)
    st.session_state.pop("summaries_dict kind of summaries", None)
    st.session_state.pop("sales_context_dict kind of sales_context", None)
    st.session_state.pop("email_content", None)
    st.session_state.pop("email_data", None)