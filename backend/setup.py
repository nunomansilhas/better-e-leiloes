#!/usr/bin/env python3
"""
Script de deploy e setup do E-Leiloes API Backend
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Executa comando e mostra output"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    print(f"$ {cmd}\n")
    
    result = subprocess.run(cmd, shell=True, capture_output=False)
    
    if result.returncode != 0:
        print(f"\n❌ Erro ao executar: {description}")
        sys.exit(1)
    
    print(f"\n✅ {description} - Concluído!")

def check_python_version():
    """Verifica versão Python"""
    version = sys.version_info
    print(f"🐍 Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("❌ Python 3.10+ é necessário!")
        sys.exit(1)

def create_venv():
    """Cria virtual environment"""
    if os.path.exists("venv"):
        print("📦 Virtual environment já existe, pulando...")
        return
    
    run_command(
        f"{sys.executable} -m venv venv",
        "Criar virtual environment"
    )

def get_pip_command():
    """Retorna comando pip correto dependendo do OS"""
    if sys.platform == "win32":
        return r"venv\Scripts\pip"
    else:
        return "venv/bin/pip"

def get_python_command():
    """Retorna comando python correto dependendo do OS"""
    if sys.platform == "win32":
        return r"venv\Scripts\python"
    else:
        return "venv/bin/python"

def install_dependencies():
    """Instala dependências do requirements.txt"""
    pip_cmd = get_pip_command()
    
    run_command(
        f"{pip_cmd} install --upgrade pip",
        "Atualizar pip"
    )
    
    run_command(
        f"{pip_cmd} install -r requirements.txt",
        "Instalar dependências"
    )

def install_playwright():
    """Instala browsers Playwright"""
    python_cmd = get_python_command()
    
    run_command(
        f"{python_cmd} -m playwright install chromium",
        "Instalar Playwright Chromium browser"
    )

def setup_env_file():
    """Cria .env a partir do .env.example se não existir"""
    if os.path.exists(".env"):
        print("\n📝 Arquivo .env já existe")
        return
    
    if not os.path.exists(".env.example"):
        print("\n⚠️ .env.example não encontrado!")
        return
    
    print("\n📝 Criar arquivo .env...")
    
    with open(".env.example", "r", encoding="utf-8") as f:
        content = f.read()
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ Arquivo .env criado a partir de .env.example")
    print("⚠️ ATENÇÃO: Edita o .env com as tuas configurações!")

def test_import():
    """Testa importação dos módulos principais"""
    print("\n" + "="*60)
    print("🧪 Testar importações...")
    print("="*60)
    
    python_cmd = get_python_command()
    
    test_script = """
import sys
try:
    import fastapi
    print(f"✅ FastAPI {fastapi.__version__}")
    
    import playwright
    print(f"✅ Playwright {playwright.__version__}")
    
    import sqlalchemy
    print(f"✅ SQLAlchemy {sqlalchemy.__version__}")
    
    import redis
    print(f"✅ Redis {redis.__version__}")
    
    import pydantic
    print(f"✅ Pydantic {pydantic.__version__}")
    
    print("\\n🎉 Todas as dependências instaladas corretamente!")
    
except ImportError as e:
    print(f"❌ Erro ao importar: {e}")
    sys.exit(1)
"""
    
    result = subprocess.run(
        [python_cmd, "-c", test_script],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    
    if result.returncode != 0:
        print(result.stderr)
        print("\n❌ Erro nos testes de importação!")
        sys.exit(1)

def show_next_steps():
    """Mostra próximos passos"""
    python_cmd = get_python_command()
    
    if sys.platform == "win32":
        activate_cmd = r"venv\Scripts\activate"
    else:
        activate_cmd = "source venv/bin/activate"
    
    print("\n" + "="*60)
    print("✨ Setup concluído com sucesso!")
    print("="*60)
    
    print("\n📋 Próximos passos:\n")
    print(f"1. Ativa o virtual environment:")
    print(f"   {activate_cmd}\n")
    print(f"2. (Opcional) Edita o arquivo .env:\n")
    print(f"3. Inicia o servidor:")
    print(f"   {python_cmd} main.py\n")
    print(f"4. Acede à API:")
    print(f"   http://localhost:8000")
    print(f"   http://localhost:8000/docs (Swagger UI)\n")
    print("="*60)

def main():
    """Main setup"""
    print("="*60)
    print("🚀 E-Leiloes API Backend - Setup")
    print("="*60)
    
    # Verifica se está no diretório correto
    if not os.path.exists("requirements.txt"):
        print("❌ requirements.txt não encontrado!")
        print("Execute este script no diretório 'backend'")
        sys.exit(1)
    
    # Verifica versão Python
    check_python_version()
    
    # Cria virtual environment
    create_venv()
    
    # Instala dependências
    install_dependencies()
    
    # Instala Playwright
    install_playwright()
    
    # Setup .env
    setup_env_file()
    
    # Testa importações
    test_import()
    
    # Mostra próximos passos
    show_next_steps()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Setup cancelado pelo utilizador")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro inesperado: {e}")
        sys.exit(1)
