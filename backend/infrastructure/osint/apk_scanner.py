import os
from typing import Dict, Any

class APKScanner:
    """
    Malicious APK static analysis scanner.
    Uses androguard to parse AndroidManifest.xml and flag highly dangerous permissions
    commonly used by Banking Trojans and SMS stealers.
    """
    
    # Permissions commonly abused by Android malware
    DANGEROUS_PERMISSIONS = {
        "android.permission.RECEIVE_SMS": "Can intercept incoming SMS (used for OTP stealing).",
        "android.permission.READ_SMS": "Can read all stored SMS messages.",
        "android.permission.SEND_SMS": "Can send SMS in the background (used for premium SMS fraud).",
        "android.permission.BIND_ACCESSIBILITY_SERVICE": "Can control the screen, log keystrokes, and bypass UI security (Overlay attacks).",
        "android.permission.READ_CONTACTS": "Can steal the victim's contact list.",
        "android.permission.CALL_PHONE": "Can make phone calls without user interaction.",
        "android.permission.SYSTEM_ALERT_WINDOW": "Can draw over other apps (used for Phishing overlays).",
        "android.permission.RECEIVE_BOOT_COMPLETED": "Malware persistence (starts on device boot)."
    }

    def scan_apk(self, file_path: str) -> Dict[str, Any]:
        """
        Analyzes an APK file and returns its threat profile based on requested permissions.
        """
        try:
            from androguard.core.bytecodes.apk import APK
            
            # Parse the APK binary
            a = APK(file_path)
            
            app_name = a.get_app_name()
            package_name = a.get_package()
            requested_permissions = a.get_permissions()
            
            flagged_permissions = []
            for perm in requested_permissions:
                if perm in self.DANGEROUS_PERMISSIONS:
                    flagged_permissions.append({
                        "permission": perm,
                        "threat": self.DANGEROUS_PERMISSIONS[perm]
                    })
                    
            risk_level = "LOW"
            if len(flagged_permissions) > 0:
                risk_level = "HIGH"
            if "android.permission.BIND_ACCESSIBILITY_SERVICE" in requested_permissions or "android.permission.RECEIVE_SMS" in requested_permissions:
                risk_level = "CRITICAL"
                
            return {
                "is_malicious": risk_level == "CRITICAL",
                "app_name": app_name,
                "package_name": package_name,
                "risk_level": risk_level,
                "flagged_permissions": flagged_permissions,
                "total_permissions": len(requested_permissions)
            }
            
        except Exception as e:
            print(f"APK Parsing failed: {str(e)}")
            return {
                "is_malicious": False,
                "app_name": "Unknown",
                "package_name": "Unknown",
                "risk_level": "UNKNOWN",
                "flagged_permissions": [],
                "error": str(e)
            }
