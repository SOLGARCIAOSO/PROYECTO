import json
import hashlib
import os

USERS_FILE = "users.json"

def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${hashed}"

def verify_password(password: str, stored: str) -> bool:
    salt, hashed = stored.split("$")
    return hashlib.sha256((password + salt).encode()).hexdigest() == hashed

def load_users() -> dict:
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(data: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def register(username: str, password: str) -> bool:
    data = load_users()
    if any(u["username"] == username for u in data["usuarios"]):
        print(" El usuario ya existe.")
        return False
    data["usuarios"].append({
        "username": username,
        "password": hash_password(password)
    })
    save_users(data)
    print(" Usuario registrado exitosamente.")
    return True

def login(username: str, password: str) -> bool:
    data = load_users()
    for user in data["usuarios"]:
        if user["username"] == username:
            if verify_password(password, user["password"]):
                print(f" Bienvenido, {username}!")
                return True
            else:
                print(" Contraseña incorrecta.")
                return False
    print(" Usuario no encontrado.")
    return False