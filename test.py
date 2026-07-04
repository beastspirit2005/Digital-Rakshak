import urllib.request, urllib.error, json

req = urllib.request.Request(
    'http://localhost:8000/v1/auth/request-otp',
    data=json.dumps({"email": "harshit2005sharma@gmail.com"}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    res = urllib.request.urlopen(req)
    print("Success:", res.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTPError {e.code}: {e.reason}")
    print(e.read().decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
