from typing import List

from flask import Flask, render_template
from lib.google_sheets import read_google_sheet_rows, PhoneboothSheetRow

app = Flask(__name__)


def get_rows_by_location(location: str) -> List[PhoneboothSheetRow]:
    cleaned_location = location.lower().strip()

    rows = read_google_sheet_rows()
    return [row for row in rows if row.location.lower().strip() == cleaned_location]


@app.route("/")
def home():
    rows = get_rows_by_location('somerville')
    return render_template("index.html", rows=rows)


@app.route("/<location>/")
def load_location(location: str):
    rows = get_rows_by_location(location)
    return render_template("index.html", rows=rows)

