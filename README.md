# Dependencies 
git \
python3.9 

#Setup
it is recommended that you clone the repos in your venv\
venv\Scripts\activate\
git clone https://github.com/pannet1/oc_chain.git\
cd oc-trade\
pip install -r requirements.txt\
cd oc-trade\oc_trade\strikes\

update credential file bypass.yaml with your credentials\
edit <script>.yaml\
```
base_name: NIFTY
base_script: NFO:NIFTY22DECFUT
sample: 18000
addsub: 100
expiry: 22D08
abv_atm: 5
opt_exch: NFO
```
addsub refers to the the distance between strike price. here i skipped `NIFTY` minor strikeprices. \

#Run
copy the enctoken from kite web \
paste it to the bypass.tok file \
cd oc-trade\oc_trade \


