import json
import os
import random
import uuid
import unidecode
import re
import datetime

CERTIFICATE_ISSUER = "Ministry of Health Welfare and Sport"
TEST_TYPES = [
    "test",
    "vaccination",
    "recovery",
    "test+vaccination",
    "test+recovery",
    "recovery+vaccination",
    "test+recovery+vaccination",
    "test+wrong_key"]

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


testcases = []
for type_id, type in enumerate(TEST_TYPES):
    for n in TEST_DATA_SETS["names"]:
        for d in TEST_DATA_SETS["birthdates"]:
            is_ok = n['result'] == 'T' and d['result'] == 'T'

            # Don't include too many invalid cases
            if not is_ok and random.random() > FRACTION_INVALID_CASES:
                continue
            if is_ok and random.random() > FRACTION_VALID_CASES:
                continue

            tests = []
            vaccinations = []
            recoveries = []

            if "test" in type:
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

            if "vaccination" in type:
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

            if "recovery" in type:
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

            name = {
                "fn": n['values'][1],
                "fnt": normalize_name(n['values'][1]),
                "gn": n['values'][0],
                "gnt": normalize_name(n['values'][0])
            }

            test_json = {
                "ver": "1.0.0",
                "nam": name,
                "dob": d['values'][0]
            }
            if vaccinations:
                test_json.update({"v": vaccinations})
            if tests:
                test_json.update({"t": tests})
            if recoveries:
                test_json.update({"r": recoveries})

            testcases.append({
                "JSON": test_json,
                "CBOR": "",
                "COSE": "",
                "COMPRESSED": "",
                "BASE45": "",
                "PREFIX": "",
                "2DCODE": "",
                "TESTCTX": {
                    "VERSION": 1,
                    "SCHEMA": "1.0.0",
                    "CERTIFICATE": "M",
                    "VALIDATIONCLOCK": datetime.datetime.now().isoformat(),
                    "DESCRIPTION": f"NL {type}",
                    "_use_wrong_key": "wrong_key" in type
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
