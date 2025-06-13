from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import yfinance as yf
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configuração do banco LOCAL
def get_local_db_connection():
    """Conecta no PostgreSQL (local ou produção)"""
    try:
        # ✅ Se estiver no Render (produção), usa DATABASE_URL
        if os.environ.get('DATABASE_URL'):
            print("🌐 Conectando no banco de produção (Render)...")
            return psycopg2.connect(os.environ.get('DATABASE_URL'))
        else:
            # ✅ Local (seu computador)
            print("💻 Conectando no banco local...")
            return psycopg2.connect(
                host="localhost",
                database="postgres",
                user="postgres",
                password="#geminii",
                port="5432"
            )
    except Exception as e:
        print(f"❌ Erro de conexão com banco: {e}")
        raise

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

# ROTAS PARA HTML
@app.route('/')
def index():
    return send_from_directory('../frontend', 'home.html')

@app.route('/home.html')
def home():
    return send_from_directory('../frontend', 'home.html')

@app.route('/monitor-basico.html')
def monitor_basico():
    return send_from_directory('../frontend', 'monitor-basico.html')

@app.route('/radar-setores.html')
def radar_setores():
    return send_from_directory('../frontend', 'radar-setores.html')

# ROTAS DA API - AÇÕES
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

# ROTAS DA API - SETORES
@app.route('/api/setores')
def get_setores():
    """Lista todos os setores com quantidade de empresas"""
    try:
        print("🔍 Conectando no banco para buscar setores...")
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        # Primeiro verificar se a tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'setor_b3'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        if not table_exists:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Tabela setor_b3 não encontrada'}), 404
        
        # Buscar setores
        cursor.execute("""
            SELECT 
                setor_economico,
                COUNT(*) as total_empresas
            FROM setor_b3 
            GROUP BY setor_economico 
            ORDER BY total_empresas DESC
        """)
        
        setores = cursor.fetchall()
        cursor.close()
        conn.close()
        
        result = []
        for setor in setores:
            result.append({
                'setor_economico': setor[0],
                'total_empresas': setor[1]
            })
        
        print(f"✅ Encontrados {len(result)} setores")
        
        return jsonify({
            'success': True, 
            'data': result,
            'total_setores': len(result)
        })
        
    except Exception as e:
        print(f"❌ Erro na API setores: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/setor/<setor_nome>')
def get_empresas_setor(setor_nome):
    """Buscar empresas por setor"""
    try:
        print(f"🔍 Buscando empresas do setor: {setor_nome}")
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT acao, ticker, setor_economico, nivel_na_bolsa, tipo
            FROM setor_b3 
            WHERE setor_economico ILIKE %s 
            ORDER BY acao
            LIMIT 10
        """, (f'%{setor_nome}%',))
        
        empresas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        result = []
        for empresa in empresas:
            result.append({
                'empresa': empresa[0],  # acao
                'ticker': empresa[1],
                'setor_economico': empresa[2],
                'nivel_bolsa': empresa[3],
                'tipo_governanca': empresa[4]
            })
        
        print(f"✅ Encontradas {len(result)} empresas")
        
        return jsonify({
            'success': True, 
            'data': result,
            'total_empresas': len(result),
            'setor': setor_nome
        })
        
    except Exception as e:
        print(f"❌ Erro ao buscar empresas do setor {setor_nome}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/empresa/<ticker>')
def get_empresa_info(ticker):
    """Buscar informações completas de uma empresa"""
    try:
        print(f"🔍 Buscando informações da empresa: {ticker}")
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, setor_economico, setor, setor_puro, segmento, acao, ticker, nivel_na_bolsa, tipo
            FROM setor_b3 
            WHERE ticker = %s
        """, (ticker.upper(),))
        
        empresa = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if empresa:
            return jsonify({
                'success': True, 
                'data': {
                    'id': empresa[0],
                    'setor_economico': empresa[1],
                    'setor': empresa[2],
                    'setor_puro': empresa[3],
                    'segmento': empresa[4],
                    'empresa': empresa[5],  # acao
                    'ticker': empresa[6],
                    'nivel_bolsa': empresa[7],
                    'tipo_governanca': empresa[8]
                }
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Empresa não encontrada'
            }), 404
            
    except Exception as e:
        print(f"❌ Erro ao buscar empresa {ticker}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ROTAS DA API - UTILITÁRIAS
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

# ROTA DE TESTE DO BANCO
@app.route('/api/test-db')
def test_db():
    """Rota para testar conexão com banco"""
    try:
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        # Testar conexão
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM setor_b3;")
        total = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'postgres_version': version,
            'total_empresas': total,
            'message': 'Banco funcionando!'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 Iniciando Geminii API...")
    print("📊 APIs disponíveis:")
    print("  - /api/setores")
    print("  - /api/setor/<nome>")
    print("  - /api/empresa/<ticker>")
    print("  - /api/test-db")
    app.run(host='0.0.0.0', port=port, debug=True)