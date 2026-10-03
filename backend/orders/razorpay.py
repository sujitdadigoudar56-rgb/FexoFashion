"""Minimal Razorpay REST client (orders, payments, refunds) plus signature
checks — stdlib only, no SDK dependency.

Docs: https://razorpay.com/docs/api/  — amounts are in paise.
"""

import base64
import hashlib
import hmac
import json
import urllib.error
import urllib.request
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

API_BASE = 'https://api.razorpay.com/v1'
TIMEOUT = 20


class RazorpayError(Exception):
    def __init__(self, message, status=None, body=None):
        super().__init__(message)
        self.status = status
        self.body = body


def is_configured():
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def to_paise(amount):
    return int((Decimal(amount) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _request(method, path, payload=None):
    if not is_configured():
        raise RazorpayError('Online payments are not configured.')
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f'{API_BASE}{path}', data=data, method=method)
    token = base64.b64encode(f'{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}'.encode()).decode()
    req.add_header('Authorization', f'Basic {token}')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read() or b'{}')
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors='replace')
        try:
            message = json.loads(body).get('error', {}).get('description') or body
        except ValueError:
            message = body
        raise RazorpayError(message or f'Razorpay error {exc.code}', status=exc.code, body=body) from exc
    except urllib.error.URLError as exc:
        raise RazorpayError(f'Could not reach Razorpay: {exc.reason}') from exc


def create_order(amount, receipt, notes=None):
    return _request('POST', '/orders', {
        'amount': to_paise(amount),
        'currency': 'INR',
        'receipt': receipt[:40],
        'notes': notes or {},
    })


def fetch_payment(payment_id):
    return _request('GET', f'/payments/{payment_id}')


def capture_payment(payment_id, amount_paise):
    return _request('POST', f'/payments/{payment_id}/capture', {'amount': amount_paise, 'currency': 'INR'})


def refund_payment(payment_id, amount_paise=None, notes=None):
    payload = {'notes': notes or {}}
    if amount_paise is not None:
        payload['amount'] = amount_paise
    return _request('POST', f'/payments/{payment_id}/refund', payload)


def verify_payment_signature(razorpay_order_id, razorpay_payment_id, signature):
    """Checkout handler signature: HMAC-SHA256(order_id|payment_id, key secret)."""
    if not (razorpay_order_id and razorpay_payment_id and signature and settings.RAZORPAY_KEY_SECRET):
        return False
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f'{razorpay_order_id}|{razorpay_payment_id}'.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(body: bytes, signature):
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not (secret and signature):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
