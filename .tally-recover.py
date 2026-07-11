"""
Tally password recovery helper.
1. Fetches the service_role key from the Supabase Management API.
2. Lists all users, generates a recovery link for the specified email.
Usage: python .tally-recover.py [email]
"""
import json, os, sys, urllib.request, urllib.error

PROJECT_REF = "tvyqpewyxbisclkahnte"
PROJECT_URL = f"https://{PROJECT_REF}.supabase.co"
PAT = open(os.path.expanduser('~/.supabase-pat')).read().strip()

def req(method, url, headers, body=None):
    r = urllib.request.Request(
        url, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or '{}')
        except Exception:
            return e.code, {"raw": e.read().decode()}

mgmt_h = {
    "Authorization": f"Bearer {PAT}",
    "User-Agent": "tally-cli/1.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

print("== Fetching service_role key ==")
status, keys = req("GET", f"https://api.supabase.com/v1/projects/{PROJECT_REF}/api-keys", mgmt_h)
if status != 200:
    print(f"  HTTP {status}: {keys}"); sys.exit(1)
srv = next((k for k in keys if k.get('name') == 'service_role'), None)
if not srv:
    print(f"  no service_role in {keys}"); sys.exit(1)
SRV = srv['api_key']
print("  ✓ got service_role")

admin_h = {
    "apikey": SRV,
    "Authorization": f"Bearer {SRV}",
    "User-Agent": "tally-cli/1.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

print("\n== Users ==")
status, users = req("GET", f"{PROJECT_URL}/auth/v1/admin/users?page=1&per_page=100", admin_h)
if status != 200:
    print(f"  HTTP {status}: {users}"); sys.exit(1)

user_list = users.get('users', users) if isinstance(users, dict) else users
for u in user_list:
    print(f"  - {u.get('email')}  confirmed_at={u.get('email_confirmed_at')}  last_sign_in={u.get('last_sign_in_at')}")

target_email = sys.argv[1].strip() if len(sys.argv) > 1 else None
if target_email:
    pick = next((u for u in user_list if (u.get('email') or '').lower() == target_email.lower()), None)
elif len(user_list) == 1:
    pick = user_list[0]
else:
    print("\nMultiple users. Pass an email as an argument."); sys.exit(0)

if not pick:
    print(f"\nNo user matches '{target_email}'."); sys.exit(1)

print(f"\n== Generating recovery link for {pick.get('email')} ==")
status, link = req(
    "POST",
    f"{PROJECT_URL}/auth/v1/admin/generate_link",
    admin_h,
    body={
        "type": "recovery",
        "email": pick['email'],
        "options": {"redirect_to": "https://tally.greenfield.build/"},
    },
)
if status == 200:
    props = link.get('properties') or link
    action = props.get('action_link') or link.get('action_link')
    print(f"\n  ✓ CLICK THIS LINK to reset password:")
    print(f"  {action}")
else:
    print(f"  HTTP {status}: {link}")
