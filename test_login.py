import urllib.request, urllib.error, json

req = urllib.request.Request(
    'https://frontend-chi-lemon-78.vercel.app/api/v1/auth/login-password',
    data=json.dumps({
        "email": "harshit2005sharma@gmail.com",
        "password": "Welcome@2029"
    }).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    res = urllib.request.urlopen(req)
    print("Success:", res.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTPError {e.code}: {e.read().decode()}")
