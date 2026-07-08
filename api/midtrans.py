"""Thin Midtrans Snap helper (ported from bukugambar_ai)."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.error
import urllib.request


def _is_production() -> bool:
    return os.getenv('MIDTRANS_IS_PRODUCTION', 'true').lower() in ('1', 'true', 'yes')


def _snap_base_url() -> str:
    return 'https://app.midtrans.com' if _is_production() else 'https://app.sandbox.midtrans.com'


def _api_base_url() -> str:
    return 'https://api.midtrans.com' if _is_production() else 'https://api.sandbox.midtrans.com'


def get_server_key() -> str:
    key = os.getenv('MIDTRANS_SERVER_KEY')
    if not key:
        raise ValueError('MIDTRANS_SERVER_KEY is missing')
    return key


def get_client_key() -> str:
    key = os.getenv('MIDTRANS_CLIENT_KEY')
    if not key:
        raise ValueError('MIDTRANS_CLIENT_KEY is missing')
    return key


def _auth_header(server_key: str) -> str:
    token = base64.b64encode(f'{server_key}:'.encode()).decode()
    return f'Basic {token}'


def create_snap_transaction(payload: dict, extra_headers: dict | None = None) -> dict:
    server_key = get_server_key()
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': _auth_header(server_key),
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(
        f'{_snap_base_url()}/snap/v1/transactions',
        data=json.dumps(payload).encode(),
        headers=headers,
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
            msg = ', '.join(err.get('error_messages', [])) or err.get('status_message') or body
        except Exception:
            msg = body or str(e)
        raise ValueError(msg) from e

    return {'token': data['token'], 'redirect_url': data.get('redirect_url')}


def verify_signature(payload: dict) -> bool:
    server_key = os.getenv('MIDTRANS_SERVER_KEY')
    order_id = payload.get('order_id')
    status_code = payload.get('status_code')
    gross_amount = payload.get('gross_amount')
    signature_key = payload.get('signature_key')
    if not all([server_key, order_id, status_code, gross_amount, signature_key]):
        return False
    raw = f'{order_id}{status_code}{gross_amount}{server_key}'
    expected = hashlib.sha512(raw.encode()).hexdigest()
    return expected == signature_key


def to_local_status(transaction_status: str | None, fraud_status: str | None = None) -> str:
    if transaction_status == 'settlement':
        return 'paid'
    if transaction_status == 'capture':
        return 'paid' if fraud_status == 'accept' else 'pending'
    if transaction_status in ('pending', 'authorize', 'challenge'):
        return 'pending'
    if transaction_status in ('deny', 'cancel', 'expire', 'failure'):
        return 'failed'
    return 'pending'


def snap_script_url() -> str:
    base = 'https://app.midtrans.com' if _is_production() else 'https://app.sandbox.midtrans.com'
    return f'{base}/snap/snap.js'
