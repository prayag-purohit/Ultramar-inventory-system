Prompt:

```
You are tasked with extracting key tabular information from this PDF.

The PDFs are of two types: Beer Store and LCBO invoices.

Return the data strictly as a valid CSV string — no text before or after.
If a column contains text (like Product Description) that may include commas, wrap the content in double quotes ("") to ensure the CSV remains valid and parsable.

UPC should be treated as string

Ensure the output is compatible with pandas.read_csv(). That means:

    Every row must have the same number of comma-separated columns

    If any field is missing or blank, explicitly write "NA"

From each PDF, extract tables that include item, prices, quantity, UPC, and LCBO number if available (you can include all fields if there are extras)
```