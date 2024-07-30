import streamlit as st
from PIL import Image, ImageFilter
import numpy as np
from streamlit_drawable_canvas import st_canvas
import pysftp
import json
import io
import fitz  # PyMuPDF
import pyperclip
from paramiko import SSHException
import os
import pandas as pd

st.set_page_config(layout="wide", page_title="")

# Custom CSS to hide Streamlit elements and style the JSON content box
st.markdown("""
    <style>
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
sftp_threeway_directory = "/home/spf/threeway_matching"

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

# Display login form if not logged in
if not st.session_state.logged_in:
    col_login1, col_login2, col_login3 = st.columns([2.5,5,2.5])
    with col_login1:
        st.empty()
    with col_login2:
        st.title("PreFlight Cockpit")
        st.header("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if login(username, password):
                st.success("Login successful!")
                st.experimental_rerun()
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
                if st.button('Previous page', key='prev_page'):
                    if current_page > 0:
                        st.session_state['canvas_reset'] = True  # Flag to reset canvas
                        current_page -= 1
                        st.session_state['current_page'] = current_page

            with col3:
                if st.button('Next page', key='next_page'):
                    if current_page < total_pages - 1:
                        st.session_state['canvas_reset'] = True  # Flag to reset canvas
                        current_page += 1
                        st.session_state['current_page'] = current_page

            page = doc.load_page(current_page)
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            img = img.filter(ImageFilter.SHARPEN)
            images.append(img)
            original_sizes.append((pix.width, pix.height))
        except Exception as e:
            st.error(f"Error in PDF processing: {e}")
        return images, original_sizes

    def process_json_content(json_content, selected_folder):
        if selected_folder == 'Bankstatement':
            tabs = st.tabs(["Information Details", "Transaction Details", "Time Deposit Details"])
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

        elif selected_folder == 'Receipt':
            tabs = st.tabs(["General Information", "Line Items"])
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

        elif selected_folder == 'Invoice':
            tabs = st.tabs(["General Information", "Line Items"])
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

        elif selected_folder == 'Business Card':
            st.markdown("### Business Card Details")
            card_info_fields = [
                "company_name", "full_name", "title", "email_address",
                "phone_number", "website", "address"
            ]
            card_info = {field: json_content.get(field, "") for field in card_info_fields}
            for field, value in card_info.items():
                card_info[field] = st.text_input(label=field.replace("_", " ").title(), value=value, key=f"{field}_input")
            st.session_state.edited_info_details = card_info

        elif selected_folder == 'threeway_matching':
            tabs = st.tabs(["General Information", "Line Items","Comparison View", "Summary View"])
            with tabs[0]:
                st.markdown("### General Information")
                general_info_fields = [
                    "invoice_number", "purchase_order_number", "document_date", "client_name", "client_address",
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
                
                if base_name.startswith("INV"):
                    comparison_file = f"PO_{common_part}.json"
                elif base_name.startswith("PO"):
                    comparison_file = f"INV_{common_part}.json"
                else:
                    comparison_file = None

                comparison_json = {}
                if comparison_file:
                    try:
                        with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
                            sftp.cwd(sftp_threeway_directory)
                            if comparison_file in sftp.listdir():
                                with sftp.open(comparison_file, 'r') as json_file:
                                    comparison_json = json.load(json_file)
                            else:
                                st.error(f"No comparison file found: {comparison_file}")
                    except FileNotFoundError:
                        st.error(f"No comparison file found: {comparison_file}")

                if comparison_json:
                    combined_line_items = {
                        "Invoice Item No": json_content.get("item_no_of_invoice_items", []),
                        "PO Item No": comparison_json.get("item_no_of_invoice_items", []),
                        "Invoice Item Name": json_content.get("names_of_invoice_items", []),
                        "PO Item Name": comparison_json.get("names_of_invoice_items", []),
                        "Invoice Quantity": json_content.get("quantities_of_invoice_items", []),
                        "PO Quantity": comparison_json.get("quantities_of_invoice_items", []),
                        "Invoice Unit Price": json_content.get("unit_prices_of_invoice_items", []),
                        "PO Unit Price": comparison_json.get("unit_prices_of_invoice_items", []),
                        "Invoice Gross Worth": json_content.get("gross_worth_of_invoice_items", []),
                        "PO Gross Worth": comparison_json.get("gross_worth_of_invoice_items", []),
                    }
                    combined_line_items_df = pd.DataFrame(combined_line_items)

                    # Style function to highlight columns in pairs
                    def highlight_columns(x):
                        color = 'background-color: #c0ffbc'
                        df1 = pd.DataFrame('', index=x.index, columns=x.columns)
                        df1.iloc[:, ::2] = color
                        return df1

                    styled_df = combined_line_items_df.style.apply(highlight_columns, axis=None)
                    st.dataframe(styled_df)

                    # Create new table with Fields, Invoice, and PO columns
                    fields = []
                    invoice_values = []
                    po_values = []

                    for key in ["item_no_of_invoice_items", "names_of_invoice_items", "quantities_of_invoice_items", "unit_prices_of_invoice_items", "gross_worth_of_invoice_items"]:
                        for i, value in enumerate(json_content.get(key, [])):
                            fields.append(f"{key} {i + 1}")
                            invoice_values.append(value)
                            po_values.append(comparison_json.get(key, [""] * len(invoice_values))[i])

                    comparison_table = pd.DataFrame({
                        "Fields": fields,
                        "Invoice": invoice_values,
                        "PO": po_values
                    })
                    # Function to apply background color to specific rows
                    def highlight_discrepancies(data):
                        attr = 'background-color: #ffcccc'  # Light red for discrepancies
                        df1 = pd.DataFrame('', index=data.index, columns=data.columns)
                        for i in range(len(data)):
                            if data["Invoice"][i] != data["PO"][i] or pd.isnull(data["Invoice"][i]) or pd.isnull(data["PO"][i]):
                                df1.iloc[i, 1] = attr  # Highlight Invoice column
                                df1.iloc[i, 2] = attr  # Highlight PO column
                        return df1

                    styled_comparison_table = comparison_table.style.apply(highlight_discrepancies, axis=None)
                    st.dataframe(styled_comparison_table, use_container_width=True)

            with tabs[3]:
                # Summary Section
                    total_fields = len(fields)
                    matched = sum(i == j for i, j in zip(invoice_values, po_values))
                    mismatched = total_fields - matched
                    missing = po_values.count("")

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
                    for field, inv_val, po_val in zip(fields, invoice_values, po_values):
                        if inv_val != po_val:
                            discrepancy_details.append(f"- {field}: Invoice Value: {inv_val}, PO Value: {po_val}")
                    st.markdown("\n".join(discrepancy_details))

    # Function to reset other selectbox selections
    def reset_selections(except_folder):
        for folder in all_folders:
            if folder != except_folder:
                if f"{folder}_file_selector" in st.session_state:
                    del st.session_state[f"{folder}_file_selector"]

    # Sidebar with navigation
    if st.session_state.role == "user":
        allowed_pages = ["Bankstatement"]
    else:
        allowed_pages = ["Bankstatement", "Invoice", "Receipt", "Business Card", "3-Way Matching"]

    page = st.sidebar.radio("Choose a page:", allowed_pages)

    selected_folder = ""
    if page == "3-Way Matching":
        selected_folder = "threeway_matching"
    else:
        selected_folder = page

    # Create the two-column layout
    col2, col1 = st.columns([4.5, 5.5])

    # Display the folders and their files in dropdowns within an expander
    with col2:
        st.subheader(f'{page} Document', divider='rainbow')

        try:
            with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
                if selected_folder == "threeway_matching":
                    sftp.cwd(sftp_threeway_directory)
                else:
                    sftp.cwd(os.path.join(sftp_root_directory, selected_folder))
                all_files = sftp.listdir()
        except SSHException as e:
            st.error(f"SSHException: {e}")

        # Filter PDF and image files
        supported_files = [f for f in all_files if f.endswith(('.pdf', '.png', '.jpg', '.jpeg'))]
        json_files = {os.path.splitext(f)[0]: f for f in all_files if f.endswith('.json')}

        selected_file = st.selectbox(f"Select a file from {page}", options=[""] + supported_files, index=0, key=f"{selected_folder}_file_selector")
        if selected_file:
            # Clear previous selections if folder changes
            if st.session_state.selected_folder != selected_folder:
                st.session_state.selected_file = selected_file
                st.session_state.selected_folder = selected_folder
                st.session_state.selected_json = json_files.get(os.path.splitext(selected_file)[0])
                st.session_state.current_page = 0  # Reset to first page when a new file is selected
            else:
                st.session_state.selected_file = selected_file
                st.session_state.selected_json = json_files.get(os.path.splitext(selected_file)[0])
                st.session_state.current_page = 0    # Reset to first page when a new file is selected

        if 'selected_file' in st.session_state and st.session_state.selected_file:
            selected_file = st.session_state.selected_file
            selected_folder = st.session_state.selected_folder
            selected_json = st.session_state.selected_json

            with st.spinner('Loading ...'):
                # Download and display file as images or PDF pages
                with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
                    if selected_folder == "threeway_matching":
                        sftp.cwd(sftp_threeway_directory)
                    else:
                        sftp.cwd(os.path.join(sftp_root_directory, selected_folder))
                    if selected_file.endswith('.pdf'):
                        with sftp.open(selected_file, 'rb') as file:
                            file_content = file.read()
                            images, _ = display_pdf_and_convert_to_image(file_content)
                            if images:
                                st.image(images[0], use_column_width=True)
                    else:
                        with sftp.open(selected_file, 'rb') as file:
                            img = Image.open(file)
                            st.image(img, use_column_width=True)

                # Score field and submit button
                score = st.number_input(label="Score", min_value=0, max_value=100, value=0, step=1, key='score_input')

                if st.button("Done and Submit", type="primary", key='done_submit'):
                    # Collect all form data
                    form_data = {
                        "Document Label": selected_file,
                        "Score": score,
                    }

                    if selected_folder == 'Bankstatement':
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
                    elif selected_folder == 'threeway_matching':
                        form_data.update(st.session_state.edited_info_details)
                        form_data.update({
                            "item_no_of_invoice_items": [item.get("item_no_of_invoice_items", "") for item in st.session_state.edited_transactions] if st.session_state.edited_transactions else [],
                            "names_of_invoice_items": [item.get("names_of_invoice_items", "") for item in st.session_state.edited_transactions] if st.session_state.edited_transactions else [],
                            "quantities_of_invoice_items": [item.get("quantities_of_invoice_items", "") for item in st.session_state.edited_transactions] if st.session_state.edited_transactions else [],
                            "unit_prices_of_invoice_items": [item.get("unit_prices_of_invoice_items", "") for item in st.session_state.edited_transactions] if st.session_state.edited_transactions else [],
                            "gross_worth_of_invoice_items": [item.get("gross_worth_of_invoice_items", "") for item in st.session_state.edited_transactions] if st.session_state.edited_transactions else [],
                        })

                    json_filename = f"{os.path.splitext(selected_file)[0]}.json"
                    # Write JSON data to a temporary file
                    if json_filename:
                        with open(json_filename, 'w') as json_file:
                            json.dump(form_data, json_file, indent=4)

                        # Upload updated JSON file back to SFTP with the original name
                        with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
                            if selected_folder == "threeway_matching":
                                sftp.cwd(sftp_threeway_directory)  # Change to the correct directory
                            else:
                                sftp.cwd(os.path.join(sftp_root_directory, selected_folder))  # Change to the correct directory

                            sftp.put(json_filename, json_filename)
                            st.success(f"File {json_filename} uploaded successfully to {os.path.join(sftp_root_directory, selected_folder)}!")

                        # Provide download button for JSON file
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
                    if selected_folder == "threeway_matching":
                        sftp.cwd(sftp_threeway_directory)
                    else:
                        sftp.cwd(os.path.join(sftp_root_directory, selected_folder))
                    with sftp.open(selected_json, 'r') as json_file:
                        json_content = json.load(json_file)

                process_json_content(json_content, selected_folder)
            else:
                st.error(f"No JSON file found for {selected_file}")
