from omspy.brokers.kotak import Kotak 
from toolkit.fileutils import Fileutils

f = Fileutils().get_lst_fm_yml('../../../confid/kotak.yaml')
k = Kotak(*f)

#print(k)
#consumer_secret= '5lQiv2TA8rgPmrJMFlFoFPbcaq4a'
#neotradeapi





