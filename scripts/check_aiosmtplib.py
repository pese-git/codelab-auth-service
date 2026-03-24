import aiosmtplib
print("Available exceptions:")
for attr in dir(aiosmtplib):
    if "Error" in attr or "Exception" in attr:
        print(f"  - {attr}")
