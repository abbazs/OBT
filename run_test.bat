REM ssg    Back test strangle for number of expiries
python run.py -mitr=10 -ssaf=0.95 -noad=1 ssg -nexp=5 -month=1 -price=100
REM ssgc   Study strangle for a given start date, end date and expiry date
python run.py -mitr=10 -ssaf=0.95 -noad=1 ssgc -ST=30AUG2019 -ND=26SEP2019 -ED=26SEP2019 -price=100
REM ssgcf  Study custom strangle for a given start date, end date, expiry...
python run.py -mitr=10 -ssaf=0.85 -noad=1 ssgcf -name=ssgcg_aug.json
REM ssgnd  Study strangles for given number of expiry and ndays before by...
python run.py -mitr=10 -ssaf=0.95 -noad=1 ssgnd -price=100 -ndays=30 -nexp=5
REM ssgsf  Study strangle for a given start date, end date and expiry date
python run.py -mitr=10 -ssaf=0.85 -noad=1 ssgcf -name=oct_ssgcf1.json
REM ssr    Study straddles for given number of expiry and month current month...
python run.py -mitr=10 -ssaf=0.95 -noad=1 ssr -month=1 -nexp=5
REM ssrc   Study custom straddle for a given start date, end date, expiry...
python run.py -mitr=10 -ssaf=0.95 -noad=1 ssrc -name=oct_ssrc.json
REM ssrnd  Study straddles for given number of expiry and ndays before
python run.py -mitr=10 -ssaf=0.95 -noad=1 ssrnd -nexp=5 -ndays=45
REM ssrs   Study straddles for start, end and expiry days
python run.py -mitr=10 -ssaf=0.95 -noad=1 ssrs -ST=30AUG2019 -ND=26SEP2019 -ED=26SEP2019