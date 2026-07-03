from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser
import re

app = FastAPI()

# Enable CORS (required by the assignment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvoiceRequest(BaseModel):
    invoice_text: str


def search(patterns, text):
    """Try multiple regex patterns and return the first match."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


def clean_amount(value):
    if value is None:
        return None

    value = (
        value.replace(",", "")
        .replace("Rs.", "")
        .replace("Rs", "")
        .replace("₹", "")
        .replace("$", "")
        .strip()
    )

    try:
        return float(value)
    except:
        return None


@app.post("/extract")
def extract(req: InvoiceRequest):

    text = req.invoice_text

    # ---------------- Invoice Number ----------------

    invoice_no = search([
        r"Invoice\s*(?:No|Number|#)?\.?\s*:?\s*([^\n]+)",
        r"Bill\s*(?:No|Number)?\.?\s*:?\s*([^\n]+)",
        r"Ref(?:erence)?\.?\s*:?\s*([^\n]+)",
    ], text)

    # ---------------- Vendor ----------------

    vendor = search([
        r"Vendor\s*:?\s*([^\n]+)",
        r"Supplier\s*:?\s*([^\n]+)",
        r"Seller\s*:?\s*([^\n]+)",
        r"From\s*:?\s*([^\n]+)",
    ], text)

    # ---------------- Date ----------------

    date_str = search([
        r"Invoice\s*Date\s*:?\s*([^\n]+)",
        r"Date\s*:?\s*([^\n]+)",
        r"Issued\s*:?\s*([^\n]+)",
    ], text)

    iso_date = None

    if date_str:
        try:
            iso_date = parser.parse(date_str).date().isoformat()
        except:
            iso_date = None

    # ---------------- Amount (Subtotal) ----------------

    subtotal = search([
        r"Subtotal.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Sub\s*Total.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Amount\s*Before\s*Tax.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
    ], text)

    # ---------------- Tax ----------------

    tax = search([
        r"(?:GST|CGST|SGST|IGST|VAT|Tax).*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
    ], text)

    # ---------------- Currency ----------------

    currency = search([
        r"Currency\s*:?\s*([A-Z]{3})"
    ], text)

    if currency is None:
        if "₹" in text or "Rs" in text:
            currency = "INR"
        elif "$" in text:
            currency = "USD"
        elif "€" in text:
            currency = "EUR"
        elif "£" in text:
            currency = "GBP"

    # ---------------- Response ----------------

    return {
        "invoice_no": invoice_no,
        "date": iso_date,
        "vendor": vendor,
        "amount": clean_amount(subtotal),
        "tax": clean_amount(tax),
        "currency": currency,
    }