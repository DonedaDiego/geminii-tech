from flask import Flask, jsonify, send_from_directory, request, g
from flask_cors import CORS
import os
from datetime import datetime
import yfinance as yf
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, coint
from statsmodels.regression.linear_model import OLS
from statsmodels.regression.rolling import RollingOLS
from datetime import datetime, timedelta
import logging
from configuracoes.database import get_local_db_connection
from configuracoes.config import Config

# ===== IMPORTAÇÕES DE AUTENTICAÇÃO =====
from auth.auth_service import AuthService
from auth.middleware import require_auth, require_plan, optional_auth

app = Flask(__name__)
CORS(app)

# ✅ SUA FUNÇÃO YFINANCE ORIGINAL (mantida igual)
def get_stock_data(symbol, period='1y'):
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

# ===== ROTAS HTML (mantidas iguais) =====
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

@app.route('/planos.html')
def planos():
    return send_from_directory('../frontend', 'planos.html')

@app.route('/planos')
def planos_sem_extensao():
    return send_from_directory('../frontend', 'planos.html')

# ===== NOVAS ROTAS HTML PARA AUTH =====
@app.route('/login.html')
def login_page():
    return send_from_directory('../frontend', 'login.html')

@app.route('/login')
def login_page_sem_extensao():
    return send_from_directory('../frontend', 'login.html')

@app.route('/register.html')
def register_page():
    return send_from_directory('../frontend', 'register.html')

@app.route('/register')
def register_page_sem_extensao():
    return send_from_directory('../frontend', 'register.html')

@app.route('/dashboard.html')
def dashboard_page():
    return send_from_directory('../frontend', 'dashboard.html')

@app.route('/dashboard')
def dashboard_page_sem_extensao():
    return send_from_directory('../frontend', 'dashboard.html')

# ===== ROTAS DE AUTENTICAÇÃO =====

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Login do usuário"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados JSON necessários'
            }), 400
        
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'E-mail e senha são obrigatórios'
            }), 400
        
        # Fazer login
        result = AuthService.login(email, password)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 401
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """Registrar novo usuário"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados JSON necessários'
            }), 400
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        plan_id = data.get('plan_id', 1)  # Plano básico por padrão
        
        # Validações
        if not name or not email or not password:
            return jsonify({
                'success': False,
                'error': 'Nome, e-mail e senha são obrigatórios'
            }), 400
        
        if len(password) < 6:
            return jsonify({
                'success': False,
                'error': 'Senha deve ter pelo menos 6 caracteres'
            }), 400
        
        if '@' not in email:
            return jsonify({
                'success': False,
                'error': 'E-mail inválido'
            }), 400
        
        # Registrar usuário
        result = AuthService.register(name, email, password, plan_id)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@app.route('/api/auth/verify', methods=['GET'])
@require_auth
def api_verify_session():
    """Verificar se sessão está válida"""
    return jsonify({
        'success': True,
        'data': {
            'user': g.current_user,
            'message': 'Sessão válida'
        }
    })

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def api_logout():
    """Logout do usuário"""
    try:
        auth_header = request.headers.get('Authorization')
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else auth_header
        
        result = AuthService.logout(token)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500

@app.route('/api/auth/profile')
@require_auth
def api_profile():
    """Perfil do usuário logado"""
    return jsonify({
        'success': True,
        'data': g.current_user
    })

@app.route('/api/auth/cleanup-sessions', methods=['POST'])
@require_plan(3)  # Só admins (plano ID >= 3)
def api_cleanup_sessions():
    """Limpar sessões expiradas"""
    result = AuthService.cleanup_expired_sessions()
    return jsonify(result)

# ===== ROTAS PROTEGIDAS - DASHBOARD =====

@app.route('/api/dashboard')
@require_auth
def api_dashboard():
    """Dashboard protegido"""
    return jsonify({
        'success': True,
        'data': {
            'message': f'Bem-vindo, {g.current_user["name"]}!',
            'plan': g.current_user['plan_name'],
            'user_id': g.current_user['user_id'],
            'email': g.current_user['email']
        }
    })

@app.route('/api/dashboard/stats')
@require_auth
def api_dashboard_stats():
    """Estatísticas do dashboard do usuário"""
    return jsonify({
        'success': True,
        'data': {
            'total_watchlists': 3,
            'total_alerts': 5,
            'total_backtests': 12,
            'plan_features': ['Monitor Básico', 'Radar Setores', 'RSL'],
            'user_since': '2024-01-15'
        }
    })

# ===== ROTAS COM RECURSOS PREMIUM =====

@app.route('/api/premium/advanced-charts')
@require_plan(2)  # Exige plano ID >= 2
def api_premium_charts():
    """Gráficos avançados - funcionalidade premium"""
    return jsonify({
        'success': True,
        'data': {
            'message': 'Acesso liberado para gráficos avançados!',
            'charts': ['Candlestick', 'Volume Profile', 'Fibonacci'],
            'user': g.current_user['name'],
            'plan': g.current_user['plan_name']
        }
    })

@app.route('/api/premium/ai-recommendations')
@require_plan(3)  # Exige plano top (ID >= 3)
def api_ai_recommendations():
    """Recomendações IA - funcionalidade top"""
    return jsonify({
        'success': True,
        'data': {
            'message': 'Acesso liberado para recomendações de IA!',
            'recommendations': [
                {'ticker': 'PETR4', 'action': 'COMPRA', 'confidence': 0.85},
                {'ticker': 'VALE3', 'action': 'HOLD', 'confidence': 0.72},
                {'ticker': 'ITUB4', 'action': 'VENDA', 'confidence': 0.91}
            ],
            'user': g.current_user['name'],
            'plan': g.current_user['plan_name']
        }
    })

# ===== ROTAS DE PLANOS (mantidas) =====

@app.route('/api/plans')
def get_plans():
    """Buscar todos os planos do banco"""
    try:
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, display_name, price_monthly, price_annual, 
                   description, features, is_active
            FROM plans 
            WHERE is_active = true
            ORDER BY price_monthly
        """)
        
        plans = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Converter para formato JSON
        result = []
        for plan in plans:
            result.append({
                'id': plan[0],
                'name': plan[1], 
                'display_name': plan[2],
                'price_monthly': float(plan[3]),
                'price_annual': float(plan[4]),
                'description': plan[5],
                'features': plan[6],  # Array PostgreSQL
                'is_active': plan[7],
                'discount_percent': round(((plan[3] * 12 - plan[4]) / (plan[3] * 12)) * 100, 1)
            })
        
        return jsonify({
            'success': True,
            'data': result,
            'total_plans': len(result)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/plans/select', methods=['POST'])
@require_auth  # Agora exige autenticação
def select_plan():
    """Selecionar um plano (usuário logado)"""
    try:
        data = request.get_json()
        plan_id = data.get('plan_id')
        billing_cycle = data.get('billing_cycle', 'monthly')
        
        if not plan_id:
            return jsonify({
                'success': False,
                'error': 'plan_id é obrigatório'
            }), 400
        
        # Buscar dados do plano
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT display_name, price_monthly, price_annual
            FROM plans 
            WHERE id = %s AND is_active = true
        """, (plan_id,))
        
        plan = cursor.fetchone()
        
        if not plan:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Plano não encontrado'
            }), 404
        
        display_name, price_monthly, price_annual = plan
        final_price = price_annual if billing_cycle == 'annual' else price_monthly
        
        # Atualizar plano do usuário
        cursor.execute("""
            UPDATE users SET plan_id = %s WHERE id = %s
        """, (plan_id, g.current_user['user_id']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'plan_id': plan_id,
                'plan_name': display_name,
                'billing_cycle': billing_cycle,
                'price': float(final_price),
                'user': g.current_user['name'],
                'message': f'Plano {display_name} ativado com sucesso!'
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===== ROTAS API - AÇÕES (com auth opcional) =====
@app.route('/relatorios.html')
def relatorios():
    return send_from_directory('../frontend', 'relatorios.html')

@app.route('/relatorios')
def relatorios_sem_extensao():
    return send_from_directory('../frontend', 'relatorios.html')


@app.route('/api/stock/<symbol>')
@optional_auth
def get_stock(symbol):
    data = get_stock_data(symbol)
    if data:
        # Adicionar recursos extras para usuários logados
        if g.current_user and g.current_user.get('plan_id', 1) >= 2:
            data['premium_indicators'] = {
                'rsi': 65.2,
                'macd': 1.45,
                'bollinger_position': 'upper'
            }
        
        return jsonify({'success': True, 'data': data})
    else:
        return jsonify({'success': False, 'error': 'Ação não encontrada'}), 404

@app.route('/api/stocks')
@optional_auth
def get_stocks():
    symbols = request.args.get('symbols', 'PETR4,VALE3,ITUB4').split(',')
    results = {}
    
    for symbol in symbols:
        symbol = symbol.strip()
        data = get_stock_data(symbol)
        if data:
            # Adicionar recursos extras para usuários premium
            if g.current_user and g.current_user.get('plan_id', 1) >= 2:
                data['premium_data'] = True
                data['analyst_rating'] = 'COMPRA'
            else:
                data['premium_data'] = False
                
            results[symbol] = data
    
    # Informações extras baseadas no plano
    extra_info = {}
    if g.current_user:
        extra_info = {
            'user_plan': g.current_user['plan_name'],
            'enhanced_features': g.current_user.get('plan_id', 1) >= 2
        }
    else:
        extra_info = {
            'message': 'Faça login para acessar recursos premium',
            'enhanced_features': False
        }
    
    return jsonify({
        'success': True, 
        'data': results,
        'extra': extra_info
    })

# ===== ROTAS API - SETORES (mantidas iguais) =====
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

# ===== ROTAS RSL (protegidas por plano) =====

@app.route('/api/rsl/<symbol>')
@require_plan(2)  # RSL só para planos premium
def get_rsl_ticker(symbol):
    """Calcular RSL de um ticker - FUNCIONALIDADE PREMIUM"""
    from configuracoes.yfinance_service import YFinanceService
    
    try:
        resultado = YFinanceService.get_rsl_data(symbol)
        
        if resultado:
            return jsonify({'success': True, 'data': resultado})
        else:
            return jsonify({'success': False, 'error': f'RSL não calculado para {symbol}'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/rsl-setor/<setor_nome>')
@require_plan(2)  # RSL só para planos premium
def get_rsl_setor(setor_nome):
    """Calcular RSL médio de um setor - FUNCIONALIDADE PREMIUM"""
    from configuracoes.yfinance_service import YFinanceService
    
    try:
        # Buscar tickers do setor no banco
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ticker FROM setor_b3 
            WHERE setor_economico ILIKE %s
        """, (f'%{setor_nome}%',))
        
        tickers = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        if not tickers:
            return jsonify({'success': False, 'error': f'Nenhum ticker para {setor_nome}'}), 404
        
        resultado = YFinanceService.get_sector_rsl_data(tickers, setor_nome)
        
        if resultado:
            return jsonify({'success': True, 'data': resultado})
        else:
            return jsonify({'success': False, 'error': f'RSL não calculado para {setor_nome}'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/api/cache-info')
@require_auth
def get_cache_info():
    """Informações sobre o cache RSL"""
    from configuracoes.yfinance_service import YFinanceService
    
    cache_info = YFinanceService.get_cache_info()
    return jsonify({
        'success': True,
        'data': cache_info
    })

@app.route('/api/clear-cache', methods=['POST'])
@require_plan(3)  # Só admins podem limpar cache
def clear_cache():
    """Limpar cache RSL"""
    from configuracoes.yfinance_service import YFinanceService
    
    YFinanceService.clear_cache()
    return jsonify({
        'success': True,
        'message': 'Cache RSL limpo com sucesso!'
    })

# ===== ROTAS API - UTILITÁRIAS =====
@app.route('/api/status')
def status():
    return jsonify({
        'status': 'online',
        'message': 'API funcionando',
        'timestamp': datetime.now().isoformat(),
        'auth_enabled': True
    })

@app.route('/api/newsletter', methods=['POST'])
def newsletter():
    data = request.get_json()
    email = data.get('email')
    if email and '@' in email:
        return jsonify({'success': True, 'message': 'E-mail cadastrado!', 'email': email})
    return jsonify({'success': False, 'error': 'E-mail inválido'}), 400

@app.route('/api/backtest', methods=['POST'])
@require_plan(2)  # Backtest só para premium
def backtest():
    return jsonify({
        'strategy': 'Momentum Strategy',
        'initial_capital': 100000,
        'final_capital': 168750,
        'return_percent': 68.75,
        'trades': 47,
        'win_rate': 72,
        'sharpe_ratio': 1.85,
        'user': g.current_user['name'],
        'plan': g.current_user['plan_name']
    })


# ===== ROTA DE TESTE DO BANCO =====
@app.route('/api/test-db')
def test_db():
    """Rota para testar conexão com banco"""
    from configuracoes.database import test_database_connection
    
    result = test_database_connection()
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 Iniciando Geminii API...")
    print("📊 APIs disponíveis:")
    print("  - /api/auth/login (POST)")
    print("  - /api/auth/register (POST)")
    print("  - /api/auth/verify (GET)")
    print("  - /api/auth/logout (POST)")
    print("  - /api/dashboard (GET) - 🔒 AUTH")
    print("  - /api/premium/* - 🔒 PREMIUM")
    print("  - /api/setores")
    print("  - /api/setor/<nome>")
    print("  - /api/empresa/<ticker>")
    print("  - /api/rsl/* - 🔒 PREMIUM")
    print("  - /api/test-db")
    print("🔐 Sistema de autenticação ativado!")
    app.run(host='0.0.0.0', port=port, debug=True)