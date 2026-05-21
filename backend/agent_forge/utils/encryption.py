"""
AgentForge API Key 加密工具

使用 PBKDF2 密钥派生 + Fernet (AES-128-CBC + HMAC) 加密。
"""
import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class APIKeyEncryption:
    """API Key 加密管理器
    
    使用 PBKDF2 从主密钥和盐值派生 32 字节密钥，再用 Fernet 加密。
    这样即使 ENCRYPTION_KEY 是用户自定义的短字符串也能安全工作。
    """
    
    def __init__(self, master_key: str, salt: str):
        """初始化加密管理器
        
        Args:
            master_key: 主密钥（来自环境变量 ENCRYPTION_KEY）
            salt: 盐值（来自环境变量 ENCRYPTION_SALT）
        """
        key = self._derive_key(master_key, salt)
        self._fernet = Fernet(key)
    
    @staticmethod
    def _derive_key(master_key: str, salt: str) -> bytes:
        """从主密钥和盐值派生 Fernet 密钥
        
        使用 PBKDF2-HMAC-SHA256，480,000 次迭代（OWASP 2024 推荐）。
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=480_000,
        )
        return base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
    
    def encrypt(self, plaintext: str) -> str:
        """加密明文 → Fernet token 字符串"""
        return self._fernet.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """解密 Fernet token 字符串 → 明文"""
        return self._fernet.decrypt(ciphertext.encode()).decode()
    
    @staticmethod
    def mask_key(key: str) -> str:
        """生成掩码格式用于展示
        
        sk-1234567890abcdef → sk-12****cdef
        """
        if len(key) <= 8:
            return "****"
        return f"{key[:4]}****{key[-4:]}"
