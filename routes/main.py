
from flask import Blueprint, render_template
from db import get_db_connection

main = Blueprint("main", __name__)

@main.route("/")
def home():
    connection = get_db_connection()
    pcs = []

    if connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT pc_ID, model_name, price, specs, type
            FROM PC
            WHERE order_ID IS NULL
        """)

        pcs = cursor.fetchall()

        cursor.close()
        connection.close()

    return render_template("index.html", pcs=pcs)


@main.route("/test-db")
def test_db():
    connection = get_db_connection()

    if connection is None:
        return "<h1>Database connection failed!</h1>"

    try:
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        cursor.close()
        connection.close()

        return f"<h1>Database Connected!</h1><p>Tables found: {tables}</p>"

    except Exception as error:
        connection.close()
        return f"<h1>Database query failed!</h1><p>{error}</p>"
