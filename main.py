#!env python3.8
import json
import os
import random
import uuid
import unidecode
import re
import datetime
import cbor2
import zlib
import base64
import qrcode
import io

from base45 import b45encode
from cose.curves import P256
from cose.algorithms import Es256
from cose.headers import Algorithm, KID
from cose.keys import CoseKey
from cose.keys.keyparam import KpAlg, EC2KpD, EC2KpCurve
from cose.keys.keyparam import KpKty
from cose.keys.keytype import KtyEC2
from cose.messages import Sign1Message
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding, load_pem_private_key

CERTIFICATE_ISSUER = "Ministry of Health Welfare and Sport"
TEST_TYPES = [
    ["test"],
    ["vaccination"],
    ["recovery"],
    ["test", "vaccination"],
    ["test", "recovery"],
    ["recovery", "vaccination"],
    ["test", "recovery", "vaccination"],
    ["test", "wrong_key"],
]

FRACTION_INVALID_CASES = 0.5
FRACTION_VALID_CASES = 1.0

# READ OFFICIAL VALUE SETS
SCHEMA_DIR = "./ehn-dgc-schema"
VALUE_SET_DIR = "valuesets"

VALUE_SETS = {
    "countries": ["NL", "SD", "GR", "AT"]
}

DATA_DIR = "./data"
TEST_DATA_SETS = {}

for f in os.listdir(os.path.join(SCHEMA_DIR, VALUE_SET_DIR)):
    with open(os.path.join(SCHEMA_DIR, VALUE_SET_DIR, f), "r") as json_file:
        valueset = json.load(json_file)
        VALUE_SETS.update({
            valueset['valueSetId']: valueset['valueSetValues']
        })


# READ TEST DATA SETS
def parse_test_record(line):
    result, record = line.split(':')
    values = record.split(';')
    values[-1] = values[-1][: -1]
    return dict(result=result, values=values)


for test_file in ['birthdates', 'names', 'vaccins']:
    with open(os.path.join(DATA_DIR, test_file), 'r') as f:
        TEST_DATA_SETS.update({
            test_file: [parse_test_record(l) for l in f.readlines()]
        })


def get_a_random(value_set_id):
    keys = ["", *list(VALUE_SETS[value_set_id])]
    return random.choice(keys)


def get_random_uvci():
    id = uuid.uuid4().hex
    return f"urn:uvci:01:NL:{id}"


def normalize_name(n):
    encoded = unidecode.unidecode(n)
    encoded = encoded.upper()
    encoded = re.sub(r"\s+", "<", encoded)
    encoded = re.sub(r"[^A-Z<]+", "", encoded)
    return encoded

def qr_png_base64(str):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=3,
        border=2,
    )

    qr.add_data(str)

    qr_image_buffer = io.BytesIO()
    qr.make_image().save(qr_image_buffer, format="PNG")
    return base64.b64encode(qr_image_buffer.getvalue()).decode("utf-8")

# Load keys
signing_keys = {}
for key_type, key_filename in {"test": "test", "vaccination": "vaccinations", "recovery": "recovery"}.items():
    filename_base = f"./nl-dsc-keys/Health_DSC_valid_for_{key_filename}"

    # Get public key with keyid
    with open(f"{filename_base}.pem", "rb") as file:
        pem = file.read()

    cert = x509.load_pem_x509_certificate(pem)
    fingerprint = cert.fingerprint(hashes.SHA256())
    keyid = fingerprint[0:8]

    # Get private key
    with open(f"{filename_base}.key", "rb") as file:
        pem = file.read()
    keyfile = load_pem_private_key(pem, password=None)
    privkey = keyfile.private_numbers().private_value.to_bytes(32, byteorder="big")

    # Construct COSE key object
    cose_key = {
        KpKty: KtyEC2,
        KpAlg: Es256,
        EC2KpCurve: P256,
        EC2KpD: privkey,
    }

    # Encode the certificate as base64
    cert_der = cert.public_bytes(Encoding.DER)
    cert_base64 = base64.b64encode(cert_der).decode("utf-8")

    # Create lookup entry
    signing_keys[key_type] = {
        "keyid": keyid,
        "cose_key": cose_key,
        "certificate_base64": cert_base64,
    }

# Construct and process test cases
print("Generating testcases. This can take a while (especially generating the QRs)", end='')

testcases = []
for type_id, type in enumerate(TEST_TYPES):
    for n in TEST_DATA_SETS["names"]:
        for d in TEST_DATA_SETS["birthdates"]:
            print(".", end="", flush=True)

            is_ok = n['result'] == 'T' and d['result'] == 'T'

            # Don't include too many invalid cases
            if not is_ok and random.random() > FRACTION_INVALID_CASES:
                continue
            if is_ok and random.random() > FRACTION_VALID_CASES:
                continue

            # Build JSON payload
            signing_key = None
            tests = []
            vaccinations = []
            recoveries = []

            if "test" in type:
                signing_key = signing_keys["test"]
                tests = [
                    {
                        "tg": get_a_random("disease-agent-targeted"),
                        "tt": "a test",
                        "sc": "2021-04-25T12:45:31Z",
                        "tr": get_a_random("covid-19-lab-result"),
                        "tc": "a place",
                        "co": get_a_random("countries"),
                        "is": CERTIFICATE_ISSUER,
                        "ci": get_random_uvci()
                    }
                    for _ in range(random.randint(1, 3))
                ]

            if "recovery" in type:
                signing_key = signing_keys["recovery"]
                recoveries = [
                    {
                        "tg": get_a_random("disease-agent-targeted"),
                        "fr": "2021-03-25",
                        "co": get_a_random("countries"),
                        "is": CERTIFICATE_ISSUER,
                        "df": "2021-04-12",
                        "du": "2021-06-01",
                        "ci": get_random_uvci()
                    }
                    for _ in range(random.randint(1, 2))
                ]

            if "vaccination" in type:
                signing_key = signing_keys["vaccination"]
                vaccinations = [
                    {
                        "tg": get_a_random("disease-agent-targeted"),
                        "vp": get_a_random("sct-vaccines-covid-19"),
                        "mp": get_a_random("vaccines-covid-19-names"),
                        "ma": get_a_random("vaccines-covid-19-auth-holders"),
                        "dn": random.randint(0, 9),
                        "sd": random.randint(1, 9),
                        "dt": "2021-02-18",  # Date of Vaccination
                        "co": get_a_random("countries"),  # Country of Vaccination
                        "is": CERTIFICATE_ISSUER,
                        "ci": get_random_uvci()
                    }
                    for _ in range(random.randint(0, 5))
                ]

            name = {
                "fn": n['values'][1],
                "fnt": normalize_name(n['values'][1]),
                "gn": n['values'][0],
                "gnt": normalize_name(n['values'][0])
            }

            json_payload = {
                "ver": "1.0.0",
                "nam": name,
                "dob": d['values'][0]
            }

            if vaccinations:
                json_payload.update({"v": vaccinations})
            if tests:
                json_payload.update({"t": tests})
            if recoveries:
                json_payload.update({"r": recoveries})

            # Potentially use the wrong key
            if "wrong_key" in type:
                other_key_types = list(signing_keys.keys() - set(type))
                signing_key = signing_keys[other_key_types[0]]

            # Sign
            cbor_message = cbor2.dumps(json_payload)

            cose_message = Sign1Message(phdr={Algorithm: Es256, KID: signing_key["keyid"]}, payload=cbor_message)
            cose_message.key = CoseKey.from_dict(signing_key["cose_key"])

            signed_message = cose_message.encode()
            compressed_message = zlib.compress(signed_message, 9)

            base45_message = b45encode(compressed_message)
            prefixed_message = "HC1:" + base45_message

            testcases.append({
                "JSON": json_payload,
                "CBOR": cbor_message.hex(),
                "COSE": signed_message.hex(),
                "COMPRESSED": compressed_message.hex(),
                "BASE45": base45_message,
                "PREFIX": prefixed_message,
                "2DCODE": qr_png_base64(prefixed_message),
                "TESTCTX": {
                    "VERSION": 1,
                    "SCHEMA": "1.0.0",
                    "CERTIFICATE": signing_key["certificate_base64"],
                    "VALIDATIONCLOCK": datetime.datetime.now().isoformat(),
                    "DESCRIPTION": f"NL {'+'.join(type)}",
                },
                "EXPECTEDRESULTS": {
                    "EXPECTEDVALIDOBJECT": True,
                    "EXPECTEDSCHEMAVALIDATION": is_ok,  # afhankelijk van de data
                    "EXPECTEDDECODE": True,
                    "EXPECTEDVERIFY": True,
                    "EXPECTEDUNPREFIX": True,
                    "EXPECTEDVALIDJSON": True,
                    "EXPECTEDCOMPRESSION": True,
                    "EXPECTEDB45DECODE": True,
                    "EXPECTEDEXPIRATIONCHECK": True,
                    "EXPECTEDPICTUREDECODE": True,
                    "EXPECTEDKEYUSAGE": "wrong_key" not in type
                }
            })

print(json.dumps(testcases, indent=2))