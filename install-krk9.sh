#!/bin/bash
# KRK-9 One-Click Installer
# Uso: curl -fsSL https://raw.githubusercontent.com/vaseksindelaru/lenguage-room/main/install-krk9.sh | bash
# O:  bash <(curl -fsSL https://raw.githubusercontent.com/vaseksindelaru/lenguage-room/main/install-krk9.sh)

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${GREEN}============================================================${NC}"
    echo -e "${GREEN}  KRK-9: English Practice Room — Installer${NC}"
    echo -e "${GREEN}============================================================${NC}\n"
}

print_step() {
    echo -e "\n${YELLOW}[$1/$2] $3${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Detectar SO
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Instalar dependencias según SO
install_deps() {
    local os=$1
    
    if [[ "$os" == "linux" ]]; then
        print_step "1/5" "Instalando dependencias (Linux)"
        
        # Detectar gestor de paquetes
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y git python3 python3-venv docker.io
        elif command -v yum &> /dev/null; then
            sudo yum install -y git python3 docker
        elif command -v pacman &> /dev/null; then
            sudo pacman -Syu --noconfirm git python docker
        else
            print_error "No se pudo identificar el gestor de paquetes. Instala manualmente: git, python3, docker"
            exit 1
        fi
        
        # Iniciar Docker
        sudo systemctl start docker || true
        sudo systemctl enable docker || true
        
    elif [[ "$os" == "macos" ]]; then
        print_step "1/5" "Instalando dependencias (macOS)"
        
        # Verificar Homebrew
        if ! command -v brew &> /dev/null; then
            echo "Instalando Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        
        brew install git python3 docker
        
    elif [[ "$os" == "windows" ]]; then
        print_error "Windows detectado. Por favor:"
        echo "  1. Instala Git: https://git-scm.com/download/win"
        echo "  2. Instala Python: https://www.python.org/downloads/"
        echo "  3. Instala Docker Desktop: https://www.docker.com/products/docker-desktop/"
        echo "  4. Luego ejecuta este script desde Git Bash"
        exit 1
    fi
}

# Clonar repo
clone_repo() {
    print_step "2/5" "Clonando repositorio"
    
    if [ -d "krk9" ]; then
        print_error "La carpeta 'krk9' ya existe. ¿Quieres actualizarla?"
        read -p "Eliminar y volver a clonar? (s/n): " confirm
        if [[ "$confirm" == "s" ]]; then
            rm -rf krk9
        else
            echo "Instalación cancelada."
            exit 1
        fi
    fi
    
    git clone https://github.com/vaseksindelaru/lenguage-room.git krk9
    cd krk9
    print_success "Repositorio clonado"
}

# Configurar .env
setup_env() {
    print_step "3/5" "Configuración inicial"
    
    if [ ! -f ".env" ]; then
        if [ -f "setup_wizard.py" ]; then
            python3 setup_wizard.py
        else
            print_error "No se encontró setup_wizard.py. Crea .env manualmente (copia .env.example)."
            exit 1
        fi
    else
        print_success ".env ya existe. Saltando configuración."
    fi
}

# Instalar Ollama (opcional)
setup_ollama() {
    print_step "4/5" "Configuración de Ollama (opcional)"
    
    read -p "¿Quieres instalar Ollama para uso sin internet? (s/n): " confirm
    if [[ "$confirm" == "s" ]]; then
        if ! command -v ollama &> /dev/null; then
            echo "Instalando Ollama..."
            curl -fsSL https://ollama.com/install.sh | sh
        fi
        
        echo "Descargando modelo qwen2.5:3b (puede tardar unos minutos)..."
        ollama pull qwen2.5:3b
        print_success "Ollama configurado"
    else
        print_success "Ollama no instalado. Usarás APIs externas."
    fi
}

# Iniciar aplicación
start_app() {
    print_step "5/5" "Iniciando KRK-9"
    
    if [ -f "start.sh" ]; then
        chmod +x start.sh
        ./start.sh
    else
        print_error "No se encontró start.sh. Ejecuta manualmente: python3 bot.py"
        exit 1
    fi
}

# Main
main() {
    print_header
    
    # Detectar SO
    local os=$(detect_os)
    echo -e "Sistema operativo detectado: ${YELLOW}$os${NC}"
    
    # Instalar dependencias
    if [[ "$os" != "windows" ]]; then
        install_deps "$os"
    else
        print_error "Por favor, instala las dependencias manualmente (ver arriba)."
        exit 1
    fi
    
    # Clonar repo
    clone_repo
    
    # Configurar .env
    setup_env
    
    # Ollama
    setup_ollama
    
    # Iniciar
    start_app
    
    print_header
    print_success "¡KRK-9 instalado y en funcionamiento!"
    echo -e "\nAbre tu navegador en: ${YELLOW}http://localhost:8081${NC}"
    echo -e "Únete al canal de Discord y empieza a practicar inglés.\n"
}

# Ejecutar
main
