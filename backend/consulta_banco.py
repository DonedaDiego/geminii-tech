import psycopg2
import pandas as pd

def descobrir_tabelas():
    try:
        # Conectar
        conn = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password="#geminii",
            port="5432"
        )
        
        cursor = conn.cursor()
        
        print("🔍 DESCOBRINDO TODAS AS TABELAS...")
        print("="*60)
        
        # 1. LISTAR TODAS AS TABELAS
        cursor.execute("""
            SELECT 
                table_name,
                table_type
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tabelas = cursor.fetchall()
        
        print(f"📋 ENCONTRADAS {len(tabelas)} TABELAS:")
        print("-" * 40)
        
        for i, (nome, tipo) in enumerate(tabelas, 1):
            print(f"{i:2d}. {nome} ({tipo})")
        
        print("\n" + "="*60)
        
        # 2. PARA CADA TABELA, MOSTRAR INFORMAÇÕES
        for nome, tipo in tabelas:
            print(f"\n📊 TABELA: {nome.upper()}")
            print("-" * 30)
            
            # Contar registros
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {nome}")
                total = cursor.fetchone()[0]
                print(f"📈 Total de registros: {total}")
            except Exception as e:
                print(f"❌ Erro ao contar: {e}")
                continue
            
            # Ver estrutura
            try:
                cursor.execute(f"""
                    SELECT 
                        column_name, 
                        data_type,
                        is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = '{nome}'
                    ORDER BY ordinal_position;
                """)
                
                colunas = cursor.fetchall()
                print(f"🏗️  Estrutura ({len(colunas)} colunas):")
                
                for col_nome, tipo_dado, nullable in colunas:
                    null_info = "NULL" if nullable == "YES" else "NOT NULL"
                    print(f"   - {col_nome}: {tipo_dado} ({null_info})")
                
            except Exception as e:
                print(f"❌ Erro ao ver estrutura: {e}")
            
            # Ver alguns dados (só se tiver registros)
            if total > 0 and total < 1000:  # Só para tabelas pequenas
                try:
                    cursor.execute(f"SELECT * FROM {nome} LIMIT 3")
                    dados = cursor.fetchall()
                    
                    if dados:
                        print(f"👀 Primeiros registros:")
                        for i, linha in enumerate(dados, 1):
                            print(f"   {i}. {linha}")
                except Exception as e:
                    print(f"❌ Erro ao ver dados: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")

def buscar_tabelas_por_nome():
    """Busca tabelas que podem ter sido criadas ontem"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="postgres", 
            user="postgres",
            password="#geminii",
            port="5432"
        )
        
        cursor = conn.cursor()
        
        print("\n🔍 BUSCANDO TABELAS QUE PODEM SER SUAS...")
        print("="*50)
        
        # Palavras-chave que podem estar no nome da tabela
        palavras_busca = [
            'user', 'usuario', 'login', 'conta', 'auth', 
            'plano', 'subscription', 'assinatura',
            'geminii', 'trading', 'investimento',
            'test', 'teste', 'temp'
        ]
        
        for palavra in palavras_busca:
            cursor.execute(f"""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name ILIKE '%{palavra}%'
            """)
            
            resultados = cursor.fetchall()
            if resultados:
                print(f"🎯 Tabelas com '{palavra}':")
                for (nome,) in resultados:
                    print(f"   - {nome}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")

def consultar_tabela_especifica(nome_tabela):
    """Consulta uma tabela específica que você lembrar"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres", 
            password="#geminii",
            port="5432"
        )
        
        print(f"\n🔍 CONSULTANDO TABELA: {nome_tabela}")
        print("="*40)
        
        # Ver todos os dados
        df = pd.read_sql(f"SELECT * FROM {nome_tabela}", conn)
        print(f"📊 DADOS DA TABELA {nome_tabela.upper()}:")
        print(df.to_string(index=False))
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao consultar {nome_tabela}: {e}")

if __name__ == '__main__':
    # 1. Descobrir todas as tabelas
    descobrir_tabelas()
    
    # 2. Buscar por palavras-chave
    buscar_tabelas_por_nome()
    
    # 3. Se você lembrar o nome da tabela, descomente e execute:
    # consultar_tabela_especifica("nome_da_sua_tabela")
    
    print("\n✅ ANÁLISE COMPLETA!")
    print("\n💡 DICA: Se encontrar sua tabela, use:")
    print("   consultar_tabela_especifica('nome_da_tabela')")