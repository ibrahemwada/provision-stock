import streamlit as st
import sqlite3
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="3-Tier Scanner Test", layout="centered")

# ==============================================================================
# 0. ISOLATED TEST DATABASE (Does not touch your real SQLite DB)
# ==============================================================================
DB_FILE = "test_scanner.db"

def get_test_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_test_db():
    with get_test_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                barcode TEXT UNIQUE,
                category TEXT,
                brand TEXT,
                variant TEXT,
                unit TEXT,
                buy REAL,
                sell REAL,
                stock REAL,
                created TEXT
            )
        """)
        # Insert a sample local product for testing Tier 1
        con.execute("""
            INSERT OR IGNORE INTO products (id, name, barcode, category, brand, variant, unit, buy, sell, stock, created)
            VALUES (1, 'Indomie Instant Noodles (Local Demo)', '11111', 'Provisions', 'Dufil', '70g', 'pack', 250, 300, 48, ?)
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))

init_test_db()

# ==============================================================================
# 1. TIER 2: GOOGLE SHEETS / COMMUNITY DATABASE
# ==============================================================================
# When you have your own published CSV link, put it here:
COMMUNITY_SHEET_CSV_URL = "" 

def lookup_google_sheet(barcode: str):
    """Tier 2: Checks Google Sheets (Simulated fallback included for testing)"""
    # If user provided a real published CSV URL:
    if COMMUNITY_SHEET_CSV_URL.strip():
        try:
            df = pd.read_csv(COMMUNITY_SHEET_CSV_URL, dtype=str)
            if "barcode" in df.columns:
                match = df[df["barcode"].str.strip() == str(barcode).strip()]
                if not match.empty:
                    row = match.iloc[0]
                    return {
                        "name": row.get("name", ""),
                        "brand": row.get("brand", ""),
                        "category": row.get("category", "Provisions"),
                        "variant": row.get("variant", ""),
                        "unit": row.get("unit", "piece"),
                        "source": "Google Sheets (Live Cloud)"
                    }
        except Exception as e:
            st.error(f"Google Sheet error: {e}")

    # SIMULATED COMMUNITY DATABASE FOR TESTING (Barcode: '22222')
    simulated_community_db = {
        "22222": {
            "name": "Peak Evaporated Milk (Community Saved)",
            "brand": "Peak",
            "category": "Provisions",
            "variant": "160g tin",
            "unit": "tin",
            "source": "Google Sheets (Community)"
        }
    }
    return simulated_community_db.get(barcode)

# ==============================================================================
# 2. TIER 3: ONLINE SEARCH (Open Food Facts Global Retail API)
# ==============================================================================
def lookup_online(barcode: str):
    """Tier 3: Queries millions of international packaged retail barcodes"""
    try:
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        res = requests.get(url, headers={"User-Agent": "InventoryScannerTest/1.0"}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == 1:
                p = data.get("product", {})
                name = p.get("product_name") or p.get("generic_name") or ""
                brand = p.get("brands") or ""
                variant = p.get("quantity") or ""
                if name:
                    return {
                        "name": name,
                        "brand": brand,
                        "category": "Provisions",
                        "variant": variant,
                        "unit": "piece",
                        "source": "Online Retail Database (Open Food Facts)"
                    }
    except Exception as e:
        st.warning(f"Online search timed out: {e}")
    return None

# ==============================================================================
# CAMERA DECODER HELPER (Optional PyZbar)
# ==============================================================================
def decode_barcode_image(img_file):
    try:
        from pyzbar.pyzbar import decode
        from PIL import Image
        img = Image.open(img_file)
        decoded = decode(img)
        if decoded:
            return decoded[0].data.decode("utf-8")
    except ImportError:
        st.warning("⚠️ Install `pyzbar` and `pillow` for camera decoding (`pip install pyzbar pillow`). Typing barcodes works immediately!")
    except Exception:
        pass
    return None

# ==============================================================================
# UI: SCANNER & VERIFICATION DASHBOARD
# ==============================================================================
st.title("🧪 3-Tier Barcode Scanner (Test Lab)")
st.info("Test how the 3 lookup tiers work before applying this to your main app.")

# Instructions & quick test buttons
with st.expander("💡 Click to view Barcode Cheat-Sheet for Testing"):
    st.markdown("""
    Use these test barcodes in the input box below:
    * **`11111`** ➡️ Hits **Tier 1 (Local SQLite)** (Already in test DB)
    * **`22222`** ➡️ Hits **Tier 2 (Google Sheets / Community)**
    * **`3017620422003`** ➡️ Hits **Tier 3 (Online Search)** (Nutella Ferrero)
    * **`5449000000996`** ➡️ Hits **Tier 3 (Online Search)** (Coca-Cola bottle)
    * **`99999`** ➡️ Hits **Tier 4 (Not Found)** (Enter product manually)
    """)

# Scanner Inputs
scanned_code = None
tab_input, tab_cam = st.tabs(["⌨️ Scanner Gun / Type Barcode", "📸 Camera Scanner"])

with tab_input:
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        manual_code = st.text_input("Enter or scan barcode with scanner gun:", key="barcode_test_box")
    with col_btn:
        st.write("") # spacing
        search_clicked = st.button("🔎 Search", use_container_width=True)

    if manual_code and (search_clicked or manual_code != st.session_state.get("prev_manual")):
        scanned_code = manual_code.strip()
        st.session_state["prev_manual"] = scanned_code

with tab_cam:
    cam_file = st.camera_input("Hold barcode up to camera")
    if cam_file:
        cam_code = decode_barcode_image(cam_file)
        if cam_code:
            scanned_code = cam_code
            st.success(f"Scanned from camera: `{cam_code}`")
        else:
            st.warning("No barcode detected in camera frame.")

# ==============================================================================
# LOOKUP PIPELINE
# ==============================================================================
if scanned_code:
    st.subheader(f"Results for Barcode: `{scanned_code}`")
    
    with st.spinner("Checking Tier 1 (SQLite) ➡️ Tier 2 (Google Sheets) ➡️ Tier 3 (Online)..."):
        # 1. Check Local SQLite
        with get_test_db() as con:
            cur = con.execute("SELECT * FROM products WHERE barcode = ? LIMIT 1", (scanned_code,))
            local_row = cur.fetchone()

        if local_row:
            # TIER 1 HIT
            st.success("✅ **Tier 1 Match: Found in Local SQLite Database!**")
            p = dict(local_row)
            
            st.markdown(f"""
            ### {p['name']}
            - **Current Stock:** `{p['stock']} {p['unit']}`
            - **Buying Price:** ₦{p['buy']:,.2f}
            - **Selling Price:** ₦{p['sell']:,.2f}
            """)
            
            with st.form("test_stock_in"):
                st.write("#### Add Stock Directly")
                add_qty = st.number_input("Quantity Received", min_value=1.0, value=5.0, step=1.0)
                update_cost = st.number_input("Cost per unit (₦)", min_value=0.0, value=float(p['buy']))
                
                if st.form_submit_button("📥 Update Stock in SQLite", type="primary"):
                    with get_test_db() as con:
                        con.execute("UPDATE products SET stock = stock + ?, buy = ? WHERE id = ?", (add_qty, update_cost, p['id']))
                    st.success(f"Updated! New stock is {p['stock'] + add_qty}")
                    st.rerun()

        else:
            # 2. Check Tier 2: Google Sheets
            sheet_data = lookup_google_sheet(scanned_code)
            
            if sheet_data:
                st.info(f"🌐 **Tier 2 Match: Found in {sheet_data['source']}!** Form autofilled below.")
                prefill = sheet_data
            else:
                # 3. Check Tier 3: Online
                online_data = lookup_online(scanned_code)
                if online_data:
                    st.info(f"🌍 **Tier 3 Match: Found in {online_data['source']}!** Form autofilled below.")
                    prefill = online_data
                else:
                    st.warning("⚠️ **Not Found in any database.** Please enter details manually.")
                    prefill = {"name": "", "brand": "", "variant": "", "category": "Provisions", "unit": "piece"}

            # Registration Form
            st.write("---")
            st.write("### 📝 Register New Product into Local SQLite")
            with st.form("test_register_product"):
                c1, c2 = st.columns(2)
                with c1:
                    new_name = st.text_input("Product Name", value=prefill.get("name", ""))
                    new_barcode = st.text_input("Barcode", value=scanned_code, disabled=True)
                    new_category = st.selectbox("Category", ["Provisions", "Pharmacy", "Textiles", "Electronics", "Others"])
                    new_brand = st.text_input("Brand", value=prefill.get("brand", ""))
                    new_unit = st.selectbox("Stock Unit", ["piece", "pack", "carton", "tin", "bottle", "sachet"])
                with c2:
                    new_variant = st.text_input("Size / Variant", value=prefill.get("variant", ""))
                    new_buy = st.number_input("Buying Price (₦)", min_value=0.0, value=500.0, step=50.0)
                    new_sell = st.number_input("Selling Price (₦)", min_value=0.0, value=700.0, step=50.0)
                    new_stock = st.number_input("Initial Quantity", min_value=1.0, value=12.0, step=1.0)

                if st.form_submit_button("💾 Save Product to SQLite", type="primary"):
                    if not new_name.strip():
                        st.error("Product name is required.")
                    else:
                        with get_test_db() as con:
                            con.execute("""
                                INSERT INTO products (name, barcode, category, brand, variant, unit, buy, sell, stock, created)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (new_name.strip(), scanned_code, new_category, new_brand.strip(), 
                                  new_variant.strip(), new_unit, new_buy, new_sell, new_stock, 
                                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        st.success(f"🎉 Saved '{new_name}' to Local SQLite! If you scan barcode `{scanned_code}` again, it will now hit **Tier 1 (Local)**.")
                        st.rerun()

# ==============================================================================
# VIEW CURRENT TEST DATABASE
# ==============================================================================
st.divider()
st.subheader("📦 Current Products in Test SQLite Database")
with get_test_db() as con:
    current_df = pd.read_sql_query("SELECT id, name, barcode, brand, variant, stock, buy, sell FROM products", con)

st.dataframe(current_df, use_container_width=True, hide_index=True)
