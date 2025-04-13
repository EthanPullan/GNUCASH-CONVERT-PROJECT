import csv
import re
from tkinter import Tk, filedialog
import os
from tabulate import tabulate
from collections import defaultdict

# Default accounts
DEFAULT_CASH_ACCOUNT = "Assets:Investments:FHSA's:WS Managed"
DEFAULT_DIVIDEND_ACCOUNT = "Income:Dividend Income:FHSA"
DEFAULT_FEE_ACCOUNT = "Expenses:Fees and Charges:Financial Charges (Investing)"

def parse_transaction(row, cash_account, dividend_account, fee_account, txn_id):
    date, ttype, desc, amount = row[:4]
    amount = float(amount)
    entries = []

    # Extract symbol
    symbol_match = re.match(r"([A-Z]+) -", desc)
    symbol = symbol_match.group(1) if symbol_match else "UNKNOWN"
    stock_account = f"{cash_account}:{symbol}"

    if ttype == "DIV":
        entries.append([date, f"Dividend {symbol}", dividend_account, "", "", -amount, ttype, txn_id, "div"])
        entries.append([date, f"Dividend {symbol}", cash_account, "", "", amount, ttype, txn_id, "cash"])
        entries.append([date, f"Dividend {symbol}", stock_account, "", "", 0.00, ttype, txn_id, "stock"])

    elif ttype in ["FEE", "NRT"]:
        # Use a clearer description for NRT
        label = "Non-Resident Tax Fee" if ttype == "NRT" else "Investment Fee"
        entries.append([date, label, fee_account, "", "", abs(amount), ttype, txn_id, "fee"])
        entries.append([date, label, cash_account, "", "", -abs(amount), ttype, txn_id, "cash"])

    elif ttype == "BUY":
        share_match = re.search(r"([\d.]+) shares", desc)
        shares = float(share_match.group(1)) if share_match else 0.0
        price = abs(amount) / abs(shares) if shares else 0.0

        entries.append([date, f"{ttype} {symbol}", stock_account, shares, round(price, 4), abs(amount), ttype, txn_id, "buy"])
        entries.append([date, f"{ttype} {symbol}", cash_account, "", "", amount, ttype, txn_id, "cash"])

    elif ttype == "SELL":
        share_match = re.search(r"([\d.]+) shares", desc)
        shares = float(share_match.group(1)) if share_match else 0.0
        price = abs(amount) / abs(shares) if shares else 0.0

        entries.append([date, f"{ttype} {symbol}", stock_account, -shares, round(price, 4), abs(amount), ttype, txn_id, "sell"])
        entries.append([date, f"{ttype} {symbol}", cash_account, "", "", amount, ttype, txn_id, "cash"])

    return entries

def convert_csv(input_file, output_file, cash_account, dividend_account, fee_account):
    all_entries = []
    txn_counters = defaultdict(int)

    with open(input_file, newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header
        for row in reader:
            if len(row) < 4:
                print(f"Skipping malformed row: {row}")
                continue
            try:
                date = row[0]
                txn_counters[date] += 1
                txn_id = f"TXN-{date.replace('-', '')}-{txn_counters[date]:03d}"
                all_entries.extend(parse_transaction(row[:4], cash_account, dividend_account, fee_account, txn_id))
            except Exception as e:
                print(f"Error on row: {row}\n{e}")

    # Write output
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Date", "Description", "Account", "Num.Shares", "Price", "Amount", "Type", "TransactionID", "Action"])
        writer.writerows(all_entries)

    # Show output in terminal
    print("\nConverted Transactions:")
    print(tabulate(all_entries, headers=["Date", "Description", "Account", "Num.Shares", "Price", "Amount", "Type", "TransactionID", "Action"], tablefmt="grid"))

def main():
    root = Tk()
    root.withdraw()  # Hide Tkinter window

    input_path = filedialog.askopenfilename(
        title="Select Input CSV File",
        filetypes=[("CSV files", "*.csv")]
    )
    if not input_path:
        print("❌ No file selected.")
        return

    # Prompt user for accounts with defaults
    user_cash = input(f"Enter your brokerage cash account [default: {DEFAULT_CASH_ACCOUNT}]: ").strip()
    cash_account = user_cash if user_cash else DEFAULT_CASH_ACCOUNT

    user_div = input(f"Enter your dividend income account [default: {DEFAULT_DIVIDEND_ACCOUNT}]: ").strip()
    dividend_account = user_div if user_div else DEFAULT_DIVIDEND_ACCOUNT

    user_fee = input(f"Enter your fee expense account [default: {DEFAULT_FEE_ACCOUNT}]: ").strip()
    fee_account = user_fee if user_fee else DEFAULT_FEE_ACCOUNT

    output_path = os.path.splitext(input_path)[0] + "_gnucash.csv"
    convert_csv(input_path, output_path, cash_account, dividend_account, fee_account)
    print(f"\n✅ Converted file saved to:\n{output_path}")

if __name__ == "__main__":
    main()
