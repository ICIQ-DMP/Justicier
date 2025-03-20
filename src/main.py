import re
import os

from pypdf import PdfReader, PdfWriter
import pypdf


def get_matching_page(pdf_path: str, naf: str) -> pypdf.PageObject:
    # Open PDF
    reader = PdfReader(pdf_path)

    # Define regex pattern to search for "NN/NNNNNNNN-NN" and extract SS number
    pattern = re.compile(r"\d{2}/\d{8}-\d{2}")

    for page_num, page in enumerate(reader.pages):
        # Get text of the page
        text = page.extract_text()

        if not text:
            continue

        match = pattern.search(text)
        if not match:
            continue

        ss_number = match.group(0)  # TODO: ensure only one match per page, error otherwise
        if ss_number.__eq__(naf):
            return page

    raise ValueError("The NAF " + naf + " can't be found in the PDF")


def write_page(page: pypdf.PageObject, naf):
    # Create a new PDF with only this page
    writer = PdfWriter()
    writer.add_page(page)

    naf_clean = naf.replace("/", "").replace("-", "")

    with open("output/" + naf_clean + ".pdf", "wb+") as output_pdf:
        writer.write(output_pdf)
    pass


# Load NAF numbers from file
with open("input/NAFs.txt", "r", encoding="utf-8") as f:
    naf_numbers = [line.strip() for line in f]

salaries_file = open("input/Salaries.pdf")

# Ensure output directory exists
os.makedirs("output", exist_ok=True)

for naf in naf_numbers:
    print("looking for " + naf)
    page = get_matching_page("input/Salaries.pdf", naf)
    write_page(page, naf)


