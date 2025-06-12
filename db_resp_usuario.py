import os
from dotenv import load_dotenv
import psycopg2

# Carrega as variáveis do arquivo .env (busca no diretório pai)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

def criar_conexao():
    """Cria uma nova conexão com o banco de dados"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar com PostgreSQL: {e}")
        return None

def criar_tabela():
    """Cria a tabela se ela não existir"""
    conn = criar_conexao()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS respostas_satisfacao (
            id SERIAL PRIMARY KEY,
            setor VARCHAR(100) NOT NULL,
            material_faltando BOOLEAN NOT NULL,
            qual_material VARCHAR(100),
            qualidade_servico VARCHAR(50) NOT NULL,
            mensagem TEXT,
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()
        print("✅ Tabela de respostas de satisfação criada/verificada com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar tabela: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

# Chama a função para criar a tabela na inicialização
criar_tabela()

def salvar_resposta(setor, material_faltando, qual_material, qualidade_servico, mensagem):
    """Salva uma nova resposta no banco de dados"""
    conn = criar_conexao()
    if not conn:
        print("❌ Sem conexão com o banco de dados")
        return False
        
    try:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO respostas_satisfacao 
        (setor, material_faltando, qual_material, qualidade_servico, mensagem)
        VALUES (%s, %s, %s, %s, %s)
        """, (setor, material_faltando == "Sim", qual_material, qualidade_servico, mensagem))
        conn.commit()
        print(f"✅ Resposta salva: {setor} - {qualidade_servico}")
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar resposta: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def obter_todas_respostas():
    """Obtém todas as respostas do banco de dados"""
    conn = criar_conexao()
    if not conn:
        print("❌ Sem conexão com o banco de dados")
        return []
        
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM respostas_satisfacao ORDER BY data_registro DESC")
        respostas = cursor.fetchall()
        print(f"✅ {len(respostas)} respostas recuperadas do banco")
        return respostas
    except Exception as e:
        print(f"❌ Erro ao obter respostas: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

