import streamlit as st
import sqlite3
from datetime import datetime
import streamlit.components.v1 as components

st.set_page_config(page_title="Add Stock", layout="wide")

def get_db():
    return sqlite3.connect("sme.db")

def init_db():
    with get_db() as con:
        con.execute("CREATE TABLE IF NOT EXISTS stock (id INTEGER PRIMARY KEY AUTOINCREMENT, product_name TEXT, business_category TEXT, brand TEXT, stock_unit TEXT, quantity REAL, buying_price REAL, selling_price REAL, pieces_per_unit INTEGER, piece_buy_price REAL, piece_sell_price REAL, low_stock_alert REAL, size_variant TEXT, barcode TEXT, date_added TEXT)")
        con.commit()

init_db()

st.markdown("## Add Stock - Buying and Selling Price")

# 1. Barcode FIRST
barcode = st.text_input("Barcode (optional)", placeholder="Scan or type", key="barcode_widget")

# 2. Check DB and FORCE auto-fill BEFORE product name box
if barcode.strip():
    with get_db() as con:
        row = con.execute("SELECT product_name FROM stock WHERE barcode=? LIMIT 1", (barcode.strip(),)).fetchone()
        if row:
            found_name = row[0]
            if st.session_state.get("product_name", "") != found_name:
                st.session_state["product_name"] = found_name
                st.rerun()

# 3. Product name AFTER
product_name = st.text_input("Product Name *", placeholder="e.g. Vaseline 225ml", key="product_name")

# Show message after box
if barcode.strip():
    with get_db() as con:
        row = con.execute("SELECT product_name FROM stock WHERE barcode=? LIMIT 1", (barcode.strip(),)).fetchone()
        if row:
            st.success(f"Found: {row[0]} - auto-filled")

if st.checkbox("Open Live Scanner"):
    components.html("""
    <div id="reader" style="width:100%"></div>
    <div id="result" style="color:green;font-weight:bold"></div>
    <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <script>
    function onScanSuccess(decodedText){
      document.getElementById('result').innerHTML="Scanned: "+decodedText;
      const doc=window.parent.document;
      const inputs=doc.querySelectorAll('input[type="text"]');
      for(let inp of inputs){
        if(inp.placeholder && inp.placeholder.includes("Scan or type")){
            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            nativeSetter.call(inp, decodedText);
            inp.dispatchEvent(new Event('input', {bubbles:true}));
            inp.dispatchEvent(new Event('change', {bubbles:true}));
            break;
        }
      }
    }
    let scanner=new Html5QrcodeScanner("reader",{fps:10,qrbox:{width:300,height:120}},false);
    scanner.render(onScanSuccess);
    </script>
    """, height=500)

col1, col2 = st.columns(2)
with col1:
    business_category = st.selectbox("Business category", ["Provisions / Groceries","Textiles / Fabrics","Cosmetics","Electronics","Other"])
    brand = st.text_input("Brand (optional)")
    stock_unit = st.selectbox("Stock unit", ["piece","pack","carton","bag","crate","bottle","sachet"])
    buying_price = st.number_input("Buying price per unit N *", min_value=0.0, value=0.0, step=100.0)
with col2:
    quantity = st.number_input("Quantity *", min_value=0.0, value=10.0, step=1.0)
    selling_price = st.number_input("Selling price per unit N *", min_value=0.0, value=0.0, step=100.0)
    low_stock = st.number_input("Low-stock alert at", min_value=0.0, value=5.0, step=1.0)
    size_variant = st.text_input("Size / variant (optional)", placeholder="e.g. 225ml, 50g")

pieces_per_unit = 1
piece_buy_price = buying_price
piece_sell_price = selling_price

if stock_unit == "bag":
    c1, c2, c3 = st.columns(3)
    with c1:
        pieces_per_unit = st.number_input("Mudu inside 1 bag", min_value=1, value=20, step=1)
    with c2:
        piece_sell_price = st.number_input("Mudu Selling Price N", min_value=0.0, value=0.0, step=10.0)
    with c3:
        if buying_price>0:
            piece_buy_price = buying_price / pieces_per_unit
            st.metric("Mudu Cost", f"N{piece_buy_price:.2f}")

if st.button("Save to Stock", use_container_width=True):
    if not product_name or buying_price==0 or selling_price==0:
        st.error("Fill Product Name, Buying and Selling Price!")
    elif selling_price <= buying_price:
        st.error(f"Selling N{selling_price} must be > Buying N{buying_price}")
    else:
        with get_db() as con:
            con.execute("INSERT INTO stock (product_name, business_category, brand, stock_unit, quantity, buying_price, selling_price, pieces_per_unit, piece_buy_price, piece_sell_price, low_stock_alert, size_variant, barcode, date_added) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (product_name, business_category, brand, stock_unit, quantity, buying_price, selling_price, pieces_per_unit, piece_buy_price, piece_sell_price, low_stock, size_variant, barcode, datetime.now().strftime("%Y-%m-%d %H:%M")))
            con.commit()
        st.success(f"Saved {product_name}")
        st.balloons()

st.divider()
st.subheader("Stock List")
with get_db() as con:
    rows = con.execute("SELECT id, product_name, stock_unit, quantity, buying_price, selling_price, barcode FROM stock ORDER BY id DESC LIMIT 20").fetchall()
    for r in rows:
        sid, prod, unit, qty, buy, sell, bc = r
        c1, c2 = st.columns([4,1])
        with c1:
            st.write(f"*{prod}* | {qty} {unit} | Buy N{buy} Sell N{sell} | BC: {bc}")
        with c2:
            if st.button("Delete", key=f"del_{sid}"):
                with get_db() as con2:
                    con2.execute("DELETE FROM stock WHERE id=?", (sid,))
                    con2.commit()
                st.rerun()
