import streamlit as st
import Invoice_parsing as ip
import pandas as pd
import tempfile

def update_master_sheet(master_df: pd.DataFrame, sales_df: pd.DataFrame, invoice_df: pd.DataFrame) -> pd.DataFrame:
    """
    Updates the master inventory DataFrame based on sales and invoice data.

    Args:
        master_df: DataFrame with current product list and stock levels. 
                   Expected columns: 'UPC', 'current_stock', 'Description'.
        sales_df: DataFrame with outgoing product data. 
                  Expected columns: 'Item_no' (as UPC), 'Units'.
        invoice_df: DataFrame with incoming product data. 
                    Expected columns: 'UPC code', 'QTY'.

    Returns:
        A clean, updated DataFrame with new stock levels and transaction summaries.
    """
    master = master_df.copy()
    sales = sales_df.copy()
    invoices = invoice_df.copy()

    #Standardizing column names
    master.rename(columns={'UPC Code': 'UPC'}, inplace=True)
    sales.rename(columns={'Item No': 'UPC'}, inplace=True)
    invoices.rename(columns={'UPC Code': 'UPC'}, inplace=True)

    #Cleaning Column types
    master['UPC'] = master['UPC'].astype(str).str.strip()
    sales['UPC'] = sales['UPC'].astype(str).str.strip()
    invoices['UPC'] = invoices['UPC'].astype(str).str.strip()

    if 'current_stock' in master.columns:
        master['current_stock'] = pd.to_numeric(master['current_stock'], errors='coerce').fillna(0)
    else:
        master['current_stock'] = 0  #
        st.warning("'current_stock' column not found, creating new one with 0s")
    sales['Units'] = pd.to_numeric(sales['Units'], errors='coerce').fillna(0)
    invoices['Quantity Confirmed'] = pd.to_numeric(invoices['Quantity Confirmed'], errors='coerce').fillna(0)

    #Generating Sales and Invoice summary: 
    sales_summary = sales.groupby('UPC')[['Description', 'Units']].sum().reset_index()
    sales_summary.rename(columns={'Units': 'quantity_sold', 'Description': 'sold_product_name'}, inplace=True)

    invoice_summary = invoices.groupby('UPC')[['Product Description', 'Quantity Confirmed']].sum().reset_index()
    invoice_summary.rename(columns={'Quantity Confirmed': 'quantity_received', 'Product Description': 'recived_product_name'}, inplace=True)

    #Conducting merge operations

    updated_df = pd.merge(master, sales_summary, on='UPC', how='left')
    updated_df = pd.merge(updated_df, invoice_summary, on='UPC', how='left')

    updated_df['sold_product_name'].fillna('Not Applicable')
    updated_df['recived_product_name'].fillna('Not Applicable')
    updated_df['quantity_sold'] = updated_df['quantity_sold'].fillna(0)
    updated_df['quantity_received'] = updated_df['quantity_received'].fillna(0)
    # Calculate the new stock
    updated_df['new_stock'] = (
        updated_df['current_stock'] + 
        updated_df['quantity_received'] - 
        updated_df['quantity_sold']
    )


    # Cleaning for end user
    updated_df[['current_stock', 'quantity_sold', 'quantity_received', 'new_stock']] = updated_df[['current_stock', 'quantity_sold', 'quantity_received', 'new_stock']].astype(int)
    return updated_df

def clean_sales_xlsx(sales_df) -> pd.DataFrame:
    # Remove the first column
    sales_df_cleaned = sales_df.drop(sales_df.columns[0], axis=1)

    # Find the row containing 'Entry Type' and 'Item No'
    header_row_idx = sales_df_cleaned[
        sales_df_cleaned.apply(lambda row: row.astype(str).str.contains('Entry Type').any() and row.astype(str).str.contains('Item No').any(), axis=1)
    ].index

    if len(header_row_idx) > 0:
        header_row = header_row_idx[0]
        # Promote this row to header
        sales_df_cleaned.columns = sales_df_cleaned.iloc[header_row]
        sales_df_cleaned = sales_df_cleaned.iloc[header_row + 1:].reset_index(drop=True)

    sales_df_cleaned['Item No'] = sales_df_cleaned['Item No'].astype(str).str.strip()
    sales_df_cleaned.dropna(inplace=True)
    sales_df_cleaned.reset_index(drop=True, inplace=True)

    return sales_df_cleaned

def clean_beer_store_master(beer_store_master_df):
    """
    Removes UPC "-" from UPC, 
    Removes "0" prefix from UPC.
    """
    beer_store_master_df['UPC'] = beer_store_master_df['UPC'].str.replace('-', '', regex=False).str.strip()
    beer_store_master_df['UPC'] = beer_store_master_df['UPC'].str.lstrip('0') if beer_store_master_df['UPC'].dtype == object else beer_store_master_df['UPC']
    return beer_store_master_df

def clean_beer_store_invoice_df(beer_store_invoice_df):
    beer_store_invoice_df['UPC Code'] = beer_store_invoice_df['UPC Code'].apply(lambda x: str(int(x)) if pd.notnull(x) else x)
    beer_store_invoice_df = beer_store_invoice_df.dropna(subset=['UPC Code'])
    return beer_store_invoice_df



st.set_page_config(page_title="Streamlit App", page_icon=":guardsman:", layout="wide")
st.title("Beer Inventory App")

"""
### Instructions: 
- You can upload 3 files total, one file per each upload button - master sheet, invoice pdf, and sales xls
- The Master sheet needs to be cleaned, without any empty rows or without multiple headers

Required columns to run (do not change case or name)
- Master sheet - "UPC", "current_stock"
- Sales sheet - "Item No" (where item no is actually UPC), "Description" 
- Invoice - "UPC Code", "Quantity Confirmed"

Running the App:
- Click the Run button after uploading files to process the inventory update.
- Ensure the master sheet and at two other files (sales and invoice) are uploaded, or an error will display.


Re-running the App:
- After downloading the updated inventory CSV, update the master sheet's current_stock column with the new_stock values from the CSV before re-running.
- Replace the old current_stock values with the new_stock values to reflect the latest inventory state.
---
"""

master_df = None
sales_df = pd.DataFrame()
beer_store_invoice_df = pd.DataFrame()


beer_store_invoice_upload = st.file_uploader("Upload beer store invoice", type=["pdf"])
sales_excel_upload = st.file_uploader("Upload sales excel file", type=['XLS', 'XLSX'])
beer_store_master_upload = st.file_uploader("Upload beer store master excel file", type=['XLS', 'XLSX'])

# Process only if master sheet is uploaded and at least one other file is present
if st.button("Run"):
        
    if beer_store_invoice_upload is not None:
        # Create a temporary file to save the uploaded PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(beer_store_invoice_upload.read())
            temp_path = temp_file.name

        # Process the PDF using the main function from Invoice_parsing.py
        beer_store_invoice_df = ip.main(document_path=temp_path)
        beer_store_invoice_df = clean_beer_store_invoice_df(beer_store_invoice_df)
        #st.dataframe(beer_store_invoice_df)

    if sales_excel_upload is not None:
        with tempfile.NamedTemporaryFile(delete=False) as sales_temp_file:
            sales_temp_file.write(sales_excel_upload.read())
            sales_temp_path = sales_temp_file.name
        sales_df = pd.read_excel(sales_temp_path)
        sales_df = clean_sales_xlsx(sales_df=sales_df)
        #st.dataframe(sales_df)

    if beer_store_master_upload is not None:
        with tempfile.NamedTemporaryFile(delete=False) as beer_master_temp_file:
            beer_master_temp_file.write(beer_store_master_upload.read())
            beer_master_temp_path = beer_master_temp_file.name
        master_df = pd.read_excel(beer_master_temp_path)
        master_df = clean_beer_store_master(beer_store_master_df=master_df)

    if master_df is not None and (not sales_df.empty and not beer_store_invoice_df.empty):
        updated_inventory_sheet = update_master_sheet(master_df=master_df, sales_df=sales_df, invoice_df=beer_store_invoice_df)
        st.dataframe(updated_inventory_sheet)  # Display the updated inventory
        csv = updated_inventory_sheet.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download updated inventory CSV",
            data=csv,
            file_name="updated_inventory.csv",
            mime="text/csv"
        )
    else:
        if master_df is None:
            st.error("Please upload the master sheet.")
        else:
            st.error("Please upload at least one of the sales Excel or beer store invoice PDF.")
