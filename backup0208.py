import streamlit as st
from PIL import Image, ImageFilter
import numpy as np
import pytesseract
from streamlit_drawable_canvas import st_canvas
import pysftp
import json
import io
import fitz  # PyMuPDF
import pyperclip
from paramiko import SSHException
import os
import pandas as pd
import subprocess
import requests
st.set_page_config(layout="wide", page_title="")

# Configure the path to Tesseract if necessary
pytesseract.pytesseract.tesseract_cmd = r'F:\\Tesseract-OCR\\tesseract.exe'

# Custom CSS to hide Streamlit elements and style the JSON content box
st.markdown("""
    <style>
        .custom-title {
            color: #D2691E;  /* Màu cam-nâu */
            font-size: 3em;
            font-weight: bold;
        }
        /* Hide Streamlit header, footer, and burger menu */
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .css-1rs6os.edgvbvh3 {visibility: hidden;} /* This targets the "Fork me on GitHub" ribbon */
        .css-15tx938.egzxvld1 {visibility: hidden;} /* This targets the GitHub icon in the menu */
        
        /* Style for the JSON content box */
        .json-box {
            border: 2px solid #d3d3d3;
            border-radius: 5px;
            padding: 10px;
            margin-top: 10px;
        }
        .json-box-label {
            font-weight: bold;
            background-color: #f0f0f0;
            padding: 2px 5px;
            position: absolute;
            margin-top: -20px;
            margin-left: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# SFTP connection details
sftp_host = "hotfolder.epik.live"
sftp_username = "spf"
sftp_password = "1234@BCD"
sftp_root_directory = "/home/spf/watching_folder/"
sftp_threeway_directory = "/home/spf/three_way_matching/"

# Custom SFTP options to bypass hostkey checking
cnopts = pysftp.CnOpts()
cnopts.hostkeys = None

# Initialize session state for login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'role' not in st.session_state:
    st.session_state.role = None

# Define user credentials
credentials = {
    "user1": {"password": "h2PCYTpuBMHf", "role": "user"},
    "admin": {"password": "YFfDVw7ZY7as", "role": "admin"},
    "manager": {"password": "LIIsgNrWcfo1", "role": "manager"}
}

# Login function
def login(username, password):
    if username in credentials and credentials[username]["password"] == password:
        st.session_state.logged_in = True
        st.session_state.role = credentials[username]["role"]
        return True
    return False
def copy_to_clipboard(text):
    process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, text=True)
    process.communicate(input=text)
# Display login form if not logged in
if not st.session_state.logged_in:
    col_login1, col_login2, col_login3 = st.columns([2.5, 5, 2.5])
    with col_login1:
        st.empty()
    with col_login2:
        st.markdown('<h1 class="custom-title">PreFlight Cockpit</h1>', unsafe_allow_html=True)
        st.header("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if login(username, password):
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    with col_login3:
        st.empty()
else:
    # Connect to SFTP server and list directories
    try:
        with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
            sftp.cwd(sftp_root_directory)
            all_folders = sftp.listdir()
            all_folders = [f for f in all_folders if sftp.isdir(f)]
    except SSHException as e:
        st.error(f"SSHException: {e}")

    # Initialize session state for page numbers and edited data
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0
    if 'edited_info_details' not in st.session_state:
        st.session_state.edited_info_details = []
    if 'edited_transactions' not in st.session_state:
        st.session_state.edited_transactions = {}
    if 'edited_transaction_summary' not in st.session_state:
        st.session_state.edited_transaction_summary = {}
    if 'edited_time_deposit_details' not in st.session_state:
        st.session_state.edited_time_deposit_details = []
    if 'selected_file' not in st.session_state:
        st.session_state.selected_file = ""
    if 'selected_folder' not in st.session_state:
        st.session_state.selected_folder = ""
    if 'selected_json' not in st.session_state:
        st.session_state.selected_json = ""

    # Function to display PDF and convert to image with navigation
    def display_pdf_and_convert_to_image(pdf_content):
        images = []
        original_sizes = []
        try:
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            total_pages = len(doc)
            current_page = st.session_state.current_page

            col_empty_PDF, col1_titlePDF, col2, col3, col4 = st.columns([0.5, 4, 2.5, 2.5, 0.5])
            with col1_titlePDF:
                st.markdown("#### Preview of the PDF:")

            with col2:
                if st.button('Previous page', key=f'prev_page_{current_page}'):
                    if current_page > 0:
                        st.session_state['canvas_reset'] = True  # Flag to reset canvas
                        st.session_state['current_page'] = current_page - 1

            with col3:
                if st.button('Next page', key=f'next_page_{current_page}'):
                    if current_page < total_pages - 1:
                        st.session_state['canvas_reset'] = True  # Flag to reset canvas
                        st.session_state['current_page'] = current_page + 1

            page = doc.load_page(st.session_state.current_page)
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            img = img.filter(ImageFilter.SHARPEN)
            images.append(img)
            original_sizes.append((pix.width, pix.height))
        except Exception as e:
            st.error(f"Error in PDF processing: {e}")
        return images, original_sizes
    def export_to_xero_csv(json_content):
        # Test API endpoint
        test_api_url = "https://httpbin.org/post"
        
        response = requests.post(test_api_url, json=json_content)
        if response.status_code == 200:
            st.success("Successfully exported to Xero CSV.")
            st.json(response.json())  # Display the response for verification
        else:
            st.error("Failed to export to Xero CSV.")

    def export_to_peppol_xml(json_content):
        # Test API endpoint
        test_api_url = "https://httpbin.org/post"
        
        response = requests.post(test_api_url, json=json_content)
        if response.status_code == 200:
            st.success("Successfully exported to PEPPOL XML.")
            st.json(response.json())  # Display the response for verification
        else:
            st.error("Failed to export to PEPPOL XML.")
    def process_json_content(json_content, selected_folder):
        if selected_folder == 'Bank statement':
            tabs = st.tabs(["Information Details", "Transaction Details", "Time Deposit Details","Export to"])
            with tabs[0]:
                st.markdown("### Information Details")
                info_details_df = pd.DataFrame(json_content.get("information_details", []))
                edited_info_details = st.data_editor(info_details_df, num_rows="dynamic", key='info_details_editor')
                st.session_state.edited_info_details = edited_info_details.to_dict(orient='records')

            with tabs[1]:
                subtab = st.selectbox("Select Transaction", options=[f"Transaction {i+1}" for i in range(len(json_content.get("transaction_details", [])))], index=0, key='transaction_select')
                selected_index = int(subtab.split()[1]) - 1

                transaction_detail = json_content.get("transaction_details", [])[selected_index]

                st.markdown(f"#### {subtab}")
                transactions_df = pd.DataFrame(transaction_detail.get("transactions", []))
                edited_transactions = st.data_editor(transactions_df, num_rows="dynamic", key=f'transactions_editor_{selected_index}')
                st.session_state.edited_transactions[selected_index] = edited_transactions.to_dict(orient='records')

                st.markdown(f"##### Transaction Summary {selected_index+1}")
                transaction_summary_df = pd.DataFrame(transaction_detail.get("transaction_summary", []))
                edited_transaction_summary = st.data_editor(transaction_summary_df, num_rows="dynamic", key=f'transaction_summary_editor_{selected_index}')
                st.session_state.edited_transaction_summary[selected_index] = edited_transaction_summary.to_dict(orient='records')

            with tabs[2]:
                st.markdown("### Time Deposit Details")
                time_deposit_details_df = pd.DataFrame(json_content.get("time_deposit_details", []))
                edited_time_deposit_details = st.data_editor(time_deposit_details_df, num_rows="dynamic", key='time_deposit_editor')
                st.session_state.edited_time_deposit_details = edited_time_deposit_details.to_dict(orient='records')
            with tabs[3]:
                st.markdown("### Export to")
                col_export1, col_export2 = st.columns(2)
                if st.button("Export to Xero CSV"):
                    form_data = collect_form_data(selected_folder)
                    st.write(form_data)
                    export_to_xero_csv(form_data)
                if st.button("Export to PEPPOL XML"):
                    form_data = collect_form_data(selected_folder)
                    export_to_peppol_xml(form_data)

        elif selected_folder == 'Receipt':
            tabs = st.tabs(["General Information", "Line Items","Export to"])
            with tabs[0]:
                st.markdown("### General Information")
                general_info_fields = [
                    "receipt_number", "document_date", "store_name", "store_address",
                    "phone_number", "fax_number", "email", "website", "gst_id",
                    "pax_number", "table_number", "cashier_name", "subtotal",
                    "rounding_amount", "paid_amount", "change_amount", "service_charge_percent",
                    "service_charge", "tax_percent", "tax_total", "total"
                ]
                general_info = {field: json_content.get(field, "") for field in general_info_fields}
                for field, value in general_info.items():
                    general_info[field] = st.text_input(label=field.replace("_", " ").title(), value=value, key=f"{field}_input")
                st.session_state.edited_info_details = general_info

            with tabs[1]:
                st.markdown("### Line Items")
                line_items_fields = [
                    "item_no_of_receipt_items", "names_of_receipt_items",
                    "quantities_of_invoice_items", "unit_prices_of_receipt_items",
                    "gross_worth_of_receipt_items"
                ]
                line_items = {field: json_content.get(field, []) for field in line_items_fields}
                line_items_df = pd.DataFrame(line_items)
                edited_line_items = st.data_editor(line_items_df, num_rows="dynamic", key='line_items_editor')
                st.session_state.edited_transactions = edited_line_items.to_dict(orient='records')
            with tabs[2]:
                st.markdown("### Export to")
                col_export1, col_export2 = st.columns(2)
                if st.button("Export to Xero CSV"):
                    form_data = collect_form_data(selected_folder)
                    export_to_xero_csv(form_data)
                if st.button("Export to PEPPOL XML"):
                    form_data = collect_form_data(selected_folder)
                    export_to_peppol_xml(form_data)
        elif selected_folder == 'Invoice':
            tabs = st.tabs(["General Information", "Line Items","Export to"])
            with tabs[0]:
                st.markdown("### General Information")
                general_info_fields = [
                    "invoice_number", "invoice_date", "client_name", "client_address",
                    "sale_order_number", "client_tax_id", "seller_name", "seller_address",
                    "seller_tax_id", "iban", "total_net_worth", "tax_amount",
                    "tax_percent", "total_gross_worth"
                ]
                general_info = {field: json_content.get(field, "") for field in general_info_fields}
                for field, value in general_info.items():
                    general_info[field] = st.text_input(label=field.replace("_", " ").title(), value=value, key=f"{field}_input")
                st.session_state.edited_info_details = general_info

            with tabs[1]:
                st.markdown("### Line Items")
                line_items_fields = [
                    "item_no_of_invoice_items", "names_of_invoice_items",
                    "quantities_of_invoice_items", "unit_prices_of_invoice_items",
                    "gross_worth_of_invoice_items"
                ]
                line_items = {field: json_content.get(field, []) for field in line_items_fields}
                line_items_df = pd.DataFrame(line_items)
                edited_line_items = st.data_editor(line_items_df, num_rows="dynamic", key='line_items_editor')
                st.session_state.edited_transactions = edited_line_items.to_dict(orient='records')
            with tabs[2]:
                st.markdown("### Export to")
                col_export1, col_export2 = st.columns(2)
                if st.button("Export to Xero CSV"):
                    form_data = collect_form_data(selected_folder)
                    export_to_xero_csv(form_data)
                if st.button("Export to PEPPOL XML"):
                    form_data = collect_form_data(selected_folder)
                    export_to_peppol_xml(form_data)
        elif selected_folder == 'Business Card':
            tabs = st.tabs(["General Information","Export to"])
            with tabs[0]:
                st.markdown("### Business Card Details")
                card_info_fields = [
                    "company_name", "full_name", "title", "email_address",
                    "phone_number", "website", "address"
                ]
                card_info = {field: json_content.get(field, "") for field in card_info_fields}
                for field, value in card_info.items():
                    card_info[field] = st.text_input(label=field.replace("_", " ").title(), value=value, key=f"{field}_input")
                st.session_state.edited_info_details = card_info
            with tabs[1]:
                st.markdown("### Export to")
                col_export1, col_export2 = st.columns(2)
                if st.button("Export to Xero CSV"):
                    form_data = collect_form_data(selected_folder)
                    export_to_xero_csv(form_data)
                if st.button("Export to PEPPOL XML"):
                    form_data = collect_form_data(selected_folder)
                    export_to_peppol_xml(form_data)
        elif selected_folder == 'three_way_matching':
            tabs = st.tabs(["General Information", "Line Items", "Comparison View", "Summary View","Export to"])
            with tabs[0]:
                st.markdown("### General Information")
                general_info_fields = [
                    "invoice_number", "purchase_order_number","delivery_order_number", "document_date", "client_name", "client_address",
                    "sale_order_number", "client_tax_id", "seller_name", "seller_address",
                    "seller_tax_id", "iban", "total_net_worth", "tax_amount",
                    "tax_percent", "total_gross_worth"
                ]
                general_info = {field: json_content.get(field, "") for field in general_info_fields}
                for field, value in general_info.items():
                    general_info[field] = st.text_input(label=field.replace("_", " ").title(), value=value, key=f"{field}_input")
                st.session_state.edited_info_details = general_info

            with tabs[1]:
                st.markdown("### Line Items")
                line_items_fields = [
                    "item_no_of_invoice_items", "names_of_invoice_items",
                    "quantities_of_invoice_items", "unit_prices_of_invoice_items",
                    "gross_worth_of_invoice_items"
                ]
                line_items = {field: json_content.get(field, []) for field in line_items_fields}
                line_items_df = pd.DataFrame(line_items)
                edited_line_items = st.data_editor(line_items_df, num_rows="dynamic", key='line_items_editor')
                st.session_state.edited_transactions = edited_line_items.to_dict(orient='records')

            with tabs[2]:
                st.markdown("### Comparison View")

                # Extract the common part from the filename
                base_name = os.path.splitext(selected_file)[0]  # Remove the extension
                common_part = "_".join(base_name.split("_")[1:])

                # Determine the comparison files based on the selected file
                if base_name.startswith("INV"):
                    comparison_files = [f"PO_{common_part}.json", f"DO_{common_part}.json"]
                elif base_name.startswith("PO"):
                    comparison_files = [f"INV_{common_part}.json", f"DO_{common_part}.json"]
                elif base_name.startswith("DO"):
                    comparison_files = [f"INV_{common_part}.json", f"PO_{common_part}.json"]
                else:
                    comparison_files = []

                # Get the JSON files from the selected subfolder
                selected_subfolder_path = os.path.join(sftp_threeway_directory, selected_subfolder)
                selected_json_file = os.path.join(selected_subfolder_path, f"{base_name}.json")
                comparison_json_files = [os.path.join(selected_subfolder_path, file) for file in comparison_files]

                selected_json = {}
                comparison_jsons = []
                try:
                    with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
                        sftp.cwd(selected_subfolder_path)

                        # Load the selected JSON file
                        if f"{base_name}.json" in sftp.listdir():
                            with sftp.open(f"{base_name}.json", 'r') as json_file:
                                selected_json = json.load(json_file)
                        else:
                            st.error(f"No JSON file found: {base_name}.json")

                        # Load the comparison JSON files
                        for comparison_file in comparison_files:
                            if comparison_file in sftp.listdir():
                                with sftp.open(comparison_file, 'r') as json_file:
                                    comparison_jsons.append(json.load(json_file))
                            else:
                                st.error(f"No comparison file found: {comparison_file}")
                except FileNotFoundError:
                    st.error(f"File not found in the directory: {selected_subfolder_path}")

                if selected_json and comparison_jsons:
                    if base_name.startswith("INV"):
                        inv_json = selected_json
                        po_json = comparison_jsons[0] if len(comparison_jsons) > 0 else {}
                        do_json = comparison_jsons[1] if len(comparison_jsons) > 1 else {}
                    elif base_name.startswith("PO"):
                        po_json = selected_json
                        inv_json = comparison_jsons[0] if len(comparison_jsons) > 0 else {}
                        do_json = comparison_jsons[1] if len(comparison_jsons) > 1 else {}
                    elif base_name.startswith("DO"):
                        do_json = selected_json
                        inv_json = comparison_jsons[0] if len(comparison_jsons) > 0 else {}
                        po_json = comparison_jsons[1] if len(comparison_jsons) > 1 else {}
                    
                    combined_line_items = {
                        "Invoice Item No": inv_json.get("item_no_of_invoice_items", []),
                        "PO Item No": po_json.get("item_no_of_invoice_items", []),
                        "DO Item No": do_json.get("item_no_of_invoice_items", []),
                        "Invoice Item Name": inv_json.get("names_of_invoice_items", []),
                        "PO Item Name": po_json.get("names_of_invoice_items", []),
                        "DO Item Name": do_json.get("names_of_invoice_items", []),
                        "Invoice Quantity": inv_json.get("quantities_of_invoice_items", []),
                        "PO Quantity": po_json.get("quantities_of_invoice_items", []),
                        "DO Quantity": do_json.get("quantities_of_invoice_items", []),
                        "Invoice Unit Price": inv_json.get("unit_prices_of_invoice_items", []),
                        "PO Unit Price": po_json.get("unit_prices_of_invoice_items", []),
                        "DO Unit Price": do_json.get("unit_prices_of_invoice_items", []),
                        "Invoice Gross Worth": inv_json.get("gross_worth_of_invoice_items", []),
                        "PO Gross Worth": po_json.get("gross_worth_of_invoice_items", []),
                        "DO Gross Worth": do_json.get("gross_worth_of_invoice_items", []),
                    }
                    combined_line_items_df = pd.DataFrame(combined_line_items)

                    # Function to apply background color to specific rows
                    def highlight_discrepancies(data):
                        attr = 'background-color: #ffcccc'  # Light red for discrepancies
                        df1 = pd.DataFrame('', index=data.index, columns=data.columns)
                        for i in range(len(data)):
                            for j in range(0, len(data.columns), 3):
                                if data.iloc[i, j] != data.iloc[i, j + 1] or data.iloc[i, j] != data.iloc[i, j + 2]:
                                    df1.iloc[i, j] = attr
                                    df1.iloc[i, j + 1] = attr
                                    df1.iloc[i, j + 2] = attr
                        return df1

                    # Applying the highlight function to the dataframe
                    styled_comparison_table = combined_line_items_df.style.apply(highlight_discrepancies, axis=None)
                    st.dataframe(styled_comparison_table, use_container_width=True)
            with tabs[3]:
                # Summary Section
                total_fields = combined_line_items_df.shape[0]
                matched = sum(
                    row["Invoice Item No"] == row["PO Item No"] == row["DO Item No"] and
                    row["Invoice Item Name"] == row["PO Item Name"] == row["DO Item Name"] and
                    row["Invoice Quantity"] == row["PO Quantity"] == row["DO Quantity"] and
                    row["Invoice Unit Price"] == row["PO Unit Price"] == row["DO Unit Price"] and
                    row["Invoice Gross Worth"] == row["PO Gross Worth"] == row["DO Gross Worth"]
                    for _, row in combined_line_items_df.iterrows()
                )
                mismatched = total_fields - matched
                missing = len([item for sublist in combined_line_items_df.values.tolist() for item in sublist if item == ""])

                st.markdown("### Summary View")
                st.markdown(f"""
                    **Matching Status:**
                    - Total Fields: **{total_fields}**
                    - :green[Matched] : **{matched}**
                    - :red[Mismatched]: **{mismatched}**
                    - Missing: **{missing}**

                    **Discrepancy Details:**
                """)
                discrepancy_details = []
                for i, row in combined_line_items_df.iterrows():
                    discrepancies = {}
                    if row["Invoice Item No"] != row["PO Item No"] or row["Invoice Item No"] != row["DO Item No"]:
                        discrepancies.update({
                            "Invoice Item No": row["Invoice Item No"],
                            "PO Item No": row["PO Item No"],
                            "DO Item No": row["DO Item No"]
                        })
                    if row["Invoice Item Name"] != row["PO Item Name"] or row["Invoice Item Name"] != row["DO Item Name"]:
                        discrepancies.update({
                            "Invoice Item Name": row["Invoice Item Name"],
                            "PO Item Name": row["PO Item Name"],
                            "DO Item Name": row["DO Item Name"]
                        })
                    if row["Invoice Quantity"] != row["PO Quantity"] or row["Invoice Quantity"] != row["DO Quantity"]:
                        discrepancies.update({
                            "Invoice Quantity": row["Invoice Quantity"],
                            "PO Quantity": row["PO Quantity"],
                            "DO Quantity": row["DO Quantity"]
                        })
                    if row["Invoice Unit Price"] != row["PO Unit Price"] or row["Invoice Unit Price"] != row["DO Unit Price"]:
                        discrepancies.update({
                            "Invoice Unit Price": row["Invoice Unit Price"],
                            "PO Unit Price": row["PO Unit Price"],
                            "DO Unit Price": row["DO Unit Price"]
                        })
                    if row["Invoice Gross Worth"] != row["PO Gross Worth"] or row["Invoice Gross Worth"] != row["DO Gross Worth"]:
                        discrepancies.update({
                            "Invoice Gross Worth": row["Invoice Gross Worth"],
                            "PO Gross Worth": row["PO Gross Worth"],
                            "DO Gross Worth": row["DO Gross Worth"]
                        })
                    if discrepancies:
                        discrepancy_details.append(f"- Row {i + 1}: {discrepancies}")
                
                st.markdown("\n".join(discrepancy_details))
            with tabs[4]:
                st.markdown("### Export to")
                col_export1, col_export2 = st.columns(2)
                if st.button("Export to Xero CSV"):
                    form_data = collect_form_data(selected_folder)
                    export_to_xero_csv(form_data)
                if st.button("Export to PEPPOL XML"):
                    form_data = collect_form_data(selected_folder)
                    export_to_peppol_xml(form_data)
    # Function to reset other selectbox selections
    def reset_selections(except_folder):
        for folder in all_folders:
            if folder != except_folder:
                if f"{folder}_file_selector" in st.session_state:
                    del st.session_state[f"{folder}_file_selector"]
    # Function to apply background color to specific rows or cells for discrepancies
    def highlight_discrepancies(data):
        attr = 'background-color: #ffcccc'  # Light red for discrepancies
        df1 = pd.DataFrame('', index=data.index, columns=data.columns)
        
        for i in range(len(data)):
            row = data.iloc[i]
            if (row["Invoice Item No"] != row["PO Item No"] or row["Invoice Item No"] != row["DO Item No"] or row["PO Item No"] != row["DO Item No"]):
                df1.iloc[i, 0] = attr  # Highlight Invoice Item No column
                df1.iloc[i, 1] = attr  # Highlight PO Item No column
                df1.iloc[i, 2] = attr  # Highlight DO Item No column
            if (row["Invoice Item Name"] != row["PO Item Name"] or row["Invoice Item Name"] != row["DO Item Name"] or row["PO Item Name"] != row["DO Item Name"]):
                df1.iloc[i, 3] = attr  # Highlight Invoice Item Name column
                df1.iloc[i, 4] = attr  # Highlight PO Item Name column
                df1.iloc[i, 5] = attr  # Highlight DO Item Name column
            if (row["Invoice Quantity"] != row["PO Quantity"] or row["Invoice Quantity"] != row["DO Quantity"] or row["PO Quantity"] != row["DO Quantity"]):
                df1.iloc[i, 6] = attr  # Highlight Invoice Quantity column
                df1.iloc[i, 7] = attr  # Highlight PO Quantity column
                df1.iloc[i, 8] = attr  # Highlight DO Quantity column
            if (row["Invoice Unit Price"] != row["PO Unit Price"] or row["Invoice Unit Price"] != row["DO Unit Price"] or row["PO Unit Price"] != row["DO Unit Price"]):
                df1.iloc[i, 9] = attr  # Highlight Invoice Unit Price column
                df1.iloc[i, 10] = attr  # Highlight PO Unit Price column
                df1.iloc[i, 11] = attr  # Highlight DO Unit Price column
            if (row["Invoice Gross Worth"] != row["PO Gross Worth"] or row["Invoice Gross Worth"] != row["DO Gross Worth"] or row["PO Gross Worth"] != row["DO Gross Worth"]):
                df1.iloc[i, 12] = attr  # Highlight Invoice Gross Worth column
                df1.iloc[i, 13] = attr  # Highlight PO Gross Worth column
                df1.iloc[i, 14] = attr  # Highlight DO Gross Worth column
        return df1
    def collect_form_data(selected_folder):
        form_data = {
            "Document Label": st.session_state.selected_file,
        }

        if selected_folder == 'Bank statement':
            form_data.update({
                "information_details": st.session_state.edited_info_details,
                "transaction_details": [
                    {
                        "transactions": st.session_state.edited_transactions[i],
                        "transaction_summary": st.session_state.edited_transaction_summary.get(i, [])
                    } for i in range(len(st.session_state.edited_transactions))
                ],
                "time_deposit_details": st.session_state.edited_time_deposit_details
            })
        elif selected_folder == 'Receipt':
            form_data.update(st.session_state.edited_info_details)
            form_data.update({
                "item_no_of_receipt_items": st.session_state.edited_transactions.get("item_no_of_receipt_items", []),
                "names_of_receipt_items": st.session_state.edited_transactions.get("names_of_receipt_items", []),
                "quantities_of_invoice_items": st.session_state.edited_transactions.get("quantities_of_invoice_items", []),
                "unit_prices_of_receipt_items": st.session_state.edited_transactions.get("unit_prices_of_receipt_items", []),
                "gross_worth_of_receipt_items": st.session_state.edited_transactions.get("gross_worth_of_receipt_items", []),
            })
        elif selected_folder == 'Invoice':
            form_data.update(st.session_state.edited_info_details)
            form_data.update({
                "item_no_of_invoice_items": st.session_state.edited_transactions.get("item_no_of_invoice_items", []),
                "names_of_invoice_items": st.session_state.edited_transactions.get("names_of_invoice_items", []),
                "quantities_of_invoice_items": st.session_state.edited_transactions.get("quantities_of_invoice_items", []),
                "unit_prices_of_invoice_items": st.session_state.edited_transactions.get("unit_prices_of_invoice_items", []),
                "gross_worth_of_invoice_items": st.session_state.edited_transactions.get("gross_worth_of_invoice_items", []),
            })
        elif selected_folder == 'Business Card':
            form_data.update(st.session_state.edited_info_details)
        elif selected_folder == 'three_way_matching':
            form_data.update(st.session_state.edited_info_details)
            form_data.update({
                "item_no_of_invoice_items": [item.get("item_no_of_invoice_items", "") for item in st.session_state.edited_transactions] if st.session_state.edited_transactions else [],
                "names_of_invoice_items": [item.get("names_of_invoice_items", "") for item in st.session_state.edited_transactions] if st.session_state.edited_transactions else [],
                "quantities_of_invoice_items": [item.get("quantities_of_invoice_items", "") for item in st.session_state.edited_transactions] if st.session_state.edited_transactions else [],
                "unit_prices_of_invoice_items": [item.get("unit_prices_of_invoice_items", "") for item in st.session_state.edited_transactions] if st.session_state.edited_transactions else [],
                "gross_worth_of_invoice_items": [item.get("gross_worth_of_invoice_items", "") for item in st.session_state.edited_transactions] if st.session_state.edited_transactions else [],
            })

        return form_data
    # Sidebar with navigation
    if st.session_state.role == "user":
        allowed_pages = ["Bank statement"]
    else:
        allowed_pages = ["Bank statement", "Invoice", "Receipt", "Business Card", "3-Way Matching"]

    page = st.sidebar.radio("Choose a page:", allowed_pages)

    selected_folder = ""
    if page == "3-Way Matching":
        selected_folder = "three_way_matching"
    else:
        selected_folder = page

    # Create the two-column layout
    col2, col1 = st.columns([6, 4])

    # Display the folders and their files in dropdowns within an expander
    with col2:
        st.subheader(f'{page} Document', divider='rainbow')

        try:
            with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
                if selected_folder == "three_way_matching":
                    sftp.cwd(sftp_threeway_directory)
                    subfolders = sftp.listdir()
                    selected_subfolder = st.selectbox("Select a subfolder", options=subfolders)
                    if selected_subfolder:
                        sftp.cwd(os.path.join(sftp_threeway_directory, selected_subfolder))
                else:
                    sftp.cwd(os.path.join(sftp_root_directory, selected_folder))
                all_files = sftp.listdir()
        except SSHException as e:
            st.error(f"SSHException: {e}")

        # Filter PDF and image files
        supported_files = [f for f in all_files if f.endswith(('.pdf', '.png', '.jpg', '.jpeg'))]
        json_files = {os.path.splitext(f)[0]: f for f in all_files if f.endswith('.json')}

        if selected_folder == "three_way_matching":
            selected_file = st.selectbox(f"Select a file from folder {selected_subfolder}", options=[""] + supported_files, index=0, key=f"{selected_folder}_{selected_subfolder}_file_selector")
        else:
            selected_file = st.selectbox(f"Select a file from {page}", options=[""] + supported_files, index=0, key=f"{selected_folder}_file_selector")

        if selected_file:
            # Only update if the selected file has changed
            if st.session_state.selected_file != selected_file:
                st.session_state.selected_file = selected_file
                st.session_state.selected_folder = selected_folder
                st.session_state.selected_json = json_files.get(os.path.splitext(selected_file)[0])
                st.session_state.current_page = 0  # Reset to first page when a new file is selected

        if 'selected_file' in st.session_state and st.session_state.selected_file:
            selected_file = st.session_state.selected_file
            selected_folder = st.session_state.selected_folder
            selected_json = st.session_state.selected_json

            with st.spinner('Loading ...'):
                # Download and display file as images or PDF pages
                with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
                    if selected_folder == "three_way_matching":
                        sftp.cwd(os.path.join(sftp_threeway_directory, selected_subfolder))
                    else:
                        sftp.cwd(os.path.join(sftp_root_directory, selected_folder))
                    if selected_file.endswith('.pdf'):
                        with sftp.open(selected_file, 'rb') as file:
                            file_content = file.read()
                            images, _ = display_pdf_and_convert_to_image(file_content)
                            if images:
                                img = images[0]
                                original_size = img.size
                                aspect_ratio = img.width / img.height

                                if 'canvas_state' not in st.session_state:
                                    st.session_state['canvas_state'] = {}

                                if 'canvas_reset' not in st.session_state:
                                    st.session_state['canvas_reset'] = False
                                # Apply sharpening filter
                                
                                
                                
                                img = img.filter(ImageFilter.SHARPEN)
                                # Create a placeholder for the success message
                                success_placeholder = st.empty()

                                # Load the canvas state if it exists for the current page
                                canvas_state = st.session_state['canvas_state'].get(st.session_state.get('current_page', 0), {})

                                # Set fixed width for the column
                                col_width = 800  # Set this to the desired width
                                new_width = col_width
                                new_height = int(new_width / aspect_ratio)
                                img_resized = img.resize((new_width, new_height))

                                # Use columns to ensure image fits within the column width
                                col_image, col_empty = st.columns([9.9, 0.1])
                                with col_image:
                                    canvas_result = st_canvas(
                                        fill_color="rgba(255, 0, 0, 0.3)",  # Rectangle color
                                        stroke_width=2,
                                        stroke_color="rgba(255, 0, 0, 1)",
                                        background_image=img_resized,
                                        update_streamlit=True,
                                        height=new_height,
                                        width=new_width,
                                        drawing_mode="rect",
                                        key=f"canvas_{st.session_state['current_page']}",
                                        initial_drawing=None if st.session_state.get('canvas_reset', False) else canvas_state.get('initial_drawing', {}),
                                    )

                                # Reset the canvas reset flag
                                if st.session_state.get('canvas_reset', False):
                                    st.session_state['canvas_reset'] = False

                                if 'interaction_processed' not in st.session_state:
                                    st.session_state.interaction_processed = False

                                if canvas_result.json_data is not None:
                                    objects = canvas_result.json_data["objects"]
                                    if objects:
                                        obj = objects[-1]
                                        left = int(obj["left"])
                                        top = int(obj["top"])
                                        width = int(obj["width"])
                                        height = int(obj["height"])

                                        roi = np.array(img_resized.convert('RGB'))[top:top + height, left:left + width]
                                        text = pytesseract.image_to_string(roi, lang='eng').strip()

                                        # Copy extracted text to clipboard
                                        
                                        copy_to_clipboard(text)
                                        # Display success message above the metadata inputs
                                        success_placeholder.success(f"Extracted text copied to clipboard: {text}")

                                        # Store the updated canvas state
                                        st.session_state['canvas_state'][st.session_state['current_page']] = canvas_result.json_data
                    else:
                        with sftp.open(selected_file, 'rb') as file:
                            img = Image.open(file)
                            
                            # Set fixed width for the column
                            col_width = 800  # Set this to the desired width
                            aspect_ratio = img.width / img.height
                            new_width = col_width
                            new_height = int(new_width / aspect_ratio)
                            img_resized = img.resize((new_width, new_height))
                            
                            #st.image(img_resized, use_column_width=True)

                            img_cv = np.array(img_resized.convert('RGB'))

                            if 'canvas_state' not in st.session_state:
                                st.session_state['canvas_state'] = {}

                            if 'canvas_reset' not in st.session_state:
                                st.session_state['canvas_reset'] = False
                            # Apply sharpening filter
                            img = img.filter(ImageFilter.SHARPEN)
                            # Create a placeholder for the success message
                            success_placeholder = st.empty()

                            # Load the canvas state if it exists for the current page
                            canvas_state = st.session_state['canvas_state'].get(st.session_state.get('current_page', 0), {})

                            canvas_result = st_canvas(
                                fill_color="rgba(255, 0, 0, 0.3)",  # Rectangle color
                                stroke_width=2,
                                stroke_color="rgba(255, 0, 0, 1)",
                                background_image=Image.fromarray(np.array(img_resized)),
                                update_streamlit=True,
                                height=new_height,
                                width=new_width,
                                drawing_mode="rect",
                                key=f"canvas_{st.session_state['current_page']}",
                                initial_drawing=None if st.session_state.get('canvas_reset', False) else canvas_state.get('initial_drawing', {}),
                            )

                            # Reset the canvas reset flag
                            if st.session_state.get('canvas_reset', False):
                                st.session_state['canvas_reset'] = False

                            if 'interaction_processed' not in st.session_state:
                                st.session_state.interaction_processed = False

                            if canvas_result.json_data is not None:
                                objects = canvas_result.json_data["objects"]
                                if objects:
                                    obj = objects[-1]
                                    left = int(obj["left"])
                                    top = int(obj["top"])
                                    width = int(obj["width"])
                                    height = int(obj["height"])

                                    roi = img_cv[top:top + height, left:left + width]
                                    text = pytesseract.image_to_string(roi, lang='eng').strip()

                                    # Copy extracted text to clipboard
                                    # Copy extracted text to clipboard
                                    copy_to_clipboard(text)
                                    # Display success message above the metadata inputs
                                    success_placeholder.success(f"Extracted text copied to clipboard: {text}")

                                    # Store the updated canvas state
                                    st.session_state['canvas_state'][st.session_state['current_page']] = canvas_result.json_data
                
                if st.button("Done and Submit", type="primary", key='done_submit'):
                    form_data = collect_form_data(selected_folder)

                    json_filename = f"{os.path.splitext(selected_file)[0]}.json"
                    if json_filename:
                        with open(json_filename, 'w') as json_file:
                            json.dump(form_data, json_file, indent=4)

                        with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
                            if selected_folder == "three_way_matching":
                                sftp.cwd(os.path.join(sftp_threeway_directory, selected_subfolder).replace("\\", "/"))
                            else:
                                sftp.cwd(os.path.join(sftp_root_directory, selected_folder))

                            sftp.put(json_filename, json_filename)
                            st.success(f"File {json_filename} uploaded successfully ")

                        with open(json_filename, 'r') as json_file:
                            json_data = json_file.read()
                        st.download_button("Download JSON", json_data, json_filename, "application/json", key='download_json')
                        st.success("Data submitted and uploaded successfully!")
    # Display JSON content in the left column with tabs and subtabs
    with col1:
        st.subheader('JSON Data Table', divider='rainbow')
        if 'selected_file' in st.session_state and st.session_state.selected_file:
            selected_file = st.session_state.selected_file
            selected_folder = st.session_state.selected_folder
            selected_json = st.session_state.selected_json

            if selected_json:
                with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
                    if selected_folder == "three_way_matching":
                        sftp.cwd(os.path.join(sftp_threeway_directory, selected_subfolder))
                    else:
                        sftp.cwd(os.path.join(sftp_root_directory, selected_folder))
                    with sftp.open(selected_json, 'r') as json_file:
                        json_content = json.load(json_file)

                process_json_content(json_content, selected_folder)
            else:
                st.error(f"No JSON file found for {selected_file}")
