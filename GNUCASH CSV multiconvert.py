import csv
import re
import os
import json
from tkinter import Tk, filedialog
from tabulate import tabulate
from datetime import datetime

def load_config(config_path="config.json"):
    if not os.path.exists(config_path):
        print(f"⚠️ Config file '{config_path}' not found. Using internal defaults.")
        return {}
    with open(config_path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"❌ Failed to parse config file '{config_path}'.")
            return {}

# Load defaults from config
config = load_config()

DEFAULT_CASH_ACCOUNT = config.get("cash_account", "Assets:Investments:FHSA's:WS Managed")
DEFAULT_DIVIDEND_ACCOUNT = config.get("dividend_account", "Income:Dividend Income:FHSA")
DEFAULT_FEE_ACCOUNT = config.get("fee_account", "Expenses:Fees and Charges:Financial Charges (Investing)")
DEFAULT_CONTRIBUTION_ACCOUNT = config.get("contribution_account", "Imbalance-CAD")

def parse_transaction(row, cash_account, dividend_account, fee_account, all_dates):
    date, ttype, desc, amount = row[:4]

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        print(f"⚠️ Skipping transaction with invalid or missing amount: {row}")
        return []
    if amount == 0:
        print(f"⚠️ Skipping {ttype} transaction with $0 amount: {row}")
        return []

    all_dates.append(date)
    entries = []

    # Extract and normalize symbol
    symbol_match = re.match(r"([\w\.\-]+) -", desc)
    raw_symbol = symbol_match.group(1) if symbol_match else "UNKNOWN"
    symbol = re.split(r"[.\-]", raw_symbol)[0]
    stock_account = f"{cash_account}:{symbol}"

    if ttype == "DIV":
        entries.append([date, f"Dividend {symbol}", dividend_account, "", "", -amount, "DIV"])   # Credit income
        entries.append([date, f"Dividend {symbol}", cash_account, "", "", amount, "CASH"])       # Debit cash
        entries.append([date, f"Dividend {symbol}", stock_account, "", "", 0.00, "STOCK"])       # $0 entry in stock register


    elif ttype == "FEE":
        if amount < 0:
            entries.append([date, "Investment Fee", fee_account, "", "", abs(amount), "FEE"])
            entries.append([date, "Investment Fee", cash_account, "", "", -abs(amount), "CASH"])
        else:
            entries.append([date, "Fee Rebate", cash_account, "", "", abs(amount), "CASH"])
            entries.append([date, "Fee Rebate", fee_account, "", "", -abs(amount), "FEE"])

    elif ttype == "CONT":
        entries.append([date, "Contribution", cash_account, "", "", abs(amount), "CASH"])
        entries.append([date, "Contribution", DEFAULT_CONTRIBUTION_ACCOUNT, "", "", -abs(amount), "CONT"])

    elif ttype in ["BUY", "SELL"]:
        share_match = re.search(r"([\d.]+) shares", desc)
        shares = float(share_match.group(1)) if share_match else 0.0
        shares = -shares if ttype == "SELL" else shares
        price = abs(amount) / abs(shares) if shares else 0.0

        entries.append([date, f"{ttype} {symbol}", stock_account, shares, round(price, 4), abs(amount), ttype])

        cash_amount = -abs(amount) if ttype == "BUY" else abs(amount)
        entries.append([date, f"{ttype} {symbol}", cash_account, "", "", cash_amount, "CASH"])

    else:
        print(f"⚠️ Unhandled transaction type '{ttype}' on row: {row}")

    return entries

def convert_multiple_csvs(input_files, output_dir, cash_account, dividend_account, fee_account):
    all_entries = []
    all_dates = []
    txn_counter_per_date = {}

    for file in input_files:
        with open(file, newline='') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header
            for row in reader:
                if len(row) < 4:
                    print(f"⚠️ Skipping malformed row in {file}: {row}")
                    continue
                try:
                    txn_entries = parse_transaction(row[:4], cash_account, dividend_account, fee_account, all_dates)
                    if txn_entries:
                        date = txn_entries[0][0]
                        txn_counter_per_date.setdefault(date, 0)
                        txn_counter_per_date[date] += 1
                        txn_id = f"TRX-{date}-{txn_counter_per_date[date]:03d}"

                        for entry in txn_entries:
                            all_entries.append(entry + [txn_id])
                except Exception as e:
                    print(f"❌ Error in {file} on row: {row}\n{e}")

    if not all_entries:
        print("❌ No transactions found.")
        return

    all_entries.sort(key=lambda x: x[0])  # Sort by date
    all_dates.sort()
    start_date = datetime.strptime(all_dates[0], "%Y-%m-%d").date()
    end_date = datetime.strptime(all_dates[-1], "%Y-%m-%d").date()
    output_filename = f"gnucash_{start_date}_to_{end_date}.csv"
    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Date", "Description", "Account", "Num.Shares", "Price", "Amount", "Type", "Transaction ID"])
        writer.writerows(all_entries)

    print("\nConverted Transactions:")
    print(tabulate(all_entries, headers=["Date", "Description", "Account", "Num.Shares", "Price", "Amount", "Type", "Transaction ID"], tablefmt="grid"))
    print(f"\n✅ Saved to:\n{output_path}")

def main():
    root = Tk()
    root.withdraw()

    input_paths = filedialog.askopenfilenames(
        title="Select Input CSV Files",
        filetypes=[("CSV files", "*.csv")]
    )
    if not input_paths:
        print("❌ No files selected.")
        return

    user_cash = input(f"Enter your brokerage cash account [default: {DEFAULT_CASH_ACCOUNT}]: ").strip()
    cash_account = user_cash if user_cash else DEFAULT_CASH_ACCOUNT

    user_div = input(f"Enter your dividend income account [default: {DEFAULT_DIVIDEND_ACCOUNT}]: ").strip()
    dividend_account = user_div if user_div else DEFAULT_DIVIDEND_ACCOUNT

    user_fee = input(f"Enter your investment fee account [default: {DEFAULT_FEE_ACCOUNT}]: ").strip()
    fee_account = user_fee if user_fee else DEFAULT_FEE_ACCOUNT

    convert_multiple_csvs(input_paths, os.path.dirname(input_paths[0]), cash_account, dividend_account, fee_account)

if __name__ == "__main__":
    main()
