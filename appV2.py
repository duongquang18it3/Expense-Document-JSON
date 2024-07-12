import streamlit as st
from PIL import Image, ImageFilter
import fitz  # PyMuPDF
import os
import json
import io

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

# Folder paths
pdf_folder = "PDF_FILES/"
json_folder = "JSON_FILES/"

# Get list of PDF files
pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith('.pdf')]

# Initialize session state for page numbers
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0

# Function to display PDF and convert to image with navigation
def display_pdf_and_convert_to_image(pdf_path):
    images = []
    original_sizes = []
    try:
        doc = fitz.open(pdf_path)
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
col2, col1 = st.columns([6, 4])

# Create the dropdown and display the PDF
with col2:
    st.subheader('Epiklah Expense Document - JSON data', divider='rainbow')
    document_label = st.selectbox("Select Document", options=[""] + pdf_files, index=0)

    if document_label:
        # Load and display PDF as images
        pdf_path = os.path.join(pdf_folder, document_label)
        images, _ = display_pdf_and_convert_to_image(pdf_path)
        if images:
            st.image(images[0], use_column_width=True)
        
        # Score field
        score = st.number_input(label="Score", min_value=0, max_value=100, value=0, step=1)
        
        if st.button("Done and Submit", type="primary"):
            # Collect all form data
            form_data = {
                "Document Label": document_label,
                "Score": score
            }
            
            if document_label:
                json_filename = os.path.splitext(document_label)[0] + ".json"
                json_path = os.path.join(json_folder, json_filename)
                
                if os.path.exists(json_path):
                    with open(json_path, "r") as json_file:
                        json_content = json.load(json_file)
                    form_data["JSON Content"] = json_content
            
            # Write JSON data to a file
            with open('submitted_data.json', 'w') as json_file:
                json.dump(form_data, json_file, indent=4)

            # Provide download button for JSON file
            with open('submitted_data.json', 'r') as json_file:
                json_data = json_file.read()
            st.download_button("Download JSON", json_data, "submitted_data.json", "application/json")
            
            st.success("Data submitted successfully!")

# Display JSON content in the left column with a border
with col1:
    
    st.subheader('JSON Content', divider='rainbow')
    if document_label:
        json_filename = os.path.splitext(document_label)[0] + ".json"
        json_path = os.path.join(json_folder, json_filename)
        
        if os.path.exists(json_path):
            with open(json_path, "r") as json_file:
                json_content = json.load(json_file)

            # Create tabs for different sections
            tabs = st.tabs(["Information Details", "Transaction Details", "Time Deposit Details", "JSON content"])
            
            with tabs[0]:
                st.markdown("### Information Details")
                for i, detail in enumerate(json_content.get("information_details", [])):
                    st.text_input(f"Deposits {i+1}", value=detail["deposits"], key=f"deposits_{i}")
                    st.text_input(f"Account Number {i+1}", value=detail["account_number"], key=f"account_number_{i}")
                    st.text_input(f"OD Limit {i+1}", value=detail["od_limit"], key=f"od_limit_{i}")
                    st.text_input(f"Currency Balance {i+1}", value=detail["currency_balance"], key=f"currency_balance_{i}")
                    st.text_input(f"SGD Balance {i+1}", value=detail["sgd_balance"], key=f"sgd_balance_{i}")

            with tabs[1]:
                subtab = st.selectbox("Select Transaction", options=[f"Transaction {i+1}" for i in range(len(json_content.get("transaction_details", [])))], index=0)
                selected_index = int(subtab.split()[1]) - 1
                
                transaction_detail = json_content.get("transaction_details", [])[selected_index]
                
                st.markdown(f"#### {subtab}")
                for j, transaction in enumerate(transaction_detail.get("transactions", [])):
                    st.text_input(f"Value Date {selected_index+1}.{j+1}", value=transaction["value_date"], key=f"value_date_{selected_index}_{j}")
                    st.text_input(f"Description {selected_index+1}.{j+1}", value=transaction["description"], key=f"description_{selected_index}_{j}")
                    st.text_input(f"Cheque {selected_index+1}.{j+1}", value=transaction["cheque"], key=f"cheque_{selected_index}_{j}")
                    st.text_input(f"Withdrawal {selected_index+1}.{j+1}", value=transaction["withdrawal"], key=f"withdrawal_{selected_index}_{j}")
                    st.text_input(f"Deposit {selected_index+1}.{j+1}", value=transaction["deposit"], key=f"deposit_{selected_index}_{j}")
                    st.text_input(f"Balance {selected_index+1}.{j+1}", value=transaction["balance"], key=f"balance_{selected_index}_{j}")

                st.markdown(f"##### Transaction Summary {selected_index+1}")
                for k, summary in enumerate(transaction_detail.get("transaction_summary", [])):
                    st.text_input(f"Summary Type {selected_index+1}.{k+1}", value=summary["summary_type"], key=f"summary_type_{selected_index}_{k}")
                    st.text_input(f"Withdrawal {selected_index+1}.{k+1}", value=summary["withdrawal"], key=f"summary_withdrawal_{selected_index}_{k}")
                    st.text_input(f"Deposit {selected_index+1}.{k+1}", value=summary["deposit"], key=f"summary_deposit_{selected_index}_{k}")

            with tabs[2]:
                st.markdown("### Time Deposit Details")
                for l, time_deposit in enumerate(json_content.get("time_deposit_details", [])):
                    st.text_input(f"Account Number {l+1}", value=time_deposit["account_number"], key=f"time_deposit_account_number_{l}")
                    st.text_input(f"Deposit {l+1}", value=time_deposit["deposit"], key=f"time_deposit_deposit_{l}")
                    st.text_input(f"Maturity Date {l+1}", value=time_deposit["maturity_date"], key=f"time_deposit_maturity_date_{l}")
                    st.text_input(f"Balance {l+1}", value=time_deposit["balance"], key=f"time_deposit_balance_{l}")
            with tabs[3]:
                st.json(json_content)
        else:
            st.error(f"No JSON file found for {document_label}")
