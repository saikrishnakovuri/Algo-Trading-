from SmartApi.smartConnect import SmartConnect
import pyotp

api_key = "2ySP2Eop"
client_id = "K256728"
password = "8106"
totp = pyotp.TOTP("KJYIZLEKPADIT6KNUGX2QBM6TQ").now()

obj = SmartConnect(api_key=api_key)
data = obj.generateSession(client_id, password, totp)

print(data)