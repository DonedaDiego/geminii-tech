import psycopg2
import os
from .config import Config

def get_local_db_connection():
    """Conecta no PostgreSQL (local ou produção)"""
    try:
        # ✅ Produção (Render) - usa DATABASE_URL
        if os.environ.get('DATABASE_URL'):
            print("🌐 Conectando no banco de produção (Render)...")
            return psycopg2.connect(os.environ.get('DATABASE_URL'))
        else:
            # ✅ Local - usa configurações do Config
            print("💻 Conectando no banco local...")
            config = Config.DATABASE_CONFIG['local']
            return psycopg2.connect(
                host=config['host'],
                database=config['database'],
                user=config['user'],
                password=config['password'],
                port=config['port']
            )
    except Exception as e:
        print(f"❌ Erro de conexão com banco: {e}")
        raise

def test_database_connection():
    """Testa conexão e retorna informações do banco"""
    try:
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        # Testar conexão
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        # Contar registros na tabela setor_b3
        cursor.execute("SELECT COUNT(*) FROM setor_b3;")
        total = cursor.fetchone()[0]
        
        # ✅ NOVO: Verificar estrutura da tabela
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'setor_b3'
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            'success': True,
            'postgres_version': version,
            'total_empresas': total,
            'table_columns': [col[0] for col in columns],
            'message': 'Banco funcionando!'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

# ✅ NOVA FUNÇÃO: Validar tabela setor_b3
def validate_setor_table():
    """Verifica se a tabela setor_b3 existe e tem dados"""
    try:
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        # Verificar se tabela existe
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
            return {'exists': False, 'error': 'Tabela setor_b3 não encontrada'}
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM setor_b3;")
        total = cursor.fetchone()[0]
        
        # Buscar alguns exemplos
        cursor.execute("SELECT setor_economico, ticker, acao FROM setor_b3 LIMIT 3;")
        samples = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            'exists': True,
            'total_records': total,
            'sample_data': samples,
            'message': f'Tabela OK com {total} registros'
        }
        
    except Exception as e:
        return {'exists': False, 'error': str(e)}

# ✅ NOVA FUNÇÃO: Buscar setores únicos
def get_unique_sectors():
    """Retorna lista de setores únicos do banco"""
    try:
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                setor_economico,
                COUNT(*) as total_empresas
            FROM setor_b3 
            WHERE setor_economico IS NOT NULL
            GROUP BY setor_economico 
            ORDER BY total_empresas DESC
        """)
        
        setores = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {
            'success': True,
            'setores': [
                {
                    'setor_economico': setor[0],
                    'total_empresas': setor[1]
                }
                for setor in setores
            ],
            'total_setores': len(setores)
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ✅ NOVA FUNÇÃO: Buscar empresas por setor
def get_companies_by_sector(setor_nome, limit=10):
    """Busca empresas de um setor específico"""
    try:
        conn = get_local_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT acao, ticker, setor_economico, nivel_na_bolsa, tipo
            FROM setor_b3 
            WHERE setor_economico ILIKE %s 
            ORDER BY acao
            LIMIT %s
        """, (f'%{setor_nome}%', limit))
        
        empresas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {
            'success': True,
            'empresas': [
                {
                    'empresa': empresa[0],
                    'ticker': empresa[1],
                    'setor_economico': empresa[2],
                    'nivel_bolsa': empresa[3],
                    'tipo_governanca': empresa[4]
                }
                for empresa in empresas
            ],
            'total_encontradas': len(empresas)
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ✅ NOVA FUNÇÃO: Context manager para conexões
class DatabaseConnection:
    """Context manager para conexões de banco"""
    
    def __enter__(self):
        self.conn = get_local_db_connection()
        self.cursor = self.conn.cursor()
        return self.cursor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'cursor'):
            self.cursor.close()
        if hasattr(self, 'conn'):
            self.conn.close()

# ✅ EXEMPLO DE USO DO CONTEXT MANAGER:
def example_using_context_manager():
    """Exemplo de como usar o context manager"""
    try:
        with DatabaseConnection() as cursor:
            cursor.execute("SELECT COUNT(*) FROM setor_b3;")
            total = cursor.fetchone()[0]
            return {'total': total}
    except Exception as e:
        return {'error': str(e)}