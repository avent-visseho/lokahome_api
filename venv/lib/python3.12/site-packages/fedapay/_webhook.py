import json
import hmac
import hashlib
from fedapay import _util
import time
from fedapay._error import SignatureVerificationError


class Webhook():
    DEFAULT_TOLERANCE=300
    
    @staticmethod
    def construct_event(payload, signature_header, secret, tolerance=DEFAULT_TOLERANCE):
        if hasattr(payload, "decode"):
            payload = payload.decode("utf-8")
        WebhookSignature.verify_header(payload, signature_header, secret, tolerance)
        
        data = json.loads(payload)
        return data

class WebhookSignature():
    EXPECTED_SCHEME = 's'
    
    @classmethod
    def verify_header(cls, payload, header, secret, tolerance=None):
        timestamp = cls._get_timestamp(header)
        signatures = cls._get_signatures(header, scheme=cls.EXPECTED_SCHEME)
        if timestamp == -1:
            raise SignatureVerificationError(
                "Unable to extract timestamp and signatures from header",
                header,
                payload,
            )
        
        if not signatures:
            raise SignatureVerificationError(
                "No signatures found with expected scheme",
                header,
                payload,
            )
        
        signed_payload = str(timestamp) + '.' + str(payload)
        expected_signature = cls._compute_signature(signed_payload, secret)
        signature_found = False
        for signature in signatures:
            if _util.secure_compare(expected_signature, signature):
                signature_found = True
                break
        
        if not signature_found:
            raise SignatureVerificationError(
                "No signatures found matching the expected signature for payload",
                header,
                payload,
            )
            
        # Check if timestamp is within tolerance
        if ((tolerance > 0) and (abs(time.time() - timestamp) > tolerance)):
            raise SignatureVerificationError(
                "Timestamp outside the tolerance zone",
                header,
                payload,
            )
        
        return True
        
    @staticmethod
    def _get_timestamp(header):
        items = header.split(',')
        for item in items:
            item_parts = item.split('=', maxsplit=1)
            if item_parts[0] == 't':
                if not item_parts[1].isnumeric():
                    return -1
                return int(item_parts[1])
        return -1
    
    @staticmethod
    def _get_signatures(header, scheme):
        signatures = []
        items = header.split(',')
        for item in items:
            item_parts = item.split('=', maxsplit=1)
            if item_parts[0] == scheme:
                signatures.append(item_parts[1])
        return signatures
        
    @staticmethod
    def _compute_signature(payload, secret):
        return hmac.new(
            bytes(secret, 'utf-8'), 
            msg=bytes(payload, 'utf-8'), 
            digestmod=hashlib.sha256
            ).hexdigest()
