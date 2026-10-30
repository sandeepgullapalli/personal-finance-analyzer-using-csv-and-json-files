"""
Sample Dataset Generator & Loader
Provides realistic financial datasets in INR (Indian Rupees) for instant testing.
"""

import os
import json

SAMPLE_CHECKING_CSV = """Date,Description,Amount,Account
2026-08-01,EMPLOYER SALARY CREDIT,85000.00,SBI Savings
2026-08-01,APARTMENT RENT PAYMENT,-18000.00,SBI Savings
2026-08-02,DMART GROCERY STORE,-3240.00,SBI Savings
2026-08-03,INDIAN OIL PETROL PUMP,-2200.00,SBI Savings
2026-08-05,ACT BROADBAND INTERNET BILL,-999.00,SBI Savings
2026-08-06,STARBUCKS CAFE KORAMANGALA,-420.00,SBI Savings
2026-08-07,NETFLIX SUBSCRIPTION,-649.00,SBI Savings
2026-08-08,SWIGGY FOOD ORDER,-380.00,SBI Savings
2026-08-10,BESCOM ELECTRICITY BILL,-1850.00,SBI Savings
2026-08-12,BIGBASKET GROCERY,-2180.00,SBI Savings
2026-08-14,CULT FIT GYM MEMBERSHIP,-1999.00,SBI Savings
2026-08-15,EMPLOYER SALARY CREDIT,85000.00,SBI Savings
2026-08-15,ZERODHA INVESTMENT TRANSFER,-15000.00,SBI Savings
2026-08-17,SPOTIFY INDIA,-119.00,SBI Savings
2026-08-18,AMAZON INDIA ORDER,-3450.00,SBI Savings
2026-08-20,OLA RIDE BOOKING,-340.00,SBI Savings
2026-08-22,APOLLO PHARMACY,-890.00,SBI Savings
2026-08-24,MYNTRA ONLINE SHOPPING,-1890.00,SBI Savings
2026-08-27,ZOMATO FOOD ORDER,-680.00,SBI Savings
2026-08-29,RELIANCE FRESH GROCERY,-1850.00,SBI Savings
2026-09-01,EMPLOYER SALARY CREDIT,85000.00,SBI Savings
2026-09-01,APARTMENT RENT PAYMENT,-18000.00,SBI Savings
2026-09-02,DMART GROCERY STORE,-2980.00,SBI Savings
2026-09-04,HP PETROL PUMP,-2400.00,SBI Savings
2026-09-05,ACT BROADBAND INTERNET BILL,-999.00,SBI Savings
2026-09-07,NETFLIX SUBSCRIPTION,-649.00,SBI Savings
2026-09-09,THIRD WAVE COFFEE,-380.00,SBI Savings
2026-09-11,BESCOM ELECTRICITY BILL,-2100.00,SBI Savings
2026-09-13,BIGBASKET GROCERY,-2450.00,SBI Savings
2026-09-14,CULT FIT GYM MEMBERSHIP,-1999.00,SBI Savings
2026-09-15,EMPLOYER SALARY CREDIT,85000.00,SBI Savings
2026-09-15,ZERODHA INVESTMENT TRANSFER,-15000.00,SBI Savings
2026-09-17,SPOTIFY INDIA,-119.00,SBI Savings
2026-09-19,CROMA ELECTRONICS STORE,-12999.00,SBI Savings
2026-09-21,SWIGGY FOOD ORDER,-920.00,SBI Savings
2026-09-24,JIOMART GROCERY,-4200.00,SBI Savings
2026-09-28,RAPIDO BIKE RIDE,-180.00,SBI Savings
2026-10-01,EMPLOYER SALARY CREDIT,85000.00,SBI Savings
2026-10-01,APARTMENT RENT PAYMENT,-18000.00,SBI Savings
2026-10-02,DMART GROCERY STORE,-3100.00,SBI Savings
2026-10-04,INDIAN OIL PETROL PUMP,-2500.00,SBI Savings
2026-10-05,ACT BROADBAND INTERNET BILL,-999.00,SBI Savings
2026-10-07,NETFLIX SUBSCRIPTION,-649.00,SBI Savings
2026-10-10,BESCOM ELECTRICITY BILL,-1650.00,SBI Savings
2026-10-14,CULT FIT GYM MEMBERSHIP,-1999.00,SBI Savings
2026-10-15,EMPLOYER SALARY CREDIT,85000.00,SBI Savings
2026-10-15,ZERODHA INVESTMENT TRANSFER,-15000.00,SBI Savings
2026-10-17,SPOTIFY INDIA,-119.00,SBI Savings
2026-10-18,AMAZON INDIA ORDER,-2280.00,SBI Savings
2026-10-22,FLIPKART SALE ORDER,-3400.00,SBI Savings
2026-10-25,DECATHLON SPORTS STORE,-4500.00,SBI Savings
2026-10-27,CHAI POINT CAFE,-210.00,SBI Savings
"""

SAMPLE_CREDIT_CARD_JSON = {
    "account_name": "HDFC Regalia Credit Card",
    "currency": "INR",
    "transactions": [
        {"timestamp": "2026-08-03", "merchant_name": "Apple One Subscription", "charged_amount": 1100.00, "category_tag": "Subscription"},
        {"timestamp": "2026-08-04", "merchant_name": "IndiGo Airlines Ticket", "charged_amount": 8400.00, "category_tag": "Travel"},
        {"timestamp": "2026-08-07", "merchant_name": "Taj Hotels Bengaluru", "charged_amount": 7200.00, "category_tag": "Lodging"},
        {"timestamp": "2026-08-11", "merchant_name": "Zomato Food Delivery", "charged_amount": 890.00, "category_tag": "Dining"},
        {"timestamp": "2026-08-16", "merchant_name": "Steam PC Games", "charged_amount": 1499.00, "category_tag": "Entertainment"},
        {"timestamp": "2026-08-20", "merchant_name": "Myntra Clothing Sale", "charged_amount": 3200.00, "category_tag": "Shopping"},
        {"timestamp": "2026-08-25", "merchant_name": "Puma India Online Store", "charged_amount": 4800.00, "category_tag": "Shopping"},
        {"timestamp": "2026-08-31", "merchant_name": "Monthly Credit Card Payment", "charged_amount": -27089.00, "category_tag": "Payment"},
        {"timestamp": "2026-09-03", "merchant_name": "Apple One Subscription", "charged_amount": 1100.00, "category_tag": "Subscription"},
        {"timestamp": "2026-09-06", "merchant_name": "Nature's Basket Grocery", "charged_amount": 3600.00, "category_tag": "Groceries"},
        {"timestamp": "2026-09-12", "merchant_name": "Nykaa Beauty Online", "charged_amount": 2100.00, "category_tag": "Shopping"},
        {"timestamp": "2026-09-18", "merchant_name": "Smoke House Deli Restaurant", "charged_amount": 2850.00, "category_tag": "Dining"},
        {"timestamp": "2026-09-22", "merchant_name": "Wildcraft Outdoor Gear", "charged_amount": 4400.00, "category_tag": "Shopping"},
        {"timestamp": "2026-09-30", "merchant_name": "Monthly Credit Card Payment", "charged_amount": -14050.00, "category_tag": "Payment"},
        {"timestamp": "2026-10-03", "merchant_name": "Apple One Subscription", "charged_amount": 1100.00, "category_tag": "Subscription"},
        {"timestamp": "2026-10-08", "merchant_name": "DMart Grocery", "charged_amount": 2700.00, "category_tag": "Groceries"},
        {"timestamp": "2026-10-14", "merchant_name": "BookMyShow Concert Tickets", "charged_amount": 5200.00, "category_tag": "Entertainment"},
        {"timestamp": "2026-10-19", "merchant_name": "MedPlus Pharmacy", "charged_amount": 960.00, "category_tag": "Health"},
        {"timestamp": "2026-10-23", "merchant_name": "Blue Tokai Coffee", "charged_amount": 360.00, "category_tag": "Dining"},
        {"timestamp": "2026-10-26", "merchant_name": "PVR Cinemas", "charged_amount": 780.00, "category_tag": "Entertainment"}
    ]
}

SAMPLE_ARBITRARY_CSV = """Txn_Date;Payee_Vendor;Paid_Out;Paid_In;Notes
01/08/2026;Client Project Payment;;120000.00;Monthly Retainer
03/08/2026;WeWork Coworking Space;9500.00;;Office Desk
05/08/2026;AWS India Cloud;4200.00;;Server Hosting
08/08/2026;Github Pro Plan;750.00;;Developer Tools
12/08/2026;Staples Office Supplies;1200.00;;Printer Cartridge
15/08/2026;Ola Business Rides;840.00;;Client Meeting
18/08/2026;Zoom Pro License;1300.00;;Video Conferencing
22/08/2026;Google Workspace;850.00;;Email Suite
28/08/2026;LinkedIn Premium;3200.00;;Lead Generation
01/09/2026;Client Project Payment;;120000.00;Monthly Retainer
03/09/2026;WeWork Coworking Space;9500.00;;Office Desk
05/09/2026;AWS India Cloud;4800.00;;Server Hosting
08/09/2026;Github Pro Plan;750.00;;Developer Tools
14/09/2026;Dell Monitor Purchase;28000.00;;Hardware
18/09/2026;Zoom Pro License;1300.00;;Video Conferencing
22/09/2026;Google Workspace;850.00;;Email Suite
28/09/2026;LinkedIn Premium;3200.00;;Lead Generation
01/10/2026;Client Project Payment;;120000.00;Monthly Retainer
03/10/2026;WeWork Coworking Space;9500.00;;Office Desk
05/10/2026;AWS India Cloud;4500.00;;Server Hosting
08/10/2026;Github Pro Plan;750.00;;Developer Tools
18/10/2026;Zoom Pro License;1300.00;;Video Conferencing
22/10/2026;Google Workspace;850.00;;Email Suite
"""


def write_sample_files_to_disk(base_dir: str):
    """Write sample datasets to sample_datasets directory if they don't exist."""
    samples_dir = os.path.join(base_dir, "sample_datasets")
    os.makedirs(samples_dir, exist_ok=True)

    csv_path = os.path.join(samples_dir, "sample_checking_statement.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(SAMPLE_CHECKING_CSV.strip())

    json_path = os.path.join(samples_dir, "sample_credit_card_statement.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(SAMPLE_CREDIT_CARD_JSON, f, indent=2)

    arb_path = os.path.join(samples_dir, "sample_arbitrary_format.csv")
    with open(arb_path, "w", encoding="utf-8") as f:
        f.write(SAMPLE_ARBITRARY_CSV.strip())
