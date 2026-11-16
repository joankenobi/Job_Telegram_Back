import base64

entoded_comand = "UwB0AGEAcgB0ACAAIgBoAHQAdABwADoALwAvADEAMgA3AC4AMAAuADAALgAxADoANAAwADkANgAvACIA"

try:
    decode_bytes = base64.b64decode(entoded_comand)

    decode_script = decode_bytes.decode("utf-16le")

    print(decode_script)

except Exception as e:
    print(e)
