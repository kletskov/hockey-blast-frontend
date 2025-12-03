#!/usr/bin/env python3
"""
Generate QR codes for Sharks Ice rink locations
"""
import qrcode
import os

# Sharks Ice rinks from location.py
sharks_ice_rinks = [
    {"id": 14, "name": "Black"},
    {"id": 8, "name": "Grey"},
    {"id": 18, "name": "Orange"},
    {"id": 1, "name": "Sharks"},
    {"id": 13, "name": "Tech CU"},
    {"id": 35, "name": "White"},
]

# Base URL
base_url = "https://hockey-blast.com/location/qr_location_redirect?id="

# Create output directory if it doesn't exist
output_dir = "qr_codes"
os.makedirs(output_dir, exist_ok=True)

# Generate QR codes
for rink in sharks_ice_rinks:
    url = f"{base_url}{rink['id']}"
    filename = f"{output_dir}/{rink['name'].replace(' ', '_')}_rink_id_{rink['id']}.png"

    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Create an image
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)

    print(f"Generated QR code for {rink['name']} Rink (ID: {rink['id']})")
    print(f"  URL: {url}")
    print(f"  File: {filename}")
    print()

print(f"All QR codes saved to '{output_dir}/' directory")
