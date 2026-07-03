from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser
import re

app = FastAPI()

# Enable CORS
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
    """Convert strings like 'Rs. 1,40,000.00' to float."""
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


def extract_line_value(text, labels):
    """
    Find a line beginning with one of the labels and
    return everything after ':'.
    """
    for line in text.splitlines():
        line = line.strip()

        for label in labels:
            if re.match(rf"^{label}\s*:?", line, re.IGNORECASE):
                value = re.sub(rf"^{label}\s*:?\s*", "", line, flags=re.IGNORECASE)
                return value.strip()

    return None


@app.post("/extract")
def extract(req: InvoiceRequest):

    text = req.invoice_text

    # ---------------- Invoice Number ----------------

    invoice_no = extract_line_value(
        text,
        [
            r"Invoice No\.?",
            r"Invoice Number",
            r"Invoice #",
            r"Invoice",
            r"Bill No\.?",
            r"Bill Number",
            r"Ref",
            r"Reference",
        ],
    )

    # ---------------- Vendor ----------------

    vendor = extract_line_value(
        text,
        [
            r"Vendor",
            r"Supplier",
            r"Seller",
            r"From",
        ],
    )

    # ---------------- Date ----------------

    date_str = extract_line_value(
        text,
        [
            r"Invoice Date",
            r"Date",
            r"Issued",
        ],
    )

    iso_date = None
    if date_str:
        try:
            iso_date = parser.parse(date_str).date().isoformat()
        except:
            iso_date = None

    # ---------------- Amount ----------------

    subtotal = None

    subtotal_patterns = [
        r"Subtotal.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Sub\s*Total.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
        r"Amount\s*Before\s*Tax.*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
    ]

    for pattern in subtotal_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            subtotal = m.group(1)
            break

    # ---------------- Tax ----------------

    tax = None

    tax_patterns = [
        r"(?:GST|CGST|SGST|IGST|VAT|Tax).*?(?:Rs\.?|₹|\$)?\s*([\d,]+(?:\.\d+)?)",
    ]

    for pattern in tax_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            tax = m.group(1)
            break

    # ---------------- Currency ----------------

    currency = extract_line_value(
        text,
        [
            r"Currency",
        ],
    )

    if currency is None:
        if "₹" in text or "Rs" in text:
            currency = "INR"
        elif "$" in text:
            currency = "USD"
        elif "€" in text:
            currency = "EUR"
        elif "£" in text:
            currency = "GBP"

    return {
        "invoice_no": invoice_no,
        "date": iso_date,
        "vendor": vendor,
        "amount": clean_amount(subtotal),
        "tax": clean_amount(tax),
        "currency": currency,
    }