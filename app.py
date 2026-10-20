# 1. Function to find product by barcode
def lookup_barcode():
    barcode = str(
        st.session_state.get("barcode_widget", "")
    ).strip()

    st.session_state["barcode_message"] = ""

    if not barcode:
        return

    with get_db() as con:
        row = con.execute(
            """
            SELECT product_name
            FROM stock
            WHERE TRIM(CAST(barcode AS TEXT)) = ?
            LIMIT 1
            """,
            (barcode,)
        ).fetchone()

    if row:
        st.session_state["product_name"] = row[0] or ""
        st.session_state["barcode_message"] = (
            f"Found product: {row[0]}"
        )
    else:
        st.session_state["barcode_message"] = (
            "Barcode not found in the database."
        )
…
1. Barcode FIRST

barcode = st.text_input("Barcode (optional)", placeholder="Scan or type", key="barcode_widget")

2. Check DB and FORCE auto-fill BEFORE product name box

if barcode.strip():
with get_db() as con:
row = con.execute("SELECT product_name FROM stock WHERE barcode=? LIMIT 1", (barcode.strip(),)).fetchone()
if row:
found_name = row[0]
if st.session_state.get("product_name", "") != found_name:
st.session_state["product_name"] = found_name
st.rerun()

3. Product name AFTER

product_name = st.text_input("Product Name *", placeholder="e.g. Vaseline 225ml", key="product_name")

Show message after box

if barcode.strip():
with get_db() as con:
row = con.execute("SELECT product_name FROM stock WHERE barcode=? LIMIT 1", (barcode.strip(),)).fetchone()
if row:
st.success(f"Found: {row[0]} - auto-filled")
