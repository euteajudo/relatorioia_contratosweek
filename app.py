import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from io import BytesIO

# Importações da OpenAI
from openai import OpenAI

# Importações para PDF
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Importar funções do banco de dados
from db.db_resp_usuario import obter_todas_respostas, criar_conexao

# Carregar variáveis de ambiente
load_dotenv()

# Configuração da página
st.set_page_config(
    page_title="Relatório de Satisfação - Contratos Week",
    page_icon="🧹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar o cliente OpenAI
@st.cache_resource
def inicializar_openai_client():
    """Inicializa o cliente da OpenAI"""
    try:
        return OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    except Exception as e:
        st.error(f"Erro ao inicializar cliente OpenAI: {e}")
        return None

# Os prompts agora são carregados dos arquivos .txt

def carregar_dados():
    """Carrega dados do banco de dados"""
    try:
        respostas = obter_todas_respostas()
        if not respostas:
            return pd.DataFrame()
        
        # Converter para DataFrame
        colunas = ['id', 'setor', 'material_faltando', 'qual_material', 'qualidade_servico', 'mensagem', 'data_registro']
        df = pd.DataFrame(respostas, columns=colunas)
        
        # Converter data para datetime
        df['data_registro'] = pd.to_datetime(df['data_registro'])
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

def analisar_sentimentos(df, client):
    """Realiza análise de sentimentos usando OpenAI GPT-4.1"""
    if df.empty or not client:
        return None
    
    # Preparar respostas para análise
    respostas_texto = []
    for idx, row in df.iterrows():
        texto = f"Setor: {row['setor']}, Qualidade: {row['qualidade_servico']}"
        if row['mensagem']:
            texto += f", Comentário: {row['mensagem']}"
        respostas_texto.append(texto)
    
    try:
        # Carregar prompt do arquivo
        with open("prompt_analise_sentimento.txt", "r", encoding="utf-8") as f:
            instructions = f.read()
        
        # Limitar o número de respostas para análise (evitar tokens excessivos)
        respostas_sample = respostas_texto[:50] if len(respostas_texto) > 50 else respostas_texto
        input_data = "\n".join(respostas_sample)
        
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": f"Analise as seguintes respostas:\n\n{input_data}"}
            ],
            temperature=0.5,
            max_tokens=3000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Erro na análise de sentimentos: {e}")
        return None

def gerar_relatorio_gestao(dados_analise, client):
    """Gera relatório executivo para gestão usando OpenAI GPT-4.1"""
    if not dados_analise or not client:
        return None
    
    try:
        # Carregar prompt do arquivo
        with open("prompt_relatorio_gestao.txt", "r", encoding="utf-8") as f:
            instructions = f.read()
        
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": f"Baseie-se nos seguintes dados para gerar o relatório:\n\n{dados_analise}"}
            ],
            temperature=0.3,
            max_tokens=3000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {e}")
        return None

def gerar_pdf_relatorio(conteudo_relatorio, dados_df):
    """Gera PDF do relatório executivo"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch)
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # Centralizado
            textColor='darkblue'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor='darkgreen'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            alignment=0  # Justificado
        )
        
        # Conteúdo do PDF
        story = []
        
        # Título
        story.append(Paragraph("🧹 RELATÓRIO EXECUTIVO DE SATISFAÇÃO - CONTRATOS WEEK", title_style))
        story.append(Paragraph("Serviço de Limpeza", styles['Heading3']))
        story.append(Spacer(1, 20))
        
        # Informações básicas
        data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M")
        story.append(Paragraph(f"<b>Data de Geração:</b> {data_atual}", normal_style))
        story.append(Paragraph(f"<b>Total de Registros Analisados:</b> {len(dados_df)}", normal_style))
        story.append(Paragraph(f"<b>Período dos Dados:</b> {dados_df['data_registro'].min().strftime('%d/%m/%Y')} até {dados_df['data_registro'].max().strftime('%d/%m/%Y')}", normal_style))
        story.append(Spacer(1, 20))
        
        # Processamento do conteúdo do relatório
        linhas = conteudo_relatorio.split('\n')
        
        for linha in linhas:
            linha = linha.strip()
            if not linha:
                story.append(Spacer(1, 6))
                continue
                
            # Títulos principais (##)
            if linha.startswith('## '):
                titulo = linha.replace('## ', '').replace('#', '')
                story.append(Paragraph(titulo, heading_style))
                story.append(Spacer(1, 12))
            
            # Subtítulos (###)
            elif linha.startswith('### '):
                subtitulo = linha.replace('### ', '').replace('#', '')
                story.append(Paragraph(f"<b>{subtitulo}</b>", ParagraphStyle('SubHeading', parent=normal_style, fontSize=12, spaceAfter=8)))
            
            # Listas com -
            elif linha.startswith('- '):
                item = linha.replace('- ', '• ')
                story.append(Paragraph(item, normal_style))
            
            # Texto normal
            elif linha and not linha.startswith('#'):
                # Remover markdown básico
                linha_limpa = linha.replace('**', '').replace('*', '')
                if linha_limpa:
                    story.append(Paragraph(linha_limpa, normal_style))
        
        # Rodapé
        story.append(Spacer(1, 30))
        story.append(Paragraph("_" * 50, normal_style))
        story.append(Paragraph("<b>Desenvolvido por:</b> Abimael Torcate de Souza", normal_style))
        story.append(Paragraph("<b>Tecnologia:</b> Streamlit + OpenAI GPT-4.1", normal_style))
        story.append(Paragraph(f"<b>Gerado em:</b> {data_atual}", normal_style))
        
        # Construir PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
        
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {e}")
        return None

def main():
    """Função principal do aplicativo"""
    st.title("🧹 Relatório de Satisfação - Contratos Week")
    st.markdown("### Análise Inteligente de Satisfação dos Usuários")
    
    # Sidebar
    st.sidebar.title("⚙️ Configurações")
    st.sidebar.markdown("---")
    
    # Verificar conexão com banco
    if st.sidebar.button("🔄 Testar Conexão BD"):
        conn = criar_conexao()
        if conn:
            st.sidebar.success("✅ Conexão com banco OK!")
            conn.close()
        else:
            st.sidebar.error("❌ Erro na conexão com banco!")
    
    # Carregar dados
    with st.spinner("Carregando dados do banco de dados..."):
        df = carregar_dados()
    
    if df.empty:
        st.error("⚠️ Nenhum dado encontrado no banco de dados. Verifique a conexão e as credenciais.")
        st.info("💡 Certifique-se de que:")
        st.info("- O arquivo .env existe com as credenciais corretas")
        st.info("- O banco de dados está rodando")
        st.info("- A tabela 'respostas_satisfacao' possui dados")
        return
    
    # Tabs principais
    tab1, tab2 = st.tabs(["🤖 Análise IA", "📄 Relatório Executivo"])
    
    with tab1:
        st.header("🤖 Análise com Inteligência Artificial")
        
        # Inicializar cliente OpenAI
        client = inicializar_openai_client()
        
        if not client:
            st.error("❌ Não foi possível inicializar o cliente OpenAI. Verifique sua chave API.")
            st.info("💡 Adicione sua chave OpenAI no arquivo .env: OPENAI_API_KEY=sua_chave_aqui")
        else:
            if st.button("🚀 Iniciar Análise de Sentimentos", type="primary"):
                with st.spinner("Analisando sentimentos das respostas..."):
                    resultado_analise = analisar_sentimentos(df, client)
                
                if resultado_analise:
                    st.subheader("🎯 Resultado da Análise de Sentimentos")
                    st.markdown(resultado_analise)
                    
                    # Salvar análise na sessão para uso no relatório
                    st.session_state['analise_sentimentos'] = resultado_analise
                else:
                    st.error("Erro ao realizar análise de sentimentos.")
    
    with tab2:
        st.header("📄 Relatório Executivo")
        
        client = inicializar_openai_client()
        
        if not client:
            st.error("❌ Cliente OpenAI não disponível.")
        else:
            if st.button("📊 Gerar Relatório Executivo", type="primary"):
                # Preparar dados de análise
                dados_para_relatorio = f"""
                DADOS ESTATÍSTICOS:
                - Total de respostas: {len(df)}
                - Setores avaliados: {df['setor'].nunique()}
                - Material faltando: {df['material_faltando'].sum()} casos ({(df['material_faltando'].sum()/len(df)*100):.1f}%)
                - Distribuição de qualidade: {df['qualidade_servico'].value_counts().to_dict()}
                - Período: {df['data_registro'].min().strftime('%d/%m/%Y')} até {df['data_registro'].max().strftime('%d/%m/%Y')}
                
                ANÁLISE DE SENTIMENTOS:
                {st.session_state.get('analise_sentimentos', 'Análise de sentimentos não realizada ainda.')}
                """
                
                with st.spinner("Gerando relatório executivo..."):
                    relatorio = gerar_relatorio_gestao(dados_para_relatorio, client)
                
                if relatorio:
                    st.markdown(relatorio)
                    
                    # Gerar PDF
                    pdf_data = gerar_pdf_relatorio(relatorio, df)
                    
                    if pdf_data:
                        # Opção de download em PDF
                        st.download_button(
                            label="📥 Download Relatório PDF",
                            data=pdf_data,
                            file_name=f"relatorio_executivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf"
                        )
                    else:
                        # Fallback para TXT se PDF falhar
                        st.download_button(
                            label="📥 Download Relatório TXT",
                            data=relatorio,
                            file_name=f"relatorio_executivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain"
                        )
                else:
                    st.error("Erro ao gerar relatório executivo.")
    
    # Footer
    st.markdown("---")
    st.markdown("**Desenvolvido por:** Abimael Torcate de Souza | **Powered by:** Streamlit + LangChain + OpenAI")

if __name__ == "__main__":
    main()
