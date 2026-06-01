import os, sqlite3, datetime
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

app = Flask(__name__)
app.secret_key = "secret123"  # for sessions

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "rks_pos.db")
BILLS_DIR = os.path.join(BASE_DIR, "bills")
os.makedirs(BILLS_DIR, exist_ok=True)

def db():
    return sqlite3.connect(DB_PATH)

@app.route("/")
def index():
    con = db()
    cur = con.execute("SELECT id,name,price FROM menu WHERE active=1")
    menu = cur.fetchall()
    con.close()
    bill = session.get("bill", {})
    total = sum(v["qty"]*v["price"] for v in bill.values())
    return render_template("index.html", menu=menu, bill=bill, total=total)

@app.route("/add/<int:menu_id>")
def add_item(menu_id):
    con = db()
    name,price = con.execute("SELECT name,price FROM menu WHERE id=?", (menu_id,)).fetchone()
    con.close()
    bill = session.get("bill", {})
    if name in bill:
        bill[name]["qty"] += 1
    else:
        bill[name] = {"price":price,"qty":1}
    session["bill"] = bill
    return redirect(url_for("index"))

@app.route("/generate")
def generate_bill():
    bill = session.get("bill", {})
    if not bill:
        return redirect(url_for("index"))
    total = sum(v["qty"]*v["price"] for v in bill.values())
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    pdf = os.path.join(BILLS_DIR, f"bill_{ts}.pdf")

    # Discount logic
    if 100 <= total <= 200:
        discount = "Next Purchase Discount: 5%"
    elif 201 <= total <= 300:
        discount = "Next Purchase Discount: 10%"
    elif 301 <= total <= 400:
        discount = "Next Purchase Discount: 15%"
    elif total >= 401:
        discount = "Next Purchase Discount: 20%"
    else:
        discount = "No Discount"

    # PDF generation
    c = canvas.Canvas(pdf, pagesize=(12*cm,12*cm))
    c.setFillColorRGB(0,0,0)
    c.rect(0,0,12*cm,12*cm,fill=1)
    c.setFillColorRGB(1,0.84,0)
    y = 11*cm
    c.setFont("Helvetica-Bold",14)
    c.drawCentredString(6*cm,y,"★ ROYAL KULHAD STUDIO ★")
    y -= 1.2*cm
    c.setFont("Helvetica",10)
    for name,data in bill.items():
        c.drawString(1*cm,y,f"{name} x{data['qty']}   ₹{data['qty']*data['price']}")
        y -= 0.6*cm
    y -= 0.4*cm
    c.setFont("Helvetica-Bold",12)
    c.drawString(1*cm,y,f"TOTAL: ₹{total}")
    y -= 0.8*cm
    c.setFont("Helvetica",10)
    c.drawString(1*cm,y,discount)
    y -= 1*cm
    c.setFont("Helvetica-Bold",12)
    c.drawCentredString(6*cm,y,"✨ THANK YOU - VISIT AGAIN ✨")
    c.save()

    # Save sales
    con = db()
    con.execute("INSERT INTO sales(datetime,items,total) VALUES (?,?,?)",
                (datetime.datetime.now().isoformat(), str(bill), total))
    con.commit()
    con.close()

    session["bill"] = {}
    return send_file(pdf, as_attachment=True)
def init_db():
    con = db()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS menu(
            id INTEGER PRIMARY KEY,
            name TEXT,
            price REAL,
            category TEXT,
            active INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales(
            id INTEGER PRIMARY KEY,
            datetime TEXT,
            items TEXT,
            total REAL
        )
    """)
    con.commit()

    # insert default menu if empty
    cur.execute("SELECT COUNT(*) FROM menu")
    if cur.fetchone()[0] == 0:
        items = [
            ("Royale Chai", 20, "Chai", 1),
            ("Velvet Dalgona", 49, "Drinks", 1),
            ("Royale Shake Burst", 49, "Drinks", 1),
            ("Paneer Kulhad Pizza", 99, "Pizza", 1),
            ("Chicken Kulhad Pizza", 109, "Pizza", 1),
            ("Choco Lava Bomb", 69, "Dessert", 1),
            ("Royale Kulhad Tukra", 59, "Dessert", 1)
        ]
        cur.executemany("INSERT INTO menu(name,price,category,active) VALUES (?,?,?,?)", items)
        con.commit()
    con.close()

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
