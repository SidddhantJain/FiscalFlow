import io, csv
import pandas as pd

# Test unclosed quote at row 649 (classic bank statement issue)
lines = [
    "Tran Date,CHQNO,PARTICULARS,DR,CR,BAL\n"
]
for i in range(1, 648):
    lines.append(f"01-10-2024,-,Regular transaction {i},,100,5000\n")

# Row 649 has an unclosed quote, e.g., in a particular or footer disclaimer
lines.append('02-10-2024,-,"Unclosed quote transaction or disclaimer\n')
lines.append('03-10-2024,-,More data\n')

csv_data = "".join(lines)

print("1. Default pd.read_csv:")
try:
    df = pd.read_csv(io.StringIO(csv_data))
    print("Success:", len(df))
except Exception as e:
    print("Failed:", type(e), e)

print("\n2. With quoting=csv.QUOTE_NONE:")
try:
    df = pd.read_csv(io.StringIO(csv_data), quoting=csv.QUOTE_NONE, on_bad_lines="skip")
    print("Success with QUOTE_NONE! Rows:", len(df))
except Exception as e:
    print("Failed with QUOTE_NONE:", type(e), e)
