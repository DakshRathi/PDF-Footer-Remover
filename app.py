import pymupdf as fitz
import streamlit as st
import tempfile
from pathlib import Path

st.set_page_config(page_title="PDF Footer Remover - Batch", layout="centered")

st.title("📄 PDF Footer Remover")
st.markdown("""
This app removes footer text from the bottom of every page in your PDF(s).  
Use the **Height from Bottom** slider to fine-tune how much area is removed.
""")

# Initialize session state
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = {} 
if 'preview_images' not in st.session_state:
    st.session_state.preview_images = {}  

# --- File Upload ---
uploaded_files = st.file_uploader("Upload your PDF files", type=["pdf"], accept_multiple_files=True)

footer_height = st.number_input(
    "Height from bottom to remove (in points)",
    min_value=10,
    max_value=200,
    value=60,
    help="Try 60–90 if the footer text is large. 1cm = 60 points"
)

def redact_footer_fixed_position(input_path: str, output_path: str, footer_height: float):
    doc = fitz.open(input_path)

    for page in doc:
        width, height = page.rect.width, page.rect.height

        footer_rect = fitz.Rect(
            0,
            height - footer_height,
            width,
            height
        )

        page.add_redact_annot(footer_rect, fill=(1, 1, 1))
        page.apply_redactions()

    doc.save(output_path, deflate=True, garbage=4, clean=True)
    doc.close()

# Process button
if uploaded_files and st.button("Remove Footer from All PDFs"):
    st.session_state.processed_files = {}  # Clear previous results
    st.session_state.preview_images = {}
    
    for uploaded_file in uploaded_files:
        original_name = uploaded_file.name
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_input:
            temp_input.write(uploaded_file.read())
            temp_input_path = temp_input.name

        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name

        with st.spinner(f"Processing {original_name}..."):
            redact_footer_fixed_position(temp_input_path, output_path, footer_height)

        # Store in session state
        st.session_state.processed_files[original_name] = output_path
        
        # Generate and store previews
        preview_paths = []
        try:
            doc = fitz.open(output_path)
            num_pages = min(3, len(doc))  # Display up to 3 pages as per your query
            
            for page_num in range(num_pages):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=150)
                img_path = Path(tempfile.gettempdir()) / f"preview_{original_name}_{page_num}.png"
                pix.save(str(img_path))
                preview_paths.append(str(img_path))
            doc.close()
        except Exception as e:
            st.error(f"Couldn't generate previews for {original_name}: {e}")
            preview_paths = []
        
        st.session_state.preview_images[original_name] = preview_paths

# Display results from session state (persists across re-runs)
if st.session_state.processed_files:
    for original_name, output_path in st.session_state.processed_files.items():
        st.markdown(f"### Processed: {original_name}")

        # Download button (uses stored path)
        try:
            with open(output_path, "rb") as f:
                st.download_button(
                    label=f"📥 Download Cleaned PDF: {original_name}",
                    data=f,
                    file_name=f"footer_removed_{original_name}",
                    mime="application/pdf"
                )
        except FileNotFoundError:
            st.warning(f"Output file for {original_name} not found. Please re-process.")

        # Display preview from stored image paths
        st.subheader(f"📄 Preview of cleaned PDF (first 3 pages): {original_name}")
        
        preview_paths = st.session_state.preview_images.get(original_name, [])
        if preview_paths:
            with st.container():
                for idx, img_path in enumerate(preview_paths):
                    st.image(img_path, caption=f"Page {idx+1}", use_container_width=True)
        else:
            st.info("No previews available for this file.")
else:
    if uploaded_files:
        st.info("Click 'Remove Footer from All PDFs' to process your files.")

# Optional: Button to clear session state and reset
if st.button("Clear Processed Files"):
    st.session_state.processed_files = {}
    st.session_state.preview_images = {}
    st.rerun()
