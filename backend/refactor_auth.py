import os
import re

api_dir = r"C:\Users\Lenovo\Desktop\DigitalRakshak\backend\api\v1"

for root, _, files in os.walk(api_dir):
    for file in files:
        if file.endswith(".py") and file != "users.py":
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            
            # Replace imports
            content = re.sub(r'from api\.v1\.users import.*get_current_user_token.*', 'from api.deps import get_current_user, get_current_admin\nfrom domain.models.user import User', content)
            content = re.sub(r'from api\.v1\.users import.*get_current_admin.*', 'from api.deps import get_current_user, get_current_admin\nfrom domain.models.user import User', content)
            
            # Cases.py specifically defines get_current_user_token
            if file == "cases.py":
                content = re.sub(r'async def get_current_user_token.*?return payload', '', content, flags=re.DOTALL)
                content = content.replace("from api.v1.users import get_current_admin", "from api.deps import get_current_user, get_current_admin\nfrom domain.models.user import User")
                # Remove oauth2_scheme if it's there
                # content = re.sub(r'oauth2_scheme = OAuth2PasswordBearer\(.*?login"\)', '', content)

            # Replace Depends(get_current_user_token) -> Depends(get_current_user)
            content = content.replace("get_current_user_token", "get_current_user")
            
            # Replace user_payload: dict -> user: User
            content = content.replace("user_payload: dict", "user: User")
            
            # Replace user_payload.get("sub") -> str(user.id)
            content = content.replace('user_payload.get("sub")', 'str(user.id)')
            
            # Replace user_payload.get("role") -> user.role
            content = content.replace('user_payload.get("role")', 'user.role')
            
            # In cases where they pass user_payload to something that expects a dict?
            # E.g., user_payload -> user if it's just passing it around, or we might need to be careful.
            
            if content != original_content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Updated {file}")

