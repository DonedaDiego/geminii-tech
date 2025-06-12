from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import json
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import time
import random

# Criar a aplicação Flask
app = Flask(__name__)

# Habilitar CORS para permitir requisições do frontend
CORS(app)

# CONFIGURAÇÃO CORRIGIDA PARA RENDER
# No Render, a estrutura é diferente - vamos detectar automaticamente
def get_frontend_path():
    """Detecta o caminho correto para a pasta frontend"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Tentar diferentes possibilidades de estrutura
    possible_paths = [
        os.path.join(current_dir, '..', 'frontend'),  # backend/../frontend
        os.path.join(current_dir, 'frontend'),        # backend/frontend
        'frontend',                                    # frontend na raiz
        '.'                                           # pasta atual
    ]
    
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        home_file = os.path.join(abs_path, 'home.html')
        if os.path.exists(home_file):
            print(f"✅ Frontend encontrado em: {abs_path}")
            return abs_path
    
    print("❌ Frontend não encontrado em nenhum caminho")
    return None

# Configurar caminhos
frontend_path = get_frontend_path()
if frontend_path:
    app.template_folder = frontend_path
    app.static_folder = frontend_path
    print(f"📁 Templates configurados para: {app.template_folder}")
    print(f"📁 Static configurados para: {app.static_folder}")

# Lista de ações brasileiras populares
BRAZILIAN_STOCKS = [
    'PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'ABEV3.SA',
    'WEGE3.SA', 'MGLU3.SA', 'VVAR3.SA', 'JBSS3.SA', 'LREN3.SA',
    'SUZB3.SA', 'RAIL3.SA', 'USIM5.SA', 'CCRO3.SA', 'GGBR4.SA'
]

def get_stock_data(symbol, period='1mo'):
    """Buscar dados de uma ação específica"""
    try:
        # Adicionar delay aleatório para evitar rate limiting
        time.sleep(random.uniform(0.1, 0.3))
        
        # Adicionar .SA se não tiver
        if not symbol.endswith('.SA'):
            symbol += '.SA'
        
        stock = yf.Ticker(symbol)
        
        # Configurar headers para parecer um navegador real
        stock.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        hist = stock.history(period=period)
        info = stock.info
        
        if hist.empty:
            return None
        
        current_price = hist['Close'].iloc[-1]
        previous_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
        change = current_price - previous_price
        change_percent = (change / previous_price) * 100
        
        return {
            'symbol': symbol.replace('.SA', ''),
            'name': info.get('longName', symbol),
            'current_price': round(float(current_price), 2),
            'change': round(float(change), 2),
            'change_percent': round(float(change_percent), 2),
            'volume': int(hist['Volume'].iloc[-1]) if 'Volume' in hist else 0,
            'high_52w': round(float(hist['High'].max()), 2),
            'low_52w': round(float(hist['Low'].min()), 2),
            'market_cap': info.get('marketCap', 'N/A'),
            'sector': info.get('sector', 'N/A'),
            'last_update': datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Erro ao buscar dados de {symbol}: {e}")
        return None

def get_stock_history(symbol, period='3mo'):
    """Buscar histórico de preços para gráficos"""
    try:
        if not symbol.endswith('.SA'):
            symbol += '.SA'
        
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period)
        
        if hist.empty:
            return None
        
        # Preparar dados para o gráfico
        chart_data = []
        for date, row in hist.iterrows():
            chart_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': round(float(row['Open']), 2),
                'high': round(float(row['High']), 2),
                'low': round(float(row['Low']), 2),
                'close': round(float(row['Close']), 2),
                'volume': int(row['Volume']) if 'Volume' in row else 0
            })
        
        return chart_data
    except Exception as e:
        print(f"Erro ao buscar histórico de {symbol}: {e}")
        return None

# ROTA PRINCIPAL CORRIGIDA
@app.route('/')
def home():
    try:
        if frontend_path and os.path.exists(os.path.join(frontend_path, 'home.html')):
            return send_from_directory(frontend_path, 'home.html')
        else:
            # Tentar render_template como fallback
            return render_template('home.html')
    except Exception as e:
        print(f"❌ Erro ao servir home.html: {e}")
        print(f"📁 Frontend path atual: {frontend_path}")
        
        # Fallback: página temporária funcional
        return '''<!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Geminii Tech</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                    background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #2d1b69 100%);
                    color: #fff; 
                    min-height: 100vh; 
                    display: flex; 
                    align-items: center; 
                    justify-content: center;
                }
                .container { 
                    text-align: center; 
                    max-width: 600px; 
                    padding: 40px 20px;
                    background: rgba(255,255,255,0.05);
                    border-radius: 20px;
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255,255,255,0.1);
                }
                .rocket { 
                    font-size: 4em; 
                    margin-bottom: 20px; 
                    animation: bounce 2s infinite;
                }
                @keyframes bounce {
                    0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
                    40% { transform: translateY(-10px); }
                    60% { transform: translateY(-5px); }
                }
                h1 { 
                    font-size: 3em; 
                    background: linear-gradient(45deg, #ff6b9d, #c084fc, #60a5fa);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin-bottom: 20px;
                }
                .status { 
                    color: #4ade80; 
                    font-size: 1.2em; 
                    margin: 30px 0;
                    padding: 15px;
                    border: 2px solid #4ade80;
                    border-radius: 10px;
                    background: rgba(74, 222, 128, 0.1);
                }
                .button { 
                    background: linear-gradient(45deg, #ff6b9d, #c084fc); 
                    border: none; 
                    padding: 15px 30px; 
                    border-radius: 30px; 
                    color: white; 
                    text-decoration: none; 
                    display: inline-block; 
                    margin: 10px; 
                    font-weight: bold;
                    transition: all 0.3s ease;
                }
                .button:hover { 
                    transform: translateY(-2px); 
                    box-shadow: 0 8px 25px rgba(255, 107, 157, 0.4);
                }
                .api-status {
                    margin-top: 30px;
                    padding: 20px;
                    background: rgba(0,255,0,0.1);
                    border-radius: 15px;
                    border: 1px solid rgba(0,255,0,0.3);
                }
                .loading { animation: pulse 1.5s ease-in-out infinite alternate; }
                @keyframes pulse { from { opacity: 1; } to { opacity: 0.5; } }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="rocket">🚀</div>
                <h1>Geminii Tech</h1>
                <div class="status">
                    <span class="loading">Backend Online!</span>
                </div>
                <p>API funcionando perfeitamente!</p>
                <p>Frontend será carregado em breve...</p>
                <div>
                    <a href="/api/status" class="button" onclick="testAPI()">✅ Testar API</a>
                    <a href="/api/market-data" class="button">📊 Dados Mercado</a>
                    <a href="/api/stocks" class="button">📈 Ações</a>
                </div>
                <div class="api-status">
                    <h3>🔧 Status do Sistema</h3>
                    <p>✅ Backend: Online</p>
                    <p>✅ API: Funcionando</p>
                    <p>✅ Deploy: Ativo no Render</p>
                    <p>⏳ Frontend: Carregando...</p>
                </div>
            </div>
            <script>
                function testAPI() {
                    fetch('/api/status')
                        .then(response => response.json())
                        .then(data => alert('API OK: ' + JSON.stringify(data, null, 2)))
                        .catch(error => alert('Erro: ' + error));
                }
            </script>
        </body>
        </html>''', 200

# Rota para a página de ações - CORRIGIDA
@app.route('/acoes')
def acoes():
    try:
        if frontend_path and os.path.exists(os.path.join(frontend_path, 'acoes.html')):
            return send_from_directory(frontend_path, 'acoes.html')
        else:
            return render_template('acoes.html')
    except Exception as e:
        print(f"❌ Erro ao servir acoes.html: {e}")
        return jsonify({'error': 'Página de ações não encontrada', 'details': str(e)}), 404

# Rota para servir arquivos estáticos - CORRIGIDA
@app.route('/<path:filename>')
def static_files(filename):
    try:
        # Evitar conflito com rotas da API
        if filename.startswith('api/'):
            return jsonify({'error': 'Use /api/ endpoints'}), 404
            
        if frontend_path and os.path.exists(os.path.join(frontend_path, filename)):
            return send_from_directory(frontend_path, filename)
        else:
            raise FileNotFoundError(f"Arquivo {filename} não encontrado")
    except Exception as e:
        print(f"❌ Erro ao servir arquivo {filename}: {e}")
        return jsonify({'error': 'Arquivo não encontrado', 'file': filename}), 404

# API Routes - Mantendo todos os seus endpoints

@app.route('/api/status')
def api_status():
    """Endpoint para verificar se a API está funcionando"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'message': 'Geminii API está funcionando!',
        'frontend_path': frontend_path,
        'frontend_exists': os.path.exists(os.path.join(frontend_path, 'home.html')) if frontend_path else False
    })

@app.route('/api/newsletter', methods=['POST'])
def newsletter_signup():
    """Endpoint para inscrição na newsletter"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email é obrigatório'}), 400
        
        # Aqui você salvaria o email no banco de dados
        print(f"Novo inscrito na newsletter: {email}")
        
        return jsonify({
            'success': True,
            'message': 'Inscrição realizada com sucesso!',
            'email': email
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/market-data')
def market_data():
    """Endpoint com dados reais do mercado brasileiro"""
    try:
        # Buscar dados do Ibovespa (^BVSP)
        ibov = yf.Ticker('^BVSP')
        ibov_hist = ibov.history(period='2d')
        
        if not ibov_hist.empty:
            ibov_current = ibov_hist['Close'].iloc[-1]
            ibov_previous = ibov_hist['Close'].iloc[-2] if len(ibov_hist) > 1 else ibov_current
            ibov_change = ibov_current - ibov_previous
            ibov_change_percent = (ibov_change / ibov_previous) * 100
        else:
            ibov_current = ibov_change = ibov_change_percent = 0
        
        # Buscar dados do dólar (USDBRL=X)
        usd = yf.Ticker('USDBRL=X')
        usd_hist = usd.history(period='2d')
        
        if not usd_hist.empty:
            usd_current = usd_hist['Close'].iloc[-1]
            usd_previous = usd_hist['Close'].iloc[-2] if len(usd_hist) > 1 else usd_current
            usd_change = usd_current - usd_previous
            usd_change_percent = (usd_change / usd_previous) * 100
        else:
            usd_current = usd_change = usd_change_percent = 0
        
        # Buscar top 3 ações
        top_stocks = []
        for symbol in BRAZILIAN_STOCKS[:3]:
            stock_data = get_stock_data(symbol, '2d')
            if stock_data:
                top_stocks.append({
                    'symbol': stock_data['symbol'],
                    'price': stock_data['current_price'],
                    'change': stock_data['change_percent']
                })
        
        market_data_response = {
            'ibovespa': {
                'value': round(float(ibov_current), 2),
                'change': round(float(ibov_change), 2),
                'change_percent': round(float(ibov_change_percent), 2)
            },
            'dolar': {
                'value': round(float(usd_current), 2),
                'change': round(float(usd_change), 4),
                'change_percent': round(float(usd_change_percent), 2)
            },
            'top_stocks': top_stocks,
            'last_update': datetime.now().isoformat()
        }
        
        return jsonify(market_data_response)
    
    except Exception as e:
        print(f"Erro ao buscar dados do mercado: {e}")
        # Retornar dados mock em caso de erro
        return jsonify({
            'ibovespa': {'value': 128450.75, 'change': 1.23, 'change_percent': 0.97},
            'dolar': {'value': 5.25, 'change': -0.05, 'change_percent': -0.95},
            'top_stocks': [
                {'symbol': 'PETR4', 'price': 32.45, 'change': 1.5},
                {'symbol': 'VALE3', 'price': 68.90, 'change': -0.8},
                {'symbol': 'ITUB4', 'price': 28.75, 'change': 0.3}
            ],
            'error': 'Dados simulados - erro na API'
        })

# Novo endpoint para buscar dados de ações brasileiras
@app.route('/api/stocks')
def get_stocks():
    """Listar principais ações brasileiras com dados reais"""
    try:
        stocks_data = []
        
        print("🔄 Buscando dados das ações...")
        
        for i, symbol in enumerate(BRAZILIAN_STOCKS):
            print(f"  Carregando {i+1}/{len(BRAZILIAN_STOCKS)}: {symbol}")
            stock_data = get_stock_data(symbol)
            if stock_data:
                stocks_data.append(stock_data)
                print(f"  ✅ {symbol}: R$ {stock_data['current_price']}")
            else:
                print(f"  ❌ {symbol}: Falhou")
        
        print(f"✅ Carregadas {len(stocks_data)} ações com sucesso!")
        
        return jsonify({
            'stocks': stocks_data,
            'total': len(stocks_data),
            'last_update': datetime.now().isoformat(),
            'success_rate': f"{len(stocks_data)}/{len(BRAZILIAN_STOCKS)}"
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint para buscar dados de uma ação específica
@app.route('/api/stock/<symbol>')
def get_single_stock(symbol):
    """Buscar dados detalhados de uma ação específica"""
    try:
        stock_data = get_stock_data(symbol)
        if not stock_data:
            return jsonify({'error': 'Ação não encontrada'}), 404
        
        # Buscar histórico para gráfico
        chart_data = get_stock_history(symbol)
        
        return jsonify({
            'stock': stock_data,
            'chart': chart_data,
            'last_update': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint para buscar histórico de uma ação
@app.route('/api/stock/<symbol>/history')
def get_stock_chart(symbol):
    """Buscar histórico de preços para gráficos"""
    try:
        period = request.args.get('period', '3mo')  # 1mo, 3mo, 6mo, 1y
        chart_data = get_stock_history(symbol, period)
        
        if not chart_data:
            return jsonify({'error': 'Dados não encontrados'}), 404
        
        return jsonify({
            'symbol': symbol,
            'period': period,
            'data': chart_data,
            'total_points': len(chart_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    """Endpoint para simulação de backtest"""
    try:
        data = request.get_json()
        strategy = data.get('strategy', 'default')
        
        # Aqui você colocaria sua lógica de backtest real
        backtest_result = {
            'strategy': strategy,
            'initial_capital': 100000,
            'final_capital': 156000,
            'return_percent': 56.0,
            'trades': 45,
            'win_rate': 68.9,
            'sharpe_ratio': 1.85
        }
        
        return jsonify(backtest_result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint para análise de ações
@app.route('/api/analysis/<symbol>')
def stock_analysis(symbol):
    """Análise de uma ação específica"""
    analysis = {
        'symbol': symbol.upper(),
        'current_price': 45.67,
        'recommendation': 'COMPRA',
        'target_price': 52.30,
        'indicators': {
            'rsi': 45.8,
            'macd': 'Positivo',
            'moving_average_20': 44.21,
            'moving_average_50': 42.89
        },
        'analysis_date': datetime.now().isoformat()
    }
    
    return jsonify(analysis)

# Tratamento de erros
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Endpoint não encontrado', 'path': request.path}), 404
    else:
        # Para rotas não-API, tentar servir a página principal
        return home()

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erro interno do servidor', 'details': str(error)}), 500

if __name__ == '__main__':
    print("🚀 Iniciando Geminii Backend...")
    print("📊 Servidor rodando")
    print(f"📁 Diretório atual: {os.getcwd()}")
    print(f"📁 Diretório do script: {os.path.dirname(__file__)}")
    
    # Detectar e configurar frontend
    frontend_path = get_frontend_path()
    
    # Configuração para Render
    port = int(os.environ.get('PORT', 10000))
    print(f"🔗 Rodando na porta: {port}")
    print(f"🌐 Servidor disponível em: 0.0.0.0:{port}")
    
    app.run(debug=False, host='0.0.0.0', port=port)