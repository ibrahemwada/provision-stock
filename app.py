import streamlit as st
import sqlite3
import json
import urllib.request
import streamlit.components.v1 as components
from datetime import datetime

st.set_page_config(page_title="Add Stock", layout="wide")

# --- DATABASE SETUP ---
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
        con.commit()

init_db()

CATEGORIES = ["Provisions / Groceries", "Textiles / Fabrics", "Cosmetics", "Electronics", "Other"]
UNITS = ["piece", "pack", "carton", "bag", "crate", "bottle", "sachet"]

# --- INITIALIZE SESSION STATE DEFAULTS ---
defaults = {
    "barcode_input": "",
    "product_name": "",
    "business_category": CATEGORIES[0],
    "brand": "",
    "stock_unit": UNITS[0],
    "buying_price": 0.0,
    "selling_price": 0.0,
    "quantity": 10.0,
    "low_stock": 5.0,
    "size_variant": "",
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# --- AUTOFILL LOGIC ---
def autofill_product(code):
    code = (code or "").strip()
    if not code:
        return

    # 1. Search existing local database
    with get_db() as con:
        cur = con.cursor()
        cur.execute("""
            SELECT product_name, business_category, brand, stock_unit, 
                   buying_price, selling_price, low_stock_alert, size_variant 
            FROM stock WHERE barcode = ? ORDER BY id DESC LIMIT 1
        """, (code,))
        row = cur.fetchone()

        if row:
            st.session_state.product_name = row[0] or ""
            if row[1] in CATEGORIES:
                st.session_state.business_category = row[1]
            st.session_state.brand = row[2] or ""
            if row[3] in UNITS:
                st.session_state.stock_unit = row[3]
            st.session_state.buying_price = float(row[4] or 0.0)
            st.session_state.selling_price = float(row[5] or 0.0)
            st.session_state.low_stock = float(row[6] or 5.0)
            st.session_state.size_variant = row[7] or ""
            st.toast(f"📦 Found in stock history: {row[0]}")
            return

    # 2. Search Open Food Facts online (for packaged consumer products)
    try:
        url = f"https://world.openfoodfacts.org/api/v0/product/{code}.json"
        req = urllib.request.Request(url, headers={"User-Agent": "StreamlitStockApp/1.0"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode())
            if data.get("status") == 1:
                p = data.get("product", {})
                name = p.get("product_name") or p.get("product_name_en", "")
                brand_online = p.get("brands", "")
                if name:
                    st.session_state.product_name = name
                if brand_online:
                    st.session_state.brand = brand_online
                st.toast(f"🌐 Product details fetched online: {name}")
                return
    except Exception:
        pass

    st.toast("ℹ️ New barcode. Fill in product details.")


def on_barcode_change():
    autofill_product(st.session_state.barcode_input)


# --- UI ---
st.markdown("## 🟡 Add Stock - Buying & Selling Price")

col_bar1, col_bar2 = st.columns([4, 1])
with col_bar1:
    barcode = st.text_input(
        "Barcode (optional)", 
        key="barcode_input", 
        placeholder="Scan or type barcode here",
        on_change=on_barcode_change
    )
with col_bar2:
    st.write("")
    st.write("")
    if st.button("🔍 Autofill", use_container_width=True):
        autofill_product(st.session_state.barcode_input)
        st.rerun()

# Scanner toggle with persistent key
scanner_open = st.checkbox("📷 Open Live Scanner", key="scanner_active")

if scanner_open:
    components.html("""
    <div id="reader" style="width:100%; max-width: 480px; margin: auto;"></div>
    <div id="scanner-status" style="color: green; font-weight: bold; text-align: center; margin-top: 8px;"></div>
    
    <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <script>
    let lastCode = "";
    let isProcessing = false;

    function onScanSuccess(decodedText) {
        if (isProcessing || decodedText === lastCode) return;
        lastCode = decodedText;
        isProcessing = true;
        setTimeout(() => { isProcessing = false; }, 2500); // 2.5s scan throttle

        document.getElementById('scanner-status').innerText = "✓ Scanned: " + decodedText;

        // Audio Beep Feedback
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            osc.frequency.setValueAtTime(850, ctx.currentTime);
            osc.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.15);
        } catch(e) {}

        // Inject directly into Streamlit React input without page reload
        try {
            const doc = window.parent.document;
            const inputs = doc.querySelectorAll('input[type="text"]');
            let targetInput = null;

            for (let inp of inputs) {
                const p = (inp.placeholder || "").toLowerCase();
                const a = (inp.getAttribute("aria-label") || "").toLowerCase();
                if (p.includes("barcode") || p.includes("scan") || a.includes("barcode")) {
                    targetInput = inp;
                    break;
                }
            }

            if (targetInput) {
                // Call native setter to bypass React's synthetic tracking
                const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeSetter.call(targetInput, decodedText);

                // Dispatch input and change events
                targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                targetInput.dispatchEvent(new Event('change', { bubbles: true }));

                // Dispatch Enter key to trigger Streamlit's WebSocket sync and on_change
                targetInput.dispatchEvent(new KeyboardEvent('keydown', {
                    bubbles: true,
                    cancelable: true,
                    key: 'Enter',
                    code: 'Enter',
                    keyCode: 13
                }));

                targetInput.blur();
            }
        } catch(err) {
            console.error("DOM access failed:", err);
            // Fallback for sandboxed cross-origin environments
            navigator.clipboard.writeText(decodedText);
            document.getElementById('scanner-status').innerText = "✓ Scanned: " + decodedText + " (Copied to clipboard)";
        }
    }

    let scanner = new Html5QrcodeScanner("reader", { 
        fps: 10, 
        qrbox: { width: 280, height: 120 },
        rememberLastUsedCamera: true
    }, false);
    scanner.render(onScanSuccess);
    </script>
    """, height=380)

# Alternative fallback: Snap photo using native Streamlit camera input
with st.expander("📸 Can't open webcam scanner? Click here to snap a photo"):
    cam_file = st.camera_input("Take photo of barcode")
    if cam_file:
        try:
            import cv2
            import numpy as np
            bytes_data = cam_file.getvalue()
            cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

            found_code = None
            if hasattr(cv2, "barcode"):
                det = cv2.barcode.BarcodeDetector()
                res = det.detectAndDecode(cv2_img)
                if isinstance(res, tuple) and res[0]:
                    found_code = res[0]

            if not found_code:
                qr_det = cv2.QRCodeDetector()
                res_qr, _, _ = qr_det.detectAndDecode(cv2_img)
                if res_qr:
                    found_code = res_qr

            if found_code:
                st.session_state.barcode_input = found_code
                autofill_product(found_code)
                st.rerun()
            else:
                st.warning("Barcode not detected in photo. Try holding it closer or steady.")
        except Exception as e:
            st.error(f"Image processing error: {e}")

# Form Inputs
product_name = st.text_input("Product Name *", key="product_name", placeholder="e.g. Vaseline 225ml")

col1, col2 = st.columns(2)
with col1:
    business_category = st.selectbox(
        "Business category", 
        CATEGORIES, 
        index=CATEGORIES.index(st.session_state.business_category) if st.session_state.business_category in CATEGORIES else 0,
        key="business_category"
    )
    brand = st.text_input("Brand (optional)", key="brand")
    stock_unit = st.selectbox(
        "Stock unit", 
        UNITS, 
        index=UNITS.index(st.session_state.stock_unit) if st.session_state.stock_unit in UNITS else 0,
        key="stock_unit"
    )
    buying_price = st.number_input("Buying price per unit ₦ *", min_value=0.0, step=100.0, key="buying_price")

with col2:
    quantity = st.number_input("Quantity *", min_value=0.0, step=1.0, key="quantity")
    selling_price = st.number_input("Selling price per unit ₦ *", min_value=0.0, step=100.0, key="selling_price")
    low_stock = st.number_input("Low-stock alert at", min_value=0.0, step=1.0, key="low_stock")
    size_variant = st.text_input("Size / variant (optional)", placeholder="e.g. 225ml, 50g", key="size_variant")

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
        if buying_price > 0:
            piece_buy_price = buying_price / pieces_per_unit
            st.metric("Mudu Cost", f"₦{piece_buy_price:.2f}")

if st.button("💾 Save to Stock", use_container_width=True):
    if not product_name or buying_price == 0 or selling_price == 0:
        st.error("Fill Product Name, Buying and Selling Price!")
    elif selling_price <= buying_price:
        st.error(f"Selling price (₦{selling_price}) must be > Buying price (₦{buying_price})")
    else:
        with get_db() as con:
            con.execute("""
                INSERT INTO stock (
                    product_name, business_category, brand, stock_unit, quantity, 
                    buying_price, selling_price, pieces_per_unit, piece_buy_price, 
                    piece_sell_price, low_stock_alert, size_variant, barcode, date_added
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                product_name, business_category, brand, stock_unit, quantity,
                buying_price, selling_price, pieces_per_unit, piece_buy_price,
                piece_sell_price, low_stock, size_variant, st.session_state.barcode_input,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))
            con.commit()
        st.success(f"Saved {product_name}!")
        st.balloons()
        st.rerun()

st.divider()
st.subheader("Stock List")
with get_db() as con:
    rows = con.execute("SELECT id, product_name, stock_unit, quantity, buying_price, selling_price FROM stock ORDER BY id DESC LIMIT 20").fetchall()
    for r in rows:
        sid, prod, unit, qty, buy, sell = r
        c1, c2 = st.columns([4, 1])
        with c1:
            st.write(f"**{prod}** | {qty} {unit} | Buy ₦{buy} Sell ₦{sell}")
        with c2:
            if st.button("🗑️ Delete", key=f"del_{sid}"):
                with get_db() as con2:
                    con2.execute("DELETE FROM stock WHERE id=?", (sid,))
                    con2.commit()
                st.rerun()
