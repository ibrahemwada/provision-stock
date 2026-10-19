import streamlit as st
import sqlite3
from datetime import datetime
from PIL import Image

st.set_page_config(page_title="Add Stock", layout="wide")
if "barcode" not in st.session_state:
    st.session_state.barcode = ""
st.markdown("""
<style>
div.stButton > button:first-child {
    background-color: #e53935;
    color: white;
    height: 50px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

def get_db():
    return sqlite3.connect("sme.db")

def init_db():
    with get_db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT,
            business_category TEXT,
            brand TEXT,
            stock_unit TEXT,
            quantity REAL,
            buying_price REAL,
            selling_price REAL,
            pieces_per_unit INTEGER,
            piece_buy_price REAL,
            piece_sell_price REAL,
            low_stock_alert REAL,
            size_variant TEXT,
            barcode TEXT,
            date_added TEXT
        )
        """)
        # If table already exists, add barcode column (for your old sme.db)
        try:
            con.execute("ALTER TABLE stock ADD COLUMN barcode TEXT")
        except:
            pass
        con.commit()

init_db()

init_db()

if "do_clear" not in st.session_state:
    st.session_state.do_clear = False

if st.session_state.do_clear:
    st.session_state.do_clear = False
    st.session_state.buy_price = 0.0
    st.session_state.sell_price = 0.0

st.markdown("## 🟡 Add Stock")
st.markdown("## 🟡 Add Stock - Buying & Selling Price")
st.write("")

# ----- FORM LIKE YOUR SCREENSHOT - NEW LIVE SCANNER -----
product_name = st.text_input("Product Name *", value=st.session_state.get("found_name", ""), placeholder="e.g. Indomie (Carton)")
size_variant = st.text_input("Size / variant (optional)", value=st.session_state.get("found_size", ""), placeholder="e.g. 20gm, 50g, 225ml")

st.markdown("### Barcode (optional) - Scan or type")
barcode_input = st.text_input("Barcode", value=st.session_state.barcode, placeholder="e.g. 0705652150209", label_visibility="collapsed", key="barcode_box")
# --- SMART AUTO-FILL from your own database ---
if barcode_input:
    with get_db() as con:
        row = con.execute("SELECT product_name, size_variant FROM stock WHERE barcode=? ORDER BY id DESC LIMIT 1", (barcode_input,)).fetchone()
        if row:
            found_name, found_size = row
            # auto-fill product name if empty
            if found_name:
                st.session_state["found_name"] = found_name
            if found_size:
                st.session_state["found_size"] = found_size

# Use found values for form defaults
default_name = st.session_state.get("found_name", "")
default_size = st.session_state.get("found_size", "")
import streamlit.components.v1 as components

if st.checkbox("📷 Open Live Scanner (better than photo)"):
    st.info("Point camera to barcode — it will auto-fill your form")
    components.html(
        """
        <div id="reader" style="width:100%"></div>
        <div id="result" style="font-size:18px; font-weight:bold; color:green; margin-top:10px;"></div>
        <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
        <script>
        function setInParent(placeholderText, value) {
            try {
                const parentDoc = window.parent.document;
                const inputs = parentDoc.querySelectorAll('input[type="text"]');
                for (let inp of inputs) {
                    if (inp.placeholder && inp.placeholder.includes(placeholderText)) {
                        inp.focus();
                        inp.value = value;
                        inp.dispatchEvent(new Event('input', {bubbles: true}));
                        inp.dispatchEvent(new Event('change', {bubbles: true}));
                        break;
                    }
                }
            } catch(e) {}
        }

        function onScanSuccess(decodedText, decodedResult) {
            document.getElementById('result').innerHTML = "✅ Scanned: " + decodedText + " - Auto-filled!";
            setInParent("0705652150209", decodedText);
            
            // Try to fetch product name from internet automatically
            fetch("https://world.openfoodfacts.org/api/v0/product/" + decodedText + ".json")
            .then(res => res.json())
            .then(data => {
                if(data.status == 1) {
                    let name = data.product.product_name || "";
                    let qty = data.product.quantity || "";
                    if(name) setInParent("e.g. Indomie", name);
                    if(qty) setInParent("Size / variant", qty);
                }
            });
        }
        let html5QrcodeScanner = new Html5QrcodeScanner(
            "reader", { fps: 10, qrbox: {width: 300, height: 120} }, false);
        html5QrcodeScanner.render(onScanSuccess);
        </script>
        """,
        height=500,
    )
    st.caption("✅ Now auto-fills — no more COPY!")

    st.caption("COPY the green number and paste in box above")

barcode = barcode_input if barcode_input else st.session_state.barcode
# ----- END NEW SCANNER -----

barcode = st.session_state.barcode if st.session_state.barcode else barcode_input

col_left, col_right = st.columns(2)

with col_left:
    business_category = st.selectbox("Business category", ["Provisions / Groceries", "Textiles / Fabrics", "Cosmetics", "Electronics", "Other"], index=0)
    brand = st.text_input("Brand (optional)")
    stock_unit = st.selectbox("Stock unit", ["piece", "pack", "carton", "bag", "crate", "bottle", "sachet"])
    buying_price = st.number_input("Buying price per unit ₦ *", min_value=0.0, value=0.0, step=100.0, key="buy_price")

with col_right:
    quantity = st.number_input("Quantity *", min_value=0.0, value=10.0, step=1.0)
    selling_price = st.number_input("Selling price per unit ₦ *", min_value=0.0, value=0.0, step=100.0, key="sell_price")
    low_stock = st.number_input("Low-stock alert at", min_value=0.0, value=5.0, step=1.0)
    size_variant = st.text_input("Size / variant (optional)")

# ----- BAG = MUDU, PACK/CARTON/CRATE = PIECES -----
pieces_per_unit = 1
piece_buy_price = buying_price
piece_sell_price = selling_price

if stock_unit == "bag":
    st.divider()
    st.markdown(f"### 🛍️ Bag Contains Mudu - Set Mudu Price")
    c1, c2, c3 = st.columns(3)
    with c1:
        pieces_per_unit = st.number_input(f"Mudu inside 1 bag", min_value=1, value=20, step=1)
    with c2:
        piece_sell_price = st.number_input(f"Mudu Selling Price ₦", min_value=0.0, value=0.0, step=10.0)
    with c3:
        if buying_price > 0:
            piece_buy_price = buying_price / pieces_per_unit
            st.metric("Mudu Cost Price", f"₦{piece_buy_price:.2f}")
    
    if buying_price > 0 and piece_sell_price > 0:
        profit_per_mudu = piece_sell_price - piece_buy_price
        profit_per_bag = selling_price - buying_price
        st.success(f"💡 Auto: Buy 1 mudu = ₦{piece_buy_price:.2f} | Sell 1 mudu = ₦{piece_sell_price} | **Profit per mudu = ₦{profit_per_mudu:.2f}** | Profit per bag = ₦{profit_per_bag:.2f}")

elif stock_unit in ["pack", "carton", "crate"]:
    st.divider()
    st.markdown(f"### 📦 {stock_unit.capitalize()} Contains Pieces - Set Piece Price")
    c1, c2, c3 = st.columns(3)
    with c1:
        pieces_per_unit = st.number_input(f"Pieces inside 1 {stock_unit}", min_value=1, value=12, step=1)
    with c2:
        piece_sell_price = st.number_input(f"Piece Selling Price ₦", min_value=0.0, value=0.0, step=10.0)
    with c3:
        if buying_price > 0:
            piece_buy_price = buying_price / pieces_per_unit
            st.metric("Piece Cost Price", f"₦{piece_buy_price:.2f}")
    
    if buying_price > 0 and piece_sell_price > 0:
        profit_per_piece = piece_sell_price - piece_buy_price
        profit_per_carton = selling_price - buying_price
        st.success(f"💡 Auto: Buy 1 piece = ₦{piece_buy_price:.2f} | Sell 1 piece = ₦{piece_sell_price} | **Profit per piece = ₦{profit_per_piece:.2f}** | Profit per {stock_unit} = ₦{profit_per_carton:.2f}")

# ----- SAVE BUTTON -----
st.write("")
btn1, btn2 = st.columns([2,1])
with btn1:
    save_clicked = st.button("💾 Save to Stock", use_container_width=True)
with btn2:
    st.button("Close", use_container_width=True)

if save_clicked:
    # --- ADD THIS NEW BLOCK ---
    if selling_price <= buying_price:
        st.error(f"❌ Can't save! Selling ₦{selling_price} must be higher than buying ₦{buying_price}")
        st.stop()
    # --------------------------

    if not product_name or buying_price == 0 or selling_price == 0:
        st.error("Please fill Product Name, Buying and Selling Price!")
    else:
        with get_db() as con:
            con.execute("""
    INSERT INTO stock (product_name, business_category, brand, stock_unit, quantity, buying_price, selling_price, pieces_per_unit, piece_buy_price, piece_sell_price, low_stock_alert, size_variant, barcode, date_added)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
""", (product_name, business_category, brand, stock_unit, quantity, buying_price, selling_price, pieces_per_unit, piece_buy_price, piece_sell_price, low_stock, size_variant, barcode, datetime.now().strftime("%Y-%m-%d %H:%M")))
            con.commit()
        st.success(f"✅ Saved! {product_name} - {quantity} {stock_unit} | Piece buy ₦{piece_buy_price:.2f} piece sell ₦{piece_sell_price}")
        st.balloons()
        import time
        time.sleep(2.0)
        st.session_state.do_clear = True
        st.rerun()

st.divider()
st.subheader("Stock List")
with get_db() as con:
    rows = con.execute("SELECT id, product_name, stock_unit, quantity, buying_price, selling_price, pieces_per_unit, piece_buy_price, piece_sell_price FROM stock ORDER BY id DESC LIMIT 20").fetchall()
    for r in rows:
        stock_id = r[0]
        product = r[1]
        unit = r[2]
        qty = r[3]
        buy = r[4]
        sell = r[5]
        
        c1, c2 = st.columns([4, 1])
        with c1:
            st.write(f"**{product}** | {qty} {unit} | Buy ₦{buy} Sell ₦{sell}")
        with c2:
            if st.button("🗑️ Delete", key=f"del_{stock_id}"):
                with get_db() as con2:
                    con2.execute("DELETE FROM stock WHERE id=?", (stock_id,))
                    con2.commit()
                st.rerun()
       
