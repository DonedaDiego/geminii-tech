import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from configuracoes.database import get_local_db_connection
from auth_service import AuthService

def resetar_senhas():
    """Resetar senhas dos usuários para senhas conhecidas"""
    try:
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        print("🔐 RESETANDO SENHAS DOS USUÁRIOS...")
        print("="*40)
        
        # Definir senhas conhecidas
        usuarios_senhas = [
            ('admin@geminii.com.br', 'admin123'),
            ('user@test.com', 'user123')
        ]
        
        for email, nova_senha in usuarios_senhas:
            print(f"🔑 Resetando senha para {email}...")
            
            # Gerar novo hash
            novo_hash = AuthService.hash_password(nova_senha)
            
            # Atualizar no banco
            cursor.execute("""
                UPDATE users 
                SET password_hash = %s 
                WHERE email = %s
            """, (novo_hash, email))
            
            print(f"   ✅ Nova senha: {nova_senha}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n✅ {len(usuarios_senhas)} senhas resetadas com sucesso!")
        
        # Testar login agora
        print("\n🧪 TESTANDO LOGINS...")
        print("-" * 30)
        
        for email, senha in usuarios_senhas:
            print(f"\n📧 Testando {email} com senha '{senha}'...")
            
            result = AuthService.login(email, senha)
            
            if result['success']:
                data = result['data']
                print(f"   ✅ Login OK!")
                print(f"   👤 Nome: {data['name']}")
                print(f"   📋 Plano: {data['plan_name']}")
                print(f"   🎫 Token: {data['session_token'][:20]}...")
                
                # Testar sessão
                session_check = AuthService.verify_session(data['session_token'])
                if session_check['success']:
                    print(f"   ✅ Sessão válida!")
                else:
                    print(f"   ❌ Sessão inválida: {session_check['error']}")
                    
            else:
                print(f"   ❌ Falha: {result['error']}")
        
        print(f"\n🎉 TESTE COMPLETO!")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

def criar_usuario_teste():
    """Criar um novo usuário de teste"""
    try:
        print("\n➕ CRIANDO USUÁRIO DE TESTE...")
        print("-" * 30)
        
        result = AuthService.register(
            name='Teste Geminii',
            email='teste@geminii.com', 
            password='123456',
            plan_id=2  # Plano Tático
        )
        
        if result['success']:
            print(f"✅ Usuário criado: teste@geminii.com")
            print(f"🔑 Senha: 123456")
            print(f"📋 Plano: Tático")
            
            # Testar login
            login_result = AuthService.login('teste@geminii.com', '123456')
            if login_result['success']:
                print(f"✅ Login testado com sucesso!")
            
        else:
            print(f"❌ Erro ao criar usuário: {result['error']}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def verificar_usuarios_existentes():
    """Ver todos os usuários no banco"""
    try:
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        print("\n👥 USUÁRIOS NO BANCO:")
        print("-" * 40)
        
        cursor.execute("""
            SELECT u.id, u.name, u.email, p.display_name as plano
            FROM users u
            LEFT JOIN plans p ON u.plan_id = p.id
            ORDER BY u.id
        """)
        
        usuarios = cursor.fetchall()
        
        for id_user, nome, email, plano in usuarios:
            print(f"{id_user}. {nome}")
            print(f"   📧 {email}")
            print(f"   📋 {plano}")
            print()
        
        cursor.close()
        conn.close()
        
        print(f"Total: {len(usuarios)} usuários")
        
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == '__main__':
    print("🚀 CONFIGURANDO SISTEMA DE AUTH...")
    print("="*50)
    
    # 1. Ver usuários existentes
    verificar_usuarios_existentes()
    
    # 2. Resetar senhas conhecidas
    resetar_senhas()
    
    # 3. Criar usuário de teste
    criar_usuario_teste()
    
    print("\n" + "="*50)
    print("🎯 CREDENCIAIS PARA TESTE:")
    print("admin@geminii.com.br → admin123")
    print("user@test.com → user123") 
    print("teste@geminii.com → 123456")
    print("="*50)