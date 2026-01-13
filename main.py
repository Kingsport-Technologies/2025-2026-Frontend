from flask import Flask, render_template, request


app = Flask(__name__)
connected = False
robot_ip = ""
@app.route('/')
def home():
    return render_template('index.html', connected=connected, ip=robot_ip)
@app.route('/pilot')
def pilot():
    return render_template('pilot.html', connected=connected, ip=robot_ip)

@app.route('/connect', methods=['POST'])
def connect():
    global robot_ip, connected
    robot_ip = request.form.get('robot-ip', '1.1.1.1')
    connected = True
    return render_template('index.html', connected=connected, ip=robot_ip)
@app.route('/disconnect')
def disconnect():
    global connected
    connected = False
    return render_template('index.html', connected=connected, ip=robot_ip)
@app.route('/copilot')
def copilot():
    return render_template('copilot.html', ip=robot_ip)
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)