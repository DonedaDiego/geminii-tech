from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

# Configuração para produção
if os.environ.get('FLASK_ENV') == 'production':
    app.config['DEBUG'] = False
else:
    app.config['DEBUG'] = True

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

# Rota principal
@app.route('/')
def index():
    return render_template('index.html')

# Rota para página de ações
@app.route('/acoes')
def acoes():
    return render_template('acoes.html')

# API para buscar dados de uma ação específica
@app.route('/api/stock/<symbol>')
def get_stock(symbol):
    data = get_stock_data(symbol)
    if data:
        return jsonify({'success': True, 'data': data})
    else:
        return jsonify({'success': False, 'error': 'Ação não encontrada'}), 404

# API para buscar múltiplas ações
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

# API de status
@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'message': 'API funcionando',
        'timestamp': datetime.now().isoformat()
    })

# API para newsletter (simulação)
@app.route('/api/newsletter', methods=['POST'])
def newsletter():
    data = request.get_json()
    email = data.get('email')
    
    if email and '@' in email:
        return jsonify({
            'success': True,
            'message': 'E-mail cadastrado com sucesso!',
            'email': email
        })
    else:
        return jsonify({
            'success': False,
            'error': 'E-mail inválido'
        }), 400

# API para backtest (simulação)
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
    app.run(host='0.0.0.0', port=port)