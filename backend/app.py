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

# Configurar pasta de templates (onde está o HTML)
app.template_folder = '../frontend'
app.static_folder = '../frontend'

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

# Rota principal - servir o HTML
@app.route('/')
def home():
    return send_from_directory('../frontend', 'home.html')

# Rota para a página de ações
@app.route('/acoes')
def acoes():
    return send_from_directory('../frontend', 'acoes.html')

# Rota para servir arquivos estáticos (CSS, JS, imagens)
@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('../frontend', filename)

# API Routes - Exemplos que você pode usar no seu frontend

@app.route('/api/status')
def api_status():
    """Endpoint para verificar se a API está funcionando"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'message': 'Geminii API está funcionando!'
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
        # Por enquanto, vamos só simular
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
        # Por enquanto, dados simulados
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
    # Dados fictícios para demonstração
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
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    print("🚀 Iniciando Geminii Backend...")
    print("📊 Servidor rodando em: http://localhost:5000")
    print("🔗 API disponível em: http://localhost:5000/api/")
    
    # Rodar em modo debug para desenvolvimento
    app.run(debug=True, host='0.0.0.0', port=5000)