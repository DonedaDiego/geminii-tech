import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from functools import lru_cache
from .config import Config

class YFinanceService:
    """Serviço completo para buscar dados do Yahoo Finance + cálculos RSL"""
    
    @staticmethod
    def get_stock_data(symbol, period=None):
        """Busca dados de uma ação específica"""
        try:
            # Usar período padrão do config se não especificado
            if period is None:
                period = Config.YFINANCE_PERIOD_DEFAULT
            
            # Adiciona .SA para ações brasileiras se necessário
            if not symbol.endswith('.SA'):
                symbol += '.SA'
            
            print(f"📈 Buscando dados de {symbol} (período: {period})")
            
            stock = yf.Ticker(symbol)
            data = stock.history(period=period)
            
            if data.empty:
                print(f"⚠️ Nenhum dado encontrado para {symbol}")
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
                    'volume': int(row['Volume']) if row['Volume'] > 0 else 0
                })
            
            result = {
                'symbol': symbol.replace('.SA', ''),
                'current_price': round(current_price, 2),
                'change': round(change, 2),
                'change_percent': round(change_percent, 2),
                'volume': int(data['Volume'].iloc[-1]) if data['Volume'].iloc[-1] > 0 else 0,
                'chart_data': chart_data,
                'last_update': datetime.now().strftime('%d/%m/%Y %H:%M'),
                'period': period,
                'data_points': len(data)
            }
            
            print(f"✅ Dados obtidos para {symbol}: R$ {result['current_price']}")
            return result
            
        except Exception as e:
            print(f"❌ Erro ao buscar dados para {symbol}: {e}")
            return None
    
    @staticmethod
    def get_multiple_stocks(symbols):
        """Busca dados de múltiplas ações"""
        print(f"📊 Buscando dados de {len(symbols)} ações...")
        
        results = {}
        success_count = 0
        
        for symbol in symbols:
            symbol = symbol.strip().upper()
            if symbol:  # Verificar se não está vazio
                data = YFinanceService.get_stock_data(symbol)
                if data:
                    results[symbol] = data
                    success_count += 1
        
        print(f"✅ Sucesso: {success_count}/{len(symbols)} ações")
        return results
    
    @staticmethod
    def get_stock_info(symbol):
        """Busca informações detalhadas de uma ação"""
        try:
            if not symbol.endswith('.SA'):
                symbol += '.SA'
            
            print(f"🔍 Buscando informações detalhadas de {symbol}")
            
            stock = yf.Ticker(symbol)
            info = stock.info
            
            if not info:
                return None
            
            # Extrair informações principais
            result = {
                'symbol': symbol.replace('.SA', ''),
                'longName': info.get('longName', 'N/A'),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'marketCap': info.get('marketCap', 0),
                'volume': info.get('volume', 0),
                'averageVolume': info.get('averageVolume', 0),
                'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh', 0),
                'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow', 0),
                'dividendYield': info.get('dividendYield', 0),
                'peRatio': info.get('trailingPE', 0),
                'last_update': datetime.now().strftime('%d/%m/%Y %H:%M')
            }
            
            print(f"✅ Informações obtidas para {result['longName']}")
            return result
            
        except Exception as e:
            print(f"❌ Erro ao buscar informações de {symbol}: {e}")
            return None
    
    @staticmethod
    def validate_ticker(symbol):
        """Valida se um ticker existe"""
        try:
            if not symbol.endswith('.SA'):
                symbol += '.SA'
            
            stock = yf.Ticker(symbol)
            data = stock.history(period='1d')
            
            return not data.empty
            
        except Exception:
            return False
    
    @staticmethod
    def get_default_stocks():
        """Retorna dados das ações padrão configuradas"""
        return YFinanceService.get_multiple_stocks(Config.DEFAULT_SYMBOLS)
    
    # ✅ FUNÇÕES RSL - BASEADAS NO METATRADER
    
    @staticmethod
    def get_historical_data(symbol, period='1y'):
        """Busca dados históricos para cálculo do RSL"""
        try:
            # Normalizar ticker
            if not symbol.endswith('.SA'):
                symbol += '.SA'
            
            print(f"📈 Buscando histórico de {symbol} para RSL...")
            
            stock = yf.Ticker(symbol)
            data = stock.history(period=period)
            
            if data.empty:
                print(f"⚠️ Nenhum dado histórico para {symbol}")
                return None
            
            return data['Close']
            
        except Exception as e:
            print(f"❌ Erro ao buscar histórico de {symbol}: {e}")
            return None
    
    @staticmethod
    def calculate_rsl(price_series, periodo_mm=30):
        """
        Calcula RSL exatamente como no MetaTrader:
        RSL = ((Close / MM) - 1) * 100
        """
        try:
            if price_series is None or len(price_series) < periodo_mm:
                return None
            
            # ✅ FÓRMULA IDÊNTICA AO METATRADER
            # Calcular Média Móvel
            mm = price_series.rolling(window=periodo_mm).mean()
            
            # Calcular RSL = ((Close / MM) - 1) * 100
            rsl_series = ((price_series / mm) - 1) * 100
            
            # Retornar o último valor válido
            rsl_atual = rsl_series.dropna().tail(1)
            
            if len(rsl_atual) == 0:
                return None
                
            return rsl_atual.values[0]
            
        except Exception as e:
            print(f"❌ Erro ao calcular RSL: {e}")
            return None
    
    @staticmethod
    def calculate_volatilidade(price_series):
        """
        Calcula volatilidade anualizada como no MetaTrader:
        Vol = pct_change().std() * sqrt(252) * 100
        """
        try:
            if price_series is None or len(price_series) < 30:
                return None
            
            # ✅ FÓRMULA IDÊNTICA AO METATRADER
            # Calcular retornos percentuais
            returns = price_series.pct_change()
            
            # Volatilidade anualizada
            vol = returns.std() * np.sqrt(252) * 100
            
            return vol if np.isfinite(vol) else None
            
        except Exception as e:
            print(f"❌ Erro ao calcular volatilidade: {e}")
            return None
    
    @staticmethod
    @lru_cache(maxsize=100)
    def get_rsl_data_cached(symbol, period='1y'):
        """
        Versão com cache do get_rsl_data para evitar recálculos
        Cache expira automaticamente quando maxsize é atingido
        """
        return YFinanceService.get_rsl_data(symbol, period)
    
    @staticmethod
    def get_rsl_data(symbol, period='1y', periodo_mm=30):
        """Calcula RSL e Volatilidade para um ticker específico"""
        try:
            # Buscar dados históricos
            price_data = YFinanceService.get_historical_data(symbol, period)
            
            if price_data is None:
                return None
            
            # Calcular RSL
            rsl = YFinanceService.calculate_rsl(price_data, periodo_mm)
            
            # Calcular Volatilidade
            volatilidade = YFinanceService.calculate_volatilidade(price_data)
            
            if rsl is None or volatilidade is None:
                return None
            
            # Calcular MM atual
            mm_atual = price_data.rolling(window=periodo_mm).mean().iloc[-1]
            
            return {
                'symbol': symbol.replace('.SA', ''),
                'rsl': round(rsl, 2),
                'volatilidade': round(volatilidade, 2),
                'close_atual': round(price_data.iloc[-1], 2),
                'mm_30': round(mm_atual, 2),
                'data_calculo': datetime.now().strftime('%d/%m/%Y %H:%M'),
                'periodo_usado': period,
                'periodo_mm': periodo_mm,
                'pontos_dados': len(price_data),
                'has_real_data': True
            }
            
        except Exception as e:
            print(f"❌ Erro ao calcular RSL para {symbol}: {e}")
            return None
    
    @staticmethod
    def get_sector_rsl_data(tickers_list, setor_nome, period='1y'):
        """
        Calcula RSL médio de um setor - IGUAL AO METATRADER
        Agrupa por setor e calcula média do RSL e Volatilidade
        """
        try:
            print(f"📊 Calculando RSL do setor: {setor_nome}")
            print(f"📋 Tickers: {tickers_list}")
            
            resultados_individuais = []
            
            # ✅ USAR CACHE PARA OTIMIZAR
            for ticker in tickers_list[:10]:  # Limitar a 10 para não sobrecarregar
                print(f"  ⚡ Processando {ticker}...")
                
                # Usar versão com cache
                rsl_data = YFinanceService.get_rsl_data_cached(ticker, period)
                
                if rsl_data:
                    resultados_individuais.append(rsl_data)
                    print(f"    ✅ {ticker}: RSL={rsl_data['rsl']}%, Vol={rsl_data['volatilidade']}%")
                else:
                    print(f"    ❌ {ticker}: Sem dados RSL")
            
            if not resultados_individuais:
                print(f"  ⚠️ Nenhum ticker válido para RSL em {setor_nome}")
                return None
            
            # ✅ CALCULAR MÉDIAS COMO NO METATRADER
            rsl_values = [r['rsl'] for r in resultados_individuais]
            vol_values = [r['volatilidade'] for r in resultados_individuais]
            
            rsl_medio = np.mean(rsl_values)
            vol_media = np.mean(vol_values)
            
            return {
                'setor': setor_nome,
                'rsl': round(rsl_medio, 2),  # ✅ PERFORMANCE = RSL MÉDIO
                'volatilidade': round(vol_media, 2),  # ✅ VOLATILIDADE MÉDIA
                'empresas_com_dados': len(resultados_individuais),
                'total_empresas': len(tickers_list),
                'taxa_sucesso': round((len(resultados_individuais) / len(tickers_list)) * 100, 1),
                'detalhes_empresas': resultados_individuais,
                'has_real_data': True,
                'data_calculo': datetime.now().strftime('%d/%m/%Y %H:%M')
            }
            
        except Exception as e:
            print(f"❌ Erro ao calcular RSL do setor {setor_nome}: {e}")
            return None
    
    @staticmethod
    def get_multiple_rsl_data(symbols_list, period='1y'):
        """Busca dados RSL de múltiplas ações com cache"""
        print(f"📊 Calculando RSL para {len(symbols_list)} símbolos...")
        
        results = {}
        success_count = 0
        
        for symbol in symbols_list:
            symbol = symbol.strip().upper()
            if symbol:
                # ✅ USAR VERSÃO COM CACHE
                rsl_data = YFinanceService.get_rsl_data_cached(symbol, period)
                if rsl_data:
                    results[symbol] = rsl_data
                    success_count += 1
        
        print(f"✅ RSL calculado para {success_count}/{len(symbols_list)} símbolos")
        return results
    
    @staticmethod
    def clear_cache():
        """Limpa o cache do RSL (útil para forçar recálculo)"""
        YFinanceService.get_rsl_data_cached.cache_clear()
        print("🧹 Cache RSL limpo com sucesso!")
    
    @staticmethod
    def get_cache_info():
        """Retorna informações sobre o cache"""
        cache_info = YFinanceService.get_rsl_data_cached.cache_info()
        return {
            'hits': cache_info.hits,
            'misses': cache_info.misses,
            'maxsize': cache_info.maxsize,
            'currsize': cache_info.currsize,
            'hit_rate': round((cache_info.hits / (cache_info.hits + cache_info.misses)) * 100, 2) if (cache_info.hits + cache_info.misses) > 0 else 0
        }