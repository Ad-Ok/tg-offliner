"""
API Blueprint для управления бэкапами базы данных.

Endpoints:
    GET    /api/backups              — Список бэкапов
    POST   /api/backups              — Создать бэкап
    POST   /api/backups/<name>/restore — Восстановить из бэкапа
    DELETE /api/backups/<name>       — Удалить бэкап
"""

from flask import Blueprint, jsonify, request
from models import db
from utils.backup import (
    create_backup,
    restore_backup,
    list_backups,
    delete_backup,
    rotate_backups
)

backup_bp = Blueprint('backup', __name__)


@backup_bp.route('/backups', methods=['GET'])
def get_backups():
    """Список всех бэкапов"""
    backups = list_backups()
    return jsonify({
        'backups': backups,
        'total': len(backups)
    })


@backup_bp.route('/backups', methods=['POST'])
def create_backup_endpoint():
    """Создать бэкап вручную"""
    data = request.get_json(silent=True) or {}
    label = data.get('label', 'manual')
    
    try:
        backup = create_backup(label=label)
        rotate_backups()
        return jsonify({
            'success': True,
            'backup': backup
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_bp.route('/backups/<name>/restore', methods=['POST'])
def restore_backup_endpoint(name):
    """Восстановить базу из бэкапа"""
    try:
        # Закрываем текущие соединения к БД
        db.engine.dispose()
        
        result = restore_backup(name)
        
        return jsonify(result)
    except FileNotFoundError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@backup_bp.route('/backups/<name>', methods=['DELETE'])
def delete_backup_endpoint(name):
    """Удалить бэкап"""
    try:
        delete_backup(name)
        return jsonify({
            'success': True,
            'message': f'Бэкап {name} удалён'
        })
    except FileNotFoundError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
