import streamlit as st
from PIL import Image, ImageFilter
import fitz  # PyMuPDF
import os
import json
import io

st.set_page_config(layout="wide", page_title="")

# Custom CSS to hide Streamlit elements
st.markdown("""
    <style>
        /* Hide Streamlit header, footer, and burger menu */
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .css-1rs6os.edgvbvh3 {visibility: hidden;} /* This targets the "Fork me on GitHub" ribbon */
        .css-15tx938.egzxvld1 {visibility: hidden;} /* This targets the GitHub icon in the menu */
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
    st.subheader('Epiklah Expense Document', divider='rainbow')
    document_label = st.selectbox("Select Document", options=[""] + pdf_files, index=0)

    if document_label:
        # Load and display PDF as images
        pdf_path = os.path.join(pdf_folder, document_label)
        images, _ = display_pdf_and_convert_to_image(pdf_path)
        if images:
            st.image(images[0], use_column_width=True)
        
        # Score field
        score = st.number_input(label="Score", min_value=0, max_value=10, value=0, step=1)
        
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

# Display JSON content in the left column
with col1:
    st.subheader('JSON Content', divider='rainbow')
    if document_label:
        json_filename = os.path.splitext(document_label)[0] + ".json"
        json_path = os.path.join(json_folder, json_filename)
        
        if os.path.exists(json_path):
            with open(json_path, "r") as json_file:
                json_content = json.load(json_file)
                st.json(json_content)
        else:
            st.error(f"No JSON file found for {document_label}")
