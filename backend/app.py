from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import yfinance as yf
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Função para buscar dados das ações
def get_stock_data(symbol, period='1mo'):
    try:
        # Adiciona .SA para ações brasileiras
        if not symbol.endswith('.SA'):
            symbol += '.SA'
        
        stock = yf.Ticker(symbol)
        data = stock.history(period=period)
        
        if data.empty:
            return None
        
        # Pega o último preço
        current_price = data['Close'].iloc[-1]
        
        # Calcula variação
        previous_price = data['Close'].iloc[-2] if len(data) > 1 else current_price
        change = current_price - previous_price
        change_percent = (change / previous_price) * 100
        
        # Dados para gráfico (últimos 30 dias)
        chart_data = []
        for i, (date, row) in enumerate(data.tail(30).iterrows()):
            chart_data.append({
                'date': date.strftime('%d/%m'),
                'price': round(row['Close'], 2),
                'volume': int(row['Volume'])
            })
        
        return {
            'symbol': symbol.replace('.SA', ''),
            'current_price': round(current_price, 2),
            'change': round(change, 2),
            'change_percent': round(change_percent, 2),
            'volume': int(data['Volume'].iloc[-1]),
            'chart_data': chart_data,
            'last_update': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
    except Exception as e:
        print(f"Erro ao buscar dados para {symbol}: {e}")
        return None

# Rota principal - serve seu HTML atual
@app.route('/')
def index():
    # Serve seu home.html que está em ../frontend/
    return send_from_directory('../frontend', 'home.html')

# Rota para página de ações (serve o HTML inline temporariamente)
@app.route('/acoes')
def acoes():
    # HTML da página de ações inline (temporário)
    return '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ações - Geminii Tech</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body { font-family: 'Inter', sans-serif; }
    .stock-card {
      background: rgba(255, 255, 255, 0.08);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 16px;
      transition: all 0.3s ease;
    }
    .stock-card:hover {
      transform: translateY(-5px);
      box-shadow: 0 20px 40px rgba(186, 57, 175, 0.2);
    }
    .positive { color: #10b981; }
    .negative { color: #ef4444; }
    .loading { animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
  </style>
</head>
<body class="bg-gradient-to-br from-gray-900 via-black to-purple-900 text-white min-h-screen">
  
  <header class="p-6 border-b border-white border-opacity-10">
    <div class="max-w-6xl mx-auto flex items-center justify-between">
      <div class="flex items-center gap-4">
        <img src="https://app.geminii.com.br/wp-content/uploads/2025/06/logo.png" alt="Geminii" class="w-8 h-8">
        <h1 class="text-2xl font-bold text-purple-400">Ações em Tempo Real</h1>
      </div>
      <a href="/" class="px-4 py-2 bg-purple-600 rounded-lg hover:bg-purple-700 transition-colors">
        <i class="fas fa-home mr-2"></i>Home
      </a>
    </div>
  </header>

  <div class="max-w-6xl mx-auto p-6">
    
    <div class="mb-8">
      <div class="flex flex-col md:flex-row gap-4 items-center justify-between">
        <div class="flex gap-2">
          <input 
            id="stockInput" 
            type="text" 
            placeholder="Digite o código da ação (ex: PETR4)" 
            class="px-4 py-2 bg-white bg-opacity-10 border border-white border-opacity-20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-400"
          >
          <button id="addStockBtn" class="px-6 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors">
            <i class="fas fa-plus mr-2"></i>Adicionar
          </button>
        </div>
        
        <button id="refreshBtn" class="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition-colors">
          <i class="fas fa-sync-alt mr-2"></i>Atualizar Dados
        </button>
      </div>
    </div>

    <div id="statusMsg" class="mb-6 p-4 rounded-lg hidden"></div>
    <div id="stocksGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"></div>

    <div id="chartSection" class="mt-12 hidden">
      <h2 class="text-2xl font-bold mb-6 text-center">Gráfico Detalhado</h2>
      <div class="stock-card p-6">
        <div class="flex justify-between items-center mb-4">
          <h3 id="chartTitle" class="text-xl font-semibold"></h3>
          <span id="chartPrice" class="text-2xl font-bold text-purple-400"></span>
        </div>
        <canvas id="stockChart" width="400" height="200"></canvas>
      </div>
    </div>
  </div>

  <script>
    const API_BASE = '/api';
    let currentChart = null;
    const defaultStocks = ['PETR4', 'VALE3', 'ITUB4', 'BBDC4'];
    let watchList = [...defaultStocks];
    
    const stocksGrid = document.getElementById('stocksGrid');
    const stockInput = document.getElementById('stockInput');
    const addStockBtn = document.getElementById('addStockBtn');
    const refreshBtn = document.getElementById('refreshBtn');
    const statusMsg = document.getElementById('statusMsg');
    const chartSection = document.getElementById('chartSection');
    
    function showStatus(message, type = 'info') {
      statusMsg.className = `mb-6 p-4 rounded-lg ${type === 'success' ? 'bg-green-600' : type === 'error' ? 'bg-red-600' : 'bg-blue-600'}`;
      statusMsg.textContent = message;
      statusMsg.classList.remove('hidden');
      setTimeout(() => statusMsg.classList.add('hidden'), 3000);
    }
    
    function formatCurrency(value) {
      return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
    }
    
    async function fetchStockData(symbol) {
      try {
        const response = await fetch(`${API_BASE}/stock/${symbol}`);
        const data = await response.json();
        return data.success ? data.data : null;
      } catch (error) {
        console.error('Erro ao buscar ação:', error);
        return null;
      }
    }
    
    function createStockCard(stockData) {
      const isPositive = stockData.change >= 0;
      const changeClass = isPositive ? 'positive' : 'negative';
      const changeIcon = isPositive ? 'fa-arrow-up' : 'fa-arrow-down';
      
      return `
        <div class="stock-card p-6 cursor-pointer" onclick="showChart('${stockData.symbol}')">
          <div class="flex justify-between items-start mb-4">
            <div>
              <h3 class="text-xl font-bold">${stockData.symbol}</h3>
              <p class="text-gray-400 text-sm">${stockData.last_update}</p>
            </div>
            <button onclick="removeStock('${stockData.symbol}', event)" class="text-red-400 hover:text-red-300">
              <i class="fas fa-times"></i>
            </button>
          </div>
          
          <div class="space-y-3">
            <div>
              <span class="text-3xl font-bold text-purple-400">${formatCurrency(stockData.current_price)}</span>
            </div>
            
            <div class="flex items-center gap-2">
              <i class="fas ${changeIcon} ${changeClass}"></i>
              <span class="${changeClass} font-semibold">
                ${formatCurrency(Math.abs(stockData.change))} (${Math.abs(stockData.change_percent).toFixed(2)}%)
              </span>
            </div>
            
            <div class="grid grid-cols-2 gap-4 pt-4 border-t border-white border-opacity-10">
              <div>
                <p class="text-gray-400 text-xs">Volume</p>
                <p class="font-semibold">${stockData.volume.toLocaleString('pt-BR')}</p>
              </div>
              <div>
                <p class="text-gray-400 text-xs">Dados</p>
                <p class="font-semibold">${stockData.chart_data.length} pontos</p>
              </div>
            </div>
          </div>
        </div>
      `;
    }
    
    async function updateStocksGrid() {
      stocksGrid.innerHTML = '<div class="col-span-full text-center loading text-2xl">📊 Carregando ações...</div>';
      
      const stocksData = [];
      for (const symbol of watchList) {
        const data = await fetchStockData(symbol);
        if (data) stocksData.push(data);
      }
      
      if (stocksData.length === 0) {
        stocksGrid.innerHTML = '<div class="col-span-full text-center text-gray-400">❌ Nenhuma ação encontrada</div>';
        return;
      }
      
      stocksGrid.innerHTML = stocksData.map(createStockCard).join('');
      showStatus(`✅ ${stocksData.length} ações carregadas!`, 'success');
    }
    
    function addStock() {
      const symbol = stockInput.value.trim().toUpperCase();
      if (!symbol) {
        showStatus('❌ Digite o código de uma ação', 'error');
        return;
      }
      if (watchList.includes(symbol)) {
        showStatus('⚠️ Ação já está na lista', 'error');
        return;
      }
      watchList.push(symbol);
      stockInput.value = '';
      showStatus(`✅ ${symbol} adicionada!`, 'success');
      updateStocksGrid();
    }
    
    function removeStock(symbol, event) {
      event.stopPropagation();
      watchList = watchList.filter(s => s !== symbol);
      showStatus(`🗑️ ${symbol} removida`, 'success');
      updateStocksGrid();
    }
    
    async function showChart(symbol) {
      const data = await fetchStockData(symbol);
      if (!data) return;
      
      chartSection.classList.remove('hidden');
      document.getElementById('chartTitle').textContent = `${symbol} - Últimos 30 dias`;
      document.getElementById('chartPrice').textContent = formatCurrency(data.current_price);
      
      const ctx = document.getElementById('stockChart').getContext('2d');
      if (currentChart) currentChart.destroy();
      
      currentChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: data.chart_data.map(d => d.date),
          datasets: [{
            label: 'Preço de Fechamento',
            data: data.chart_data.map(d => d.price),
            borderColor: '#ba39af',
            backgroundColor: 'rgba(186, 57, 175, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.4
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { labels: { color: 'white' } } },
          scales: {
            x: { ticks: { color: 'white' }, grid: { color: 'rgba(255,255,255,0.1)' } },
            y: { 
              ticks: { 
                color: 'white',
                callback: function(value) { return formatCurrency(value); }
              },
              grid: { color: 'rgba(255,255,255,0.1)' }
            }
          }
        }
      });
      
      chartSection.scrollIntoView({ behavior: 'smooth' });
    }
    
    addStockBtn.addEventListener('click', addStock);
    refreshBtn.addEventListener('click', updateStocksGrid);
    stockInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') addStock();
    });
    
    // Inicializar
    updateStocksGrid();
    setInterval(updateStocksGrid, 120000); // Auto refresh 2min
  </script>
</body>
</html>
    '''

# APIs
@app.route('/api/stock/<symbol>')
def get_stock(symbol):
    data = get_stock_data(symbol)
    if data:
        return jsonify({'success': True, 'data': data})
    else:
        return jsonify({'success': False, 'error': 'Ação não encontrada'}), 404

@app.route('/api/stocks')
def get_stocks():
    symbols = request.args.get('symbols', 'PETR4,VALE3,ITUB4').split(',')
    results = {}
    for symbol in symbols:
        symbol = symbol.strip()
        data = get_stock_data(symbol)
        if data:
            results[symbol] = data
    return jsonify({'success': True, 'data': results})

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'message': 'API funcionando',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/newsletter', methods=['POST'])
def newsletter():
    data = request.get_json()
    email = data.get('email')
    if email and '@' in email:
        return jsonify({'success': True, 'message': 'E-mail cadastrado!', 'email': email})
    return jsonify({'success': False, 'error': 'E-mail inválido'}), 400

@app.route('/api/backtest', methods=['POST'])
def backtest():
    return jsonify({
        'strategy': 'Momentum Strategy',
        'initial_capital': 100000,
        'final_capital': 168750,
        'return_percent': 68.75,
        'trades': 47,
        'win_rate': 72,
        'sharpe_ratio': 1.85
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)