# auth/auth_service.py
import bcrypt
import secrets
from datetime import datetime, timedelta
import sys
import os

# Adicionar o diretório pai ao path para importar configuracoes
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from configuracoes.database import get_local_db_connection

class AuthService:
    """Serviço de autenticação simples"""
    
    @staticmethod
    def hash_password(password):
        """Criar hash da senha"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password, hashed):
        """Verificar senha"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def login(email, password):
        """Fazer login do usuário"""
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            # Buscar usuário
            cursor.execute("""
                SELECT u.id, u.email, u.password_hash, u.name, u.is_active,
                       p.display_name as plan_name, p.id as plan_id
                FROM users u
                LEFT JOIN plans p ON u.plan_id = p.id
                WHERE u.email = %s
            """, (email,))
            
            user = cursor.fetchone()
            
            if not user:
                return {'success': False, 'error': 'Usuário não encontrado'}
            
            user_id, user_email, password_hash, name, is_active, plan_name, plan_id = user
            
            if not is_active:
                return {'success': False, 'error': 'Conta desativada'}
            
            # Verificar senha
            if not AuthService.verify_password(password, password_hash):
                return {'success': False, 'error': 'Senha incorreta'}
            
            # Criar sessão
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=24)  # 24 horas
            
            cursor.execute("""
                INSERT INTO user_sessions (user_id, session_token, expires_at, is_active)
                VALUES (%s, %s, %s, %s)
            """, (user_id, session_token, expires_at, True))
            
            # Atualizar último login
            cursor.execute("""
                UPDATE users SET last_login = %s WHERE id = %s
            """, (datetime.now(), user_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'data': {
                    'user_id': user_id,
                    'name': name,
                    'email': user_email,
                    'plan_name': plan_name,
                    'plan_id': plan_id,
                    'session_token': session_token,
                    'expires_at': expires_at.isoformat()
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def verify_session(session_token):
        """Verificar se sessão é válida"""
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.user_id, u.name, u.email, p.display_name as plan_name, p.id as plan_id
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                LEFT JOIN plans p ON u.plan_id = p.id
                WHERE s.session_token = %s 
                AND s.expires_at > %s 
                AND s.is_active = true
                AND u.is_active = true
            """, (session_token, datetime.now()))
            
            session = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if session:
                user_id, name, email, plan_name, plan_id = session
                return {
                    'success': True,
                    'data': {
                        'user_id': user_id,
                        'name': name,
                        'email': email,
                        'plan_name': plan_name,
                        'plan_id': plan_id
                    }
                }
            else:
                return {'success': False, 'error': 'Sessão inválida ou expirada'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def logout(session_token):
        """Fazer logout (invalidar sessão)"""
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_sessions 
                SET is_active = false
                WHERE session_token = %s
            """, (session_token,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {'success': True, 'message': 'Logout realizado com sucesso'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def register(name, email, password, plan_id=1):
        """Registrar novo usuário"""
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            # Verificar se email já existe
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return {'success': False, 'error': 'E-mail já cadastrado'}
            
            # Criar hash da senha
            password_hash = AuthService.hash_password(password)
            
            # Inserir usuário
            cursor.execute("""
                INSERT INTO users (name, email, password_hash, plan_id, email_verified, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (name, email, password_hash, plan_id, True, True))
            
            user_id = cursor.fetchone()[0]
            
            # Criar watchlist padrão
            cursor.execute("""
                INSERT INTO user_watchlists (user_id, name, symbols, is_default)
                VALUES (%s, %s, %s, %s)
            """, (user_id, 'Minha Carteira', '["PETR4", "VALE3", "ITUB4"]', True))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'data': {
                    'user_id': user_id,
                    'message': 'Usuário criado com sucesso!'
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def cleanup_expired_sessions():
        """Limpar sessões expiradas (para executar periodicamente)"""
        try:
            conn = get_local_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_sessions 
                SET is_active = false
                WHERE expires_at < %s AND is_active = true
            """, (datetime.now(),))
            
            affected_rows = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            
            return {'success': True, 'cleaned_sessions': affected_rows}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

# ✅ FUNÇÃO PARA TESTAR O SISTEMA
def test_auth_system():
    """Testar sistema de autenticação"""
    print("🧪 TESTANDO SISTEMA DE AUTH...")
    print("="*40)
    
    # 1. Testar login com usuário existente
    print("1️⃣ Testando login...")
    result = AuthService.login('admin@geminii.com.br', 'admin123')
    
    if result['success']:
        print(f"✅ Login OK: {result['data']['name']} ({result['data']['plan_name']})")
        session_token = result['data']['session_token']
        
        # 2. Testar verificação de sessão
        print("\n2️⃣ Testando sessão...")
        session_check = AuthService.verify_session(session_token)
        
        if session_check['success']:
            print(f"✅ Sessão válida: {session_check['data']['name']}")
        else:
            print(f"❌ Sessão inválida: {session_check['error']}")
        
        # 3. Testar logout
        print("\n3️⃣ Testando logout...")
        logout_result = AuthService.logout(session_token)
        print(f"✅ Logout: {logout_result['message']}")
        
        # 4. Testar limpeza de sessões
        print("\n4️⃣ Testando limpeza de sessões...")
        cleanup_result = AuthService.cleanup_expired_sessions()
        if cleanup_result['success']:
            print(f"✅ Limpeza: {cleanup_result['cleaned_sessions']} sessões limpas")
        
    else:
        print(f"❌ Login falhou: {result['error']}")
        
        # Tentar com senha padrão
        print("🔄 Tentando com senha padrão...")
        for senha_teste in ['password', '123456', 'admin']:
            result = AuthService.login('admin@geminii.com.br', senha_teste)
            if result['success']:
                print(f"✅ Login OK com senha '{senha_teste}'!")
                break
        else:
            print("❌ Nenhuma senha padrão funcionou")
    
    print("\n✅ Teste concluído!")

if __name__ == '__main__':
    test_auth_system()