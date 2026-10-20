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


# 2. Barcode input
barcode = st.text_input(
    "Barcode (optional)",
    placeholder="Scan or type",
    key="barcode_widget",
    on_change=lookup_barcode
)

# 3. Product name input
product_name = st.text_input(
    "Product Name *",
    placeholder="e.g. Vaseline 225ml",
    key="product_name"
)

# 4. Display lookup result
message = st.session_state.get("barcode_message", "")

if message:
    st.info(message)
