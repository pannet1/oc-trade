const init_html = (obj) => {
  let markup = ""
  let ctml = ""
  let ptml = ""
  const messages = document.getElementById('messages')
  Object.keys(obj).forEach(function(strike) {
      oStrike = obj[strike]
      markup += "<tr>"
      Object.keys(oStrike).forEach(function(options) {
          oPtions = oStrike[options]
          Object.keys(oPtions).forEach(function(prices) {
              if (options=="call") {
                 ctml = "<td class='chip'>&nbsp;</td>"
                 ctml += "<td><input class='ordQty' name='oqty'>"
                 ctml += "<input class='ordDir' type='hidden' name='odir' value=''></td>"
                 ctml += "<td><input name='chk' class='chkCall' value='" + [prices] + "' type='checkbox' style='float:right'>"
                 ctml += "<input type='hidden' name='tsym'  value='" + [prices] + "'></td>"
                 ctml += "<td class='right' id='" + prices + "'>" + oPtions[prices] + "</td>"
                 ctml += "<td class='callQty'>0</td><td class='callPnl'>0</td>"
              }
              else if (options=="put") {
                 ptml = "<td class='putPnl' data-num=0>0</td><td class='putQty'>0</td>"
                 ptml += "<td class='right' id='" + prices + "'>" + oPtions[prices] + "</td>"
                 ptml += "<td><input name='chk' class='chkPut' value='" + [prices] + "' type='checkbox'>"
                 ptml += "<input type='hidden' name='tsym'  value='" + [prices] + "'></td>"
                 ptml += "<td><input class='ordQty' type='text' name='oqty'>"
                 ptml += "<input class='ordDir' type='hidden' name='odir' value=''></td>"
                 ptml += "<td class='chip'>&nbsp;</td>"
              }
          });
      });
      markup += ctml
      markup += "<td id='" + strike +  "'class='center'>" + strike + "</td>"
      markup += ptml
      markup += "</tr>\n"
  })
  messages.innerHTML = markup
}

const get_quotes = (obj, atm) => {
  Object.keys(obj).forEach(function(strike) {
    oStrike = obj[strike]
    Object.keys(oStrike).forEach(function(options) {
      oPtions = oStrike[options]
      Object.keys(oPtions).forEach(function(prices) {
        const elmPrices = document.getElementById(prices)
        const oldVal = elmPrices.innerText
        const newVal = Math.floor(oPtions[prices])
        elmPrices.innerText = newVal;
        if (oldVal<newVal) {
          elmPrices.classList.remove('dn');
          elmPrices.classList.add('up');
        }
        else if (oldVal>newVal) {
          elmPrices.classList.remove('up');
          elmPrices.classList.add('dn')
        }
      });
    });
    if (strike != atm) {
      elmStrike = document.getElementById(strike)
      elmStrike.classList.remove('ntrl')
    }
  })
}

const get_stat = (stat) => {
  const strHsl = stat.slept.toString().split(".")[1];
  const h = strHsl.substring(0,2)
  const s = parseInt(strHsl.substring(2,4))<50 ? 50 : strHsl.substring(2,4)
  const l = parseInt(strHsl.substring(4,6))>50 ? 50 : strHsl.substring(4,6)
  const menu = document.getElementsByClassName('menu')[0]
  menu.style.backgroundColor = `hsl(${h},${s}\%,${l}\%)`
  document.getElementById('tsym').innerText = stat.tsym
  document.getElementById('ltp').innerText = stat.ltp
  document.getElementById('inp').value = stat.lot
  const atm = stat.atm
  document.getElementById(atm).classList.add('ntrl')
  return atm
}

const get_pos = (obj) => {
  let elmQty
  let elmPnl
  let pnl = 0
  let callProfit = 0
  let putProfit = 0

  Object.keys(obj).forEach(function(pos) {
    const tsym = obj[pos]
    try {
    const elmTsym = document.getElementById(tsym.symbol)
    const tr = elmTsym.parentElement
    const ltp = elmTsym.innerHTML

    if (tsym.quantity<0) {
      pnl = tsym.day_sell_value - tsym.day_buy_value - (tsym.quantity * ltp)
    } else if (tsym.quantity>0) {
      pnl = tsym.day_sell_value - tsym.day_buy_value + (tsym.quantity * ltp)
    } else {
      pnl = tsym.pnl
    }

    if (tsym.symbol.slice(-2) == 'CE') {
      elmQty = tr.getElementsByClassName('callQty')[0]
      elmPnl = tr.getElementsByClassName('callPnl')[0]
      callProfit += pnl
    } else  if (tsym.symbol.slice(-2) == 'PE') {
      elmQty = tr.getElementsByClassName('putQty')[0]
      elmPnl = tr.getElementsByClassName('putPnl')[0]
     putProfit += pnl
    }

    if (parseFloat(elmQty.innerHTML) >= 0 && tsym.quantity < 0) {
      elmQty.classList.remove('up')
      elmQty.classList.add('dn')
    } else if (parseFloat(elmQty.innerHTML) <= 0 && tsym.quantity > 0) {
      elmQty.classList.remove('dn')
      elmQty.classList.add('up')
    }
    elmQty.innerHTML = tsym.quantity

    if (parseFloat(elmPnl.innerHTML) >= 0 && pnl < 0) {
      elmPnl.classList.remove('up')
      elmPnl.classList.add('dn')
    } else if ( parseFloat(elmPnl.innerHTML) <= 0 && pnl > 0) {
      elmPnl.classList.remove('dn')
      elmPnl.classList.add('up')
    }
    elmPnl.innerHTML = parseInt(pnl)
    }
    catch(e) {
      console.log('error: ' + e + tsym)
    }
  })
  document.getElementById('ttlcallpnl').innerHTML = parseInt(callProfit)
  document.getElementById('ttlputpnl').innerHTML = parseInt(putProfit)
  document.getElementById('ttlpnl').innerHTML = parseInt(callProfit+putProfit)
}

let fired = 0
const ws = new WebSocket("ws://localhost:8000/ws");
ws.onmessage = function(event) {
  try {
      const parsed = JSON.parse(event.data)
      if (fired > 0) {
        atm = get_stat(parsed.time)
        get_quotes(parsed.quotes, atm)
        get_pos(parsed.positions)
      } else {
        init_html(parsed.quotes)
      }
     fired += 1
  }
  catch (err) {
      console.log(err)
  }
};


const batch_orders = (action) => {
  const checks = document.querySelectorAll('input[type=checkbox]:checked');
  let tgtChip
  let tgtQty
  let tgtDir
  checks.forEach(chk => {
    const opt = chk.className
    const chip = chk.parentElement.parentElement.getElementsByClassName('chip')
    const qty  = chk.parentElement.parentElement.getElementsByClassName('ordQty')
    const dir = chk.parentElement.parentElement.getElementsByClassName('ordDir')
    if (opt == 'chkCall') {
      tgtChip = chip[0]
      tgtQty = qty[0]
      tgtDir = dir[0]
    } else  {
      tgtChip = chip[1]
      tgtQty = qty[1]
      tgtDir = dir[1]
    }
    if (action == 'SELL') {
      tgtChip.classList.remove('BUY')
    } else {
      tgtChip.classList.remove('SELL')
    }
    tgtChip.innerText = action
    tgtChip.classList.add(action)
    tgtQty.value = document.getElementById('inp').value
    chk.click()
    tgtDir.value = action
  });
}

const clearBuySell = () => {
  const checks = document.querySelectorAll('input[type=checkbox]:checked');
  let tgtChip
  let tgtQty
  let tgtDir
  checks.forEach(chk => {
    const opt = chk.className
    const chip = chk.parentElement.parentElement.getElementsByClassName('chip')
    const qty  = chk.parentElement.parentElement.getElementsByClassName('ordQty')
    const dir = chk.parentElement.parentElement.getElementsByClassName('ordDir')

    if (opt == 'chkCall') {
      tgtChip = chip[0]
      tgtQty = qty[0]
      tgtDir = dir[0]
    } else  {
      tgtChip = chip[1]
      tgtQty = qty[1]
      tgtDir = dir[1]
    }
    tgtChip.classList.remove('BUY')
    tgtChip.classList.remove('SELL')
    tgtChip.innerText = ''
    tgtQty.value = 0
    tgtDir.value = ''
    chk.click()
  });

}

