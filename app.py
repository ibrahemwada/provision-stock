import streamlit as st
import sqlite3
from datetime import datetime
import streamlit.components.v1 as components

st.set_page_config(page_title="Add Stock", layout="wide")

# --- FIX 1: Keep barcode in session properly ---
if "barcode" not in st.session_state:
    st.session_state.barcode = ""
if "product_name" not in st.session_state:
    st.session_state.product_name = ""

def get_db():
    return sqlite3.connect("sme.db")

def init_db():
    with get_db() as con:
        con.execute("CREATE TABLE IF NOT EXISTS stock (id INTEGER PRIMARY KEY AUTOINCREMENT, product_name TEXT, business_category TEXT, brand TEXT, stock_unit TEXT, quantity REAL, buying_price REAL, selling_price REAL, pieces_per_unit INTEGER, piece_buy_price REAL, piece_sell_price REAL, low_stock_alert REAL, size_variant TEXT, barcode TEXT, date_added TEXT)")
        con.commit()

init_db()

st.markdown("## 🟡 Add Stock - Buying & Selling Price")

# --- FIX 2: Auto-fill if barcode exists ---
def check_barcode_exists(bc):
    if not bc:
        return None
    try:
        with get_db() as con:
            row = con.execute("SELECT product_name, business_category, brand, stock_unit, buying_price, selling_price, size_variant FROM stock WHERE barcode=?", (bc.strip(),)).fetchone()
            return row
    except:
        return None

# Use key + on_change so JS scanner will persist
def on_barcode_change():
    st.session_state.barcode = st.session_state.barcode_widget

product_name = st.text_input("Product Name *", placeholder="e.g. Vaseline 225ml", key="product_name")

# ONE barcode box only, with key
barcode = st.text_input("Barcode (optional)", placeholder="Scan or type", key="barcode_widget", value=st.session_state.barcode, on_change=on_barcode_change)

# Sync manual typing immediately
if barcode != st.session_state.barcode:
    st.session_state.barcode = barcode

# If barcode typed/scanned, auto-fill name if already in sme.db
if st.session_state.barcode:
    existing = check_barcode_exists(st.session_state.barcode)
    if existing:
        prod, cat, br, unit, buy, sell, size = existing
        if not st.session_state.product_name:
            st.session_state.product_name = prod
        st.info(f"✅ Found in LOCAL sme.db: {prod} — auto-filling")
        # Optional: auto set product_name input via rerun
        if product_name != prod:
            product_name = prod

if st.checkbox("📷 Open Live Scanner"):
    components.html("""
    <div id="reader" style="width:100%"></div>
    <div id="result" style="color:green;font-weight:bold"></div>
    <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <script>
    function onScanSuccess(decodedText){
      document.getElementById('result').innerHTML="Scanned: "+decodedText;
      try{
        const doc=window.parent.document;
        const inputs=doc.querySelectorAll('input[type="text"]');
        for(let inp of inputs){
          // This now matches your keyed input
          if(inp.placeholder.includes("Scan or type") || inp.id.includes("barcode")){
            inp.focus();
            // For Streamlit we need to set React value
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            nativeInputValueSetter.call(inp, decodedText);
            inp.dispatchEvent(new Event('input', {bubbles:true}));
            inp.dispatchEvent(new Event('change', {bubbles:true}));
            break;
          }
        }
      }catch(e){console.log(e)}
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
    buying_price = st.number_input("Buying price per unit ₦ *", min_value=0.0, value=0.0, step=100.0)
with col2:
    quantity = st.number_input("Quantity *", min_value=0.0, value=10.0, step=1.0)
    selling_price = st.number_input("Selling price per unit ₦ *", min_value=0.0, value=0.0, step=100.0)
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
        piece_sell_price = st.number_input("Mudu Selling Price ₦", min_value=0.0, value=0.0, step=10.0)
    with c3:
        if buying_price>0:
            piece_buy_price = buying_price / pieces_per_unit
            st.metric("Mudu Cost", f"₦{piece_buy_price:.2f}")

if st.button("💾 Save to Stock", use_container_width=True):
    final_name = st.session_state.product_name or product_name
    final_barcode = st.session_state.barcode or barcode
    if not final_name or buying_price==0 or selling_price==0:
        st.error("Fill Product Name, Buying and Selling Price!")
    elif selling_price <= buying_price:
        st.error(f"Selling ₦{selling_price} must be > Buying ₦{buying_price}")
    else:
        with get_db() as con:
            con.execute("INSERT INTO stock (product_name, business_category, brand, stock_unit, quantity, buying_price, selling_price, pieces_per_unit, piece_buy_price, piece_sell_price, low_stock_alert, size_variant, barcode, date_added) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (final_name, business_category, brand, stock_unit, quantity, buying_price, selling_price, pieces_per_unit, piece_buy_price, piece_sell_price, low_stock, size_variant, final_barcode, datetime.now().strftime("%Y-%m-%d %H:%M")))
            con.commit()
        # --- For BOTH sme.db + Google Sheet (when you add GSHEET_URL later) ---
        # try: save_to_gsheet(final_barcode, final_name) 
        # except: pass
        st.success(f"Saved {final_name} [{final_barcode}]")
        st.balloons()
        # Clear only product, keep barcode? You choose - now we clear both
        st.session_state.barcode = ""
        st.session_state.product_name = ""
        st.session_state["barcode"] = ""
        st.rerun()

st.divider()
st.subheader("Stock List")
with get_db() as con:
    rows = con.execute("SELECT id, product_name, stock_unit, quantity, buying_price, selling_price, barcode FROM stock ORDER BY id DESC LIMIT 20").fetchall()
    for r in rows:
        sid, prod, unit, qty, buy, sell, bc = r
        c1, c2 = st.columns([4,1])
        with c1:
            st.write(f"**{prod}** | {qty} {unit} | Buy ₦{buy} Sell ₦{sell} | BC: {bc}")
        with c2:
            if st.button("🗑️ Delete", key=f"del_{sid}"):
                with get_db() as con2:
                    con2.execute("DELETE FROM stock WHERE id=?", (sid,))
                    con2.commit()
                st.rerun()
