const treeTraverse = (obj) => {
  let markup = ""
  let ctml = ""
  let ptml = ""
  const messages = document.getElementById('messages')
  Object.keys(obj).forEach(function(strike) {                                
      // console.log('Key : ' + strike + ', Value : ' + obj[strike])
      oStrike = obj[strike]
      markup += "<tr>"
      Object.keys(oStrike).forEach(function(options) {
      // console.log('Key : ' + options + ', Value : ' + oStrike[options])
          oPtions = oStrike[options]
          Object.keys(oPtions).forEach(function(prices) {
              if (options=="call") {
                 ctml = "<td><input type='checkbox'class='chk_call' name='chk_call' value='chk_call'></td>"
                 ctml += "<td style='text-align:right' id='" + options + "'>" + oPtions[prices].toFixed(2) + "</td>" 
              }
              else if (options=="put") {
                 ptml = "<td style='text-align:right' id='" + options + "'>" + oPtions[prices].toFixed(2) + "</td>" 
                 ptml += "<td><input type='checkbox'class='chk_put' name='chk_put' value='chk_put'></td>"

              }
          });    
      });
      markup += ctml
      markup += "<td style='text-align:center'>" + strike + "</td>"
      markup += ptml
      markup += "</tr>\n"
  })
  messages.innerHTML = markup
}

const ws = new WebSocket("ws://localhost:8000/ws");
ws.onmessage = function(event) {
  try {
      const data = event.data
      const obj = JSON.parse(data)
      treeTraverse(obj)
  }
  catch (err) {
      console.log(err)
  }
};
