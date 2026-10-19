import streamlit as st
import streamlit as st

# --- PASSWORD PROTECTION ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "Imuazzam080":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Enter Password to Access Shop", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter Password to Access Shop", type="password", on_change=password_entered, key="password")
        st.error("😕 Wrong password")
        return False
    else:
        return True

if not check_password():
    st.stop()
# --- END PASSWORD ---
import sqlite3
from datetime import datetime
import streamlit.components.v1 as components

st.set_page_config(page_title="Add Stock - Provision", layout="wide")

if "barcode" not in st.session_state:
    st.session_state.barcode = ""

def get_db():
    return sqlite3.connect("sme.db", check_same_thread=False)

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
            low_stock_alert REAL,
            barcode TEXT,
            date_added TEXT
        )
        """)
        con.commit()
init_db()

st.title("Add Stock - My Provision Shop")
product_name = st.text_input("Product Name *", placeholder="e.g. Indomie (Carton)")

st.markdown("### Barcode (optional) - Scan or type")
barcode_input = st.text_input("Barcode", value=st.session_state.barcode, placeholder="0705652150209", label_visibility="collapsed")

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

barcode = barcode_input
col1, col2 = st.columns(2)
with col1:
    business_category = st.selectbox("Business category", ["Provisions / Groceries", "Textiles / Fabrics", "Other"])
    brand = st.text_input("Brand (optional)")
    stock_unit = st.selectbox("Stock unit", ["piece", "pack", "carton", "bag", "crate", "bottle", "sachet", "mudu"])
    buying_price = st.number_input("Buying price per unit ₦ *", min_value=0.0, value=0.0, step=100.0)
with col2:
    quantity = st.number_input("Quantity *", min_value=0.0, value=10.0, step=1.0)
    selling_price = st.number_input("Selling price per unit ₦ *", min_value=0.0, value=0.0, step=100.0)
    low_stock = st.number_input("Low-stock alert at", min_value=0.0, value=5.0, step=1.0)
    size_variant = st.text_input("Size / variant (optional)")

if st.button("💾 Save to Stock", use_container_width=True, type="primary"):
    if not product_name or buying_price == 0 or selling_price == 0:
        st.error("Fill Product Name, Buying and Selling!")
    else:
        with get_db() as con:
            con.execute("INSERT INTO stock (product_name, business_category, brand, stock_unit, quantity, buying_price, selling_price, low_stock_alert, barcode, date_added) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (product_name, business_category, brand, stock_unit, quantity, buying_price, selling_price, low_stock, barcode, datetime.now().strftime("%Y-%m-%d %H:%M")))
            con.commit()
        st.success(f"Saved {product_name}")
        st.balloons()

st.divider()
st.subheader("Current Stock")
with get_db() as con:
    rows = con.execute("SELECT product_name, quantity, selling_price, barcode FROM stock ORDER BY id DESC").fetchall()
    if rows:
        st.table(rows)
    else:
        st.write("No stock yet")
