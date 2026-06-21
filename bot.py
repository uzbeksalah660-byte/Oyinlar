<!DOCTYPE html>                                                                                                                              <html lang="uz">                                                                                                                             <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Kliker Oyin</title>
    <style>
        * {
            box-sizing: border-box;                                                                                                                      user-select: none;                                                                                                                           -webkit-user-select: none;
            margin: 0;
            padding: 0;                                                                                                                              }
        body {
            background: radial-gradient(circle, #1a1a2e 0%, #0f0f1b 100%);                                                                               color: #fff;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;                                                                                                                         justify-content: space-between;
            height: 100vh;
            overflow: hidden;
            padding: 20px;
        }                                                                                                                                            .header {
            text-align: center;
            margin-top: 20px;                                                                                                                        }                                                                                                                                            .score-box {                                                                                                                                     font-size: 42px;
            font-weight: bold;
            color: #ffd700;
            text-shadow: 0 0 20px rgba(255, 215, 0, 0.6);
            margin-bottom: 5px;                                                                                                                      }                                                                                                                                            .cps-box {
            font-size: 16px;
            color: #4ade80;                                                                                                                          }                                                                                                                                            .coin-container {
            flex: 1;
            display: flex;                                                                                                                               align-items: center;                                                                                                                         justify-content: center;                                                                                                                     position: relative;                                                                                                                          width: 100%;
        }
        .coin {                                                                                                                                          width: 200px;
            height: 200px;
            background: radial-gradient(circle, #ffe066 0%, #f5b041 70%, #d35400 100%);                                                                  border-radius: 50%;                                                                                                                          box-shadow: 0 0 30px rgba(245, 176, 65, 0.5), inset 0 0 15px rgba(255,255,255,0.6);                                                          border: 8px solid #f39c12;
            display: flex;
            align-items: center;                                                                                                                         justify-content: center;                                                                                                                     font-size: 64px;                                                                                                                             cursor: pointer;
            transition: transform 0.05s ease;
        }                                                                                                                                            .coin:active {
            transform: scale(0.92);
        }                                                                                                                                            .shop-container {
            width: 100%;
            max-width: 400px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;                                                                                                                         padding: 15px;                                                                                                                               backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 20px;                                                                                                                     }                                                                                                                                            .shop-item {
            display: flex;
            justify-content: space-between;                                                                                                              align-items: center;                                                                                                                         background: rgba(255, 255, 255, 0.03);                                                                                                       padding: 10px 15px;                                                                                                                          border-radius: 10px;                                                                                                                         margin-bottom: 10px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }                                                                                                                                            .shop-item:last-child {                                                                                                                          margin-bottom: 0;
        }
        .item-info h3 {                                                                                                                                  font-size: 16px;                                                                                                                             color: #fff;
        }
        .item-info p {                                                                                                                                   font-size: 12px;                                                                                                                             color: #a0aec0;
        }
        .buy-btn {                                                                                                                                       background: #3182ce;                                                                                                                         color: white;                                                                                                                                border: none;
            padding: 8px 15px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;                                                                                                                             cursor: pointer;                                                                                                                         }
        .buy-btn:active {
            background: #2b6cb0;
        }
        .floating-text {                                                                                                                                 position: absolute;                                                                                                                          color: #ffd700;                                                                                                                              font-size: 28px;
            font-weight: bold;
            pointer-events: none;                                                                                                                        animation: floatUp 0.6s ease-out forwards;
            text-shadow: 0 0 10px rgba(255,215,0,0.8);
        }
        @keyframes floatUp {
            0% { opacity: 1; transform: translateY(0) scale(1); }                                                                                        100% { opacity: 0; transform: translateY(-100px) scale(0.8); }                                                                           }                                                                                                                                        </style>                                                                                                                                 </head>
<body>
                                                                                                                                                 <div class="header">                                                                                                                             <div class="score-box" id="balance">0</div>                                                                                                  <div class="cps-box" id="cps-info">Avto-daromad: 0/sek</div>
    </div>
                                                                                                                                                 <div class="coin-container" id="coin-area">
        <div class="coin" id="main-coin">🪙</div>
    </div>

    <div class="shop-container">
        <div class="shop-item">
            <div class="item-info">                                                                                                                          <h3>Kuchli Klik (+1 klik)</h3>                                                                                                               <p>Narxi: <span id="click-cost">15</span> tanga</p>                                                                                      </div>
            <button class="buy-btn" id="buy-click">Sotib olish</button>
        </div>                                                                                                                                       <div class="shop-item">
            <div class="item-info">
                <h3>Avto-Konchi (+1/sek)</h3>
                <p>Narxi: <span id="miner-cost">100</span> tanga</p>
            </div>
            <button class="buy-btn" id="buy-miner">Sotib olish</button>
        </div>
    </div>

    <script>
        let balance = 0;                                                                                                                             let clickPower = 1;                                                                                                                          let clickUpgradeCost = 15;
        let minersCount = 0;
        let minerUpgradeCost = 100;                                                                                                          
        const balanceEl = document.getElementById('balance');
        const cpsInfoEl = document.getElementById('cps-info');
        const coinEl = document.getElementById('main-coin');
        const coinArea = document.getElementById('coin-area');                                                                               
        const buyClickBtn = document.getElementById('buy-click');
        const clickCostEl = document.getElementById('click-cost');                                                                                   const buyMinerBtn = document.getElementById('buy-miner');                                                                                    const minerCostEl = document.getElementById('miner-cost');                                                                           
        // Klik hodisasi
        coinEl.addEventListener('touchstart', (e) => {                                                                                                   e.preventDefault();
            balance += clickPower;
            updateUI();

            // Ko'p barmoq bilan bosganda ham sonlarni chiqarish                                                                                         for(let i=0; i<e.touches.length; i++) {                                                                                                          createFloatingText(e.touches[i].clientX, e.touches[i].clientY, `+${clickPower}`);                                                        }
        });

        // Uchar sonlar effekti
        function createFloatingText(x, y, text) {                                                                                                        const el = document.createElement('div');                                                                                                    el.className = 'floating-text';                                                                                                              el.innerText = text;                                                                                                                         el.style.left = `${x - 20}px`;
            el.style.top = `${y - 40}px`;
            document.body.appendChild(el);

            setTimeout(() => {                                                                                                                               el.remove();
            }, 600);
        }

        // Kuchli Klik sotib olish                                                                                                                   buyClickBtn.addEventListener('click', () => {                                                                                                    if (balance >= clickUpgradeCost) {
                balance -= clickUpgradeCost;
                clickPower += 1;                                                                                                                             clickUpgradeCost = Math.floor(clickUpgradeCost * 1.5);                                                                                       updateUI();
            }
        });                                                                                                                                                                                                                                                                                       // Avto-Konchi sotib olish
        buyMinerBtn.addEventListener('click', () => {
            if (balance >= minerUpgradeCost) {                                                                                                               balance -= minerUpgradeCost;                                                                                                                 minersCount += 1;                                                                                                                            minerUpgradeCost = Math.floor(minerUpgradeCost * 1.6);
                updateUI();
            }                                                                                                                                        });

        // Avto daromad taymeri (Har soniyada)                                                                                                       setInterval(() => {                                                                                                                              if (minersCount > 0) {
                balance += minersCount;
                updateUI();                                                                                                                              }                                                                                                                                        }, 1000);                                                                                                                            
        // UI yangilash
        function updateUI() {
            balanceEl.innerText = Math.floor(balance);
            cpsInfoEl.innerText = `Avto-daromad: ${minersCount}/sek`;
            clickCostEl.innerText = clickUpgradeCost;
            minerCostEl.innerText = minerUpgradeCost;
        }

        updateUI();
    </script>
</body>
</html>
