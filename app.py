import streamlit as st
from dotenv import load_dotenv
from PIL import Image
import google.generativeai as genai
import os
from io import BytesIO
import base64
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

load_dotenv()

# Configure Google API
os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Function to load Google Gemini model and get response
def get_gemini_response(input, image, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([input, image[0], prompt])
    return response.text

# Function to process uploaded image
def input_image_setup(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        image_parts = [{"mime_type": uploaded_file.type, "data": bytes_data}]
        return image_parts
    else:
        raise FileNotFoundError("No file uploaded")

# Function to calculate total amount for the invoice
def calculate_total(amount, discount, tax):
    discounted_amount = amount - (amount * discount / 100)
    total = discounted_amount + (discounted_amount * tax / 100)
    return round(total, 2)

# Function to generate PDF
def generate_pdf(company_name, billed_to, invoice_number, date, items, amount, discount, tax):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    elements.append(Paragraph(company_name, styles['Title']))
    elements.append(Spacer(1, 24))
    
    invoice_details = [
        f"Invoice #: {invoice_number}",
        f"Date: {date}",
        f"Billed to: {billed_to}"
    ]
    for detail in invoice_details:
        elements.append(Paragraph(detail, styles['Normal']))
    elements.append(Spacer(1, 24))
    
    data = [['Item', 'Quantity', 'Unit Price', 'Total']]
    for item in items:
        data.append([item['name'], item['quantity'], f"Rs.{item['price']:.2f}", f"Rs.{item['quantity'] * item['price']:.2f}"])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    
    elements.append(Spacer(1, 24))
    
    total_styles = getSampleStyleSheet()
    total_styles['Normal'].fontName = 'Helvetica-Bold'
    
    elements.append(Paragraph(f"Subtotal: Rs.{amount:.2f}", total_styles['Normal']))
    elements.append(Paragraph(f"Discount: {discount}%", styles['Normal']))
    elements.append(Paragraph(f"Tax: {tax}%", styles['Normal']))
    elements.append(Paragraph(f"Total: Rs.{calculate_total(amount, discount, tax):.2f}", total_styles['Normal']))
    
    doc.build(elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# Initialize Streamlit app
st.set_page_config(page_title="Invoice and Image Analysis App")

# Create tabs
tab1, tab2, tab3 = st.tabs(["📃Invoice Generator", "✨Ask Invoice", "👋About"])

with tab1:
    st.title("📃Invoice Generator")
    
    company_name = st.text_input("Company Name")
    billed_to = st.text_input("Billed To")
    invoice_number = st.text_input("Invoice Number")
    date = st.date_input("Date")
    currency = "INR"
    
    st.subheader("Items")
    items = []
    for i in range(5):  # Allow up to 5 items
        col1, col2, col3 = st.columns(3)
        with col1:
            item_name = st.text_input(f"Item {i+1} Name", key=f"item_name_{i}")
        with col2:
            quantity = st.number_input(f"Item {i+1} Quantity", min_value=0, value=0, step=1, key=f"quantity_{i}")
        with col3:
            price = st.number_input(f"Item {i+1} Price", min_value=0.0, value=0.0, step=0.01, key=f"price_{i}")
        
        if item_name and quantity > 0 and price > 0:
            items.append({"name": item_name, "quantity": quantity, "price": price})
    
    amount = sum(item['quantity'] * item['price'] for item in items)
    st.write(f"Subtotal: Rs.{amount:.2f}")
    
    discount = st.number_input("Discount (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
    tax = st.number_input("Tax (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
    
    total = calculate_total(amount, discount, tax)
    st.write(f"Total: Rs.{total:.2f}")
    
    if st.button("Generate Invoice"):
        if company_name and billed_to and invoice_number and items:
            pdf = generate_pdf(company_name, billed_to, invoice_number, date, items, amount, discount, tax)
            
            b64_pdf = base64.b64encode(pdf).decode('utf-8')
            href = f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="invoice.pdf">Download Invoice PDF</a>'
            st.markdown(href, unsafe_allow_html=True)
        else:
            st.error("Please fill in all required fields and add at least one item.")

with tab2:
    st.header("✨Ask Invoice")
    
    input_prompt = """
                   You are an expert in understanding invoices.
                   You will receive input images as invoices &
                   you will have to answer questions based on the input image.
                   Note that, you can be flexible with the answers. For example,
                   use understand that the user may use a synonym for any word related to the invoice.
                   
                   If the quesiton does not pertain to the invoice, you can answer with "Please ask a question regarding the invoice. Thanks!".
                   """
    
    input = st.text_input("Input Prompt: ", key="input")
    submit = st.button("Submit")
    uploaded_file = st.file_uploader("Upload invoice (image)", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Preview", width=100)
    
    if submit:
        if uploaded_file is not None:
          with st.spinner('Doing some AI magic...'):
            image_data = input_image_setup(uploaded_file)
            response = get_gemini_response(input_prompt, image_data, input)
            st.subheader("The Response is")
            st.write(response)
            st.balloons()
        else:
            st.error("Please upload an invoice image.")
            
with tab3:
    st.title("About")
    st.write("A free, fast and simple web-based invoice generator and invoice analysis tool. Ideal for small businesses and freelancers.")
    st.divider()
    st.write("Feel free to reach out to me for any queries or feedback.")
    col1, col2 = st.columns(2)
    with col1:
        st.link_button("🧔🏻‍♂️Portfolio website", "https://prabhav.vercel.app/")
    with col2:
        st.link_button("🔗LinkedIn - Profile", "https://www.linkedin.com/in/prabhav-pandey/")