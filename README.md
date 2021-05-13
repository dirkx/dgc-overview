# dtc-generate-test-data

## Install

Make sure the submodules are installed:

     git submodule init
     git submodule update

And the dependencies (raw, of, better, via venv):

     pip3 install -r requirements.txt


## Creating signing keys

You will also need some example/test keys in

     nl-dsc-keys

These can be generated (proper instructions to follow):

     mkdir -p nl-dsc-keys
     cd nl-dsc-keys
     for i in test vaccinations recovery 
     do 
        openssl req  -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -new -x509 -subj /C=NL/CN=test-$i -nodes -out Health_DSC_valid_for_$i.pem   -keyout Health_DSC_valid_for_$i.key
     done

## Creating the tests

     python3 main.py

## Manual verify

Manual verify

     qrdecode NL/2DCode/png/30.png| <SOMPATH>/ehn-sign-verify-python-trivial/cose_verify.py  nl-dsc-keys/Health_DSC_valid_for_test.pem  | jq

should yeild

     {
       "-260": {
         "1": {
           "ver": "1.0.0",
           "nam": {
             "fn": "van der Achternaam-Leeuwarden",
             "fnt": "VAN<DER<ACHTERNAAMLEEUWARDEN",
             "gn": "Voornaam",
             "gnt": "VOORNAAM"
           },
           "dob": "",
           "t": [
             {
               "tg": "",
               "tt": "a test",
               "sc": "2021-04-25T12:45:31Z",
               "tr": "260415000",
               "tc": "a place",
               "co": "GR",
               "is": "Ministry of Health Welfare and Sport",
               "ci": "urn:uvci:01:NL:3b7a019db3944d5389b28e87e552da1e"
             }
           ]
         }
       }
     }



