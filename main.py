from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser
import re

app = FastAPI()

# CORS (required)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvoiceRequest(BaseModel):
    invoice_text: str


def clean_amount(value):
    if value is None:
        return None

    value = value.replace(",", "")
    value = value.replace("Rs.", "")
    value = value.replace("Rs", "")
    value = value.replace("₹", "")
    value = value.strip()

    try:
        return float(value)
    except:
        return None


def search(patterns, text):
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


@app.post("/extract")
def extract(req: InvoiceRequest):

    text = req.invoice_text

    invoice_no = search([
        r"Invoice No:\s*(.+)",
        r"Invoice\s*#:\s*(.+)",
        r"Ref:\s*(.+)"
    ], text)

    vendor = search([
        r"Vendor:\s*(.+)",
        r"Supplier:\s*(.+)"
    ], text)

    date_str = search([
        r"Date:\s*(.+)",
        r"Issued:\s*(.+)"
    ], text)

    subtotal = search([
        r"Subtotal.*?Rs\.?\s*([\d,]+\.\d+)",
        r"Subtotal.*?₹\s*([\d,]+\.\d+)"
    ], text)

    tax = search([
        r"(?:GST|CGST|SGST|IGST).*?Rs\.?\s*([\d,]+\.\d+)",
        r"(?:GST|CGST|SGST|IGST).*?₹\s*([\d,]+\.\d+)"
    ], text)

    currency = search([
        r"Currency:\s*([A-Z]{3})"
    ], text)

    if currency is None:
        if "Rs" in text or "₹" in text:
            currency = "INR"

    iso_date = None

    if date_str:
        try:
            iso_date = parser.parse(date_str).date().isoformat()
        except:
            pass

    return {
        "invoice_no": invoice_no,
        "date": iso_date,
        "vendor": vendor,
        "amount": clean_amount(subtotal),
        "tax": clean_amount(tax),
        "currency": currency
    }