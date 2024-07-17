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

# Custom SFTP options to bypass hostkey checking
cnopts = pysftp.CnOpts()
cnopts.hostkeys = None

# Connect to SFTP server and list files
try:
    with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
        sftp.cwd(sftp_directory)
        all_files = sftp.listdir()
except SSHException as e:
    st.error(f"SSHException: {e}")

# Filter PDF and JSON files
pdf_files = [f for f in all_files if f.endswith('.pdf')]
json_files = {os.path.splitext(f)[0]: f for f in all_files if f.endswith('.json')}

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
def display_pdf_and_convert_to_image(pdf_content):
    images = []
    original_sizes = []
    try:
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        total_pages = len(doc)
        current_page = st.session_state.current_page

        col_empty_PDF, col1_titlePDF, col2, col3, col4 = st.columns([1, 5, 2, 2, 1])
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
col2, col1 = st.columns([4, 6])

# Display the PDF files list in a table
with col2:
    st.markdown("### Select Document")
    pdf_files_df = pd.DataFrame(pdf_files, columns=["PDF Files"])
    
    gb = GridOptionsBuilder.from_dataframe(pdf_files_df)
    gb.configure_selection(selection_mode="single", use_checkbox=True)
    grid_options = gb.build()

    grid_response = AgGrid(
        pdf_files_df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=400,
        fit_columns_on_grid_load=True
    )

    selected_rows = grid_response["selected_rows"]
    if selected_rows:
        st.session_state.selected_pdf = selected_rows[0]["PDF Files"]
        st.session_state.current_page = 0  # Reset to first page when a new PDF is selected

# Display the selected PDF and JSON content
if 'selected_pdf' in st.session_state and st.session_state.selected_pdf:
    selected_pdf = st.session_state.selected_pdf
    # Download and display PDF as images
    with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
        sftp.cwd(sftp_directory)
        with sftp.open(selected_pdf, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
            images, _ = display_pdf_and_convert_to_image(pdf_content)
            if images:
                st.image(images[0], use_column_width=True)

    # Score field
    score = st.number_input(label="Score", min_value=0, max_value=100, value=0, step=1)

    # Display JSON content in the left column with tabs and subtabs
    with col1:
        st.markdown('<div class="json-box"><span class="json-box-label">JSON content</span>', unsafe_allow_html=True)
        
        json_filename = os.path.splitext(selected_pdf)[0]  # Only the base name without extension
        if json_filename in json_files:
            json_path = json_files[json_filename]
            with pysftp.Connection(sftp_host, username=sftp_username, password=sftp_password, cnopts=cnopts) as sftp:
                sftp.cwd(sftp_directory)
                with sftp.open(json_path, 'r') as json_file:
                    json_content = json.load(json_file)

            # Create tabs for different sections
            tabs = st.tabs(["Information Details", "Transaction Details", "Time Deposit Details"])
            
            with tabs[0]:
                st.markdown("### Information Details")
                info_details_df = pd.DataFrame(json_content.get("information_details", []))
                edited_info_details = st.data_editor(info_details_df, num_rows="dynamic")
                st.session_state.edited_info_details = edited_info_details.to_dict(orient='records')

            with tabs[1]:
                subtab = st.selectbox("Select Transaction", options=[f"Transaction {i+1}" for i in range(len(json_content.get("transaction_details", [])))], index=0)
                selected_index = int(subtab.split()[1]) - 1
                
                transaction_detail = json_content.get("transaction_details", [])[selected_index]
                
                st.markdown(f"#### {subtab}")
                transactions_df = pd.DataFrame(transaction_detail.get("transactions", []))
                edited_transactions = st.data_editor(transactions_df, num_rows="dynamic")
                st.session_state.edited_transactions[selected_index] = edited_transactions.to_dict(orient='records')
                
                st.markdown(f"##### Transaction Summary {selected_index+1}")
                transaction_summary_df = pd.DataFrame(transaction_detail.get("transaction_summary", []))
                edited_transaction_summary = st.data_editor(transaction_summary_df, num_rows="dynamic")
                st.session_state.edited_transaction_summary[selected_index] = edited_transaction_summary.to_dict(orient='records')

            with tabs[2]:
                st.markdown("### Time Deposit Details")
                time_deposit_details_df = pd.DataFrame(json_content.get("time_deposit_details", []))
                edited_time_deposit_details = st.data_editor(time_deposit_details_df, num_rows="dynamic")
                st.session_state.edited_time_deposit_details = edited_time_deposit_details.to_dict(orient='records')

            if st.button("Done and Submit", type="primary"):
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
                st.download_button("Download JSON", json_data, "submitted_data.json", "application/json")
                
                st.success("Data submitted successfully!")
        else:
            st.error(f"No JSON file found for {selected_pdf}")
        
        st.markdown('</div>', unsafe_allow_html=True)
