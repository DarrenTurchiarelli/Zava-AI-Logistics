"""Test city extraction logic"""
address = "123 George Street, Sydney CBD, Sydney NSW 2000"
print(f"Address: {address}")
parts = address.split(",")
print(f"Parts: {parts}")
print(f"Last part: '{parts[-1]}'")
city_state_postcode = parts[-1].strip().split()
print(f"Split last part: {city_state_postcode}")
print(f"Extracted city: {city_state_postcode[0] if city_state_postcode else 'None'}")
