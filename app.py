from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import requests
import jwt
import urllib3
import json
from google.protobuf.internal import decoder as _pb_decoder

# Import MajorLoginRes proto
try:
    from MajorLoginRes_pb2 import MajorLoginRes
except ImportError:
    MajorLoginRes = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

AES_KEY = b'Yg&tc%DEuh6%Zc^8'
AES_IV = b'6oyZDr22E3ychjM%'


def encrypt_message(plaintext):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return cipher.encrypt(pad(plaintext, AES.block_size))


def decrypt_message(ciphertext):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return unpad(cipher.decrypt(ciphertext), AES.block_size)


# ============ MANUAL PROTOBUF ENCODING ============
def enc_varint(v):
    r = b''
    while v > 0x7F:
        r += bytes([(v & 0x7F) | 0x80])
        v >>= 7
    r += bytes([v])
    return r


def enc_str(f, v):
    if isinstance(v, str):
        v = v.encode('utf-8')
    return enc_varint((f << 3) | 2) + enc_varint(len(v)) + v


def enc_bytes(f, v):
    return enc_varint((f << 3) | 2) + enc_varint(len(v)) + v


def enc_int(f, v):
    return enc_varint((f << 3) | 0) + enc_varint(v)


def build_majorlogin(open_id, access_token, platform_type=4):
    """FF MAX MajorLogin — exact fields."""
    p = b''
    p += enc_str(3, "2026-09-30 04:21:02")
    p += enc_str(4, "free fire")
    p += enc_int(5, 1)
    p += enc_str(7, "2.132.4")
    p += enc_str(8, "Android OS 12 / API-31 (SP1A.210812.016)")
    p += enc_str(9, "Handheld")
    p += enc_str(10, "Jio")
    p += enc_str(11, "WIFI")
    p += enc_int(12, 1280)
    p += enc_int(13, 720)
    p += enc_str(14, "240")
    p += enc_str(15, "x86-64 SSE3 SSE4.1 SSE4.2 AVX AVX2 | 2400 | 4")
    p += enc_int(16, 5500)
    p += enc_str(17, "Mali-G52 MC2")
    p += enc_str(18, "OpenGL ES 3.2")
    p += enc_str(19, "Google|7667007e-2e1c-4208-a718-b46cedd84731")
    p += enc_str(20, "49.36.181.15")
    p += enc_str(21, "en")
    p += enc_str(22, open_id)
    p += enc_str(23, str(platform_type))
    p += enc_str(24, "Handheld")
    p += enc_str(25, "Infinix X6819")
    p += enc_str(26, "IND")
    p += enc_str(29, access_token)
    p += enc_int(30, 1)
    p += enc_str(41, "Jio")
    p += enc_str(42, "WIFI")
    p += enc_str(57, "1ac4b80ecf0478a44203bf8fac6120f5")
    p += enc_int(60, 30000)
    p += enc_int(61, 30000)
    p += enc_int(62, 2519)
    p += enc_int(63, 243)
    p += enc_int(64, 32357)
    p += enc_int(65, 34308)
    p += enc_int(66, 32357)
    p += enc_int(67, 34308)
    p += enc_int(73, 1)
    p += enc_str(74, "/data/app/~~iw-K-GR3srU7dLE-UxJ4bg==/com.dts.freefiremax-kbPhw3SUYautW0I_oayB_A==/lib/arm")
    p += enc_int(76, 2)
    p += enc_str(77, "428775ab8c8845bd341b5357ec61d15e|/data/app/~~iw-K-GR3srU7dLE-UxJ4bg==/com.dts.freefiremax-kbPhw3SUYautW0I_oayB_A==/base.apk")
    p += enc_int(78, 2)
    p += enc_int(79, 1)
    p += enc_str(81, "32")
    p += enc_str(83, "2019118525")
    p += enc_int(85, 3)
    p += enc_str(86, "OpenGLES3")
    p += enc_int(87, 4095)
    p += enc_int(88, 4)
    p += enc_int(92, 19788)
    p += enc_str(93, "android_max")
    p += enc_str(94, "KqsHT2gyPt7vUCc9SCjv2ioi3WEZSEL86ErvXB38suVVK/Z4IVt78ESl/r2S15C1pqu/j6ZmgFL7HbwoFiiVconX08ooKiisQffvEAPCo/C+Lahr")
    p += enc_str(96, '{"cur_rate":null,"support_etc2":true}')
    p += enc_int(97, 1)
    p += enc_int(98, 1)
    p += enc_str(99, "4")
    p += enc_str(100, "4")
    p += enc_str(102, "")
    p += enc_int(104, 77149)
    p += enc_int(105, 1)
    p += enc_str(106, "https://dl.cdn.freefiremobile.com/live/ABHotUpdates/|https://dl-core.cdn.freefiremobile.com/live/ABHotUpdates/|6b2078db9d22dd98f8e9386a39af8462")
    p += enc_str(107, "c8e41b7a93f02d56e1a94c7b8203f5d1")
    return p


def build_majorregister(open_id, access_token, nickname="Anurag6281"):
    p = b''
    p += enc_str(1, nickname)
    p += enc_str(2, open_id)
    p += enc_str(3, access_token)
    p += enc_int(5, 102000007)
    p += enc_int(6, 4)
    p += enc_int(7, 1)
    p += enc_int(13, 1)
    p += enc_int(16, 2)
    p += enc_str(15, "en")
    p += enc_str(20, "1.132.6")
    p += enc_int(21, 4)
    return p


# ============ PROTOBUF RESPONSE PARSER ============
def parse_majorlogin_response(content: bytes):
    """
    Garena MajorLogin response:
      [0:64]   -> encrypted header (skip)
      [64:]    -> MajorLoginRes protobuf
    Try both: with skip, and offsets 0..128 fallback.
    """
    if not content or len(content) < 10:
        return None, None

    # Try skip 64
    candidates = []
    if len(content) > 64:
        candidates.append(content[64:])
    candidates.append(content)

    for raw in candidates:
        # Try strict protobuf parse via generated class
        if MajorLoginRes is not None:
            for offset in range(0, min(128, len(raw))):
                try:
                    m = MajorLoginRes()
                    m.ParseFromString(raw[offset:])
                    if m.account_id and m.token:
                        return m, offset
                except Exception:
                    continue
        # Fallback: manual field scan for field 8 (token) + field 1 (account_id)
        try:
            fields = _manual_scan_proto(raw)
            if 8 in fields and 1 in fields:
                return fields, 0
        except Exception:
            continue
    return None, None


def _manual_scan_proto(data: bytes):
    """Minimal protobuf field scanner (varint + length-delimited)."""
    out = {}
    i = 0
    n = len(data)
    while i < n:
        # read tag varint
        tag = 0
        shift = 0
        while i < n:
            b = data[i]; i += 1
            tag |= (b & 0x7F) << shift
            shift += 7
            if not (b & 0x80):
                break
        if tag == 0:
            break
        fnum = tag >> 3
        wtype = tag & 0x7
        if wtype == 0:  # varint
            val = 0; shift = 0
            while i < n:
                b = data[i]; i += 1
                val |= (b & 0x7F) << shift
                shift += 7
                if not (b & 0x80):
                    break
            out[fnum] = val
        elif wtype == 2:  # length-delimited
            ln = 0; shift = 0
            while i < n:
                b = data[i]; i += 1
                ln |= (b & 0x7F) << shift
                shift += 7
                if not (b & 0x80):
                    break
            if i + ln > n:
                break
            out[fnum] = data[i:i+ln]
            i += ln
        elif wtype == 5:  # 32-bit
            i += 4
        elif wtype == 1:  # 64-bit
            i += 8
        else:
            break
    return out


def _get_field(fields, num, default=None):
    if isinstance(fields, dict):
        v = fields.get(num, default)
        if isinstance(v, bytes):
            try:
                return v.decode('utf-8')
            except Exception:
                return v
        return v
    try:
        return getattr(fields, f"field_{num}", default) or default
    except Exception:
        return default


# ============ ENDPOINTS ============
@app.route('/token', methods=['GET'])
def oauth_guest():
    uid = request.args.get('uid')
    password = request.args.get('password')
    if not uid or not password:
        return jsonify({"message": "Missing params"}), 400

    session = requests.Session()
    session.trust_env = False

    # ============ Step 1: OAuth ============
    oauth_url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    payload = {
        'uid': uid, 'password': password,
        'response_type': "token", 'client_type': "2",
        'client_secret': "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        'client_id': "100067"
    }
    headers = {'User-Agent': "GarenaMSDK/4.0.19P9(SM-M526B ;Android 13;pt;BR;)"}

    try:
        r = session.post(oauth_url, data=payload, headers=headers, timeout=15)
    except Exception as e:
        return jsonify({"step": "oauth", "error": str(e)}), 500

    if r.status_code != 200:
        return jsonify({"step": "oauth", "status": r.status_code, "body": r.text}), 400

    oauth = r.json()
    access_token = oauth.get('access_token')
    open_id = oauth.get('open_id')

    if not access_token or not open_id:
        return jsonify({"step": "oauth", "error": "no token/open_id", "data": oauth}), 400

    print(f"[OAUTH] open_id={open_id[:10]}... access_token_len={len(access_token)}")

    # ============ Step 2: MajorRegister (optional) ============
    reg_bytes = build_majorregister(open_id, access_token)
    enc_reg = encrypt_message(reg_bytes)

    reg_headers = {
        "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-GA": "v1 1",
        "X-Unity-Version": "2018.4.12f1",
        "X-GA-SV": "1790742062",
        "ReleaseVersion": "OB55"
    }

    try:
        reg_res = session.post(
            "https://loginbp.ppmainecoonghj.com/MajorRegister",
            data=enc_reg, headers=reg_headers, verify=False, timeout=15
        )
        print(f"[MAJORREGISTER] {reg_res.status_code} | {len(reg_res.content)} bytes")
    except Exception as e:
        print(f"[MAJORREGISTER] Exception: {e}")
        reg_res = None

    # ============ Step 3: MajorLogin ============
    login_bytes = build_majorlogin(open_id, access_token)
    enc_login = encrypt_message(login_bytes)

    try:
        login_res = session.post(
            "https://loginbp.ppmainecoonghj.com/MajorLogin",
            data=enc_login, headers=reg_headers, verify=False, timeout=15
        )
        print(f"[MAJORLOGIN] {login_res.status_code} | {len(login_res.content)} bytes")
    except Exception as e:
        return jsonify({"step": "majorlogin", "error": str(e)}), 500

    if login_res.status_code != 200:
        return jsonify({
            "step": "majorlogin",
            "status": login_res.status_code,
            "body": login_res.text[:300],
            "register_status": reg_res.status_code if reg_res else None
        }), 400

    # ============ Step 4: Parse protobuf (NOT regex) ============
    content = login_res.content
    res_proto, offset = parse_majorlogin_response(content)

    if res_proto is None:
        return jsonify({
            "step": "parse",
            "status": 200,
            "size": len(content),
            "hex_preview": content[:120].hex(),
            "hint": "MajorLoginRes protobuf parse failed. Check MajorLoginRes_pb2.py exists."
        }), 400

    # ============ Step 5: Extract fields ============
    if isinstance(res_proto, dict):
        account_id = _get_field(res_proto, 1)
        region = _get_field(res_proto, 2)
        token = _get_field(res_proto, 8)
        server_url = _get_field(res_proto, 10)
        server_time = _get_field(res_proto, 21)
        aes_ak = _get_field(res_proto, 22)
        iv_i = _get_field(res_proto, 23)
    else:
        account_id = getattr(res_proto, 'account_id', 0)
        region = getattr(res_proto, 'lock_region', '')
        token = getattr(res_proto, 'token', '')
        server_url = getattr(res_proto, 'server_url', '')
        server_time = getattr(res_proto, 'kts', 0)
        aes_ak = getattr(res_proto, 'ak', b'')
        iv_i = getattr(res_proto, 'aiv', b'')

    if not token:
        return jsonify({
            "step": "parse",
            "error": "token field empty in MajorLoginRes",
            "account_id": account_id,
            "region": region,
            "offset": offset
        }), 400

    # ============ Step 6: Decode JWT info ============
    decoded = {}
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
    except Exception:
        decoded = {}

    # Convert bytes to hex for JSON
    if isinstance(aes_ak, (bytes, bytearray)):
        aes_ak_hex = aes_ak.hex()
    else:
        aes_ak_hex = str(aes_ak) if aes_ak else ""
    if isinstance(iv_i, (bytes, bytearray)):
        iv_i_hex = iv_i.hex()
    else:
        iv_i_hex = str(iv_i) if iv_i else ""

    print(f"[TOKEN] {token[:60]}...")
    print(f"[SERVER] {server_url} | region={region}")

    return jsonify({
        "status": "success",
        "account_id": account_id,
        "nickname": decoded.get("nickname"),
        "region": region or decoded.get("lock_region"),
        "platform": decoded.get("external_type"),
        "is_emulator": decoded.get("is_emulator", False),
        "emulator_score": decoded.get("emulator_score", 0),
        "token": token,
        "open_id": open_id,
        "access_token": access_token,
        "server_url": server_url,
        "server_time": server_time,
        "aes_ak": aes_ak_hex,
        "iv_i": iv_i_hex,
        "parse_offset": offset,
        "register_status": reg_res.status_code if reg_res else None,
        "login_status": login_res.status_code
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1080, debug=False)