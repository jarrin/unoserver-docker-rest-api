from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Set a simple auth key
AUTH_KEY = "supersecretkey"

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check for auth key in headers
    auth = request.headers.get('Authorization')
    if auth != AUTH_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    # Check if the 'file' part is present
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    # Check if a file was actually selected
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save the file (optional: you can save or process it directly)
    file.save(f"./uploads/{file.filename}")

    return jsonify({"message": "File uploaded successfully!"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
