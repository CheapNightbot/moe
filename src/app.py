from flask import Flask, render_template, request
from datetime import datetime

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", discord_url="https://google.com", year=datetime.today().year)


if __name__ == "__main__":
    app.run(debug=True)
