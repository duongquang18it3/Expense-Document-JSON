import streamlit as st
from PIL import Image, ImageFilter
import fitz  # PyMuPDF
import os
import json
import io
import pandas as pd
import pysftp
from paramiko import SSHException
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

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
sftp_directory = "/home/spf/watching_folder/Bankstatement"
local_directory = "Bankfolder"

# Create local directory if it does not exist
if not os.path.exists(local_directory):
    os.makedirs(local_directory)

# Custom SFTP options to bypass hostkey checking
cnopts = pysftp.CnOpts()
cnopts.hostkeys = None

# Function to download files from SFTP
def download_files_from_sftp():
    try:
        with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
            sftp.cwd(sftp_directory)
            all_files = sftp.listdir()
            for filename in all_files:
                local_path = os.path.join(local_directory, filename)
                if not os.path.exists(local_path):
                    sftp.get(filename, local_path)
    except SSHException as e:
        st.error(f"SSHException: {e}")

# Download files if running for the first time
if not os.listdir(local_directory):
    download_files_from_sftp()

# Filter PDF and JSON files from local directory
local_files = os.listdir(local_directory)
pdf_files = [f for f in local_files if f.endswith('.pdf')]
json_files = {os.path.splitext(f)[0]: f for f in local_files if f.endswith('.json')}

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
if 'selected_pdf' not in st.session_state:
    st.session_state.selected_pdf = ""

# Function to display PDF and convert to image with navigation
def display_pdf_and_convert_to_image(pdf_path):
    images = []
    original_sizes = []
    try:
        doc = fitz.open(pdf_path)
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

# Create the two-column layout
col2, col1 = st.columns([4.5, 5.5])

# Display the PDF files list in a table within an expander
with col2:
    st.subheader('Epiklah Expense Document', divider='rainbow')
    with st.expander("Select Document"):
        pdf_files_df = pd.DataFrame(pdf_files, columns=["PDF Files"])
        
        gb = GridOptionsBuilder.from_dataframe(pdf_files_df)
        gb.configure_selection(selection_mode="single", use_checkbox=False)
        grid_options = gb.build()

        grid_response = AgGrid(
            pdf_files_df,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            height=170,
            fit_columns_on_grid_load=True,
            columns_auto_size_mode = True
        )

        selected_rows = grid_response["selected_rows"]
        if selected_rows and len(selected_rows) > 0:
            st.session_state.selected_pdf = selected_rows[0]["PDF Files"]
            st.session_state.current_page = 0  # Reset to first page when a new PDF is selected

    # Update this block to add a spinner
    if 'selected_pdf' in st.session_state and st.session_state.selected_pdf:
        selected_pdf = st.session_state.selected_pdf
        pdf_path = os.path.join(local_directory, selected_pdf)
        
        with st.spinner('Loading ...'):
            # Display PDF as images
            images, _ = display_pdf_and_convert_to_image(pdf_path)
            if images:
                st.image(images[0], use_column_width=True)

            # Score field and submit button
            score = st.number_input(label="Score", min_value=0, max_value=100, value=0, step=1, key='score_input')
            
            if st.button("Done and Submit", type="primary", key='done_submit'):
                # Collect all form data
                form_data = {
                    "Document Label": selected_pdf,
                    "Score": score,
                    "information_details": st.session_state.edited_info_details,
                    "transaction_details": [
                        {
                            "transactions": st.session_state.edited_transactions[i],
                            "transaction_summary": st.session_state.edited_transaction_summary[i]
                        } for i in range(len(st.session_state.edited_transactions))
                    ],
                    "time_deposit_details": st.session_state.edited_time_deposit_details
                }
                
                # Write JSON data to a file
                with open('submitted_data.json', 'w') as json_file:
                    json.dump(form_data, json_file, indent=4)

                # Provide download button for JSON file
                with open('submitted_data.json', 'r') as json_file:
                    json_data = json_file.read()
                st.download_button("Download JSON", json_data, "submitted_data.json", "application/json", key='download_json')
                
                st.success("Data submitted successfully!")

# Display JSON content in the left column with tabs and subtabs
with col1:
    st.subheader('JSON Data Table', divider='rainbow')
    if 'selected_pdf' in st.session_state and st.session_state.selected_pdf:
        selected_pdf = st.session_state.selected_pdf
        json_filename = os.path.splitext(selected_pdf)[0]  # Only the base name without extension
        if json_filename in json_files:
            json_path = os.path.join(local_directory, json_files[json_filename])
            with open(json_path, 'r') as json_file:
                json_content = json.load(json_file)

            # Create tabs for different sections
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

            if st.button("Done and Submit JSON", type="primary", key='done_submit_json'):
                # Collect all form data
                form_data = {
                    "Document Label": selected_pdf,
                    "Score": st.session_state.get('score', 0),
                    "information_details": st.session_state.edited_info_details,
                    "transaction_details": [
                        {
                            "transactions": st.session_state.edited_transactions[i],
                            "transaction_summary": st.session_state.edited_transaction_summary[i]
                        } for i in range(len(st.session_state.edited_transactions))
                    ],
                    "time_deposit_details": st.session_state.edited_time_deposit_details
                }
                
                # Write JSON data to a file
                with open('submitted_data.json', 'w') as json_file:
                    json.dump(form_data, json_file, indent=4)

                # Provide download button for JSON file
                with open('submitted_data.json', 'r') as json_file:
                    json_data = json_file.read()
                st.download_button("Download JSON", json_data, "submitted_data.json", "application/json", key='download_json_json')
                
                st.success("Data submitted successfully!")
        else:
            st.error(f"No JSON file found for {selected_pdf}")
