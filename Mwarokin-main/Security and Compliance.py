# security.py
from typing import Dict, Any, Optional
import jwt
from datetime import datetime, timedelta
import hashlib
import secrets

class SecurityManager:
    def __init__(self, secret_key: str, os_instance):
        self.secret_key = secret_key
        self.os = os_instance
        self.token_blacklist = set()
    
    def generate_token(self, tenant_id: str, permissions: Dict[str, Any]) -> str:
        """Generate a JWT token for a tenant"""
        payload = {
            "tenant_id": tenant_id,
            "permissions": permissions,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a JWT token and return the payload if valid"""
        try:
            if token in self.token_blacklist:
                return None
                
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token by adding it to the blacklist"""
        self.token_blacklist.add(token)
        return True
    
    def authorize_operation(self, tenant_id: str, operation: str, resource: Any) -> bool:
        """Check if a tenant is authorized to perform an operation on a resource"""
        # Check if the resource belongs to the tenant
        if hasattr(resource, 'tenant_id') and resource.tenant_id != tenant_id:
            return False
        
        # Additional authorization checks based on operation type
        if operation == "read":
            return True  # Most tenants can read their own resources
        
        if operation == "write":
            # Check if tenant is in good standing
            tenant = self.os.tenants.get(tenant_id)
            if tenant and tenant.status != TenantStatus.ACTIVE:
                return False
        
        if operation == "delete":
            # More restrictive permissions for deletion
            tenant = self.os.tenants.get(tenant_id)
            if not tenant or tenant.subscription_tier not in ["professional", "enterprise"]:
                return False
        
        return True
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        # In a real implementation, use a proper encryption library
        salt = secrets.token_bytes(16)
        derived_key = hashlib.pbkdf2_hmac('sha256', self.secret_key.encode(), salt, 100000)
        # Simplified encryption - use proper encryption in production
        return f"{salt.hex()}:{derived_key.hex()}"
    
    def audit_log(self, tenant_id: str, action: str, details: Dict[str, Any]) -> None:
        """Log security-relevant actions for auditing"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "action": action,
            "details": details,
            "ip_address": self.get_client_ip()  # Would be implemented in web framework
        }
        
        # Store log entry (in real implementation, this would go to a secure log store)
        print(f"AUDIT: {log_entry}")