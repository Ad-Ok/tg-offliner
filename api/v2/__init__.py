"""
API v2 - Унифицированные endpoints

Принципы:
1. Один endpoint для получения постов канала
2. Все связанные данные (layouts, hidden states) включены в ответ
3. Чёткий приоритет параметров: URL > Saved > Default
4. Единая сериализация через serializers.py
"""

from flask import Blueprint

# Создаём blueprint с префиксом /api/v2
api_v2_bp = Blueprint('api_v2', __name__, url_prefix='/api/v2')

# Импортируем routes после создания blueprint чтобы избежать circular imports
from . import channels
from . import posts
from . import layouts
