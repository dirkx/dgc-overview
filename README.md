# dtc-generate-test-data

## Install

Make sure the submodules are installed:

     git submodule init
     git submodule update

And the dependencies (raw, of, better, via venv):

     pip3 install -r requirements.txt

You will also need some example/test keys in

     nl-dsc-keys

These can be generated (proper instructions to follow):

     mkdir -p nl-dsc-keys
     cd nl-dsc-keys
     for i in test vaccinations recovery 
     do 
        openssl req  -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -new -x509 -subj /C=NL/CN=test-$i -nodes -out Health_DSC_valid_for_$i.pem   -keyout Health_DSC_valid_for_$i.key
     done

