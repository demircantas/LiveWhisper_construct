import pyautogui
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

def send_command(command, values):
    """Helper function to send Rhino commands via pyautogui"""
    pyautogui.write(command)
    pyautogui.press("enter")
    time.sleep(0.2)  # Small delay to ensure Rhino processes the command

    for value in values:
        pyautogui.write(value)
        pyautogui.press("enter")
        time.sleep(0.2)

@app.route("/execute", methods=["POST"])
def execute_command():
    data = request.get_json()
    command = data.get("command", "").lower()

    if command == "create_cube":
        send_command("_Box", ["0,0,0", "1,1,0", "1"])  # (Base, Corner, Height)

    elif command == "create_cylinder":
        send_command("_Cylinder", ["0,0,0", "1,0,0", "2"])  # (Base, Radius, Height)

    elif command == "create_sphere":
        send_command("_Sphere", ["0,0,0", "1"])  # (Center, Radius)

    elif command == "create_cone":
        send_command("_Cone", ["0,0,0", "1,0,0", "2"])  # (Base, Radius, Height)

    else:
        return jsonify({"error": "Unknown command"}), 400

    return jsonify({"status": "Command executed", "command": command})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
