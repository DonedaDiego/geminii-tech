# auth/middleware.py
from functools import wraps
from flask import request, jsonify, g
from auth.auth_service import AuthService

def require_auth(f):
    """Decorator para exigir autenticação em rotas"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar se token está presente
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'success': False,
                'error': 'Token de autorização necessário',
                'code': 'MISSING_TOKEN'
            }), 401
        
        # Extrair token (formato: "Bearer <token>")
        try:
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]  # Remove "Bearer "
            else:
                token = auth_header  # Se vier só o token
        except:
            return jsonify({
                'success': False,
                'error': 'Formato de token inválido',
                'code': 'INVALID_TOKEN_FORMAT'
            }), 401
        
        # Verificar sessão
        result = AuthService.verify_session(token)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'error': result['error'],
                'code': 'INVALID_SESSION'
            }), 401
        
        # Adicionar dados do usuário ao contexto global
        g.current_user = result['data']
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_plan(min_plan_id):
    """Decorator para exigir plano mínimo"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Primeiro verificar autenticação
            auth_header = request.headers.get('Authorization')
            
            if not auth_header:
                return jsonify({
                    'success': False,
                    'error': 'Token de autorização necessário'
                }), 401
            
            token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else auth_header
            result = AuthService.verify_session(token)
            
            if not result['success']:
                return jsonify({
                    'success': False,
                    'error': result['error']
                }), 401
            
            # Verificar plano
            user_plan_id = result['data'].get('plan_id', 1)
            
            if user_plan_id < min_plan_id:
                return jsonify({
                    'success': False,
                    'error': 'Plano insuficiente para acessar este recurso',
                    'required_plan_id': min_plan_id,
                    'current_plan_id': user_plan_id
                }), 403
            
            # Adicionar dados do usuário ao contexto
            g.current_user = result['data']
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def optional_auth(f):
    """Decorator para autenticação opcional (não obrigatória)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else auth_header
                result = AuthService.verify_session(token)
                
                if result['success']:
                    g.current_user = result['data']
                else:
                    g.current_user = None
            except:
                g.current_user = None
        else:
            g.current_user = None
        
        return f(*args, **kwargs)
    
    return decorated_function