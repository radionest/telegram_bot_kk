#!/bin/bash

# Установочный скрипт для Telegram бота
# Требования: Ubuntu/Debian, запуск от root

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Конфигурация
BOT_USER="telegram-bot-kk"
BOT_HOME="/home/$BOT_USER"
BOT_DIR="$BOT_HOME/telegram_bot_kk"
GITHUB_REPO="git@github.com:radionest/telegram_bot_kk.git"
SERVICE_NAME="telegram-bot-kk"
PYTHON_VERSION="3.12"

# Функция для вывода сообщений
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Проверка, что скрипт запущен от root
if [[ $EUID -ne 0 ]]; then
   error "Этот скрипт должен быть запущен от root"
fi

log "Начинаем установку Telegram бота..."

# Обновление системы
log "Обновление системы..."
apt-get update
apt-get upgrade -y

# Установка необходимых пакетов
log "Установка системных пакетов..."
apt-get install -y \
    build-essential \
    curl \
    git \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    wget \
    llvm \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libffi-dev \
    liblzma-dev \
    python3-openssl

# Создание пользователя для бота
if id "$BOT_USER" &>/dev/null; then
    warning "Пользователь $BOT_USER уже существует"
else
    log "Создание пользователя $BOT_USER..."
    useradd -m -s /bin/bash "$BOT_USER"
fi

# Установка Python через pyenv для пользователя бота
log "Установка pyenv и Python $PYTHON_VERSION для пользователя $BOT_USER..."
sudo -u "$BOT_USER" bash << 'EOF'
cd ~

# Установка pyenv
if [ ! -d "$HOME/.pyenv" ]; then
    curl https://pyenv.run | bash
fi

# Настройка pyenv
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc

# Активация pyenv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# Установка Python
pyenv install -s 3.12
pyenv global 3.12
EOF

# Клонирование репозитория
log "Клонирование репозитория..."
if [ -d "$BOT_DIR" ]; then
    warning "Директория $BOT_DIR уже существует. Обновляем код..."
    sudo -u "$BOT_USER" bash -c "cd $BOT_DIR && git pull"
else
    sudo -u "$BOT_USER" bash -c "cd $BOT_HOME && git clone $GITHUB_REPO telegram_bot_kk"
fi

# Создание виртуального окружения и установка зависимостей
log "Создание виртуального окружения и установка зависимостей..."
sudo -u "$BOT_USER" bash << EOF
cd $BOT_DIR
source ~/.bashrc

# Создание виртуального окружения
~/.pyenv/versions/$PYTHON_VERSION/bin/python -m venv venv

# Активация виртуального окружения
source venv/bin/activate

# Обновление pip
pip install --upgrade pip

# Установка зависимостей
if [ -f "pyproject.toml" ]; then
    pip install -e .
else
    error "Не найден файл pyproject.toml"
fi
EOF

# Создание файла с переменными окружения
log "Создание файла окружения..."
if [ ! -f "$BOT_DIR/.env" ]; then
    cat > "$BOT_DIR/.env" << EOL
# Telegram Bot Configuration
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
TG_API_ID=YOUR_API_ID_HERE
TG_API_HASH=YOUR_API_HASH_HERE
EOL
    chown "$BOT_USER:$BOT_USER" "$BOT_DIR/.env"
    chmod 600 "$BOT_DIR/.env"
    warning "Создан файл .env. Обязательно отредактируйте его и добавьте ваши API ключи!"
fi

# Создание systemd сервиса
log "Создание systemd сервиса..."
cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOL
[Unit]
Description=Telegram Bot KK Service
After=network.target

[Service]
Type=simple
User=$BOT_USER
Group=$BOT_USER
WorkingDirectory=$BOT_DIR
Environment="PATH=$BOT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$BOT_DIR/venv/bin/python -m src.main
Restart=always
RestartSec=10

# Логирование
StandardOutput=journal
StandardError=journal

# Безопасность
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$BOT_DIR

[Install]
WantedBy=multi-user.target
EOL

# Перезагрузка systemd
log "Перезагрузка systemd..."
systemctl daemon-reload

# Создание скрипта для управления ботом
log "Создание скрипта управления..."
cat > "/usr/local/bin/$SERVICE_NAME" << 'EOL'
#!/bin/bash

SERVICE="telegram-bot-kk"

case "$1" in
    start)
        echo "Запуск $SERVICE..."
        systemctl start $SERVICE
        ;;
    stop)
        echo "Остановка $SERVICE..."
        systemctl stop $SERVICE
        ;;
    restart)
        echo "Перезапуск $SERVICE..."
        systemctl restart $SERVICE
        ;;
    status)
        systemctl status $SERVICE
        ;;
    logs)
        journalctl -u $SERVICE -f
        ;;
    enable)
        echo "Включение автозапуска $SERVICE..."
        systemctl enable $SERVICE
        ;;
    disable)
        echo "Отключение автозапуска $SERVICE..."
        systemctl disable $SERVICE
        ;;
    update)
        echo "Обновление $SERVICE..."
        systemctl stop $SERVICE
        cd /home/telegram-bot-kk/telegram_bot_kk
        sudo -u telegram-bot-kk git pull
        sudo -u telegram-bot-kk bash -c "source venv/bin/activate && pip install -e ."
        systemctl start $SERVICE
        echo "Обновление завершено!"
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs|enable|disable|update}"
        exit 1
        ;;
esac
EOL

chmod +x "/usr/local/bin/$SERVICE_NAME"

log "Установка завершена!"
echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Установка Telegram бота завершена!${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo "Дальнейшие шаги:"
echo "1. Отредактируйте файл $BOT_DIR/.env и добавьте ваши API ключи"
echo "2. Запустите бота: $SERVICE_NAME start"
echo "3. Включите автозапуск: $SERVICE_NAME enable"
echo "4. Просмотр логов: $SERVICE_NAME logs"
echo
echo "Управление ботом:"
echo "  - Запуск: $SERVICE_NAME start"
echo "  - Остановка: $SERVICE_NAME stop"
echo "  - Перезапуск: $SERVICE_NAME restart"
echo "  - Статус: $SERVICE_NAME status"
echo "  - Логи: $SERVICE_NAME logs"
echo "  - Обновление: $SERVICE_NAME update"
echo
warning "Не забудьте изменить GITHUB_REPO в этом скрипте на ваш репозиторий!"