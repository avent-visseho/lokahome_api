from typing import Dict, Optional, Union
from fedapay._error_object import ErrorObject


class FedaPayError(Exception):
    _message: Optional[str]
    headers: Optional[Dict]
    http_body: Optional[str]

    def __init__(
        self,
        message: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        http_body: Optional[Union[bytes, str]] = None,
    ):
        super().__init__(message)
        
        self._message = message
        self.headers = headers or {}
        self.http_body = http_body
    
    def __str__(self):
        msg = self._message or "<empty message>"
        return msg


class SignatureVerificationError(FedaPayError):
    def __init__(self, message, sig_header, http_body=None):
        super().__init__(message, http_body)
        self.sig_header = sig_header
