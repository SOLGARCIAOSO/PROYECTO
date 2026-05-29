from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from auth import register, login
import os

BASE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE, '..', 'comprobante-backend')

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return send_from_directory(BASE, 'index.html')

@app.route('/script.js')
def script():
    return send_from_directory(BASE, 'script.js')

@app.route('/styles.css')
def styles():
    return send_from_directory(BASE, 'styles.css')

@app.route('/app')
def paylens_app():
    return send_from_directory(os.path.abspath(APP_DIR), 'index.html')

@app.route('/paylens.css')
def paylens_css():
    return send_from_directory(os.path.abspath(APP_DIR), 'paylens.css')

@app.route('/register', methods=['POST'])
def register_user():
    data = request.json
    result = register(data['username'], data['password'])
    if result:
        return jsonify({"mensaje": "Usuario registrado exitosamente"}), 201
    return jsonify({"mensaje": "El usuario ya existe"}), 400

@app.route('/login', methods=['POST'])
def login_user():
    data = request.json
    result = login(data['username'], data['password'])
    if result:
        return jsonify({"mensaje": f"Bienvenido, {data['username']}!"}), 200
    return jsonify({"mensaje": "Credenciales incorrectas"}), 401

if __name__ == '__main__':
    app.run(debug=True)