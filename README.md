# Dependencies 
git \
^python3.9 

# Setup

it is recommended that you clone the repos in your virtualenv `py39` for example \
```
py39\Scripts\activate 
cd py39
git clone https://github.com/pannet1/oc_chain.git 
pip install -r oc-trade\requirements.txt 
```

edit `oc-trade\oc_trade\strikes\<script>.yaml`
```
base_name: NIFTY
base_script: NFO:NIFTY22DECFUT
sample: 18000
addsub: 100
expiry: 22D08
abv_atm: 5
opt_exch: NFO
```
`addsub` refers to the the distance between strike price. here i skipped `NIFTY` minor strikeprices. 

in the `cred` folder two level above the `oc-trade` repos ... \
update `bypass.yaml` with your credentials 

```
userid: AB1234
password: Secret
totp: ABCDEFGHIJKLMNO9VERVQIO45ESDFDFASD
```
# Run 
* ensure that the venv is activated
* copy the `enctoken` from kite web cookies from browser
* paste it to the `bypass.tok` file  under the `confid` dir you created before  
* if the enctoken is empty, a new token is generated and reused throughout the day
```
cd py39\oc-trade\oc_trade 
py main.py
```
