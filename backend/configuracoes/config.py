# configuracoes/config.py - VERSÃO FINAL
import os

class Config:
    """Configurações gerais da aplicação"""
    
    # Configuração do Flask
    DEBUG = True
    
    # Configuração do banco
    DATABASE_CONFIG = {
        'local': {
            'host': 'localhost',
            'database': 'postgres',
            'user': 'postgres',
            'password': '#geminii',
            'port': '5432'
        }
    }
    
    @staticmethod
    def get_database_url():
        """Retorna URL do banco (produção ou local)"""
        if os.environ.get('DATABASE_URL'):
            return os.environ.get('DATABASE_URL')
        else:
            config = Config.DATABASE_CONFIG['local']
            return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    
    # Configurações adicionais para o yfinance
    YFINANCE_PERIOD_DEFAULT = '1mo'
    DEFAULT_SYMBOLS = ['PETR4', 'VALE3', 'ITUB4']