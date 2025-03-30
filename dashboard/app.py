from flask_socketio import SocketIO
from . import create_app

# Initialize SocketIO
socketio = SocketIO()

app = create_app()

# Link SocketIO to the Flask app
socketio.init_app(app)
