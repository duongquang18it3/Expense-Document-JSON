import streamlit as st
from PIL import Image, ImageFilter
import fitz  # PyMuPDF
import os
import json
import io
import pandas as pd
import pysftp
from paramiko import SSHException

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

# Custom SFTP options to bypass hostkey checking
cnopts = pysftp.CnOpts()
cnopts.hostkeys = None

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



# Function to reset other selectbox selections
def reset_selections(except_folder):
    for folder in all_folders:
        if folder != except_folder:
            if f"{folder}_file_selector" in st.session_state:
                del st.session_state[f"{folder}_file_selector"]
# Create the two-column layout
col2, col1 = st.columns([4.5, 5.5])

# Display the folders and their files in dropdowns within an expander
with col2:
    st.subheader('PreFlight Cockpit', divider='rainbow')
    with st.expander("Select Document"):
        for folder in all_folders:
            st.markdown(f"### {folder}")
            try:
                with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
                    sftp.cwd(os.path.join(sftp_root_directory, folder))
                    all_files = sftp.listdir()
            except SSHException as e:
                st.error(f"SSHException: {e}")
                continue

            # Filter PDF and image files
            supported_files = [f for f in all_files if f.endswith(('.pdf', '.png', '.jpg', '.jpeg'))]
            json_files = {os.path.splitext(f)[0]: f for f in all_files if f.endswith('.json')}
            
            selected_file = st.selectbox(f"Select a file from {folder}", options=[""] + supported_files, index=0, key=f"{folder}_file_selector")
            if selected_file:
                # Clear previous selections if folder changes
                if st.session_state.selected_folder != folder:
                    st.session_state.selected_file = selected_file
                    st.session_state.selected_folder = folder
                    st.session_state.selected_json = json_files.get(os.path.splitext(selected_file)[0])
                    st.session_state.current_page = 0  # Reset to first page when a new file is selected
                else:
                    st.session_state.selected_file = selected_file
                    st.session_state.selected_json = json_files.get(os.path.splitext(selected_file)[0])
                    st.session_state.current_page = 0    # Reset to first page when a new file is selected
# Update this block to add a spinner
if 'selected_file' in st.session_state and st.session_state.selected_file:
    selected_file = st.session_state.selected_file
    selected_folder = st.session_state.selected_folder
    selected_json = st.session_state.selected_json
    
    with st.spinner('Loading ...'):
        # Download and display file as images or PDF pages
        with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
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
                            "transaction_summary": st.session_state.edited_transaction_summary[i]
                        } for i in range(len(st.session_state.edited_transactions))
                    ],
                    "time_deposit_details": st.session_state.edited_time_deposit_details
                })
            elif selected_folder == 'Receipt':
                form_data.update(st.session_state.edited_info_details)
                form_data.update({
                    "item_no_of_receipt_items": st.session_state.edited_transactions["item_no_of_receipt_items"],
                    "names_of_receipt_items": st.session_state.edited_transactions["names_of_receipt_items"],
                    "quantities_of_invoice_items": st.session_state.edited_transactions["quantities_of_invoice_items"],
                    "unit_prices_of_receipt_items": st.session_state.edited_transactions["unit_prices_of_receipt_items"],
                    "gross_worth_of_receipt_items": st.session_state.edited_transactions["gross_worth_of_receipt_items"],
                })
            elif selected_folder == 'Invoice':
                form_data.update(st.session_state.edited_info_details)
                form_data.update({
                    "item_no_of_invoice_items": st.session_state.edited_transactions["item_no_of_invoice_items"],
                    "names_of_invoice_items": st.session_state.edited_transactions["names_of_invoice_items"],
                    "quantities_of_invoice_items": st.session_state.edited_transactions["quantities_of_invoice_items"],
                    "unit_prices_of_invoice_items": st.session_state.edited_transactions["unit_prices_of_invoice_items"],
                    "gross_worth_of_invoice_items": st.session_state.edited_transactions["gross_worth_of_invoice_items"],
                })
            elif selected_folder == 'Business Card':
                form_data.update(st.session_state.edited_info_details)

            # Write JSON data to a temporary file
            json_filename = f"{os.path.splitext(selected_file)[0]}.json"
            if json_filename:
                with open(json_filename, 'w') as json_file:
                    json.dump(form_data, json_file, indent=4)

                # Upload updated JSON file back to SFTP with the original name
                updated_json_path = os.path.join(sftp_root_directory, selected_folder, json_filename)
                with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
                    sftp.put(json_filename, updated_json_path)
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
                sftp.cwd(os.path.join(sftp_root_directory, selected_folder))
                with sftp.open(selected_json, 'r') as json_file:
                    json_content = json.load(json_file)

            process_json_content(json_content, selected_folder)
        else:
            st.error(f"No JSON file found for {selected_file}")
