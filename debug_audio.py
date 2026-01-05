import sounddevice as sd
try:
    print("Querying devices...")
    print(sd.query_devices())
    print("Host APIs:")
    print(sd.query_hostapis())
    print("Success")
except Exception as e:
    print(f"Error: {e}")
